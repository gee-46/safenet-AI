"""
SafeNet AI – Citizen Shield & Evidence Package Routes
/api/v1/citizen/...
/api/v1/reports/...
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import get_settings
from backend.db.models import AuditLog, FraudCase, ScamReport, get_db
from backend.schemas.schemas import (
    CitizenAssessIn, CitizenAssessResponse,
    EvidencePackageRequest, EvidencePackageResponse,
)
from backend.services.citizen_shield import get_citizen_shield
from backend.services.evidence_generator import get_evidence_generator

citizen_router = APIRouter(prefix="/citizen", tags=["Citizen Shield"])
evidence_router = APIRouter(prefix="/reports", tags=["Evidence Packages"])
settings = get_settings()


# ── CitizenShield Endpoints ───────────────────────────────────────

@citizen_router.post(
    "/assess",
    response_model=CitizenAssessResponse,
    summary="Assess a suspicious call or message for fraud risk",
    description="""
    Describe the suspicious call/message/situation in any Indian language.
    Returns a fraud risk verdict with recommended actions in the same language.

    Supported languages: en, hi, ta, te, kn, ml, mr, gu, bn, pa, or, as
    Context types: call | sms | payment | job_offer | other
    """,
)
async def assess_citizen_situation(
    request_body: CitizenAssessIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    service = get_citizen_shield()
    result = await service.assess(
        message=request_body.message,
        language=request_body.language,
        phone_number=request_body.phone_number,
        context_type=request_body.context_type,
    )

    # Audit high-risk assessments
    if result["risk_level"] in ("scam", "high_risk"):
        db.add(AuditLog(
            action="citizen_assess_high_risk",
            entity_type="citizen_query",
            actor_id=str(request.client.host) if request.client else "api",
            model_name="CitizenShieldService",
            model_version="1.0.0",
            output={"risk_level": result["risk_level"], "confidence": result["confidence"]},
            confidence=result["confidence"],
            latency_ms=result.get("processing_time_ms", 0),
            ip_address=str(request.client.host) if request.client else None,
        ))

    return CitizenAssessResponse(
        risk_level=result["risk_level"],
        confidence=result["confidence"],
        explanation=result["explanation"],
        recommended_actions=result["recommended_actions"],
        report_url=result.get("report_url"),
        helpline_number=result["helpline_number"],
        response_language=result["response_language"],
    )


@citizen_router.post(
    "/whatsapp-webhook",
    summary="WhatsApp Business API webhook handler",
    description="""
    Receives incoming WhatsApp messages and returns fraud assessment.
    Designed for integration with Twilio WhatsApp Business API.
    Returns TwiML-compatible response.
    """,
    include_in_schema=True,
)
async def whatsapp_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Handle incoming WhatsApp messages from Twilio webhook."""
    form_data = await request.form()
    incoming_msg = str(form_data.get("Body", "")).strip()
    from_number = str(form_data.get("From", ""))

    if not incoming_msg:
        return Response(
            content='<?xml version="1.0"?><Response><Message>Please describe the suspicious call or message.</Message></Response>',
            media_type="application/xml",
        )

    # Assess the message
    service = get_citizen_shield()
    result = await service.assess(
        message=incoming_msg,
        phone_number=from_number.replace("whatsapp:", ""),
        context_type="call",
    )

    # Build WhatsApp response
    risk = result["risk_level"]
    explanation = result["explanation"]
    actions = "\n".join(f"• {a}" for a in result["recommended_actions"][:3])

    if risk in ("scam", "high_risk"):
        icon = "🚨"
        header = "FRAUD ALERT"
    elif risk == "suspicious":
        icon = "⚠️"
        header = "SUSPICIOUS"
    else:
        icon = "✅"
        header = "APPEARS SAFE"

    msg = (
        f"{icon} *SafeNet AI — {header}*\n\n"
        f"{explanation}\n\n"
        f"*What to do:*\n{actions}\n\n"
        f"📞 Cybercrime Helpline: *1930*\n"
        f"🌐 Report: cybercrime.gov.in"
    )

    twiml = f'<?xml version="1.0"?><Response><Message>{msg}</Message></Response>'
    return Response(content=twiml, media_type="application/xml")


