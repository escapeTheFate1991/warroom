"""Centralized OAuth token storage — all tokens live in the DB, not temp files.

Usage:
    from app.services.token_store import load_tokens, save_tokens, delete_tokens

    tokens = await load_tokens("google_calendar")
    await save_tokens("google_calendar", {"access_token": "...", "refresh_token": "..."})
    await delete_tokens("google_calendar")

Tokens are stored in the `public.oauth_tokens` table as JSONB.
Table auto-created on first use.
"""
import json
import logging
from typing import Optional

from sqlalchemy import text

from app.db.leadgen_db import leadgen_engine, leadgen_session

logger = logging.getLogger(__name__)

# Uses shared leadgen engine (same knowledge DB, public schema)
_engine = leadgen_engine
_session = leadgen_session

_TABLE_CREATED = False


async def _ensure_table():
    """Create the oauth_tokens table if it doesn't exist."""
    global _TABLE_CREATED
    if _TABLE_CREATED:
        return
    async with _engine.begin() as conn:
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS public.oauth_tokens (
                service     VARCHAR(50) PRIMARY KEY,
                tokens      JSONB NOT NULL DEFAULT '{}',
                updated_at  TIMESTAMP DEFAULT now()
            )
        """))
    _TABLE_CREATED = True


async def load_tokens(service: str) -> Optional[dict]:
    """Load tokens for a service from the DB."""
    await _ensure_table()
    async with _session() as db:
        result = await db.execute(
            text("SELECT tokens FROM public.oauth_tokens WHERE service = :service"),
            {"service": service},
        )
        row = result.fetchone()
        if not row or not row[0]:
            return None
        data = row[0] if isinstance(row[0], dict) else json.loads(row[0])
        return data if data.get("access_token") or data.get("refresh_token") else None


async def save_tokens(service: str, tokens: dict) -> None:
    """Save tokens for a service to the DB (upsert)."""
    await _ensure_table()
    async with _session() as db:
        await db.execute(
            text("""
                INSERT INTO public.oauth_tokens (service, tokens, updated_at)
                VALUES (:service, CAST(:tokens AS jsonb), now())
                ON CONFLICT (service) DO UPDATE SET
                    tokens = CAST(:tokens AS jsonb),
                    updated_at = now()
            """),
            {"service": service, "tokens": json.dumps(tokens)},
        )
        await db.commit()
    logger.info("Tokens saved for service: %s", service)


async def delete_tokens(service: str) -> None:
    """Delete tokens for a service."""
    await _ensure_table()
    async with _session() as db:
        await db.execute(
            text("DELETE FROM public.oauth_tokens WHERE service = :service"),
            {"service": service},
        )
        await db.commit()
    logger.info("Tokens deleted for service: %s", service)
