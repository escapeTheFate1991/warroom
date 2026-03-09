"""Twilio Voice IVR — AI-powered intake call for contact form leads.

Flow:
  1. Welcome → ask about time-consuming tasks
  2. Gather tasks → ask about services interested in
  3. Gather services → ask about scheduling preference
  4. Gather schedule → confirm & hang up
  5. Status callback → store results, create calendar event

All endpoints return TwiML XML. Twilio calls them as webhooks.
These paths are whitelisted in auth_guard.py (no JWT required).
"""

import json
import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Request, Form
from fastapi.responses import Response
from sqlalchemy import text

from app.db.leadgen_db import leadgen_session

logger = logging.getLogger(__name__)

router = APIRouter()

# ── Table for storing call conversation data ─────────────────────────
CREATE_CALL_INTAKES_SQL = """
CREATE TABLE IF NOT EXISTS public.call_intakes (
    id              SERIAL PRIMARY KEY,
    submission_id   INTEGER REFERENCES public.contact_submissions(id),
    call_sid        TEXT UNIQUE,
    contact_name    TEXT,
    contact_phone   TEXT,
    contact_email   TEXT,
    pain_points     TEXT,
    services        TEXT,
    schedule_pref   TEXT,
    call_status     VARCHAR(20) DEFAULT 'initiated',
    started_at      TIMESTAMP WITH TIME ZONE DEFAULT now(),
    completed_at    TIMESTAMP WITH TIME ZONE,
    calendar_event_created BOOLEAN DEFAULT FALSE,
    raw_data        JSONB DEFAULT '{}'
);
"""

_TABLE_CREATED = False


async def _ensure_table():
    global _TABLE_CREATED
    if _TABLE_CREATED:
        return
    async with leadgen_session() as db:
        await db.execute(text(CREATE_CALL_INTAKES_SQL))
        await db.commit()
    _TABLE_CREATED = True


def _twiml(body: str) -> Response:
    """Return a TwiML XML response."""
    xml = f'<?xml version="1.0" encoding="UTF-8"?><Response>{body}</Response>'
    return Response(content=xml, media_type="application/xml")


# Voice config — Twilio's built-in neural voices
VOICE = "Polly.Joanna"  # AWS Polly neural voice (warm, professional female)
GATHER_OPTS = 'input="speech" speechTimeout="3" language="en-US"'
BASE_URL = "https://warroom.stuffnthings.io/api/twilio"


# ── Step 1: Welcome + Ask about pain points ──────────────────────────

@router.post("/voice/welcome")
async def voice_welcome(request: Request):
    """Initial greeting when call connects. Asks about time-consuming tasks."""
    form = await request.form()
    call_sid = form.get("CallSid", "")
    to = form.get("To", "")
    from_num = form.get("From", "")

    # Look up the contact's name from submission
    contact_name = "there"
    submission_id = None
    async with leadgen_session() as db:
        result = await db.execute(
            text("""
                SELECT id, name FROM public.contact_submissions
                WHERE phone LIKE :phone
                ORDER BY submitted_at DESC LIMIT 1
            """),
            {"phone": f"%{to[-10:]}"},  # Match last 10 digits
        )
        row = result.fetchone()
        if row:
            submission_id = row[0]
            contact_name = row[1].split()[0]  # First name

    # Create intake record
    await _ensure_table()
    async with leadgen_session() as db:
        await db.execute(
            text("""
                INSERT INTO public.call_intakes (submission_id, call_sid, contact_name, contact_phone)
                VALUES (:sid, :call_sid, :name, :phone)
                ON CONFLICT (call_sid) DO NOTHING
            """),
            {"sid": submission_id, "call_sid": call_sid, "name": contact_name, "phone": to},
        )
        await db.commit()

    return _twiml(f"""
        <Say voice="{VOICE}">
            Hi {contact_name}, this is the Stuff N Things team calling about your inquiry.
            Thank you for reaching out to us.
        </Say>
        <Pause length="1"/>
        <Gather {GATHER_OPTS} action="https://warroom.stuffnthings.io/api/twilio/voice/gather-tasks">
            <Say voice="{VOICE}">
                We'd love to learn more about your business.
                What tasks or processes do you feel are taking time away from your core business?
            </Say>
        </Gather>
        <Say voice="{VOICE}">
            I didn't catch that. Let me move on.
        </Say>
        <Redirect>https://warroom.stuffnthings.io/api/twilio/voice/gather-services</Redirect>
    """)


