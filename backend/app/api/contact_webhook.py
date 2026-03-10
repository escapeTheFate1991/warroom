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
from app.services.email import _send_email_async
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
            You'll receive a call from us shortly at the number you provided.
            We'll schedule a time for a member of our team to walk you through
            your <strong>free website audit</strong> and discuss how we can help
            streamline your business.
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


def _build_lead_notification_html(submission: dict, intake: dict | None = None) -> str:
    """Build the internal lead notification email sent to contact@stuffnthings.io."""
    name = submission.get("name", "Unknown")
    email = submission.get("email", "")
    phone = submission.get("phone", "N/A")
    message = submission.get("message", "")
    business = submission.get("business_name") or "Not provided"
    website = submission.get("website_url") or "Not provided"

    # Call results section
    call_section = ""
    if intake and intake.get("call_status") == "completed":
        pain = intake.get("pain_points") or "Not captured"
        services = intake.get("services") or "Not captured"
        schedule = intake.get("schedule_pref") or "Not captured"
        call_section = f"""
        <div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;padding:16px;margin:16px 0">
            <h3 style="color:#166534;margin:0 0 12px 0;font-size:14px">✅ AI Intake Call Completed</h3>
            <table style="font-size:14px;line-height:1.6;width:100%">
                <tr><td style="color:#666;padding:4px 12px 4px 0;white-space:nowrap"><strong>Pain Points:</strong></td><td>{pain}</td></tr>
                <tr><td style="color:#666;padding:4px 12px 4px 0;white-space:nowrap"><strong>Services:</strong></td><td>{services}</td></tr>
                <tr><td style="color:#666;padding:4px 12px 4px 0;white-space:nowrap"><strong>Scheduling:</strong></td><td>{schedule}</td></tr>
            </table>
        </div>
        """
    elif intake and intake.get("call_status") in ("no-answer", "busy", "failed"):
        call_section = f"""
        <div style="background:#fef2f2;border:1px solid #fecaca;border-radius:8px;padding:16px;margin:16px 0">
            <h3 style="color:#991b1b;margin:0 0 8px 0;font-size:14px">❌ AI Call Did Not Connect</h3>
            <p style="font-size:13px;color:#666;margin:0">Status: {intake.get('call_status', 'unknown')}. Follow up manually.</p>
        </div>
        """
    else:
        call_section = """
        <div style="background:#fffbeb;border:1px solid #fde68a;border-radius:8px;padding:16px;margin:16px 0">
            <h3 style="color:#92400e;margin:0 0 8px 0;font-size:14px">📞 No Call Attempted</h3>
            <p style="font-size:13px;color:#666;margin:0">Phone number was not provided or call was not triggered.</p>
        </div>
        """

    return f"""\
    <div style="font-family:system-ui,-apple-system,sans-serif;max-width:600px;margin:0 auto;padding:32px;color:#333">
        <h2 style="color:#1a1a2e;margin-bottom:4px">New Lead: {name}</h2>
        <p style="font-size:13px;color:#999;margin-top:0">From stuffnthings.io contact form</p>

        <table style="font-size:14px;line-height:1.8;width:100%;margin:16px 0">
            <tr><td style="color:#666;padding:4px 12px 4px 0;white-space:nowrap"><strong>Name:</strong></td><td>{name}</td></tr>
            <tr><td style="color:#666;padding:4px 12px 4px 0;white-space:nowrap"><strong>Email:</strong></td><td><a href="mailto:{email}" style="color:#0ea5e9">{email}</a></td></tr>
            <tr><td style="color:#666;padding:4px 12px 4px 0;white-space:nowrap"><strong>Phone:</strong></td><td>{phone}</td></tr>
            <tr><td style="color:#666;padding:4px 12px 4px 0;white-space:nowrap"><strong>Business:</strong></td><td>{business}</td></tr>
            <tr><td style="color:#666;padding:4px 12px 4px 0;white-space:nowrap"><strong>Website:</strong></td><td>{website}</td></tr>
        </table>

        <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:16px;margin:16px 0">
            <h3 style="color:#475569;margin:0 0 8px 0;font-size:14px">Their Message</h3>
            <p style="font-size:14px;line-height:1.6;margin:0">{message}</p>
        </div>

        {call_section}

        <hr style="border:none;border-top:1px solid #e0e0e0;margin:24px 0 12px">
        <p style="font-size:11px;color:#999;text-align:center">
            War Room Lead Notification &bull; <a href="https://warroom.stuffnthings.io" style="color:#999">Open War Room</a>
        </p>
    </div>
    """