@citizen_router.get(
    "/scam-types",
    summary="Get list of known scam types with descriptions",
)
async def get_scam_types():
    return {
        "scam_types": [
            {
                "type": "digital_arrest",
                "name": "Digital Arrest",
                "description": "Fraudsters impersonate CBI/ED/Police and threaten victims with arrest via video call.",
                "red_flags": ["Govt agency calling on WhatsApp", "Threatened with arrest", "Asked to stay on call", "Told not to tell family"],
                "what_to_do": "Hang up. Govt agencies NEVER arrest via phone. Call 1930.",
            },
            {
                "type": "kyc_update",
                "name": "KYC / OTP Fraud",
                "description": "Callers pretend to be bank or telecom staff and ask for OTP to 'update KYC'.",
                "red_flags": ["Asking for OTP", "Urgent KYC expiry warning", "Aadhaar linking request"],
                "what_to_do": "NEVER share OTP. Your bank will NEVER ask for it over phone.",
            },
            {
                "type": "investment",
                "name": "Investment Fraud",
                "description": "Fake brokers promise guaranteed high returns on stocks, crypto, or 'special schemes'.",
                "red_flags": ["Guaranteed returns", "Limited time offer", "WhatsApp/Telegram investment group"],
                "what_to_do": "No investment guarantees returns. Verify with SEBI at 1800-266-7575.",
            },
            {
                "type": "loan_fraud",
                "name": "Loan Fraud",
                "description": "Fake lenders offer pre-approved loans but ask for advance processing fees.",
                "red_flags": ["Processing fee before disbursement", "No documentation needed", "Instant approval"],
                "what_to_do": "Legitimate lenders never charge upfront fees. Contact RBI at 14448.",
            },
            {
                "type": "lottery",
                "name": "Lottery / Prize Scam",
                "description": "Victims told they won a prize or lottery they never entered.",
                "red_flags": ["Unsolicited prize notification", "Must pay tax/fee to claim", "Urgency to claim"],
                "what_to_do": "You cannot win a lottery you didn't enter. Ignore and report.",
            },
        ]
    }


@citizen_router.get(
    "/helplines",
    summary="Emergency helplines and reporting portals",
)
async def get_helplines():
    return {
        "helplines": [
            {"name": "National Cybercrime Helpline", "number": "1930", "available": "24x7"},
            {"name": "RBI Banking Ombudsman", "number": "14448", "available": "9AM-5PM"},
            {"name": "SEBI Investor Helpline", "number": "1800-266-7575", "available": "9AM-6PM"},
            {"name": "Women Helpline", "number": "1091", "available": "24x7"},
            {"name": "Senior Citizen Helpline", "number": "14567", "available": "8AM-8PM"},
        ],
        "portals": [
            {"name": "Cybercrime Complaint Portal", "url": "https://cybercrime.gov.in"},
            {"name": "Sanchar Saathi (SIM block)", "url": "https://sancharsaathi.gov.in"},
            {"name": "NCRB e-FIR", "url": "https://digitalpolice.gov.in"},
        ],
    }


# ── Evidence Package Endpoints ────────────────────────────────────

