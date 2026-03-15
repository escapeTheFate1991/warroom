"""Communications Hub API — unified call logs, SMS, and email records.

Aggregates from: call_intakes, Twilio API, email_messages, outbound_emails, CRM activities.
Supports filtering by contact, organization, employee, AI agent, direction.
Full-text fuzzy search across call transcripts and message content.
CRM person linking for contact history.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.leadgen_db import leadgen_engine, leadgen_session
from app.db.crm_db import get_tenant_db
from app.services.tenant import get_org_id, get_user_id

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
    person_id: Optional[int] = None  # CRM person FK
    occurred_at: str
    metadata: dict = Field(default_factory=dict)


class CommsListResponse(BaseModel):
    items: list[CommRecord]
    total: int
    page: int
    per_page: int


class SendEmailRequest(BaseModel):
    to: str
    subject: str = "Message from War Room"
    body: str


class SendEmailResponse(BaseModel):
    ok: bool
    message: str


# ── Outbound Emails Table ────────────────────────────────────────────

OUTBOUND_EMAILS_DDL = """
CREATE TABLE IF NOT EXISTS public.outbound_emails (
    id SERIAL PRIMARY KEY,
    to_address TEXT NOT NULL,
    from_address TEXT DEFAULT 'hello@stuffnthings.io',
    subject TEXT,
    body_text TEXT,
    status VARCHAR(20) DEFAULT 'sent',
    person_id INTEGER,
    sent_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);