async def _send_auto_reply(submission_id: int, name: str, email: str):
    """Send auto-reply and update the DB record."""
    try:
        subject = "We received your request — here's what happens next"
        html = _build_auto_reply_html(name)
        sent = await _send_email_async(email, subject, html)

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

                # Log to outbound_emails for comms hub tracking
                try:
                    from app.api.comms import log_outbound_email
                    await log_outbound_email(
                        to_address=email,
                        subject=subject,
                        body_text=f"Auto-reply to {name}",
                        from_address="contact@stuffnthings.io",
                    )
                except Exception:
                    pass  # best-effort
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

        # 2. Pre-store email in intake record so calendar event has it
        from app.api.twilio_voice import _ensure_table as _ensure_intake_table
        await _ensure_intake_table()
        async with leadgen_session() as db:
            # Upsert: set email on existing row or it'll be set when call creates the row
            await db.execute(
                text("""
                    UPDATE public.call_intakes SET contact_email = :email
                    WHERE submission_id = :sid
                """),
                {"email": email, "sid": submission_id},
            )
            await db.commit()

        # 3. Wait 2 minutes then make the AI intake call
        await asyncio.sleep(120)

        try:
            # Use the webhook URL for the AI conversation flow
            webhook_base = "https://warroom.stuffnthings.io/api/twilio"
            await make_call(
                to=phone,
                url=f"{webhook_base}/voice/welcome",
            )
            logger.info("AI intake call initiated to %s for submission #%d", phone, submission_id)

        except TwilioConfigError as exc:
            logger.warning("Call not placed (config missing): %s", exc)
        except Exception as exc:
            logger.error("Call failed for submission #%d: %s", submission_id, exc)

    except Exception as exc:
        logger.error("SMS/Call pipeline failed for submission #%d: %s", submission_id, exc)


# ── Lead Notification (sent AFTER call completes or fails) ───────────

LEAD_NOTIFY_TO = "contact@stuffnthings.io"


async def send_lead_notification(submission_id: int, intake: dict | None = None):
    """Send internal lead notification email with call results to contact@stuffnthings.io."""
    try:
        # Fetch submission data
        async with _session() as db:
            result = await db.execute(
                text("SELECT * FROM public.contact_submissions WHERE id = :id"),
                {"id": submission_id},
            )
            row = result.fetchone()
            if not row:
                logger.warning("Submission #%d not found for lead notification", submission_id)
                return

        submission = dict(row._mapping)
        html = _build_lead_notification_html(submission, intake)
        name = submission.get("name", "Unknown")
        subject = f"New Lead: {name}"
        if intake and intake.get("call_status") == "completed":
            subject = f"New Lead (Call Completed): {name}"
        elif intake and intake.get("call_status") in ("no-answer", "busy", "failed"):
            subject = f"New Lead (Call Failed): {name}"

        sent = await _send_email_async(LEAD_NOTIFY_TO, subject, html)
        if sent:
            logger.info("Lead notification sent to %s for submission #%d", LEAD_NOTIFY_TO, submission_id)
            # Log to outbound_emails for comms hub tracking
            try:
                from app.api.comms import log_outbound_email
                await log_outbound_email(
                    to_address=LEAD_NOTIFY_TO,
                    subject=subject,
                    body_text=f"Lead notification for {name}",
                    from_address="contact@stuffnthings.io",
                )
            except Exception:
                pass  # best-effort
        else:
            logger.warning("Lead notification NOT sent (Resend key missing?)")
    except Exception as exc:
        logger.error("Lead notification failed for submission #%d: %s", submission_id, exc)


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
        clean_phone = re.sub(r"[^\d+]", "", body.phone)
        if not clean_phone.startswith("+"):
            clean_phone = "+1" + clean_phone  # Default to US
        asyncio.create_task(
            _send_confirmation_sms_and_call(submission_id, body.name.strip(), clean_phone, body.email.lower().strip())
        )
    else:
        # No phone → no call → send lead notification immediately
        asyncio.create_task(send_lead_notification(submission_id))

    # Fire workflow triggers for contact_submission.created (non-blocking)
    from app.services.workflow_triggers import fire_triggers_background
    fire_triggers_background(
        entity_type="contact_submission",
        event="created",
        entity_data={
            "id": submission_id,
            "name": body.name.strip(),
            "email": body.email.lower().strip(),
            "phone": body.phone,
            "message": body.message.strip(),
            "business_name": body.business_name.strip() if body.business_name else None,
            "website_url": body.website_url.strip() if body.website_url else None,
            "source_url": body.source_url,
            "lead_source": "website_form",
            "event": "created",
            "triggered_at": datetime.now(timezone.utc).isoformat(),
        },
        entity_id=submission_id,
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