# ── Step 2: Store pain points → Ask about services ──────────────────

@router.post("/voice/gather-tasks")
async def voice_gather_tasks(request: Request):
    """Receives speech about pain points, asks about services."""
    form = await request.form()
    call_sid = form.get("CallSid", "")
    speech_result = form.get("SpeechResult", "")

    # Store pain points
    async with leadgen_session() as db:
        await db.execute(
            text("UPDATE public.call_intakes SET pain_points = :pain WHERE call_sid = :sid"),
            {"pain": speech_result, "sid": call_sid},
        )
        await db.commit()

    logger.info("Call %s — pain points: %s", call_sid, speech_result[:100])

    return _twiml(f"""
        <Say voice="{VOICE}">
            Got it, that's really helpful. Thank you for sharing that.
        </Say>
        <Pause length="1"/>
        <Gather {GATHER_OPTS} action="https://warroom.stuffnthings.io/api/twilio/voice/gather-services">
            <Say voice="{VOICE}">
                Now, what services were you most interested in?
                For example, we offer website design and development, A I workflow automation,
                S E O optimization, and ongoing website management.
            </Say>
        </Gather>
        <Say voice="{VOICE}">
            No worries. Let me move to the next question.
        </Say>
        <Redirect>https://warroom.stuffnthings.io/api/twilio/voice/gather-schedule</Redirect>
    """)


# ── Step 3: Store services → Ask about scheduling ───────────────────

@router.post("/voice/gather-services")
async def voice_gather_services(request: Request):
    """Receives speech about services, asks about scheduling."""
    form = await request.form()
    call_sid = form.get("CallSid", "")
    speech_result = form.get("SpeechResult", "")

    async with leadgen_session() as db:
        await db.execute(
            text("UPDATE public.call_intakes SET services = :svc WHERE call_sid = :sid"),
            {"svc": speech_result, "sid": call_sid},
        )
        await db.commit()

    logger.info("Call %s — services: %s", call_sid, speech_result[:100])

    return _twiml(f"""
        <Say voice="{VOICE}">
            Great choices. We can definitely help with that.
        </Say>
        <Pause length="1"/>
        <Gather {GATHER_OPTS} action="https://warroom.stuffnthings.io/api/twilio/voice/gather-schedule">
            <Say voice="{VOICE}">
                Last question. When would be a good day and time for one of our team members
                to meet with you for a more detailed consultation?
                You can say something like, Tuesday afternoon, or Friday at 2 PM.
            </Say>
        </Gather>
        <Say voice="{VOICE}">
            No problem. We'll follow up by email to find a time that works.
        </Say>
        <Redirect>https://warroom.stuffnthings.io/api/twilio/voice/complete</Redirect>
    """)


# ── Step 4: Store schedule → Confirm & end call ─────────────────────

@router.post("/voice/gather-schedule")
async def voice_gather_schedule(request: Request):
    """Receives scheduling preference, wraps up the call."""
    form = await request.form()
    call_sid = form.get("CallSid", "")
    speech_result = form.get("SpeechResult", "")

    async with leadgen_session() as db:
        await db.execute(
            text("UPDATE public.call_intakes SET schedule_pref = :sched WHERE call_sid = :sid"),
            {"sched": speech_result, "sid": call_sid},
        )
        await db.commit()

    logger.info("Call %s — schedule: %s", call_sid, speech_result[:100])

    return _twiml(f"""
        <Say voice="{VOICE}">
            Perfect. I've noted that down.
            You'll receive a calendar invite at the email you provided with the meeting details.
            A member of our team will be ready to discuss your needs in depth.
        </Say>
        <Pause length="1"/>
        <Say voice="{VOICE}">
            Thank you so much for your time today. We're excited to work with you.
            Have a great day!
        </Say>
        <Redirect>https://warroom.stuffnthings.io/api/twilio/voice/complete</Redirect>
    """)


# ── Step 5: Call complete → Finalize record ──────────────────────────

