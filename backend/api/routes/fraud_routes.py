"""
SafeNet AI – Fraud Graph Routes
/api/v1/fraud/...
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.core.config import get_settings
from backend.db.models import FraudCase, ScamReport, AuditLog, get_db
from backend.models.fraud_graph.graph_intelligence import get_fraud_graph_manager
from backend.schemas.schemas import (
    FraudGraphResponse, FraudNetworkIn, EntityType,
)

router = APIRouter(prefix="/fraud", tags=["Fraud Graph Intelligence"])
settings = get_settings()


@router.post(
    "/graph/query",
    response_model=FraudGraphResponse,
    summary="Query fraud network graph for an entity",
    description="""
    Traverse the fraud graph from a seed entity (phone number, bank account, device, etc.)
    up to a configurable depth and return the connected network with risk scores.

    Depth 2 returns: direct connections + their connections.
    Depth 3-4: wider network (slower, use max_nodes to cap).
    """,
)
async def query_fraud_graph(
    query: FraudNetworkIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    manager = get_fraud_graph_manager(
        uri=settings.neo4j_uri,
        user=settings.neo4j_user,
        password=settings.neo4j_password,
        gnn_model_path=settings.fraud_gnn_model_path,
    )
    # Ensure connected (idempotent)
    if manager._driver is None:
        await manager.connect()

    result = await manager.full_query(
        entity_id=query.entity_id,
        entity_type=query.entity_type.value,
        depth=query.depth,
        max_nodes=query.max_nodes,
    )

    # Audit
    db.add(AuditLog(
        action="fraud_graph_query",
        entity_type=query.entity_type.value,
        entity_id=query.entity_id,
        actor_id=str(request.client.host) if request.client else "api",
        model_name="FraudGraphManager",
        model_version="1.0.0",
        output={
            "risk_score": result["risk_score"],
            "network_size": result["fraud_network_size"],
        },
        confidence=result["risk_score"],
        latency_ms=result.get("processing_time_ms", 0),
        ip_address=str(request.client.host) if request.client else None,
    ))

    return FraudGraphResponse(**result)


@router.get(
    "/graph/{entity_id}",
    response_model=FraudGraphResponse,
    summary="Get fraud graph for an entity via GET (quick lookup)",
)
async def get_entity_graph(
    entity_id: str,
    entity_type: EntityType = Query(EntityType.PHONE_NUMBER),
    depth: int = Query(2, ge=1, le=4),
    max_nodes: int = Query(50, ge=5, le=200),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
):
    manager = get_fraud_graph_manager(
        uri=settings.neo4j_uri,
        user=settings.neo4j_user,
        password=settings.neo4j_password,
    )
    if manager._driver is None:
        await manager.connect()

    result = await manager.full_query(
        entity_id=entity_id,
        entity_type=entity_type.value,
        depth=depth,
        max_nodes=max_nodes,
    )
    return FraudGraphResponse(**result)


@router.post(
    "/register",
    summary="Register a confirmed fraud event in the graph",
    description="Called internally when a scam is confirmed. Links entities into the fraud network.",
    status_code=status.HTTP_201_CREATED,
)
async def register_fraud_event(
    entity_id: str = Query(..., description="Phone number, bank account, etc."),
    entity_type: EntityType = Query(EntityType.PHONE_NUMBER),
    scam_type: str = Query("unknown"),
    confidence: float = Query(..., ge=0, le=1),
    location_lat: Optional[float] = Query(None),
    location_lng: Optional[float] = Query(None),
    state: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    manager = get_fraud_graph_manager(
        uri=settings.neo4j_uri,
        user=settings.neo4j_user,
        password=settings.neo4j_password,
    )
    if manager._driver is None:
        await manager.connect()

    location = None
    if location_lat and location_lng:
        location = {"lat": location_lat, "lng": location_lng, "state": state}

    await manager.register_fraud_event(
        entity_id=entity_id,
        entity_type=entity_type.value,
        scam_type=scam_type,
        confidence=confidence,
        location=location,
    )

    return {
        "entity_id": entity_id,
        "entity_type": entity_type.value,
        "registered": True,
        "message": "Entity linked into fraud network graph",
    }


@router.post(
    "/link",
    summary="Create a relationship between two entities",
    description="Link two entities in the fraud graph (e.g. TRANSFERRED_TO, SHARES_DEVICE).",
    status_code=status.HTTP_201_CREATED,
)
async def link_entities(
    source_id: str = Query(...),
    target_id: str = Query(...),
    source_type: EntityType = Query(EntityType.PHONE_NUMBER),
    target_type: EntityType = Query(EntityType.BANK_ACCOUNT),
    relationship: str = Query("TRANSFERRED_TO"),
    amount_inr: Optional[float] = Query(None),
    transaction_count: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    from backend.models.fraud_graph.graph_intelligence import EDGE_TYPES
    if relationship not in EDGE_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid relationship. Must be one of: {EDGE_TYPES}",
        )

    manager = get_fraud_graph_manager(
        uri=settings.neo4j_uri,
        user=settings.neo4j_user,
        password=settings.neo4j_password,
    )
    if manager._driver is None:
        await manager.connect()

    # Upsert both nodes first
    await manager.upsert_entity(source_id, source_type.value, {"label": source_id})
    await manager.upsert_entity(target_id, target_type.value, {"label": target_id})

    props = {}
    if amount_inr:
        props["total_amount_inr"] = amount_inr
    if transaction_count:
        props["transaction_count"] = transaction_count

    success = await manager.upsert_relationship(source_id, target_id, relationship, props)

    return {
        "source": source_id,
        "target": target_id,
        "relationship": relationship,
        "linked": success,
    }


@router.get(
    "/cases",
    summary="List fraud investigation cases",
)
async def list_fraud_cases(
    status: Optional[str] = Query(None),
    fraud_type: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import and_
    conditions = []
    if status:
        conditions.append(FraudCase.status == status)
    if fraud_type:
        conditions.append(FraudCase.fraud_type == fraud_type)
    if severity:
        conditions.append(FraudCase.severity == severity)

    query = (
        select(FraudCase)
        .where(and_(*conditions) if conditions else True)
        .order_by(FraudCase.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    cases = result.scalars().all()

    return [
        {
            "id": str(c.id),
            "case_number": c.case_number,
            "title": c.title,
            "fraud_type": c.fraud_type,
            "status": c.status,
            "severity": c.severity,
            "estimated_victims": c.estimated_victims,
            "estimated_loss_inr": c.estimated_loss_inr,
            "states_involved": c.states_involved,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in cases
    ]


@router.post(
    "/cases",
    summary="Create a new fraud investigation case",
    status_code=status.HTTP_201_CREATED,
)
async def create_fraud_case(
    title: str = Query(..., max_length=300),
    fraud_type: str = Query(...),
    severity: str = Query("medium", pattern="^(low|medium|high|critical)$"),
    description: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    import random
    case_number = f"SN-{datetime.utcnow().year}-{random.randint(10000, 99999)}"

    case = FraudCase(
        case_number=case_number,
        title=title,
        fraud_type=fraud_type,
        severity=severity,
        status="open",
    )
    db.add(case)
    await db.flush()

    return {
        "id": str(case.id),
        "case_number": case_number,
        "title": title,
        "status": "open",
        "created": True,
    }


@router.get(
    "/cases/{case_id}",
    summary="Get fraud case details",
)
async def get_fraud_case(case_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(FraudCase).where(FraudCase.id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return {
        "id": str(case.id),
        "case_number": case.case_number,
        "title": case.title,
        "fraud_type": case.fraud_type,
        "status": case.status,
        "severity": case.severity,
        "estimated_victims": case.estimated_victims,
        "estimated_loss_inr": case.estimated_loss_inr,
        "network_nodes": case.network_nodes,
        "states_involved": case.states_involved,
        "evidence_package_url": case.evidence_package_url,
        "ncrb_case_id": case.ncrb_case_id,
        "created_at": case.created_at.isoformat() if case.created_at else None,
        "updated_at": case.updated_at.isoformat() if case.updated_at else None,
    }
