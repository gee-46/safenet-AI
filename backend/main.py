
"""
SafeNet AI – Main FastAPI Application
Wires together all routes, middleware, lifespan events, and health checks.
"""
from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from backend.core.config import get_settings
from backend.db.models import create_tables
from backend.models.scam.classifier import get_scam_classifier
from backend.models.counterfeit.detector import get_counterfeit_detector
from backend.models.fraud_graph.graph_intelligence import get_fraud_graph_manager

# Route imports
from backend.api.routes.scam_routes import router as scam_router
from backend.api.routes.currency_routes import router as currency_router
from backend.api.routes.fraud_routes import router as fraud_router
from backend.api.routes.heatmap_routes import router as heatmap_router
from backend.api.routes.citizen_routes import citizen_router, evidence_router
from backend.api.routes.analytics_routes import router as analytics_router

settings = get_settings()
logger = structlog.get_logger()


# ── Lifespan ─────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic."""
    logger.info("SafeNet AI starting up", env=settings.app_env)

    # Create DB tables
    try:
        await create_tables()
        logger.info("Database tables ready")
    except Exception as e:
        logger.error("DB init failed", error=str(e))

    # Pre-load ML models (warm-up)
    try:
        get_scam_classifier(settings.scam_model_path)
        logger.info("Scam classifier loaded")
    except Exception as e:
        logger.warning("Scam classifier load failed", error=str(e))

    try:
        get_counterfeit_detector(settings.counterfeit_model_path)
        logger.info("Counterfeit detector loaded")
    except Exception as e:
        logger.warning("Counterfeit detector load failed", error=str(e))

    # Connect Neo4j fraud graph
    try:
        manager = get_fraud_graph_manager(
            uri=settings.neo4j_uri,
            user=settings.neo4j_user,
            password=settings.neo4j_password,
            gnn_model_path=settings.fraud_gnn_model_path,
        )
        await manager.connect()
        logger.info("Neo4j fraud graph connected")
    except Exception as e:
        logger.warning("Neo4j connection failed — graph features degraded", error=str(e))

    logger.info("SafeNet AI ready", port=settings.app_port)
    yield

    # Shutdown
    logger.info("SafeNet AI shutting down")
    try:
        manager = get_fraud_graph_manager()
        await manager.close()
    except Exception:
        pass
    logger.info("SafeNet AI shutdown complete")


# ── App Factory ───────────────────────────────────────────────────