@router.post("/voice/complete")
async def voice_complete(request: Request):
    """Final redirect — mark call as complete and trigger follow-ups."""
    form = await request.form()
    call_sid = form.get("CallSid", "")

    async with leadgen_session() as db:
        await db.execute(
            text("""
                UPDATE public.call_intakes
                SET call_status = 'completed', completed_at = now()
                WHERE call_sid = :sid
            """),
            {"sid": call_sid},
        )
        await db.commit()

        # Fetch the intake data for calendar event creation
        result = await db.execute(
            text("SELECT * FROM public.call_intakes WHERE call_sid = :sid"),
            {"sid": call_sid},
        )
        row = result.fetchone()

    if row:
        intake = dict(row._mapping)
        # Trigger calendar event creation (background)
        try:
            await _create_calendar_event(intake)
        except Exception as exc:
            logger.error("Failed to create calendar event for call %s: %s", call_sid, exc)

        # Send notification
        from app.services.notify import send_notification
        await send_notification(
            type="lead",
            title="AI Call Completed",
            message=f"{intake.get('contact_name', 'Contact')} — tasks: {(intake.get('pain_points') or 'n/a')[:80]}",
            data={"call_sid": call_sid, "link": "/prospects"},
        )

    return _twiml(f'<Say voice="{VOICE}">Goodbye!</Say><Hangup/>')


# ── Status callback (Twilio sends call status updates) ───────────────

@router.post("/voice/status")
async def voice_status(request: Request):
    """Twilio status callback — updates call status."""
    form = await request.form()
    call_sid = form.get("CallSid", "")
    call_status = form.get("CallStatus", "")

    if call_sid and call_status:
        await _ensure_table()
        async with leadgen_session() as db:
            await db.execute(
                text("""
                    UPDATE public.call_intakes
                    SET call_status = :status, raw_data = raw_data || :data::jsonb
                    WHERE call_sid = :sid
                """),
                {
                    "sid": call_sid,
                    "status": call_status,
                    "data": json.dumps({"status_update": call_status, "ts": datetime.now(timezone.utc).isoformat()}),
                },
            )
            await db.commit()

    return Response(content="", status_code=204)


# ── Calendar Event Creation ──────────────────────────────────────────

async def _create_calendar_event(intake: dict):
    """Create a Google Calendar event for the consultation meeting."""
    from app.services.token_store import load_tokens
    import httpx

    tokens = await load_tokens("google_calendar")
    if not tokens or not tokens.get("access_token"):
        logger.warning("Google Calendar not connected — skipping event creation")
        return

    contact_name = intake.get("contact_name", "Contact")
    contact_email = intake.get("contact_email")
    schedule_pref = intake.get("schedule_pref", "")
    pain_points = intake.get("pain_points", "Not provided")
    services = intake.get("services", "Not provided")

    # Default to 2 days from now at 2pm if no clear preference
    meeting_time = datetime.now(timezone.utc) + timedelta(days=2)
    meeting_time = meeting_time.replace(hour=18, minute=0, second=0, microsecond=0)  # 2pm ET = 18:00 UTC

    event = {
        "summary": f"Stuff N Things Consultation — {contact_name}",
        "description": (
            f"Consultation with {contact_name}\n\n"
            f"Pain Points: {pain_points}\n"
            f"Services Interested In: {services}\n"
            f"Scheduling Preference: {schedule_pref}\n\n"
            f"This event was auto-created by the War Room AI intake system."
        ),
        "start": {
            "dateTime": meeting_time.isoformat(),
            "timeZone": "America/New_York",
        },
        "end": {
            "dateTime": (meeting_time + timedelta(hours=1)).isoformat(),
            "timeZone": "America/New_York",
        },
        "attendees": [
            {"email": "info@stuffnthings.io"},
        ],
        "reminders": {
            "useDefault": False,
            "overrides": [
                {"method": "email", "minutes": 60},
                {"method": "popup", "minutes": 15},
            ],
        },
    }

    if contact_email:
        event["attendees"].append({"email": contact_email})

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            "https://www.googleapis.com/calendar/v3/calendars/primary/events",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
            json=event,
            params={"sendUpdates": "all"},
        )
        if resp.status_code in (200, 201):
            event_data = resp.json()
            logger.info("Calendar event created: %s", event_data.get("htmlLink"))

            # Update intake record
            async with leadgen_session() as db:
                await db.execute(
                    text("UPDATE public.call_intakes SET calendar_event_created = TRUE WHERE id = :id"),
                    {"id": intake["id"]},
                )
                await db.commit()
        else:
            logger.error("Calendar event creation failed: %s %s", resp.status_code, resp.text[:200])
