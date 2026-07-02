"""
SafeNet AI – Geospatial / Heatmap Routes
/api/v1/heatmap/...
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import CounterfeitReport, ScamReport, get_db
from backend.geo.geo_intelligence import get_geo_service
from backend.schemas.schemas import HeatmapParams, HeatmapResponse

router = APIRouter(prefix="/heatmap", tags=["Geospatial Intelligence"])


@router.get(
    "/crimes",
    response_model=HeatmapResponse,
    summary="Generate H3 crime heatmap",
    description="""
    Returns H3 hexagonal clusters of crime incidents for map visualisation.
    Supports bounding box filtering, H3 resolution (4-10), and date range.

    Resolution guide:
    - 5: district level  (~25 km² per cell)
    - 7: neighbourhood   (~0.74 km² per cell) ← default
    - 9: street level    (~0.01 km² per cell)
    """,
)
async def get_crime_heatmap(
    h3_resolution: int = Query(7, ge=4, le=10),
    days_back: int = Query(30, ge=1, le=365),
    min_lng: Optional[float] = Query(None, ge=-180, le=180),
    min_lat: Optional[float] = Query(None, ge=-90, le=90),
    max_lng: Optional[float] = Query(None, ge=-180, le=180),
    max_lat: Optional[float] = Query(None, ge=-90, le=90),
    fraud_types: Optional[str] = Query(None, description="Comma-separated scam types to filter"),
    state: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    cutoff = datetime.utcnow() - timedelta(days=days_back)

    # Build bbox
    bbox = None
    if all(v is not None for v in [min_lng, min_lat, max_lng, max_lat]):
        bbox = [min_lng, min_lat, max_lng, max_lat]

    # Fetch scam incidents with location data
    scam_query = select(ScamReport).where(
        ScamReport.created_at >= cutoff,
        ScamReport.location_lat.isnot(None),
        ScamReport.location_lng.isnot(None),
    )
    if state:
        scam_query = scam_query.where(ScamReport.state == state)
    if fraud_types:
        types_list = [t.strip() for t in fraud_types.split(",")]
        scam_query = scam_query.where(ScamReport.scam_type.in_(types_list))

    scam_result = await db.execute(scam_query.limit(5000))
    scam_rows = scam_result.scalars().all()

    # Fetch counterfeit incidents with location data
    count_query = select(CounterfeitReport).where(
        CounterfeitReport.created_at >= cutoff,
        CounterfeitReport.location_lat.isnot(None),
        CounterfeitReport.location_lng.isnot(None),
        CounterfeitReport.verdict == "counterfeit",
    )
    if state:
        count_query = count_query.where(CounterfeitReport.state == state)

    count_result = await db.execute(count_query.limit(2000))
    count_rows = count_result.scalars().all()

    # Convert to plain dicts for geo engine
    scam_incidents = [
        {
            "lat": r.location_lat,
            "lng": r.location_lng,
            "scam_type": r.scam_type,
            "city": r.city,
            "state": r.state,
            "created_at": r.created_at,
        }
        for r in scam_rows
    ]
    counterfeit_incidents = [
        {
            "lat": r.location_lat,
            "lng": r.location_lng,
            "city": r.city,
            "state": r.state,
            "created_at": r.created_at,
        }
        for r in count_rows
    ]

    geo_service = get_geo_service()
    heatmap = geo_service.generate_heatmap(
        scam_incidents=scam_incidents,
        counterfeit_incidents=counterfeit_incidents,
        resolution=h3_resolution,
        bbox=bbox,
        days_back=days_back,
    )

    return HeatmapResponse(
        clusters=heatmap["clusters"],
        total_incidents=heatmap["total_incidents"],
        generated_at=datetime.fromisoformat(heatmap["generated_at"]),
        bbox_used=heatmap["bbox_used"],
    )


@router.get(
    "/patrol-priorities",
    summary="Get top patrol deployment priorities",
    description="Returns ranked list of high-risk zones for police patrol deployment.",
)
async def get_patrol_priorities(
    top_n: int = Query(5, ge=1, le=20),
    days_back: int = Query(7, ge=1, le=90),
    state: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    # Reuse heatmap but at higher resolution for precision
    cutoff = datetime.utcnow() - timedelta(days=days_back)

    scam_q = select(ScamReport).where(
        ScamReport.created_at >= cutoff,
        ScamReport.location_lat.isnot(None),
    )
    if state:
        scam_q = scam_q.where(ScamReport.state == state)

    count_q = select(CounterfeitReport).where(
        CounterfeitReport.created_at >= cutoff,
        CounterfeitReport.location_lat.isnot(None),
        CounterfeitReport.verdict == "counterfeit",
    )
    if state:
        count_q = count_q.where(CounterfeitReport.state == state)

    scam_rows = (await db.execute(scam_q.limit(2000))).scalars().all()
    count_rows = (await db.execute(count_q.limit(500))).scalars().all()

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

    geo_service = get_geo_service()
    heatmap = geo_service.generate_heatmap(
        scam_incidents=scam_incidents,
        counterfeit_incidents=counterfeit_incidents,
        resolution=8,  # higher resolution for patrol
        days_back=days_back,
    )

    priorities = geo_service.get_patrol_priorities(heatmap["clusters"], top_n=top_n)
    return {
        "as_of": datetime.utcnow().isoformat(),
        "days_analysed": days_back,
        "state_filter": state,
        "priorities": priorities,
    }


@router.get(
    "/state-summary",
    summary="State-level crime summary for command dashboard",
)
async def state_summary(
    days_back: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import func, and_
    cutoff = datetime.utcnow() - timedelta(days=days_back)

    # Scam counts per state
    scam_by_state = await db.execute(
        select(ScamReport.state, func.count(ScamReport.id).label("scam_count"))
        .where(ScamReport.created_at >= cutoff, ScamReport.state.isnot(None))
        .group_by(ScamReport.state)
        .order_by(func.count(ScamReport.id).desc())
    )

    # Counterfeit counts per state
    count_by_state = await db.execute(
        select(CounterfeitReport.state, func.count(CounterfeitReport.id).label("count_count"))
        .where(
            CounterfeitReport.created_at >= cutoff,
            CounterfeitReport.state.isnot(None),
            CounterfeitReport.verdict == "counterfeit",
        )
        .group_by(CounterfeitReport.state)
    )

    scam_dict = {row[0]: row[1] for row in scam_by_state}
    count_dict = {row[0]: row[1] for row in count_by_state}

    all_states = sorted(set(scam_dict.keys()) | set(count_dict.keys()))
    summary = []
    for state in all_states:
        sc = scam_dict.get(state, 0)
        cc = count_dict.get(state, 0)
        total = sc + cc
        # Simple composite risk
        risk = min((sc * 1.0 + cc * 2.0) / 50.0, 1.0)
        summary.append({
            "state": state,
            "scam_count": sc,
            "counterfeit_count": cc,
            "total_incidents": total,
            "risk_score": round(risk, 3),
        })

    summary.sort(key=lambda x: x["risk_score"], reverse=True)
    return {
        "period_days": days_back,
        "states": summary,
        "generated_at": datetime.utcnow().isoformat(),
    }


@router.get(
    "/city-hotspots",
    summary="Top cities by incident count",
)
async def city_hotspots(
    days_back: int = Query(30, ge=1, le=365),
    limit: int = Query(15, ge=5, le=50),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import func
    cutoff = datetime.utcnow() - timedelta(days=days_back)

    result = await db.execute(
        select(ScamReport.city, ScamReport.state, func.count(ScamReport.id).label("count"))
        .where(
            ScamReport.created_at >= cutoff,
            ScamReport.city.isnot(None),
        )
        .group_by(ScamReport.city, ScamReport.state)
        .order_by(func.count(ScamReport.id).desc())
        .limit(limit)
    )
    return {
        "period_days": days_back,
        "hotspots": [
            {"city": row[0], "state": row[1], "incident_count": row[2]}
            for row in result
        ],
    }
