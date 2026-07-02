"""
SafeNet AI – Counterfeit Detection Routes
/api/v1/currency/...
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import get_settings
from backend.db.models import AuditLog, CounterfeitReport, get_db
from backend.models.counterfeit.detector import get_counterfeit_detector
from backend.schemas.schemas import CounterfeitAnalysisResponse

router = APIRouter(prefix="/currency", tags=["Counterfeit Detection"])
settings = get_settings()

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


@router.post(
    "/verify",
    response_model=CounterfeitAnalysisResponse,
    summary="Detect counterfeit currency from an image",
    description="""
    Upload an image of a currency note for counterfeit analysis.

    Analyses: watermark, security thread, microprint, colour-shift ink,
    serial number format, and perceptual hash cross-reference.

    Supported denominations: ₹100, ₹200, ₹500, ₹2000.
    Max image size: 10 MB. Formats: JPEG, PNG, WebP.
    """,
    status_code=status.HTTP_200_OK,
)
async def verify_currency(
    request: Request,
    image: UploadFile = File(..., description="Currency note image"),
    denomination: int = Form(500, description="Note denomination (100/200/500/2000)"),
    location_lat: Optional[float] = Form(None),
    location_lng: Optional[float] = Form(None),
    city: Optional[str] = Form(None),
    state: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    # ── Validation ───────────────────────────────────────────────
    if image.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported image type: {image.content_type}. Use JPEG, PNG, or WebP.",
        )

    if denomination not in (100, 200, 500, 2000):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Denomination must be one of: 100, 200, 500, 2000",
        )

    image_bytes = await image.read()
    if len(image_bytes) > MAX_IMAGE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Image must be smaller than 10 MB",
        )
    if len(image_bytes) < 1000:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Image too small — please upload a clear photo of the note",
        )

    # ── Detection ────────────────────────────────────────────────
    detector = get_counterfeit_detector(settings.counterfeit_model_path)
    result = detector.analyse(image_bytes, denomination)

    # ── Persist ──────────────────────────────────────────────────
    report_id = uuid.uuid4()
    report = CounterfeitReport(
        id=report_id,
        denomination=denomination,
        confidence_score=result["confidence_score"],
        verdict=result["verdict"],
        defects_detected=result["defects_detected"],
        serial_number_valid=result.get("serial_number_valid"),
        microprint_score=result["security_checks"].get("microprint"),
        security_thread_score=result["security_checks"].get("security_thread"),
        watermark_score=result["security_checks"].get("watermark"),
        image_hash=result["image_hash"],
        location_lat=location_lat,
        location_lng=location_lng,
        city=city,
        state=state,
        reported_to_rbi=result["verdict"] == "counterfeit",
    )
    db.add(report)

    # Audit log
    db.add(AuditLog(
        action="counterfeit_verify",
        entity_type="counterfeit_report",
        entity_id=str(report_id),
        actor_id=str(request.client.host) if request.client else "api",
        model_name="CounterfeitDetector",
        model_version="1.0.0",
        input_hash=result["image_hash"],
        output={"verdict": result["verdict"], "confidence": result["confidence_score"]},
        confidence=result["confidence_score"],
        latency_ms=result.get("processing_time_ms", 0),
        ip_address=str(request.client.host) if request.client else None,
    ))

    await db.flush()

    return CounterfeitAnalysisResponse(
        report_id=report_id,
        denomination=denomination,
        verdict=result["verdict"],
        confidence_score=result["confidence_score"],
        defects_detected=result["defects_detected"],
        security_checks=result["security_checks"],
        serial_number_valid=result.get("serial_number_valid"),
        serial_number_pattern=result.get("serial_number_pattern"),
        recommendation=result["recommendation"],
        reported_to_rbi=result["verdict"] == "counterfeit",
        processing_time_ms=result.get("processing_time_ms", 0),
    )


@router.get(
    "/reports",
    summary="List counterfeit reports with filtering",
)
async def list_counterfeit_reports(
    verdict: Optional[str] = Query(None, pattern="^(genuine|counterfeit|uncertain)$"),
    denomination: Optional[int] = Query(None),
    state: Optional[str] = Query(None),
    days_back: int = Query(30, ge=1, le=365),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import and_
    cutoff = datetime.utcnow() - timedelta(days=days_back)
    conditions = [CounterfeitReport.created_at >= cutoff]

    if verdict:
        conditions.append(CounterfeitReport.verdict == verdict)
    if denomination:
        conditions.append(CounterfeitReport.denomination == denomination)
    if state:
        conditions.append(CounterfeitReport.state == state)

    query = (
        select(CounterfeitReport)
        .where(and_(*conditions))
        .order_by(CounterfeitReport.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    reports = result.scalars().all()

    return [
        {
            "id": str(r.id),
            "denomination": r.denomination,
            "verdict": r.verdict,
            "confidence_score": r.confidence_score,
            "city": r.city,
            "state": r.state,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in reports
    ]


@router.get(
    "/stats",
    summary="Counterfeit detection statistics",
)
async def counterfeit_stats(
    days_back: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    cutoff = datetime.utcnow() - timedelta(days=days_back)

    total_q = await db.execute(
        select(func.count(CounterfeitReport.id)).where(CounterfeitReport.created_at >= cutoff)
    )
    total = total_q.scalar() or 0

    counterfeit_q = await db.execute(
        select(func.count(CounterfeitReport.id)).where(
            CounterfeitReport.created_at >= cutoff,
            CounterfeitReport.verdict == "counterfeit",
        )
    )
    confirmed_counterfeit = counterfeit_q.scalar() or 0

    # By denomination
    denom_q = await db.execute(
        select(CounterfeitReport.denomination, func.count(CounterfeitReport.id).label("count"))
        .where(CounterfeitReport.created_at >= cutoff)
        .group_by(CounterfeitReport.denomination)
        .order_by(func.count(CounterfeitReport.id).desc())
    )
    by_denomination = [{"denomination": row[0], "count": row[1]} for row in denom_q]

    # By state
    state_q = await db.execute(
        select(CounterfeitReport.state, func.count(CounterfeitReport.id).label("count"))
        .where(CounterfeitReport.created_at >= cutoff, CounterfeitReport.state.isnot(None))
        .group_by(CounterfeitReport.state)
        .order_by(func.count(CounterfeitReport.id).desc())
        .limit(10)
    )
    by_state = [{"state": row[0], "count": row[1]} for row in state_q]

    # Average confidence
    avg_q = await db.execute(
        select(func.avg(CounterfeitReport.confidence_score))
        .where(CounterfeitReport.created_at >= cutoff)
    )
    avg_conf = round(float(avg_q.scalar() or 0), 4)

    return {
        "period_days": days_back,
        "total_scanned": total,
        "confirmed_counterfeit": confirmed_counterfeit,
        "detection_rate": round(confirmed_counterfeit / total, 4) if total > 0 else 0,
        "avg_confidence": avg_conf,
        "by_denomination": by_denomination,
        "by_state": by_state,
    }


@router.get(
    "/reports/{report_id}",
    summary="Get a specific counterfeit report",
)
async def get_counterfeit_report(report_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(CounterfeitReport).where(CounterfeitReport.id == report_id)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return {
        "id": str(report.id),
        "denomination": report.denomination,
        "verdict": report.verdict,
        "confidence_score": report.confidence_score,
        "defects_detected": report.defects_detected,
        "serial_number_valid": report.serial_number_valid,
        "security_checks": {
            "microprint": report.microprint_score,
            "security_thread": report.security_thread_score,
            "watermark": report.watermark_score,
        },
        "city": report.city,
        "state": report.state,
        "reported_to_rbi": report.reported_to_rbi,
        "created_at": report.created_at.isoformat() if report.created_at else None,
    }
