"""
SafeNet AI – Scam Detection Routes
/api/v1/calls/...
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from backend.core.config import get_settings
from backend.db.models import ScamReport, get_db, AuditLog
from backend.models.scam.classifier import get_scam_classifier
from backend.schemas.schemas import (
    CallMetadataIn, ScamDetectionResponse, ScamReportOut, PaginationParams
)
from backend.services.alert_service import send_alert

router = APIRouter(prefix="/calls", tags=["Scam Detection"])
settings = get_settings()


@router.post(
    "/analyze",
    response_model=ScamDetectionResponse,
    summary="Analyse call metadata for scam patterns",
    description="""
    Main scam detection endpoint. Accepts call metadata (NOT raw audio) and
    returns a scam risk verdict with confidence score and recommended action.

    Privacy-by-design: only metadata + optional transcript snippet (max 500 chars).
    Full audio is never stored or transmitted.
    """,
    status_code=status.HTTP_200_OK,
)
async def analyze_call(
    call_data: CallMetadataIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    classifier = get_scam_classifier(settings.scam_model_path)

    # Run classification
    result = classifier.classify(call_data.model_dump())

    # Persist report
    report_id = uuid.uuid4()
    report = ScamReport(
        id=report_id,
        caller_number=call_data.caller_number,
        victim_number=call_data.victim_number,
        scam_type=result["scam_type"],
        confidence_score=result["confidence_score"],
        status="pending" if not result["is_scam"] else "confirmed",
        call_duration_seconds=call_data.call_duration_seconds,
        call_metadata=call_data.model_dump(exclude={"transcript_snippet", "location"}),
        transcript_snippet=call_data.transcript_snippet,
        script_patterns_matched=result["patterns_matched"],
        location_lat=call_data.location.lat if call_data.location else None,
        location_lng=call_data.location.lng if call_data.location else None,
    )
    db.add(report)

    # Write audit log
    audit = AuditLog(
        action="scam_call_analyze",
        entity_type="scam_report",
        entity_id=str(report_id),
        actor_id=str(request.client.host) if request.client else "api",
        model_name="ScamCallClassifier",
        model_version="1.0.0",
        input_hash=result.get("input_hash", ""),
        output={
            "scam_type": result["scam_type"],
            "confidence_score": result["confidence_score"],
            "is_scam": result["is_scam"],
        },
        confidence=result["confidence_score"],
        latency_ms=result.get("processing_time_ms", 0),
        ip_address=str(request.client.host) if request.client else None,
    )
    db.add(audit)
    await db.flush()

    # Send real-time alert if scam detected above threshold
    alert_sent = False
    if result["is_scam"] and result["confidence_score"] >= settings.scam_confidence_threshold:
        alert_sent = await send_alert(
            phone_number=call_data.victim_number,
            alert_type="scam_call",
            scam_type=result["scam_type"],
            confidence=result["confidence_score"],
            recommended_action=result["recommended_action"],
            db=db,
        )

    return ScamDetectionResponse(
        report_id=report_id,
        caller_number=call_data.caller_number,
        victim_number=call_data.victim_number,
        scam_type=result["scam_type"],
        confidence_score=result["confidence_score"],
        is_scam=result["is_scam"],
        risk_level=result["risk_level"],
        patterns_matched=result["patterns_matched"],
        recommended_action=result["recommended_action"],
        alert_sent=alert_sent,
        processing_time_ms=result.get("processing_time_ms", 0),
    )


@router.get(
    "/reports",
    response_model=List[ScamReportOut],
    summary="List scam reports with filtering",
)
async def list_reports(
    scam_type: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    min_confidence: float = Query(0.0, ge=0, le=1),
    status: Optional[str] = Query(None),
    days_back: int = Query(30, ge=1, le=365),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    from datetime import timedelta
    from sqlalchemy import and_

    cutoff = datetime.utcnow() - timedelta(days=days_back)
    conditions = [ScamReport.created_at >= cutoff]

    if scam_type:
        conditions.append(ScamReport.scam_type == scam_type)
    if state:
        conditions.append(ScamReport.state == state)
    if min_confidence:
        conditions.append(ScamReport.confidence_score >= min_confidence)
    if status:
        conditions.append(ScamReport.status == status)

    query = (
        select(ScamReport)
        .where(and_(*conditions))
        .order_by(ScamReport.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    reports = result.scalars().all()
    return [ScamReportOut.model_validate(r) for r in reports]


@router.get(
    "/reports/{report_id}",
    response_model=ScamReportOut,
    summary="Get a specific scam report",
)
async def get_report(report_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ScamReport).where(ScamReport.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return ScamReportOut.model_validate(report)


@router.patch(
    "/reports/{report_id}/status",
    summary="Update report status (officer use)",
)
async def update_report_status(
    report_id: uuid.UUID,
    new_status: str = Query(..., pattern="^(pending|confirmed|false_positive|escalated)$"),
    officer_notes: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ScamReport).where(ScamReport.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    report.status = new_status
    if officer_notes:
        meta = report.call_metadata or {}
        meta["officer_notes"] = officer_notes
        report.call_metadata = meta

    return {"report_id": str(report_id), "new_status": new_status, "updated": True}


@router.get(
    "/stats",
    summary="Aggregate scam detection statistics",
)
async def get_stats(
    days_back: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    from datetime import timedelta
    cutoff = datetime.utcnow() - timedelta(days=days_back)

    total_q = await db.execute(
        select(func.count(ScamReport.id)).where(ScamReport.created_at >= cutoff)
    )
    total = total_q.scalar() or 0

    confirmed_q = await db.execute(
        select(func.count(ScamReport.id)).where(
            ScamReport.created_at >= cutoff,
            ScamReport.status == "confirmed",
        )
    )
    confirmed = confirmed_q.scalar() or 0

    # Type breakdown
    type_q = await db.execute(
        select(ScamReport.scam_type, func.count(ScamReport.id).label("count"))
        .where(ScamReport.created_at >= cutoff)
        .group_by(ScamReport.scam_type)
        .order_by(func.count(ScamReport.id).desc())
        .limit(8)
    )
    type_breakdown = [{"type": row[0], "count": row[1]} for row in type_q]

    # State breakdown
    state_q = await db.execute(
        select(ScamReport.state, func.count(ScamReport.id).label("count"))
        .where(ScamReport.created_at >= cutoff, ScamReport.state.isnot(None))
        .group_by(ScamReport.state)
        .order_by(func.count(ScamReport.id).desc())
        .limit(10)
    )
    state_breakdown = [{"state": row[0], "count": row[1]} for row in state_q]

    # Avg confidence
    conf_q = await db.execute(
        select(func.avg(ScamReport.confidence_score)).where(ScamReport.created_at >= cutoff)
    )
    avg_confidence = round(float(conf_q.scalar() or 0), 4)

    return {
        "period_days": days_back,
        "total_analyzed": total,
        "confirmed_scams": confirmed,
        "false_positives": total - confirmed if total > confirmed else 0,
        "detection_rate": round(confirmed / total, 4) if total > 0 else 0,
        "avg_confidence": avg_confidence,
        "by_type": type_breakdown,
        "by_state": state_breakdown,
    }
