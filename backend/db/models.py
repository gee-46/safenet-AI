<<<<<<< HEAD
"""
SafeNet AI – Database Layer
SQLAlchemy async models + session factory.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import AsyncGenerator

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey,
    Integer, JSON, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.sql import func

from backend.core.config import get_settings

settings = get_settings()

# ── Engine & Session Factory ──────────────────────────────────────
engine = create_async_engine(
    settings.database_url,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=settings.debug,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yields an async DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ── Base ─────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


# ── Models ───────────────────────────────────────────────────────

class User(Base, TimestampMixin):
    """Platform users: citizens, officers, bank analysts."""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    phone = Column(String(20), unique=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="citizen")  # citizen | officer | analyst | admin
    language_preference = Column(String(10), default="en")
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    meta = Column(JSON, default=dict)

    scam_reports = relationship("ScamReport", back_populates="reporter", lazy="select")
    alerts = relationship("Alert", back_populates="user", lazy="select")


class ScamReport(Base, TimestampMixin):
    """Records of detected / reported scam calls."""
    __tablename__ = "scam_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reporter_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    caller_number = Column(String(20), index=True)
    victim_number = Column(String(20), index=True)
    scam_type = Column(String(100), index=True)   # digital_arrest | loan | lottery | kyc | impersonation
    confidence_score = Column(Float, nullable=False)
    status = Column(String(50), default="pending")  # pending | confirmed | false_positive | escalated
    call_duration_seconds = Column(Integer)
    call_metadata = Column(JSON, default=dict)      # timing, spoofing_sig, etc.
    audio_features = Column(JSON, default=dict)     # extracted audio fingerprint (no raw audio)
    transcript_snippet = Column(Text)               # first 500 chars only (privacy)
    script_patterns_matched = Column(JSON, default=list)
    location_lat = Column(Float)
    location_lng = Column(Float)
    city = Column(String(100))
    state = Column(String(100))
    ncrb_complaint_id = Column(String(100))
    evidence_package_url = Column(String(500))

    reporter = relationship("User", back_populates="scam_reports")
    linked_cases = relationship("FraudCase", secondary="scam_fraud_cases", back_populates="scam_reports")


class CounterfeitReport(Base, TimestampMixin):
    """Counterfeit currency detection records."""
    __tablename__ = "counterfeit_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reporter_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    denomination = Column(Integer, index=True)        # 500 | 2000 | 200 | 100
    series = Column(String(20))                       # Mahatma Gandhi New Series
    confidence_score = Column(Float, nullable=False)
    verdict = Column(String(20), nullable=False)      # genuine | counterfeit | uncertain
    defects_detected = Column(JSON, default=list)     # list of failed security checks
    serial_number_valid = Column(Boolean)
    microprint_score = Column(Float)
    security_thread_score = Column(Float)
    watermark_score = Column(Float)
    image_hash = Column(String(64), index=True)       # perceptual hash for dedup
    location_lat = Column(Float)
    location_lng = Column(Float)
    city = Column(String(100))
    state = Column(String(100))
    reported_to_rbi = Column(Boolean, default=False)


class FraudCase(Base, TimestampMixin):
    """Aggregated fraud network investigation case."""
    __tablename__ = "fraud_cases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_number = Column(String(50), unique=True, nullable=False, index=True)
    title = Column(String(300), nullable=False)
    fraud_type = Column(String(100), index=True)
    status = Column(String(50), default="open")       # open | investigating | closed | escalated
    severity = Column(String(20), default="medium")   # low | medium | high | critical
    estimated_victims = Column(Integer, default=0)
    estimated_loss_inr = Column(Float, default=0)
    network_nodes = Column(JSON, default=list)         # entity IDs from Neo4j
    states_involved = Column(JSON, default=list)
    assigned_officer_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    evidence_package_url = Column(String(500))
    ncrb_case_id = Column(String(100))

    scam_reports = relationship("ScamReport", secondary="scam_fraud_cases", back_populates="linked_cases")


class ScamFraudCase(Base):
    """Many-to-many: ScamReport ↔ FraudCase."""
    __tablename__ = "scam_fraud_cases"

    scam_report_id = Column(UUID(as_uuid=True), ForeignKey("scam_reports.id"), primary_key=True)
    fraud_case_id = Column(UUID(as_uuid=True), ForeignKey("fraud_cases.id"), primary_key=True)


class Alert(Base, TimestampMixin):
    """Real-time alerts dispatched to users."""
    __tablename__ = "alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    phone_number = Column(String(20), index=True)
    channel = Column(String(50), nullable=False)      # whatsapp | sms | push | email
    alert_type = Column(String(100), nullable=False)  # scam_call | counterfeit | fraud_network
    severity = Column(String(20), default="high")
    message = Column(Text, nullable=False)
    message_language = Column(String(10), default="en")
    reference_id = Column(String(100))               # scam_report_id or counterfeit_report_id
    delivered = Column(Boolean, default=False)
    delivered_at = Column(DateTime(timezone=True))
    twilio_sid = Column(String(100))

    user = relationship("User", back_populates="alerts")


class GeoCluster(Base, TimestampMixin):
    """Materialised geospatial crime cluster (refreshed hourly)."""
    __tablename__ = "geo_clusters"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    h3_index = Column(String(20), unique=True, nullable=False, index=True)
    h3_resolution = Column(Integer, default=7)
    center_lat = Column(Float, nullable=False)
    center_lng = Column(Float, nullable=False)
    city = Column(String(100))
    state = Column(String(100))
    scam_count_30d = Column(Integer, default=0)
    counterfeit_count_30d = Column(Integer, default=0)
    risk_score = Column(Float, default=0.0)
    dominant_fraud_type = Column(String(100))
    last_refreshed = Column(DateTime(timezone=True))


class AuditLog(Base):
    """Immutable audit trail for all AI decisions (legal admissibility)."""
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    action = Column(String(100), nullable=False, index=True)
    entity_type = Column(String(100))
    entity_id = Column(String(100))
    actor_id = Column(String(100))                   # user_id or "system"
    model_name = Column(String(100))
    model_version = Column(String(50))
    input_hash = Column(String(64))                  # SHA-256 of input (not raw input)
    output = Column(JSON)
    confidence = Column(Float)
    latency_ms = Column(Integer)
    ip_address = Column(String(45))


async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
=======

>>>>>>> 6e5223ae2cceedee56e5a13d0b46d847cd20c3df
