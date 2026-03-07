"""Notification & alerting system for War Room.

Table: public.notifications
SSE: GET /api/notifications/stream (token via query param)
"""
import asyncio
import json
import logging
from datetime import datetime
from typing import Optional

import jwt
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.config import settings
from app.db.leadgen_db import leadgen_engine, leadgen_session

logger = logging.getLogger(__name__)

router = APIRouter()

# ── Database — uses shared leadgen engine (same knowledge DB, public schema)
notify_engine = leadgen_engine
notify_session = leadgen_session

VALID_TYPES = {"alert", "info", "success", "warning", "task", "lead", "calendar"}

JWT_SECRET = settings.JWT_SECRET
JWT_ALGORITHM = "HS256"


async def get_notify_db():
    """DB dependency — public schema."""
    async with leadgen_session() as session:
        yield session


# ── Table auto-creation ──────────────────────────────────────────────
async def init_notifications_table(engine):
    """Create notifications table if it doesn't exist."""
    async with engine.begin() as conn:
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS public.notifications (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                type VARCHAR(20) NOT NULL DEFAULT 'info',
                title TEXT NOT NULL,
                message TEXT,
                data JSONB DEFAULT '{}',
                read BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT NOW(),
                expires_at TIMESTAMP
            )
        """))
        # Index for common queries
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_notifications_user_read
            ON public.notifications (user_id, read, created_at DESC)
        """))
    logger.info("Notifications table initialized")


# ── Schemas ──────────────────────────────────────────────────────────
class NotificationCreate(BaseModel):
    user_id: Optional[int] = None
    type: str = Field(default="info", description="One of: alert, info, success, warning, task, lead, calendar")
    title: str
    message: Optional[str] = None
    data: Optional[dict] = Field(default_factory=dict)
    expires_at: Optional[datetime] = None


class NotificationOut(BaseModel):
    id: int
    user_id: int
    type: str
    title: str
    message: Optional[str]
    data: Optional[dict]
    read: bool
    created_at: datetime
    expires_at: Optional[datetime]


# ── Endpoints ────────────────────────────────────────────────────────

@router.get("/notifications")
async def list_notifications(
    request: Request,
    read: Optional[bool] = Query(None, description="Filter by read status"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_notify_db),
):
    """List notifications for the current user, newest first."""
    user_id = request.state.user_id
    offset = (page - 1) * limit

    conditions = ["user_id = :user_id"]
    params: dict = {"user_id": user_id, "limit": limit, "offset": offset}

    if read is not None:
        conditions.append("read = :read")
        params["read"] = read

    where = " AND ".join(conditions)

    # Get total count
    count_result = await db.execute(
        text(f"SELECT COUNT(*) FROM public.notifications WHERE {where}"), params
    )
    total = count_result.scalar()

    # Get page
    result = await db.execute(
        text(f"""
            SELECT id, user_id, type, title, message, data, read, created_at, expires_at
            FROM public.notifications
            WHERE {where}
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """),
        params,
    )
    rows = result.fetchall()

    return {
        "notifications": [
            NotificationOut(
                id=r.id, user_id=r.user_id, type=r.type, title=r.title,
                message=r.message, data=r.data, read=r.read,
                created_at=r.created_at, expires_at=r.expires_at,
            ).model_dump()
            for r in rows
        ],
        "total": total,
        "page": page,
        "limit": limit,
    }


@router.post("/notifications", status_code=201)
async def create_notification(
    body: NotificationCreate,
    request: Request,
    db: AsyncSession = Depends(get_notify_db),
):
    """Create a notification. user_id defaults to the caller if omitted."""
    if body.type not in VALID_TYPES:
        raise HTTPException(400, f"Invalid type '{body.type}'. Must be one of: {', '.join(sorted(VALID_TYPES))}")

    user_id = body.user_id or request.state.user_id

    result = await db.execute(
        text("""
            INSERT INTO public.notifications (user_id, type, title, message, data, expires_at)
            VALUES (:user_id, :type, :title, :message, CAST(:data AS jsonb), :expires_at)
            RETURNING id, user_id, type, title, message, data, read, created_at, expires_at
        """),
        {
            "user_id": user_id,
            "type": body.type,
            "title": body.title,
            "message": body.message,
            "data": json.dumps(body.data or {}),
            "expires_at": body.expires_at,
        },
    )
    await db.commit()
    r = result.fetchone()

    return NotificationOut(
        id=r.id, user_id=r.user_id, type=r.type, title=r.title,
        message=r.message, data=r.data, read=r.read,
        created_at=r.created_at, expires_at=r.expires_at,
    ).model_dump()