def create_app() -> FastAPI:
    app = FastAPI(
        title="SafeNet AI",
        description="""
# SafeNet AI — India's Unified Public Safety Intelligence Platform

Protect citizens from digital arrest scams, counterfeit currency, and fraud networks.

## Modules
- **🎭 Scam Call Detector** — Real-time scam call classification via call metadata
- **💵 CounterfeitLens** — CV-based counterfeit currency detection
- **🕸️ FraudGraph** — Neo4j + GNN fraud network intelligence
- **🗺️ GeoIntel** — H3 hexagonal crime heatmaps for patrol optimisation
- **🛡️ CitizenShield** — Multilingual WhatsApp/IVR fraud advisor
- **📋 Evidence Packages** — Court-admissible PDF evidence for law enforcement

## Authentication
Use `Bearer <token>` in the Authorization header.
Obtain tokens via `/api/v1/auth/login`.

## Rate Limits
- Standard: 60 requests/minute
- Evidence package generation: 10 requests/minute
        """,
        version="1.0.0",
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        lifespan=lifespan,
        contact={
            "name": "SafeNet AI Team",
            "email": "dev@safenet.ai",
        },
        license_info={
            "name": "Proprietary — ET AI Hackathon 2026",
        },
    )

    # ── Middleware ───────────────────────────────────────────────

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Gzip compression for large responses (heatmap, graph data)
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # Request ID + timing middleware
    @app.middleware("http")
    async def request_middleware(request: Request, call_next):
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id
        request.state.start_time = time.perf_counter()

        response = await call_next(request)

        elapsed_ms = int((time.perf_counter() - request.state.start_time) * 1000)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time-Ms"] = str(elapsed_ms)
        response.headers["X-Powered-By"] = "SafeNet-AI/1.0"

        # Structured log
        logger.info(
            "request",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            latency_ms=elapsed_ms,
        )
        return response

    # ── Exception Handlers ───────────────────────────────────────

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error("Unhandled exception", path=request.url.path, error=str(exc))
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal server error",
                "detail": str(exc) if settings.debug else "An unexpected error occurred",
                "request_id": getattr(request.state, "request_id", "unknown"),
            },
        )

    # ── Routers ──────────────────────────────────────────────────
    prefix = "/api/v1"

    app.include_router(scam_router, prefix=prefix)
    app.include_router(currency_router, prefix=prefix)
    app.include_router(fraud_router, prefix=prefix)
    app.include_router(heatmap_router, prefix=prefix)
    app.include_router(citizen_router, prefix=prefix)
    app.include_router(evidence_router, prefix=prefix)
    app.include_router(analytics_router, prefix=prefix)

    # ── Health & Meta Endpoints ──────────────────────────────────

    @app.get("/health", tags=["System"], summary="Health check")
    async def health_check():
        return {
            "status": "healthy",
            "service": "SafeNet AI",
            "version": "1.0.0",
            "env": settings.app_env,
            "timestamp": time.time(),
        }

    @app.get("/health/deep", tags=["System"], summary="Deep health check with dependency status")
    async def deep_health_check():
        checks = {}

        # Database
        try:
            from backend.db.models import AsyncSessionLocal
            from sqlalchemy import text
            async with AsyncSessionLocal() as session:
                await session.execute(text("SELECT 1"))
            checks["database"] = "healthy"
        except Exception as e:
            checks["database"] = f"unhealthy: {e}"

        # Redis
        try:
            import aioredis
            redis = await aioredis.from_url(settings.redis_url, socket_connect_timeout=2)
            await redis.ping()
            await redis.close()
            checks["redis"] = "healthy"
        except Exception as e:
            checks["redis"] = f"unhealthy: {e}"

        # Neo4j
        try:
            manager = get_fraud_graph_manager()
            if manager._driver:
                checks["neo4j"] = "healthy"
            else:
                checks["neo4j"] = "degraded (not connected)"
        except Exception as e:
            checks["neo4j"] = f"unhealthy: {e}"

        # ML Models
        try:
            clf = get_scam_classifier()
            checks["scam_model"] = "loaded" if clf._loaded else "pattern-only"
        except Exception:
            checks["scam_model"] = "not loaded"

        try:
            det = get_counterfeit_detector()
            checks["counterfeit_model"] = "loaded" if det._yolo_model else "cv-only"
        except Exception:
            checks["counterfeit_model"] = "not loaded"

        overall = "healthy" if all("unhealthy" not in v for v in checks.values()) else "degraded"
        return {"status": overall, "checks": checks, "timestamp": time.time()}

    @app.get("/", tags=["System"], summary="API root")
    async def root():
        return {
            "name": "SafeNet AI",
            "tagline": "India's Unified Public Safety Intelligence Platform",
            "version": "1.0.0",
            "docs": "/docs",
            "health": "/health",
            "modules": {
                "scam_detection": f"{prefix}/calls/analyze",
                "counterfeit_detection": f"{prefix}/currency/verify",
                "fraud_graph": f"{prefix}/fraud/graph/query",
                "heatmap": f"{prefix}/heatmap/crimes",
                "citizen_shield": f"{prefix}/citizen/assess",
                "evidence_packages": f"{prefix}/reports/generate",
                "analytics": f"{prefix}/analytics/dashboard",
            },
        }

    return app


# ── Entry Point ───────────────────────────────────────────────────
app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.debug,
        log_level="info",
        access_log=True,
    )
