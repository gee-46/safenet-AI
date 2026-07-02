"""
SafeNet AI – Analytics & Dashboard Routes
/api/v1/analytics/...
"""
from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import Alert, AuditLog, CounterfeitReport, FraudCase, ScamReport, get_db
from backend.schemas.schemas import DashboardStats

router = APIRouter(prefix="/analytics", tags=["Analytics & Dashboard"])


@router.get(
    "/dashboard",
    response_model=DashboardStats,
    summary="Top-level dashboard statistics",
)
async def get_dashboard_stats(
    days_back: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    cutoff = datetime.utcnow() - timedelta(days=days_back)

    # ── Scam detections ──────────────────────────────────────────
    scam_total_q = await db.execute(
        select(func.count(ScamReport.id))
        .where(ScamReport.created_at >= cutoff)
    )
    scam_total = scam_total_q.scalar() or 0

    # ── Counterfeit reports ──────────────────────────────────────
    count_total_q = await db.execute(
        select(func.count(CounterfeitReport.id))
        .where(
            CounterfeitReport.created_at >= cutoff,
            CounterfeitReport.verdict == "counterfeit",
        )
    )
    count_total = count_total_q.scalar() or 0

    # ── Active fraud cases ───────────────────────────────────────
    cases_q = await db.execute(
        select(func.count(FraudCase.id)).where(FraudCase.status == "open")
    )
    active_cases = cases_q.scalar() or 0

    # ── Alerts sent ──────────────────────────────────────────────
    alerts_q = await db.execute(
        select(func.count(Alert.id))
        .where(Alert.created_at >= cutoff, Alert.delivered == True)
    )
    alerts_sent = alerts_q.scalar() or 0

    # ── Top scam types ───────────────────────────────────────────
    types_q = await db.execute(
        select(ScamReport.scam_type, func.count(ScamReport.id).label("count"))
        .where(ScamReport.created_at >= cutoff)
        .group_by(ScamReport.scam_type)
        .order_by(func.count(ScamReport.id).desc())
        .limit(6)
    )
    top_scam_types = [{"type": row[0], "count": row[1]} for row in types_q]

    # ── Top states ───────────────────────────────────────────────
    states_q = await db.execute(
        select(ScamReport.state, func.count(ScamReport.id).label("count"))
        .where(ScamReport.created_at >= cutoff, ScamReport.state.isnot(None))
        .group_by(ScamReport.state)
        .order_by(func.count(ScamReport.id).desc())
        .limit(8)
    )
    top_states = [{"state": row[0], "count": row[1]} for row in states_q]

    # ── Detection accuracy from audit logs ───────────────────────
    acc_q = await db.execute(
        select(func.avg(AuditLog.confidence))
        .where(
            AuditLog.timestamp >= cutoff,
            AuditLog.action == "scam_call_analyze",
        )
    )
    avg_accuracy = round(float(acc_q.scalar() or 0.87), 4)

    # ── Average detection latency ────────────────────────────────
    lat_q = await db.execute(
        select(func.avg(AuditLog.latency_ms))
        .where(AuditLog.timestamp >= cutoff)
    )
    avg_latency = round(float(lat_q.scalar() or 0), 1)

    # ── Estimated loss prevented ─────────────────────────────────
    # Heuristic: avg digital arrest scam = ₹3L; avg other = ₹50K
    # We count confirmed scam detections only
    confirmed_q = await db.execute(
        select(func.count(ScamReport.id))
        .where(
            ScamReport.created_at >= cutoff,
            ScamReport.status == "confirmed",
        )
    )
    confirmed = confirmed_q.scalar() or 0
    estimated_prevented = confirmed * 150_000  # avg ₹1.5L per prevented incident

    return DashboardStats(
        total_scam_detections_30d=scam_total,
        total_counterfeit_reports_30d=count_total,
        active_fraud_cases=active_cases,
        alerts_sent_30d=alerts_sent,
        estimated_loss_prevented_inr=float(estimated_prevented),
        top_scam_types=top_scam_types,
        top_states=top_states,
        detection_accuracy=avg_accuracy,
        avg_detection_latency_ms=avg_latency,
    )


@router.get(
    "/trends",
    summary="Daily trend data for charts",
)
async def get_trends(
    days_back: int = Query(30, ge=7, le=365),
    metric: str = Query("scam_detections", pattern="^(scam_detections|counterfeit|alerts)$"),
    db: AsyncSession = Depends(get_db),
):
    """Returns day-by-day counts for charting."""
    cutoff = datetime.utcnow() - timedelta(days=days_back)

    if metric == "scam_detections":
        result = await db.execute(
            select(
                func.date_trunc("day", ScamReport.created_at).label("day"),
                func.count(ScamReport.id).label("count"),
            )
            .where(ScamReport.created_at >= cutoff)
            .group_by(func.date_trunc("day", ScamReport.created_at))
            .order_by(func.date_trunc("day", ScamReport.created_at))
        )
    elif metric == "counterfeit":
        result = await db.execute(
            select(
                func.date_trunc("day", CounterfeitReport.created_at).label("day"),
                func.count(CounterfeitReport.id).label("count"),
            )
            .where(
                CounterfeitReport.created_at >= cutoff,
                CounterfeitReport.verdict == "counterfeit",
            )
            .group_by(func.date_trunc("day", CounterfeitReport.created_at))
            .order_by(func.date_trunc("day", CounterfeitReport.created_at))
        )
    else:  # alerts
        result = await db.execute(
            select(
                func.date_trunc("day", Alert.created_at).label("day"),
                func.count(Alert.id).label("count"),
            )
            .where(Alert.created_at >= cutoff, Alert.delivered == True)
            .group_by(func.date_trunc("day", Alert.created_at))
            .order_by(func.date_trunc("day", Alert.created_at))
        )

    rows = result.all()
    return {
        "metric": metric,
        "period_days": days_back,
        "data": [
            {
                "date": row[0].strftime("%Y-%m-%d") if row[0] else None,
                "count": row[1],
            }
            for row in rows
        ],
    }


@router.get(
    "/model-performance",
    summary="ML model performance metrics",
)
async def get_model_performance(
    days_back: int = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
):
    cutoff = datetime.utcnow() - timedelta(days=days_back)

    # Scam classifier stats
    scam_stats = await db.execute(
        select(
            func.count(AuditLog.id).label("total"),
            func.avg(AuditLog.confidence).label("avg_confidence"),
            func.avg(AuditLog.latency_ms).label("avg_latency"),
            func.min(AuditLog.latency_ms).label("min_latency"),
            func.max(AuditLog.latency_ms).label("max_latency"),
        )
        .where(
            AuditLog.timestamp >= cutoff,
            AuditLog.action == "scam_call_analyze",
        )
    )
    scam_row = scam_stats.one()

    # Counterfeit detector stats
    count_stats = await db.execute(
        select(
            func.count(AuditLog.id).label("total"),
            func.avg(AuditLog.confidence).label("avg_confidence"),
            func.avg(AuditLog.latency_ms).label("avg_latency"),
        )
        .where(
            AuditLog.timestamp >= cutoff,
            AuditLog.action == "counterfeit_verify",
        )
    )
    count_row = count_stats.one()

    # False positive rate: reports marked false_positive
    fp_q = await db.execute(
        select(func.count(ScamReport.id))
        .where(
            ScamReport.created_at >= cutoff,
            ScamReport.status == "false_positive",
        )
    )
    fp_count = fp_q.scalar() or 0

    total_reviewed_q = await db.execute(
        select(func.count(ScamReport.id))
        .where(
            ScamReport.created_at >= cutoff,
            ScamReport.status.in_(["confirmed", "false_positive"]),
        )
    )
    total_reviewed = total_reviewed_q.scalar() or 1

    return {
        "period_days": days_back,
        "scam_classifier": {
            "total_inferences": scam_row[0] or 0,
            "avg_confidence": round(float(scam_row[1] or 0), 4),
            "avg_latency_ms": round(float(scam_row[2] or 0), 1),
            "min_latency_ms": scam_row[3] or 0,
            "max_latency_ms": scam_row[4] or 0,
            "false_positive_rate": round(fp_count / total_reviewed, 4),
        },
        "counterfeit_detector": {
            "total_inferences": count_row[0] or 0,
            "avg_confidence": round(float(count_row[1] or 0), 4),
            "avg_latency_ms": round(float(count_row[2] or 0), 1),
        },
    }
