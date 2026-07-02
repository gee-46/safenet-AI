"""
SafeNet AI – Celery Task Queue
Background tasks: geo cluster refresh, evidence generation,
NCRB report submission, fraud graph enrichment.
"""
from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Dict, List, Optional

from celery import Celery
from celery.schedules import crontab

from backend.core.config import get_settings

settings = get_settings()

# ── Celery App ────────────────────────────────────────────────────
celery_app = Celery(
    "safenet",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["backend.tasks.celery_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_soft_time_limit=300,    # 5 min soft limit
    task_time_limit=600,          # 10 min hard limit
    result_expires=3600,          # Results expire after 1 hour
    # Beat schedule for periodic tasks
    beat_schedule={
        "refresh-geo-clusters": {
            "task": "backend.tasks.celery_tasks.refresh_geo_clusters",
            "schedule": crontab(minute=0),   # every hour
        },
        "enrich-fraud-graph": {
            "task": "backend.tasks.celery_tasks.enrich_fraud_graph",
            "schedule": crontab(minute=30),  # every hour at :30
        },
        "daily-analytics-snapshot": {
            "task": "backend.tasks.celery_tasks.daily_analytics_snapshot",
            "schedule": crontab(hour=1, minute=0),  # 1 AM IST daily
        },
    },
)


def run_async(coro):
    """Run an async coroutine from a sync Celery task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ── Tasks ─────────────────────────────────────────────────────────

@celery_app.task(bind=True, name="backend.tasks.celery_tasks.analyze_call_async")
def analyze_call_async(self, call_data: Dict) -> Dict:
    """
    Background scam call analysis for high-volume ingestion.
    Called when telecom partners push batches of call metadata.
    """
    from backend.models.scam.classifier import get_scam_classifier
    classifier = get_scam_classifier(settings.scam_model_path)
    result = classifier.classify(call_data)

    # If high-confidence scam, trigger alert
    if result["is_scam"] and result["confidence_score"] >= settings.scam_confidence_threshold:
        send_scam_alert.delay(
            phone_number=call_data.get("victim_number", ""),
            scam_type=result["scam_type"],
            confidence=result["confidence_score"],
            recommended_action=result["recommended_action"],
        )

        # Register in fraud graph
        register_in_fraud_graph.delay(
            entity_id=call_data.get("caller_number", ""),
            entity_type="phone_number",
            scam_type=result["scam_type"],
            confidence=result["confidence_score"],
        )

    return result


@celery_app.task(bind=True, name="backend.tasks.celery_tasks.send_scam_alert")
def send_scam_alert(
    self,
    phone_number: str,
    scam_type: str,
    confidence: float,
    recommended_action: str,
    channel: str = "whatsapp",
) -> bool:
    """Send fraud alert to victim phone number."""
    from backend.services.alert_service import _build_scam_alert_message, _send_twilio_whatsapp

    message = _build_scam_alert_message(scam_type, confidence, recommended_action)

    async def _send():
        if channel == "whatsapp":
            sid = await _send_twilio_whatsapp(phone_number, message)
        else:
            from backend.services.alert_service import _send_twilio_sms
            sid = await _send_twilio_sms(phone_number, message)
        return sid is not None

    return run_async(_send())


@celery_app.task(bind=True, name="backend.tasks.celery_tasks.register_in_fraud_graph")
def register_in_fraud_graph(
    self,
    entity_id: str,
    entity_type: str,
    scam_type: str,
    confidence: float,
    location: Optional[Dict] = None,
) -> bool:
    """Register a confirmed scam entity in the Neo4j fraud graph."""
    from backend.models.fraud_graph.graph_intelligence import get_fraud_graph_manager

    manager = get_fraud_graph_manager(
        uri=settings.neo4j_uri,
        user=settings.neo4j_user,
        password=settings.neo4j_password,
    )

    async def _register():
        await manager.connect()
        await manager.register_fraud_event(
            entity_id=entity_id,
            entity_type=entity_type,
            scam_type=scam_type,
            confidence=confidence,
            location=location,
        )
        return True

    return run_async(_register())


@celery_app.task(bind=True, name="backend.tasks.celery_tasks.generate_evidence_package_async")
def generate_evidence_package_async(
    self,
    case_id: Optional[str],
    scam_report_ids: List[str],
    case_summary: Dict,
) -> Dict:
    """
    Generate evidence PDF package asynchronously.
    Triggered when officer requests package for a large case.
    """
    from backend.services.evidence_generator import get_evidence_generator
    import uuid

    generator = get_evidence_generator()
    case_number = case_summary.get("case_number", f"SN-{datetime.utcnow().year}-{uuid.uuid4().hex[:6].upper()}")

    # Build minimal scam reports list from IDs
    # In production: fetch from DB here
    scam_reports = [{"id": rid} for rid in scam_report_ids]

    package_id, pdf_bytes = generator.generate_and_store(
        case_number=case_number,
        scam_reports=scam_reports,
        fraud_graph=None,
        case_summary=case_summary,
        include_regulatory=True,
    )

    return {
        "package_id": package_id,
        "case_number": case_number,
        "pdf_size_bytes": len(pdf_bytes),
        "download_url": f"/api/v1/reports/download/{package_id}",
        "generated_at": datetime.utcnow().isoformat(),
    }


@celery_app.task(name="backend.tasks.celery_tasks.refresh_geo_clusters")
def refresh_geo_clusters() -> Dict:
    """
    Hourly task: recompute H3 risk clusters and cache in Redis.
    Ensures heatmap API returns pre-computed data for fast response.
    """
    import json
    import redis as redis_lib

    r = redis_lib.from_url(settings.redis_url)

    async def _refresh():
        from backend.db.models import AsyncSessionLocal, ScamReport, CounterfeitReport
        from backend.geo.geo_intelligence import get_geo_service
        from sqlalchemy import select
        from datetime import timedelta

        cutoff = datetime.utcnow() - timedelta(days=30)

        async with AsyncSessionLocal() as session:
            scam_rows = (await session.execute(
                select(ScamReport)
                .where(ScamReport.created_at >= cutoff, ScamReport.location_lat.isnot(None))
                .limit(10000)
            )).scalars().all()

            count_rows = (await session.execute(
                select(CounterfeitReport)
                .where(
                    CounterfeitReport.created_at >= cutoff,
                    CounterfeitReport.location_lat.isnot(None),
                    CounterfeitReport.verdict == "counterfeit",
                )
                .limit(3000)
            )).scalars().all()

        scam_incidents = [
            {"lat": r.location_lat, "lng": r.location_lng,
             "scam_type": r.scam_type, "city": r.city,
             "state": r.state, "created_at": r.created_at}
            for r in scam_rows
        ]
        counterfeit_incidents = [
            {"lat": r.location_lat, "lng": r.location_lng,
             "city": r.city, "state": r.state, "created_at": r.created_at}
            for r in count_rows
        ]

        geo = get_geo_service()
        heatmap = geo.generate_heatmap(
            scam_incidents=scam_incidents,
            counterfeit_incidents=counterfeit_incidents,
            resolution=7,
            days_back=30,
        )
        return heatmap

    heatmap = run_async(_refresh())

    # Cache in Redis for 1 hour
    r.setex("geo:heatmap:r7:30d", 3600, json.dumps(heatmap, default=str))
    r.setex("geo:heatmap:last_refresh", 3600, datetime.utcnow().isoformat())

    return {
        "clusters_computed": len(heatmap.get("clusters", [])),
        "total_incidents": heatmap.get("total_incidents", 0),
        "cached_until": "1 hour",
    }


@celery_app.task(name="backend.tasks.celery_tasks.enrich_fraud_graph")
def enrich_fraud_graph() -> Dict:
    """
    Hourly task: cross-link newly confirmed scam reports
    into the Neo4j graph to build richer fraud networks.
    """
    async def _enrich():
        from backend.db.models import AsyncSessionLocal, ScamReport
        from backend.models.fraud_graph.graph_intelligence import get_fraud_graph_manager
        from sqlalchemy import select
        from datetime import timedelta

        manager = get_fraud_graph_manager(
            uri=settings.neo4j_uri,
            user=settings.neo4j_user,
            password=settings.neo4j_password,
        )
        await manager.connect()

        # Get all confirmed scam reports from last 2 hours
        cutoff = datetime.utcnow() - timedelta(hours=2)
        async with AsyncSessionLocal() as session:
            rows = (await session.execute(
                select(ScamReport)
                .where(
                    ScamReport.created_at >= cutoff,
                    ScamReport.status == "confirmed",
                )
                .limit(500)
            )).scalars().all()

        enriched = 0
        for report in rows:
            if report.caller_number:
                await manager.register_fraud_event(
                    entity_id=report.caller_number,
                    entity_type="phone_number",
                    scam_type=report.scam_type or "unknown",
                    confidence=report.confidence_score or 0.8,
                    location={
                        "lat": report.location_lat,
                        "lng": report.location_lng,
                        "state": report.state,
                    } if report.location_lat else None,
                )
                enriched += 1

        return enriched

    count = run_async(_enrich())
    return {"entities_enriched": count, "run_at": datetime.utcnow().isoformat()}


@celery_app.task(name="backend.tasks.celery_tasks.daily_analytics_snapshot")
def daily_analytics_snapshot() -> Dict:
    """
    Daily task: compute and cache analytics snapshot.
    Runs at 1 AM IST to pre-warm dashboard data.
    """
    import json
    import redis as redis_lib

    r = redis_lib.from_url(settings.redis_url)

    async def _snapshot():
        from backend.db.models import AsyncSessionLocal, ScamReport, CounterfeitReport, FraudCase, Alert
        from sqlalchemy import func, select
        from datetime import timedelta

        cutoff = datetime.utcnow() - timedelta(days=30)

        async with AsyncSessionLocal() as session:
            scam_total = (await session.execute(
                select(func.count(ScamReport.id)).where(ScamReport.created_at >= cutoff)
            )).scalar() or 0

            count_total = (await session.execute(
                select(func.count(CounterfeitReport.id))
                .where(CounterfeitReport.created_at >= cutoff, CounterfeitReport.verdict == "counterfeit")
            )).scalar() or 0

            cases_open = (await session.execute(
                select(func.count(FraudCase.id)).where(FraudCase.status == "open")
            )).scalar() or 0

            alerts_sent = (await session.execute(
                select(func.count(Alert.id))
                .where(Alert.created_at >= cutoff, Alert.delivered == True)
            )).scalar() or 0

        return {
            "period": "30d",
            "scam_detections": scam_total,
            "counterfeit_reports": count_total,
            "active_cases": cases_open,
            "alerts_sent": alerts_sent,
            "snapshot_at": datetime.utcnow().isoformat(),
        }

    snapshot = run_async(_snapshot())
    r.setex("analytics:daily_snapshot", 86400, json.dumps(snapshot))
    return snapshot
