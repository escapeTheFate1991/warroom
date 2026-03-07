"""Centralized configuration — all secrets and environment variables in one place.

Uses pydantic-settings to read from environment variables.
Required secrets have NO defaults and will crash on startup if missing.
"""
import os
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """War Room application settings.

    Required variables (no defaults — app crashes if missing):
        JWT_SECRET, POSTGRES_URL, LEADGEN_DB_URL

    Optional variables have sensible defaults for local development.
    """

    # ── Secrets (REQUIRED — no fallback) ─────────────────────────────
    JWT_SECRET: str
    POSTGRES_URL: str  # CRM DB (also used as CRM_DB_URL)
    LEADGEN_DB_URL: str  # LeadGen / knowledge DB

    # ── OpenClaw credentials (REQUIRED) ──────────────────────────────
    OPENCLAW_AUTH_TOKEN: str = ""
    OPENCLAW_DEVICE_ID: str = ""
    OPENCLAW_DEVICE_PUBLIC_KEY: str = ""
    OPENCLAW_DEVICE_PRIVATE_KEY: str = ""

    # ── Service URLs ─────────────────────────────────────────────────
    OPENCLAW_WS_URL: str = "ws://10.0.0.1:18789"
    OPENCLAW_API_URL: str = "http://10.0.0.1:18789"
    KANBAN_API_URL: str = "http://10.0.0.11:18794"
    TEAM_DASHBOARD_URL: str = "http://10.0.0.11:18795"
    QDRANT_URL: str = "http://10.0.0.11:6333"
    FASTEMBED_URL: str = "http://10.0.0.11:11435"
    MENTAL_LIBRARY_API_URL: str = "http://10.0.0.1:8100"
    LEADGEN_BACKEND_URL: str = "http://10.0.0.1:8200"
    BACKEND_URL: str = "https://warroom.stuffnthings.io"
    FRONTEND_URL: str = "http://localhost:3300"

    # ── Whisper ──────────────────────────────────────────────────────
    WHISPER_HOST: str = "10.0.0.1"
    WHISPER_PORT: str = "18796"

    # ── Frontend build args ──────────────────────────────────────────
    NEXT_PUBLIC_WS_URL: str = "ws://192.168.1.94:18789"

    # ── Paths ────────────────────────────────────────────────────────
    MENTAL_LIBRARY_DB: str = "/data/mental-library/mental_library.db"

    # ── Admin seed ───────────────────────────────────────────────────
    ADMIN_PASSWORD: str = ""

    # Alias: CRM_DB_URL falls back to POSTGRES_URL
    @property
    def CRM_DB_URL(self) -> str:
        return os.getenv("CRM_DB_URL", self.POSTGRES_URL)

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


@lru_cache()
def get_settings() -> Settings:
    """Singleton settings instance — cached after first call."""
    return Settings()


# Convenience: importable singleton
settings = get_settings()