@router.patch("/notifications/{notification_id}/read")
async def mark_read(
    notification_id: int,
    request: Request,
    db: AsyncSession = Depends(get_notify_db),
):
    """Mark a single notification as read."""
    user_id = request.state.user_id
    result = await db.execute(
        text("""
            UPDATE public.notifications SET read = TRUE
            WHERE id = :id AND user_id = :user_id
            RETURNING id
        """),
        {"id": notification_id, "user_id": user_id},
    )
    await db.commit()
    if not result.fetchone():
        raise HTTPException(404, "Notification not found")
    return {"ok": True}


@router.post("/notifications/read-all")
async def mark_all_read(
    request: Request,
    db: AsyncSession = Depends(get_notify_db),
):
    """Mark all notifications as read for the current user."""
    user_id = request.state.user_id
    result = await db.execute(
        text("UPDATE public.notifications SET read = TRUE WHERE user_id = :user_id AND read = FALSE"),
        {"user_id": user_id},
    )
    await db.commit()
    return {"ok": True, "updated": result.rowcount}


@router.delete("/notifications/{notification_id}")
async def delete_notification(
    notification_id: int,
    request: Request,
    db: AsyncSession = Depends(get_notify_db),
):
    """Delete a notification."""
    user_id = request.state.user_id
    result = await db.execute(
        text("DELETE FROM public.notifications WHERE id = :id AND user_id = :user_id RETURNING id"),
        {"id": notification_id, "user_id": user_id},
    )
    await db.commit()
    if not result.fetchone():
        raise HTTPException(404, "Notification not found")
    return {"ok": True}


# ── SSE Stream ───────────────────────────────────────────────────────

def _validate_sse_token(token: str) -> dict | None:
    """Validate JWT from query param for SSE connections."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if not payload.get("user_id"):
            return None
        return payload
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


@router.get("/notifications/stream")
async def notification_stream(
    request: Request,
    token: str = Query(None, description="JWT token (EventSource can't set headers)"),
):
    """SSE endpoint — polls for new notifications every 3 seconds.

    Auth via ?token=xxx since EventSource API can't set Authorization headers.
    Also falls back to header-based auth if available (path is public in middleware).
    """
    # Try query param token first, then fall back to header
    user_id = None
    if token:
        payload = _validate_sse_token(token)
        if payload:
            user_id = payload["user_id"]

    if not user_id:
        # Try header (in case middleware already parsed it)
        user_id = getattr(request.state, "user_id", None)

    if not user_id:
        raise HTTPException(401, "Valid token required for SSE stream")

    async def event_generator():
        """Yield new unread notifications as SSE events."""
        last_id = 0
        while True:
            if await request.is_disconnected():
                break

            try:
                async with notify_session() as db:
                    result = await db.execute(
                        text("""
                            SELECT id, user_id, type, title, message, data, read, created_at, expires_at
                            FROM public.notifications
                            WHERE user_id = :user_id AND id > :last_id AND read = FALSE
                            ORDER BY id ASC
                            LIMIT 20
                        """),
                        {"user_id": user_id, "last_id": last_id},
                    )
                    rows = result.fetchall()

                if rows:
                    last_id = rows[-1].id
                    for r in rows:
                        n = NotificationOut(
                            id=r.id, user_id=r.user_id, type=r.type, title=r.title,
                            message=r.message, data=r.data, read=r.read,
                            created_at=r.created_at, expires_at=r.expires_at,
                        )
                        yield {"event": "notification", "data": json.dumps(n.model_dump(), default=str)}
                else:
                    yield {"event": "ping", "data": ""}

            except asyncio.CancelledError:
                logger.debug("SSE stream cancelled for user %s", user_id)
                return
            except Exception as e:
                logger.error("SSE poll error: %s", e)
                yield {"event": "error", "data": str(e)}

            await asyncio.sleep(3)

    return EventSourceResponse(event_generator())