@evidence_router.post(
    "/generate",
    response_model=EvidencePackageResponse,
    summary="Generate court-admissible evidence package PDF",
    description="""
    Generates a comprehensive PDF evidence package for a fraud case or set of scam reports.
    Includes: incident timeline, fraud network summary, regulatory citations, audit trail.

    The generated PDF is suitable for submission alongside an FIR.
    """,
    status_code=status.HTTP_201_CREATED,
)
async def generate_evidence_package(
    req: EvidencePackageRequest,
    db: AsyncSession = Depends(get_db),
):
    generator = get_evidence_generator()

    # Fetch case
    case_summary = {}
    if req.case_id:
        case_result = await db.execute(
            select(FraudCase).where(FraudCase.id == req.case_id)
        )
        case = case_result.scalar_one_or_none()
        if case:
            case_summary = {
                "fraud_type": case.fraud_type,
                "severity": case.severity,
                "estimated_victims": case.estimated_victims,
                "estimated_loss_inr": case.estimated_loss_inr,
                "states_involved": case.states_involved or [],
                "status": case.status,
                "description": f"Investigation case for {case.fraud_type} fraud network.",
                "avg_confidence": 0.87,
            }

    # Fetch scam reports
    scam_reports_data = []
    if req.scam_report_ids:
        for rid in req.scam_report_ids:
            r_result = await db.execute(select(ScamReport).where(ScamReport.id == rid))
            r = r_result.scalar_one_or_none()
            if r:
                scam_reports_data.append({
                    "id": str(r.id),
                    "caller_number": r.caller_number,
                    "scam_type": r.scam_type,
                    "confidence_score": r.confidence_score,
                    "city": r.city,
                    "state": r.state,
                    "created_at": r.created_at,
                })
    elif req.case_id and case_summary:
        # Auto-fetch reports linked to the case
        linked = await db.execute(
            select(ScamReport)
            .join(ScamReport.linked_cases)
            .where(FraudCase.id == req.case_id)
            .limit(50)
        )
        for r in linked.scalars().all():
            scam_reports_data.append({
                "id": str(r.id),
                "caller_number": r.caller_number,
                "scam_type": r.scam_type,
                "confidence_score": r.confidence_score,
                "city": r.city,
                "state": r.state,
                "created_at": r.created_at,
            })

    if not case_summary:
        case_summary = {
            "fraud_type": "digital_arrest",
            "severity": "HIGH",
            "estimated_victims": len(scam_reports_data),
            "estimated_loss_inr": 0,
            "states_involved": list({r.get("state") for r in scam_reports_data if r.get("state")}),
            "status": "Under Investigation",
            "description": "AI-generated evidence package based on submitted scam reports.",
            "avg_confidence": (
                sum(r.get("confidence_score", 0) for r in scam_reports_data) / max(len(scam_reports_data), 1)
            ),
        }

    case_number = (
        case.case_number if req.case_id and case_summary.get("fraud_type") else
        f"SN-{datetime.utcnow().year}-{uuid.uuid4().hex[:6].upper()}"
    )

    package_id, pdf_bytes = generator.generate_and_store(
        case_number=case_number,
        scam_reports=scam_reports_data,
        fraud_graph=None,  # Could pass from fraud graph query
        case_summary=case_summary,
        include_regulatory=req.include_regulatory_sections,
    )

    # Determine legal sections
    fraud_type = case_summary.get("fraud_type", "default")
    from backend.services.evidence_generator import CRPC_SECTIONS, IT_ACT_SECTIONS
    crpc = CRPC_SECTIONS.get(fraud_type, CRPC_SECTIONS["default"])
    it_act = IT_ACT_SECTIONS.get(fraud_type, IT_ACT_SECTIONS["default"])

    return EvidencePackageResponse(
        package_id=uuid.UUID(package_id),
        case_number=case_number,
        pdf_url=f"/api/v1/reports/download/{package_id}",
        generated_at=datetime.utcnow(),
        pages=max(3, 2 + len(scam_reports_data) // 15),
        crpc_sections=crpc,
        it_act_sections=it_act,
    )


@evidence_router.get(
    "/download/{package_id}",
    summary="Download a generated evidence package PDF",
    responses={
        200: {"content": {"application/pdf": {}}, "description": "PDF file"},
        404: {"description": "Package not found"},
    },
)
async def download_evidence_package(package_id: str):
    generator = get_evidence_generator()
    pdf_bytes = generator.get_package(package_id)
    if not pdf_bytes:
        raise HTTPException(status_code=404, detail="Evidence package not found or expired")

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="safenet-evidence-{package_id[:8]}.pdf"',
            "Content-Length": str(len(pdf_bytes)),
            "X-Frame-Options": "DENY",
        },
    )


@evidence_router.get(
    "/audit-trail",
    summary="Query audit log for AI decisions",
    description="Full audit trail of all AI decisions. Required for legal admissibility.",
)
async def get_audit_trail(
    action: Optional[str] = Query(None),
    entity_type: Optional[str] = Query(None),
    entity_id: Optional[str] = Query(None),
    days_back: int = Query(7, ge=1, le=90),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import and_
    cutoff = datetime.utcnow() - __import__("datetime").timedelta(days=days_back)

    conditions = [AuditLog.timestamp >= cutoff]
    if action:
        conditions.append(AuditLog.action == action)
    if entity_type:
        conditions.append(AuditLog.entity_type == entity_type)
    if entity_id:
        conditions.append(AuditLog.entity_id == entity_id)

    query = (
        select(AuditLog)
        .where(and_(*conditions))
        .order_by(AuditLog.timestamp.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    logs = result.scalars().all()

    return {
        "page": page,
        "page_size": page_size,
        "logs": [
            {
                "id": str(log.id),
                "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                "action": log.action,
                "entity_type": log.entity_type,
                "entity_id": log.entity_id,
                "model_name": log.model_name,
                "model_version": log.model_version,
                "confidence": log.confidence,
                "latency_ms": log.latency_ms,
                "input_hash": log.input_hash,
                "output": log.output,
            }
            for log in logs
        ],
    }
