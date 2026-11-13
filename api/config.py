"""
api/config.py
-------------
Application settings loaded from environment variables / .env file.
Defaults to local SQLite if DATABASE_URL is not set or PostgreSQL is unavailable.
"""

from __future__ import annotations
import os
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All application configuration, read from environment variables or .env."""

    # ── App ────────────────────────────────────────────────────────────────
    app_name: str = "GradeMatrix AI API"
    app_version: str = "1.0.0"
    debug: bool = False

    # ── Database ───────────────────────────────────────────────────────────
    # Local SQLite fallback for zero-configuration, instant execution without Docker
    database_url: str = "sqlite+aiosqlite:///student_predictor.db"
    database_url_sync: str = "sqlite:///student_predictor.db"

    # ── JWT Auth ───────────────────────────────────────────────────────────
    secret_key: str = "super-secret-key-change-in-production-12345"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7

    # ── ML Models ──────────────────────────────────────────────────────────
    early_model_path: str = "models/early_model.joblib"
    mid_model_path: str = "models/mid_model.joblib"

    # ── CORS ───────────────────────────────────────────────────────────────
    allowed_origins: list[str] = [
        "http://localhost:8501",
        "http://localhost:3000",
        "*",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Cached singleton - returns the same Settings instance on every call."""
    return Settings()
