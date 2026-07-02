"""
SafeNet AI – Pydantic Schemas
Request / response models for all API endpoints.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


# ── Enums ─────────────────────────────────────────────────────────

class ScamType(str, Enum):
    DIGITAL_ARREST = "digital_arrest"
    LOAN_FRAUD = "loan_fraud"
    LOTTERY = "lottery"
    KYC_UPDATE = "kyc_update"
    IMPERSONATION = "impersonation"
    INVESTMENT = "investment"
    ROMANCE = "romance"
    TECH_SUPPORT = "tech_support"
    UNKNOWN = "unknown"


class Verdict(str, Enum):
    GENUINE = "genuine"
    COUNTERFEIT = "counterfeit"
    UNCERTAIN = "uncertain"


class AlertChannel(str, Enum):
    WHATSAPP = "whatsapp"
    SMS = "sms"
    PUSH = "push"
    EMAIL = "email"


class UserRole(str, Enum):
    CITIZEN = "citizen"
    OFFICER = "officer"
    ANALYST = "analyst"
    ADMIN = "admin"


# ── Shared ────────────────────────────────────────────────────────

class GeoPoint(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)


class PaginationParams(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)


# ── Auth ─────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    email: EmailStr
    phone: str = Field(..., pattern=r"^\+?[1-9]\d{9,14}$")
    password: str = Field(..., min_length=8)
    role: UserRole = UserRole.CITIZEN
    language_preference: str = "en"


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    phone: Optional[str]
    role: str
    language_preference: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Scam Detection ────────────────────────────────────────────────

class CallMetadataIn(BaseModel):
    """
    Metadata from a phone call — deliberately no raw audio.
    Telecom operators or our mobile app extract these fields.
    """
    caller_number: str = Field(..., description="E.164 format")
    victim_number: str
    call_duration_seconds: Optional[int] = None
    # Timing/flow features extracted at source
    ring_pattern: Optional[str] = None          # e.g. "short-gap-long"
    silence_ratio: Optional[float] = None       # fraction of call in silence
    speech_rate_wpm: Optional[float] = None     # words per minute
    number_spoofing_detected: Optional[bool] = None
    caller_location_reported: Optional[str] = None
    # Optional transcript snippet (first 500 chars, not full audio)
    transcript_snippet: Optional[str] = Field(None, max_length=500)
    location: Optional[GeoPoint] = None
    device_id: Optional[str] = None


class ScamDetectionResponse(BaseModel):
    report_id: uuid.UUID
    caller_number: str
    victim_number: str
    scam_type: ScamType
    confidence_score: float = Field(..., ge=0, le=1)
    is_scam: bool
    risk_level: str                 # low | medium | high | critical
    patterns_matched: List[str]
    recommended_action: str
    alert_sent: bool
    processing_time_ms: int


class ScamReportOut(BaseModel):
    id: uuid.UUID
    caller_number: str
    scam_type: str
    confidence_score: float
    status: str
    city: Optional[str]
    state: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Counterfeit Detection ─────────────────────────────────────────

class CounterfeitAnalysisResponse(BaseModel):
    report_id: uuid.UUID
    denomination: int
    verdict: Verdict
    confidence_score: float = Field(..., ge=0, le=1)
    defects_detected: List[str]
    security_checks: Dict[str, float]   # check_name → score (0-1)
    serial_number_valid: Optional[bool]
    serial_number_pattern: Optional[str]
    recommendation: str
    reported_to_rbi: bool
    processing_time_ms: int


# ── Fraud Graph ───────────────────────────────────────────────────

class EntityType(str, Enum):
    PHONE_NUMBER = "phone_number"
    BANK_ACCOUNT = "bank_account"
    DEVICE = "device"
    IP_ADDRESS = "ip_address"
    PERSON = "person"
    ORGANISATION = "organisation"


class FraudGraphNode(BaseModel):
    id: str
    type: EntityType
    label: str
    risk_score: float
    fraud_count: int
    first_seen: Optional[datetime]
    last_seen: Optional[datetime]
    attributes: Dict[str, Any] = {}


class FraudGraphEdge(BaseModel):
    source: str
    target: str
    relationship: str       # CALLED | TRANSFERRED_TO | SHARED_DEVICE | MULE_LINK
    weight: float
    transaction_count: Optional[int]
    total_amount_inr: Optional[float]
    first_seen: Optional[datetime]
    last_seen: Optional[datetime]


class FraudGraphResponse(BaseModel):
    entity_id: str
    entity_type: EntityType
    risk_score: float
    fraud_network_size: int
    nodes: List[FraudGraphNode]
    edges: List[FraudGraphEdge]
    connected_cases: List[str]
    states_involved: List[str]
    recommended_action: str


class FraudNetworkIn(BaseModel):
    entity_id: str
    entity_type: EntityType
    depth: int = Field(2, ge=1, le=4)   # graph traversal depth
    max_nodes: int = Field(50, ge=5, le=200)


# ── Geospatial ────────────────────────────────────────────────────

class HeatmapParams(BaseModel):
    bbox: Optional[List[float]] = Field(
        None,
        description="[min_lng, min_lat, max_lng, max_lat]",
        min_length=4, max_length=4,
    )
    h3_resolution: int = Field(7, ge=4, le=10)
    days_back: int = Field(30, ge=1, le=365)
    fraud_types: Optional[List[str]] = None
    state: Optional[str] = None


class HeatmapCluster(BaseModel):
    h3_index: str
    center: GeoPoint
    city: Optional[str]
    state: Optional[str]
    scam_count: int
    counterfeit_count: int
    risk_score: float
    dominant_fraud_type: Optional[str]


class HeatmapResponse(BaseModel):
    clusters: List[HeatmapCluster]
    total_incidents: int
    generated_at: datetime
    bbox_used: Optional[List[float]]


# ── Citizen Shield ────────────────────────────────────────────────

class CitizenAssessIn(BaseModel):
    message: str = Field(..., max_length=2000)
    phone_number: Optional[str] = None
    language: str = "en"
    context_type: str = "call"   # call | sms | payment | job_offer | other


class CitizenAssessResponse(BaseModel):
    risk_level: str            # safe | suspicious | high_risk | scam
    confidence: float
    explanation: str
    recommended_actions: List[str]
    report_url: Optional[str]
    helpline_number: str = "1930"    # MHA Cybercrime helpline
    response_language: str


# ── Evidence Package ──────────────────────────────────────────────

class EvidencePackageRequest(BaseModel):
    case_id: Optional[uuid.UUID] = None
    scam_report_ids: Optional[List[uuid.UUID]] = None
    include_graph: bool = True
    include_timeline: bool = True
    include_regulatory_sections: bool = True


class EvidencePackageResponse(BaseModel):
    package_id: uuid.UUID
    case_number: str
    pdf_url: str
    generated_at: datetime
    pages: int
    crpc_sections: List[str]
    it_act_sections: List[str]


# ── Analytics ─────────────────────────────────────────────────────

class DashboardStats(BaseModel):
    total_scam_detections_30d: int
    total_counterfeit_reports_30d: int
    active_fraud_cases: int
    alerts_sent_30d: int
    estimated_loss_prevented_inr: float
    top_scam_types: List[Dict[str, Any]]
    top_states: List[Dict[str, Any]]
    detection_accuracy: float
    avg_detection_latency_ms: float