"""

OUTBOUND_EMAILS_INDEX = """
CREATE INDEX IF NOT EXISTS idx_outbound_emails_to ON public.outbound_emails (to_address);
"""


async def init_outbound_emails_table():
    """Auto-create outbound_emails table on startup."""
    try:
        async with leadgen_engine.begin() as conn:
            await conn.execute(text(OUTBOUND_EMAILS_DDL))
            await conn.execute(text(OUTBOUND_EMAILS_INDEX))
        logger.info("outbound_emails table ready")
    except Exception as e:
        logger.error("Failed to init outbound_emails table: %s", e)


async def log_outbound_email(
    to_address: str,
    subject: str,
    body_text: str,
    from_address: str = "hello@stuffnthings.io",
    person_id: int | None = None,
) -> int | None:
    """Insert a record into outbound_emails. Returns the new row ID."""
    try:
        async with leadgen_session() as db:
            result = await db.execute(
                text("""
                    INSERT INTO public.outbound_emails
                        (to_address, from_address, subject, body_text, person_id)
                    VALUES (:to, :from_addr, :subject, :body, :person_id)
                    RETURNING id
                """),
                {
                    "to": to_address,
                    "from_addr": from_address,
                    "subject": subject,
                    "body": body_text,
                    "person_id": person_id,
                },
            )
            row = result.fetchone()
            await db.commit()
            return row[0] if row else None
    except Exception as exc:
        logger.error("Failed to log outbound email to %s: %s", to_address, exc)
        return None


# ── CRM Person Matching ──────────────────────────────────────────────

async def _match_crm_person(phone: str | None, email: str | None) -> tuple[int | None, str | None, str | None]:
    """Try to match a phone/email to a CRM person. Returns (person_id, person_name, org_name)."""
    if not phone and not email:
        return None, None, None

    try:
        from app.db.crm_db import crm_session
        async with crm_session() as db:
            await db.execute(text("SET search_path TO crm, public"))

            conditions = []
            params: dict = {}

            if phone:
                # Strip non-digits for matching
                clean_phone = phone.lstrip("+").replace("-", "").replace(" ", "").replace("(", "").replace(")", "")
                conditions.append(
                    "EXISTS (SELECT 1 FROM jsonb_array_elements(p.contact_numbers) cn WHERE REPLACE(REPLACE(REPLACE(REPLACE(cn->>'value', '-', ''), ' ', ''), '(', ''), ')', '') LIKE '%' || :phone)"
                )
                params["phone"] = clean_phone[-10:]  # last 10 digits

            if email:
                conditions.append(
                    "EXISTS (SELECT 1 FROM jsonb_array_elements(p.emails) em WHERE LOWER(em->>'value') = LOWER(:email))"
                )
                params["email"] = email

            if not conditions:
                return None, None, None

            where = " OR ".join(conditions)
            result = await db.execute(
                text(f"""
                    SELECT p.id, p.name, o.name AS org_name
                    FROM crm.persons p
                    LEFT JOIN crm.organizations o ON o.id = p.organization_id
                    WHERE {where}
                    LIMIT 1
                """),
                params,
            )
            row = result.fetchone()
            if row:
                return row[0], row[1], row[2]
    except Exception as exc:
        logger.debug("CRM person match failed: %s", exc)

    return None, None, None


async def _enrich_records_with_crm(records: list[CommRecord]) -> list[CommRecord]:
    """Batch-enrich comm records with CRM person data."""
    for record in records:
        person_id, person_name, org_name = await _match_crm_person(
            record.contact_phone, record.contact_email
        )
        if person_id:
            record.person_id = person_id
            if not record.contact_name and person_name:
                record.contact_name = person_name
            if not record.organization and org_name:
                record.organization = org_name
    return records


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
                    ci.person_id,
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
                person_id=r.get("person_id"),
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
    """Fetch email records from email_messages (inbound) + outbound_emails tables."""
    records: list[CommRecord] = []
    total = 0

    # ── Inbound emails from email_messages ──
    if not direction or direction == "inbound":
        inbound_where = ["1=1"]
        inbound_params: dict = {"limit": limit, "offset": offset}

        if search:
            inbound_where.append("(subject ILIKE :search OR body_text ILIKE :search OR from_address ILIKE :search OR to_addresses::text ILIKE :search)")
            inbound_params["search"] = f"%{search}%"

        inbound_sql = " AND ".join(inbound_where)

        try:
            async with leadgen_session() as db:
                count_result = await db.execute(
                    text(f"SELECT COUNT(*) FROM public.email_messages WHERE {inbound_sql}"),
                    inbound_params,
                )
                inbound_total = count_result.scalar() or 0
                total += inbound_total

                result = await db.execute(
                    text(f"""
                        SELECT id, account_id, message_id, subject, from_address, to_addresses,
                               body_text, received_at, is_read
                        FROM public.email_messages
                        WHERE {inbound_sql}
                        ORDER BY received_at DESC
                        LIMIT :limit OFFSET :offset
                    """),
                    inbound_params,
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
            logger.warning("Failed to fetch inbound email records: %s", exc)

    # ── Outbound emails from outbound_emails ──
    if not direction or direction == "outbound":
        outbound_where = ["1=1"]
        outbound_params: dict = {"limit": limit, "offset": offset}

        if search:
            outbound_where.append("(subject ILIKE :search OR body_text ILIKE :search OR to_address ILIKE :search)")
            outbound_params["search"] = f"%{search}%"

        outbound_sql = " AND ".join(outbound_where)

        try:
            async with leadgen_session() as db:
                count_result = await db.execute(
                    text(f"SELECT COUNT(*) FROM public.outbound_emails WHERE {outbound_sql}"),
                    outbound_params,
                )
                outbound_total = count_result.scalar() or 0
                total += outbound_total

                result = await db.execute(
                    text(f"""
                        SELECT id, to_address, from_address, subject, body_text, status,
                               person_id, sent_at
                        FROM public.outbound_emails
                        WHERE {outbound_sql}
                        ORDER BY sent_at DESC
                        LIMIT :limit OFFSET :offset
                    """),
                    outbound_params,
                )
                for row in result.fetchall():
                    r = dict(row._mapping)
                    records.append(CommRecord(
                        id=f"email-out-{r['id']}",
                        type="email",
                        direction="outbound",
                        status=r.get("status") or "sent",
                        contact_name=None,
                        contact_phone=None,
                        contact_email=r.get("to_address"),
                        organization=None,
                        employee=None,
                        agent=None,
                        subject=r.get("subject"),
                        summary=(r.get("body_text") or "")[:100],
                        transcript=r.get("body_text"),
                        person_id=r.get("person_id"),
                        occurred_at=r["sent_at"].isoformat() if r.get("sent_at") else datetime.now(timezone.utc).isoformat(),
                        metadata={"from_address": r.get("from_address")},
                    ))
        except Exception as exc:
            logger.warning("Failed to fetch outbound email records: %s", exc)

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

    # Enrich with CRM person data
    all_records = await _enrich_records_with_crm(all_records)

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
        # Handle both inbound and outbound
        if record_pk.startswith("out-"):
            real_pk = record_pk[4:]
            async with leadgen_session() as db:
                result = await db.execute(
                    text("SELECT * FROM public.outbound_emails WHERE id = :id"),
                    {"id": int(real_pk)},
                )
                row = result.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="Outbound email record not found")
                return dict(row._mapping)
        else:
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


# ── Contact History by CRM Person ────────────────────────────────────

@router.get("/contacts/{person_id}/history", response_model=CommsListResponse)
async def get_contact_history(
    person_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
):
    """Get all communications for a specific CRM person, ordered chronologically."""
    # First, get the person's contact info from CRM
    from app.db.crm_db import crm_session
    phone_values: list[str] = []
    email_values: list[str] = []

    try:
        async with crm_session() as db:
            await db.execute(text("SET search_path TO crm, public"))
            result = await db.execute(
                text("SELECT name, emails, contact_numbers FROM crm.persons WHERE id = :pid"),
                {"pid": person_id},
            )
            person = result.fetchone()
            if not person:
                raise HTTPException(status_code=404, detail="CRM person not found")

            p = dict(person._mapping)
            # Extract all email addresses
            if p.get("emails") and isinstance(p["emails"], list):
                for em in p["emails"]:
                    if isinstance(em, dict) and em.get("value"):
                        email_values.append(em["value"].lower())
            # Extract all phone numbers (clean to digits)
            if p.get("contact_numbers") and isinstance(p["contact_numbers"], list):
                for cn in p["contact_numbers"]:
                    if isinstance(cn, dict) and cn.get("value"):
                        cleaned = cn["value"].replace("-", "").replace(" ", "").replace("(", "").replace(")", "")
                        phone_values.append(cleaned)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to fetch CRM person %d: %s", person_id, exc)
        raise HTTPException(status_code=500, detail="Failed to fetch person data")

    if not phone_values and not email_values:
        return CommsListResponse(items=[], total=0, page=page, per_page=per_page)

    # Now fetch all comms matching those phones/emails
    all_records: list[CommRecord] = []

    # Calls — match by phone or email
    calls, _ = await _get_call_records(limit=200, offset=0)
    for c in calls:
        if c.contact_phone and any(pv in c.contact_phone.replace("-", "").replace(" ", "") for pv in phone_values):
            c.person_id = person_id
            all_records.append(c)
        elif c.contact_email and c.contact_email.lower() in email_values:
            c.person_id = person_id
            all_records.append(c)

    # SMS — match by phone
    sms_records = await _get_sms_records(limit=200)
    for s in sms_records:
        if s.contact_phone and any(pv in s.contact_phone.replace("-", "").replace(" ", "") for pv in phone_values):
            s.person_id = person_id
            all_records.append(s)

    # Emails — match by email address
    email_records, _ = await _get_email_records(limit=200, offset=0)
    for e in email_records:
        if e.contact_email and e.contact_email.lower() in email_values:
            e.person_id = person_id
            all_records.append(e)

    # Sort chronologically
    all_records.sort(key=lambda r: r.occurred_at, reverse=True)

    # Paginate
    offset = (page - 1) * per_page
    total = len(all_records)
    page_records = all_records[offset:offset + per_page]

    return CommsListResponse(
        items=page_records,
        total=total,
        page=page,
        per_page=per_page,
    )


# ── Send Email Endpoint ─────────────────────────────────────────────

@router.post("/send-email", response_model=SendEmailResponse)
async def send_email(req: SendEmailRequest):
    """Send an email via Resend and log it to outbound_emails."""
    from app.services.email import _send_email_async

    sent = await _send_email_async(req.to, req.subject, f"<p>{req.body}</p>")
    if not sent:
        raise HTTPException(status_code=500, detail="Failed to send email via Resend")

    # Log to outbound_emails
    person_id, _, _ = await _match_crm_person(None, req.to)
    await log_outbound_email(
        to_address=req.to,
        subject=req.subject,
        body_text=req.body,
        person_id=person_id,
    )

    return SendEmailResponse(ok=True, message="Email sent")
