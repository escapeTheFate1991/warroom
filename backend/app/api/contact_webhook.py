"""Contact form webhook — public endpoint for website contact submissions.

Receives form data, validates, rate-limits, stores in DB, triggers auto-reply.
Table: public.contact_submissions (auto-created on startup).
"""
import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Request, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy import text

from app.db.leadgen_db import leadgen_engine, leadgen_session
from app.services.email import _send_email
from app.services.notify import send_notification

logger = logging.getLogger(__name__)

# ── DB Setup — uses shared leadgen engine (same knowledge DB, public schema)
_engine = leadgen_engine
_session = leadgen_session

router = APIRouter()

# ── Table DDL ────────────────────────────────────────────────────────
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS public.contact_submissions (
    id              SERIAL PRIMARY KEY,
    name            TEXT NOT NULL,
    email           TEXT NOT NULL,
    phone           TEXT,
    message         TEXT NOT NULL,
    business_name   TEXT,
    website_url     TEXT,
    source_url      TEXT,
    lead_source     TEXT DEFAULT 'website_form',
    ip_address      TEXT,
    submitted_at    TIMESTAMP WITH TIME ZONE DEFAULT now(),
    status          VARCHAR(20) DEFAULT 'new',
    assigned_to     INTEGER,
    auto_reply_sent BOOLEAN DEFAULT FALSE,
    auto_reply_at   TIMESTAMP WITH TIME ZONE,
    notes           TEXT
);
"""

ALTER_SQLS = [
    "ALTER TABLE public.contact_submissions ADD COLUMN IF NOT EXISTS business_name TEXT",
    "ALTER TABLE public.contact_submissions ADD COLUMN IF NOT EXISTS website_url TEXT",
    "ALTER TABLE public.contact_submissions ADD COLUMN IF NOT EXISTS lead_source TEXT DEFAULT 'website_form'",
]

INDEX_SQLS = [
    "CREATE INDEX IF NOT EXISTS idx_contact_submissions_email ON public.contact_submissions (email)",
    "CREATE INDEX IF NOT EXISTS idx_contact_submissions_status ON public.contact_submissions (status)",
]


async def init_contact_table():
    """Auto-create the contact_submissions table on startup."""
    try:
        async with _engine.begin() as conn:
            await conn.execute(text(CREATE_TABLE_SQL))
            for alter_sql in ALTER_SQLS:
                await conn.execute(text(alter_sql))
            for idx_sql in INDEX_SQLS:
                await conn.execute(text(idx_sql))
        logger.info("contact_submissions table ready")
    except Exception as e:
        logger.error("Failed to init contact_submissions table: %s", e)


# ── Schemas ──────────────────────────────────────────────────────────
class ContactSubmission(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    message: str
    business_name: Optional[str] = None
    website_url: Optional[str] = None
    source_url: Optional[str] = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v or len(v) < 2:
            raise ValueError("Name must be at least 2 characters")
        return v

    @field_validator("message")
    @classmethod
    def message_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v or len(v) < 10:
            raise ValueError("Message must be at least 10 characters")
        return v

    @field_validator("phone")
    @classmethod
    def sanitize_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        cleaned = re.sub(r"[^\d+\-() ]", "", v.strip())
        return cleaned or None


class ContactUpdate(BaseModel):
    status: Optional[str] = None
    assigned_to: Optional[int] = None
    notes: Optional[str] = None

    @field_validator("status")
    @classmethod
    def valid_status(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        allowed = {"new", "read", "in_progress", "replied", "closed", "spam"}
        if v not in allowed:
            raise ValueError(f"Status must be one of: {', '.join(sorted(allowed))}")
        return v


# ── Auto-reply email ────────────────────────────────────────────────
AUTO_REPLY_FROM = "contact@stuffnthings.io"

def _build_auto_reply_html(name: str) -> str:
    first_name = name.split()[0]
    return f"""\
    <div style="font-family:system-ui,-apple-system,sans-serif;max-width:560px;margin:0 auto;padding:32px;color:#333">
        <h2 style="color:#1a1a2e;margin-bottom:16px">Hey {first_name}, we got your request!</h2>
        <p style="font-size:15px;line-height:1.6">
            Thanks for reaching out through <a href="https://stuffnthings.io" style="color:#0ea5e9;text-decoration:none">stuffnthings.io</a>.
            We're glad you're here.
        </p>
        <p style="font-size:15px;line-height:1.6">
            Our team will review your request within <strong>24 hours</strong>.
        </p>
        <p style="font-size:15px;line-height:1.6">
            You'll receive a call from us shortly to discuss your needs and schedule
            a time that works for you.
        </p>
        <p style="font-size:15px;line-height:1.6">
            In the meantime, feel free to reply to this email if you have any questions.
        </p>
        <p style="font-size:15px;line-height:1.6;margin-top:24px">
            Talk soon,<br>
            <strong>&mdash; The Stuff N Things Team</strong>
        </p>
        <hr style="border:none;border-top:1px solid #e0e0e0;margin:32px 0 16px">
        <p style="font-size:12px;color:#999;text-align:center">
            <a href="mailto:contact@stuffnthings.io" style="color:#999;text-decoration:none">contact@stuffnthings.io</a>
            &nbsp;|&nbsp;
            <a href="https://stuffnthings.io" style="color:#999;text-decoration:none">stuffnthings.io</a>
        </p>
    </div>
    """


async def _send_auto_reply(submission_id: int, name: str, email: str):
    """Send auto-reply and update the DB record."""
    try:
        html = _build_auto_reply_html(name)
        # _send_email is sync (uses smtplib) — run in thread to avoid blocking event loop
        sent = await asyncio.to_thread(
            _send_email, email, "We received your request — here's what happens next", html
        )

        async with _session() as db:
            if sent:
                await db.execute(
                    text("""
                        UPDATE public.contact_submissions
                        SET auto_reply_sent = TRUE, auto_reply_at = now()
                        WHERE id = :id
                    """),
                    {"id": submission_id},
                )
                await db.commit()
                logger.info("Auto-reply sent to %s for submission #%d", email, submission_id)
            else:
                logger.warning("Auto-reply NOT sent to %s (SMTP unconfigured?)", email)
    except Exception as e:
        logger.error("Auto-reply failed for submission #%d: %s", submission_id, e)


# ── SMS Confirmation + AI Call Trigger ────────────────────────────────

async def _send_confirmation_sms_and_call(submission_id: int, name: str, phone: str, email: str):
    """Send a confirmation SMS, wait a bit, then trigger the AI intake call."""
    try:
        from app.services.twilio_client import send_sms, make_call, get_twilio_config, TwilioConfigError

        first_name = name.split()[0]

        # 1. Send confirmation SMS
        try:
            await send_sms(
                to=phone,
                body=(
                    f"Hi {first_name}! Thanks for reaching out to Stuff N Things. "
                    f"We received your inquiry and will be calling you at this number "
                    f"in a few minutes to learn more about your needs and schedule a consultation. "
                    f"Talk soon! — The Stuff N Things Team"
                ),
            )
            logger.info("Confirmation SMS sent to %s for submission #%d", phone, submission_id)
        except TwilioConfigError as exc:
            logger.warning("SMS not sent (config missing): %s", exc)
        except Exception as exc:
            logger.error("SMS send failed for submission #%d: %s", submission_id, exc)

        # 2. Wait 2 minutes then make the AI intake call
        await asyncio.sleep(120)

        try:
            # Use the webhook URL for the AI conversation flow
            webhook_base = "https://warroom.stuffnthings.io/api/twilio"
            await make_call(
                to=phone,
                url=f"{webhook_base}/voice/welcome",
            )
            logger.info("AI intake call initiated to %s for submission #%d", phone, submission_id)

            # Store email in intake for calendar event creation
            async with leadgen_session() as db:
                await db.execute(
                    text("""
                        UPDATE public.call_intakes SET contact_email = :email
                        WHERE submission_id = :sid
                    """),
                    {"email": email, "sid": submission_id},
                )
                await db.commit()

        except TwilioConfigError as exc:
            logger.warning("Call not placed (config missing): %s", exc)
        except Exception as exc:
            logger.error("Call failed for submission #%d: %s", submission_id, exc)

    except Exception as exc:
        logger.error("SMS/Call pipeline failed for submission #%d: %s", submission_id, exc)


# ── Rate Limiting ────────────────────────────────────────────────────
RATE_LIMIT = 5  # max submissions per email per hour

async def _check_rate_limit(email: str) -> bool:
    """Return True if the email is within rate limit."""
    async with _session() as db:
        result = await db.execute(
            text("""
                SELECT COUNT(*) FROM public.contact_submissions
                WHERE email = :email
                  AND submitted_at > now() - INTERVAL '1 hour'
            """),
            {"email": email.lower()},
        )
        count = result.scalar()
        return count < RATE_LIMIT


# ── Endpoints ────────────────────────────────────────────────────────

@router.post("/webhooks/contact", status_code=201)
async def submit_contact(body: ContactSubmission, request: Request):
    """PUBLIC — receive a contact form submission."""
    ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "unknown")

    # Rate limit
    if not await _check_rate_limit(body.email):
        return JSONResponse(
            status_code=429,
            content={"error": "Too many submissions. Please try again later."},
        )

    # Insert
    async with _session() as db:
        result = await db.execute(
            text("""
                INSERT INTO public.contact_submissions
                    (name, email, phone, message, business_name, website_url, source_url, lead_source, ip_address)
                VALUES
                    (:name, :email, :phone, :message, :business_name, :website_url, :source_url, :lead_source, :ip)
                RETURNING id
            """),
            {
                "name": body.name.strip(),
                "email": body.email.lower().strip(),
                "phone": body.phone,
                "message": body.message.strip(),
                "business_name": body.business_name.strip() if body.business_name else None,
                "website_url": body.website_url.strip() if body.website_url else None,
                "source_url": body.source_url,
                "lead_source": "website_form",
                "ip": ip,
            },
        )
        row = result.fetchone()
        submission_id = row[0]
        await db.commit()

    # Fire auto-reply email (best-effort, don't block response)
    await _send_auto_reply(submission_id, body.name.strip(), body.email.lower().strip())

    # Send confirmation SMS + trigger AI call (best-effort)
    if body.phone:
        asyncio.create_task(
            _send_confirmation_sms_and_call(submission_id, body.name.strip(), body.phone, body.email.lower().strip())
        )

    # Notification: new contact form submission
    await send_notification(
        type="lead",
        title="New Contact Form Submission",
        message=f"{body.name.strip()} from {body.business_name.strip() if body.business_name else 'unknown'} — {body.email}",
        data={"submission_id": submission_id, "link": "/prospects"},
    )

    return {"id": submission_id, "message": "Submission received. We'll be in touch!"}


@router.get("/contact-submissions")
async def list_submissions(
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
):
    """List contact submissions (paginated, filterable by status)."""
    offset = (page - 1) * per_page

    where_clause = ""
    params: dict = {"limit": per_page, "offset": offset}

    if status:
        where_clause = "WHERE status = :status"
        params["status"] = status

    async with _session() as db:
        # Count
        count_result = await db.execute(
            text(f"SELECT COUNT(*) FROM public.contact_submissions {where_clause}"),
            params,
        )
        total = count_result.scalar()

        # Fetch page
        rows = await db.execute(
            text(f"""
                SELECT id, name, email, phone, message, business_name, website_url,
                       source_url, lead_source, ip_address,
                       submitted_at, status, assigned_to, auto_reply_sent, auto_reply_at, notes
                FROM public.contact_submissions
                {where_clause}
                ORDER BY submitted_at DESC
                LIMIT :limit OFFSET :offset
            """),
            params,
        )
        items = [dict(r._mapping) for r in rows.fetchall()]

    return {
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page if total else 0,
    }


@router.get("/contact-submissions/{submission_id}")
async def get_submission(submission_id: int):
    """Get a single contact submission by ID."""
    async with _session() as db:
        result = await db.execute(
            text("""
                SELECT id, name, email, phone, message, business_name, website_url,
                       source_url, lead_source, ip_address,
                       submitted_at, status, assigned_to, auto_reply_sent, auto_reply_at, notes
                FROM public.contact_submissions
                WHERE id = :id
            """),
            {"id": submission_id},
        )
        row = result.fetchone()
        if not row:
            return JSONResponse(status_code=404, content={"error": "Submission not found"})
        return dict(row._mapping)


@router.patch("/contact-submissions/{submission_id}")
async def update_submission(submission_id: int, body: ContactUpdate):
    """Update status, assignment, or notes on a submission."""
    updates = []
    params: dict = {"id": submission_id}

    if body.status is not None:
        updates.append("status = :status")
        params["status"] = body.status
    if body.assigned_to is not None:
        updates.append("assigned_to = :assigned_to")
        params["assigned_to"] = body.assigned_to
    if body.notes is not None:
        updates.append("notes = :notes")
        params["notes"] = body.notes

    if not updates:
        return JSONResponse(status_code=400, content={"error": "No fields to update"})

    set_clause = ", ".join(updates)

    async with _session() as db:
        result = await db.execute(
            text(f"""
                UPDATE public.contact_submissions
                SET {set_clause}
                WHERE id = :id
                RETURNING id, status, assigned_to, notes
            """),
            params,
        )
        row = result.fetchone()
        await db.commit()

        if not row:
            return JSONResponse(status_code=404, content={"error": "Submission not found"})
        return dict(row._mapping)
