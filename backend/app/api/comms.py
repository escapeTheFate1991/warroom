"""Communications Hub API — unified call logs, SMS, and email records.

Aggregates from: call_intakes, Twilio API, email_messages, CRM activities.
Supports filtering by contact, organization, employee, AI agent, direction.
Full-text fuzzy search across call transcripts and message content.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.leadgen_db import leadgen_session
from app.db.crm_db import get_crm_db

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Schemas ──────────────────────────────────────────────────────────

class CommRecord(BaseModel):
    id: str
    type: str  # call, sms, email
    direction: str  # inbound, outbound
    status: str  # completed, failed, no-answer, sent, delivered, bounced
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    organization: Optional[str] = None
    employee: Optional[str] = None  # team member involved
    agent: Optional[str] = None  # AI agent involved
    subject: Optional[str] = None
    summary: Optional[str] = None  # short summary or first line
    transcript: Optional[str] = None  # full content for calls/SMS/email
    pain_points: Optional[str] = None
    services: Optional[str] = None
    schedule_pref: Optional[str] = None
    duration_seconds: Optional[int] = None
    occurred_at: str
    metadata: dict = Field(default_factory=dict)


class CommsListResponse(BaseModel):
    items: list[CommRecord]
    total: int
    page: int
    per_page: int


# ── Call Logs from call_intakes ──────────────────────────────────────

async def _get_call_records(
    search: str | None = None,
    contact_name: str | None = None,
    status: str | None = None,
    direction: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[CommRecord], int]:
    """Fetch call records from call_intakes table."""
    records: list[CommRecord] = []

    where_clauses = ["1=1"]
    params: dict = {"limit": limit, "offset": offset}

    if contact_name:
        where_clauses.append("ci.contact_name ILIKE :contact_name")
        params["contact_name"] = f"%{contact_name}%"

    if status:
        where_clauses.append("ci.call_status = :status")
        params["status"] = status

    if search:
        where_clauses.append("""(
            ci.contact_name ILIKE :search
            OR ci.pain_points ILIKE :search
            OR ci.services ILIKE :search
            OR ci.schedule_pref ILIKE :search
            OR ci.contact_phone ILIKE :search
            OR ci.contact_email ILIKE :search
            OR cs.message ILIKE :search
            OR cs.business_name ILIKE :search
        )""")
        params["search"] = f"%{search}%"

    where_sql = " AND ".join(where_clauses)

    async with leadgen_session() as db:
        # Count
        count_result = await db.execute(
            text(f"""
                SELECT COUNT(*) FROM public.call_intakes ci
                LEFT JOIN public.contact_submissions cs ON cs.id = ci.submission_id
                WHERE {where_sql}
            """),
            params,
        )
        total = count_result.scalar() or 0

        # Fetch
        result = await db.execute(
            text(f"""
                SELECT
                    ci.id, ci.call_sid, ci.contact_name, ci.contact_phone,
                    ci.contact_email, ci.pain_points, ci.services,
                    ci.schedule_pref, ci.call_status, ci.started_at, ci.completed_at,
                    cs.name AS submission_name, cs.email AS submission_email,
                    cs.phone AS submission_phone, cs.message AS submission_message,
                    cs.business_name
                FROM public.call_intakes ci
                LEFT JOIN public.contact_submissions cs ON cs.id = ci.submission_id
                WHERE {where_sql}
                ORDER BY ci.started_at DESC
                LIMIT :limit OFFSET :offset
            """),
            params,
        )
        rows = result.fetchall()

        for row in rows:
            r = dict(row._mapping)
            # Build transcript from available data
            transcript_parts = []
            if r.get("pain_points"):
                transcript_parts.append(f"Pain Points: {r['pain_points']}")
            if r.get("services"):
                transcript_parts.append(f"Services: {r['services']}")
            if r.get("schedule_pref"):
                transcript_parts.append(f"Scheduling: {r['schedule_pref']}")

            duration = None
            if r.get("started_at") and r.get("completed_at"):
                duration = int((r["completed_at"] - r["started_at"]).total_seconds())

            records.append(CommRecord(
                id=f"call-{r['id']}",
                type="call",
                direction="outbound",
                status=r.get("call_status") or "unknown",
                contact_name=r.get("contact_name") or r.get("submission_name"),
                contact_phone=r.get("contact_phone") or r.get("submission_phone"),
                contact_email=r.get("contact_email") or r.get("submission_email"),
                organization=r.get("business_name"),
                employee=None,
                agent="AI Intake",
                subject=f"AI Intake Call — {r.get('contact_name') or 'Unknown'}",
                summary=(r.get("pain_points") or "")[:100] or (r.get("submission_message") or "")[:100] or None,
                transcript="\n".join(transcript_parts) if transcript_parts else None,
                pain_points=r.get("pain_points"),
                services=r.get("services"),
                schedule_pref=r.get("schedule_pref"),
                duration_seconds=duration,
                occurred_at=r["started_at"].isoformat() if r.get("started_at") else datetime.now(timezone.utc).isoformat(),
                metadata={"call_sid": r.get("call_sid"), "submission_message": r.get("submission_message")},
            ))

    return records, total


# ── SMS Logs from Twilio ─────────────────────────────────────────────

async def _get_sms_records(
    search: str | None = None,
    direction: str | None = None,
    limit: int = 20,
) -> list[CommRecord]:
    """Fetch recent SMS records from Twilio API."""
    records: list[CommRecord] = []
    try:
        from app.services.twilio_client import get_sms_logs
        sms_logs = await get_sms_logs(limit=limit)

        for sms in sms_logs:
            sms_direction = "outbound" if sms.get("direction", "").startswith("outbound") else "inbound"

            if direction and sms_direction != direction:
                continue

            body = sms.get("body", "")
            if search and search.lower() not in body.lower():
                continue

            records.append(CommRecord(
                id=f"sms-{sms.get('sid', '')}",
                type="sms",
                direction=sms_direction,
                status=sms.get("status", "unknown"),
                contact_name=None,
                contact_phone=sms.get("to") if sms_direction == "outbound" else sms.get("from"),
                contact_email=None,
                organization=None,
                employee=None,
                agent="System",
                subject=None,
                summary=body[:100] if body else None,
                transcript=body,
                occurred_at=sms.get("date_created", datetime.now(timezone.utc).isoformat()),
                metadata={"sid": sms.get("sid")},
            ))
    except Exception as exc:
        logger.warning("Failed to fetch Twilio SMS logs: %s", exc)

    return records


# ── Email Logs from DB ───────────────────────────────────────────────

async def _get_email_records(
    search: str | None = None,
    direction: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[CommRecord], int]:
    """Fetch email records from email_messages table."""
    records: list[CommRecord] = []

    where_clauses = ["1=1"]
    params: dict = {"limit": limit, "offset": offset}

    if search:
        where_clauses.append("(subject ILIKE :search OR body_text ILIKE :search OR from_address ILIKE :search OR to_addresses::text ILIKE :search)")
        params["search"] = f"%{search}%"

    where_sql = " AND ".join(where_clauses)

    try:
        async with leadgen_session() as db:
            count_result = await db.execute(
                text(f"SELECT COUNT(*) FROM public.email_messages WHERE {where_sql}"),
                params,
            )
            total = count_result.scalar() or 0

            result = await db.execute(
                text(f"""
                    SELECT id, account_id, message_id, subject, from_address, to_addresses,
                           body_text, received_at, is_read
                    FROM public.email_messages
                    WHERE {where_sql}
                    ORDER BY received_at DESC
                    LIMIT :limit OFFSET :offset
                """),
                params,
            )
            for row in result.fetchall():
                r = dict(row._mapping)
                records.append(CommRecord(
                    id=f"email-{r['id']}",
                    type="email",
                    direction="inbound",
                    status="delivered",
                    contact_name=None,
                    contact_phone=None,
                    contact_email=r.get("from_address"),
                    organization=None,
                    employee=None,
                    agent=None,
                    subject=r.get("subject"),
                    summary=(r.get("body_text") or "")[:100],
                    transcript=r.get("body_text"),
                    occurred_at=r["received_at"].isoformat() if r.get("received_at") else datetime.now(timezone.utc).isoformat(),
                    metadata={"message_id": r.get("message_id"), "is_read": r.get("is_read")},
                ))
    except Exception as exc:
        logger.warning("Failed to fetch email records: %s", exc)
        total = 0

    return records, total


# ── Unified Endpoint ─────────────────────────────────────────────────

@router.get("/logs", response_model=CommsListResponse)
async def get_comms_logs(
    search: Optional[str] = Query(None, description="Fuzzy search across transcripts and content"),
    type: Optional[str] = Query(None, description="Filter: call, sms, email"),
    contact: Optional[str] = Query(None, description="Filter by contact name"),
    organization: Optional[str] = Query(None, description="Filter by organization"),
    direction: Optional[str] = Query(None, description="Filter: inbound, outbound"),
    status: Optional[str] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
):
    """Unified communications log — calls, SMS, emails with filtering and search."""
    offset = (page - 1) * per_page
    all_records: list[CommRecord] = []
    total = 0

    # Fetch by type (or all)
    if not type or type == "call":
        calls, call_total = await _get_call_records(
            search=search, contact_name=contact, status=status,
            direction=direction, limit=per_page, offset=offset,
        )
        all_records.extend(calls)
        total += call_total

    if not type or type == "sms":
        sms_records = await _get_sms_records(search=search, direction=direction, limit=per_page)
        all_records.extend(sms_records)
        total += len(sms_records)

    if not type or type == "email":
        email_records, email_total = await _get_email_records(
            search=search, direction=direction, limit=per_page, offset=offset,
        )
        all_records.extend(email_records)
        total += email_total

    # Post-filter by organization if specified
    if organization:
        all_records = [r for r in all_records if r.organization and organization.lower() in r.organization.lower()]

    # Sort by most recent
    all_records.sort(key=lambda r: r.occurred_at, reverse=True)

    # Paginate
    page_records = all_records[:per_page]

    return CommsListResponse(
        items=page_records,
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/logs/{record_id}")
async def get_comm_detail(record_id: str):
    """Get full detail for a single communication record."""
    parts = record_id.split("-", 1)
    if len(parts) != 2:
        raise HTTPException(status_code=400, detail="Invalid record ID format")

    record_type, record_pk = parts[0], parts[1]

    if record_type == "call":
        async with leadgen_session() as db:
            result = await db.execute(
                text("""
                    SELECT ci.*, cs.name AS submission_name, cs.email AS submission_email,
                           cs.phone AS submission_phone, cs.message AS submission_message,
                           cs.business_name
                    FROM public.call_intakes ci
                    LEFT JOIN public.contact_submissions cs ON cs.id = ci.submission_id
                    WHERE ci.id = :id
                """),
                {"id": int(record_pk)},
            )
            row = result.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Call record not found")
            return dict(row._mapping)

    elif record_type == "email":
        async with leadgen_session() as db:
            result = await db.execute(
                text("SELECT * FROM public.email_messages WHERE id = :id"),
                {"id": int(record_pk)},
            )
            row = result.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Email record not found")
            return dict(row._mapping)

    raise HTTPException(status_code=400, detail=f"Unknown record type: {record_type}")
