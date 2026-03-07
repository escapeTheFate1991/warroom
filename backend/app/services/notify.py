"""Notification helper — fire-and-forget notifications from any module.

Usage:
    from app.services.notify import send_notification

    await send_notification(
        type="lead",
        title="New Lead Found",
        message="Acme Corp — Hot lead, 85 score",
        data={"lead_id": 123, "link": "/leadgen"},
    )
"""
import json
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
import os

logger = logging.getLogger(__name__)

NOTIFY_DB_URL = os.getenv(
    "NOTIFY_DB_URL",
    "postgresql+asyncpg://friday:friday-brain2-2026@10.0.0.11:5433/knowledge",
)

_engine = create_async_engine(NOTIFY_DB_URL, echo=False, pool_size=3, max_overflow=5)
_session = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)

VALID_TYPES = {"alert", "info", "success", "warning", "task", "lead", "calendar"}


async def send_notification(
    *,
    type: str = "info",
    title: str,
    message: str = "",
    data: Optional[dict] = None,
    user_id: int = 1,
    expires_at: Optional[datetime] = None,
) -> Optional[int]:
    """Insert a notification into public.notifications.

    Returns the notification id on success, None on failure.
    Never raises — all errors are caught and logged so callers are never broken.
    """
    try:
        if type not in VALID_TYPES:
            logger.warning("Invalid notification type '%s', defaulting to 'info'", type)
            type = "info"

        async with _session() as db:
            result = await db.execute(
                text("""
                    INSERT INTO public.notifications (user_id, type, title, message, data, expires_at)
                    VALUES (:user_id, :type, :title, :message, CAST(:data AS jsonb), :expires_at)
                    RETURNING id
                """),
                {
                    "user_id": user_id,
                    "type": type,
                    "title": title,
                    "message": message,
                    "data": json.dumps(data or {}),
                    "expires_at": expires_at,
                },
            )
            row = result.fetchone()
            await db.commit()
            notif_id = row[0] if row else None
            logger.info("Notification created: [%s] %s (id=%s)", type, title, notif_id)
            return notif_id
    except Exception as exc:
        logger.error("Failed to create notification [%s] %s: %s", type, title, exc)
        return None
