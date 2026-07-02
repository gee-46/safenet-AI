<<<<<<< HEAD
"""
SafeNet AI – Core Configuration
Centralised settings loaded from environment / .env file.
"""
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────
    app_name: str = "SafeNet AI"
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_secret_key: str = "CHANGE_ME"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    debug: bool = True

    # ── CORS ─────────────────────────────────────────────────────
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:8080"]

    # ── PostgreSQL ────────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://safenet_user:safenet_pass@localhost:5432/safenet"

    # ── Redis ─────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # ── Neo4j ─────────────────────────────────────────────────────
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "neo4j_pass"

    # ── Qdrant ────────────────────────────────────────────────────
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection: str = "safenet_docs"

    # ── OpenAI ───────────────────────────────────────────────────
    openai_api_key: Optional[str] = None

    # ── Model Paths ──────────────────────────────────────────────
    scam_model_path: str = "./ml_training/scam/checkpoints/best_model"
    counterfeit_model_path: str = "./ml_training/counterfeit/checkpoints/best_yolo.pt"
    fraud_gnn_model_path: str = "./ml_training/fraud_graph/checkpoints/best_gnn.pt"
    whisper_model_size: str = "base"

    # ── Twilio ───────────────────────────────────────────────────
    twilio_account_sid: Optional[str] = None
    twilio_auth_token: Optional[str] = None
    twilio_whatsapp_from: str = "whatsapp:+14155238886"
    twilio_sms_from: Optional[str] = None

    # ── Mapbox ───────────────────────────────────────────────────
    mapbox_token: Optional[str] = None

    # ── Rate Limiting ─────────────────────────────────────────────
    rate_limit_calls_per_minute: int = 60
    rate_limit_burst: int = 10

    # ── Detection Thresholds ─────────────────────────────────────
    scam_confidence_threshold: float = 0.72
    counterfeit_confidence_threshold: float = 0.85
    fraud_graph_alert_threshold: float = 0.80

    # ── Data Paths ───────────────────────────────────────────────
    ncrb_data_path: str = "./data/ncrb"
    rbi_currency_data_path: str = "./data/rbi"

    @field_validator("app_env")
    @classmethod
    def validate_env(cls, v: str) -> str:
        allowed = {"development", "staging", "production"}
        if v not in allowed:
            raise ValueError(f"app_env must be one of {allowed}")
        return v

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def base_dir(self) -> Path:
        return Path(__file__).resolve().parent.parent


@lru_cache
def get_settings() -> Settings:
    """Return cached singleton Settings instance."""
    return Settings()
=======

>>>>>>> 6e5223ae2cceedee56e5a13d0b46d847cd20c3df
