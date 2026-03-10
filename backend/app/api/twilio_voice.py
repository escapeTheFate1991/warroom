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
        # Add person_id column if it doesn't exist (CRM linking)
        await db.execute(text(
            "ALTER TABLE public.call_intakes ADD COLUMN IF NOT EXISTS person_id INTEGER"
        ))
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
    """Initial greeting — thanks for the audit request, asks about website challenges."""
    form = await request.form()
    call_sid = form.get("CallSid", "")
    to = form.get("To", "")
    from_num = form.get("From", "")

    # Look up the contact's name and email from submission
    contact_name = "there"
    contact_email = None
    submission_id = None
    async with leadgen_session() as db:
        result = await db.execute(
            text("""
                SELECT id, name, email FROM public.contact_submissions
                WHERE phone LIKE :phone
                ORDER BY submitted_at DESC LIMIT 1
            """),
            {"phone": f"%{to[-10:]}"},  # Match last 10 digits
        )
        row = result.fetchone()
        if row:
            submission_id = row[0]
            contact_name = row[1].split()[0]  # First name
            contact_email = row[2]

    # Create intake record
    await _ensure_table()
    async with leadgen_session() as db:
        await db.execute(
            text("""
                INSERT INTO public.call_intakes (submission_id, call_sid, contact_name, contact_phone, contact_email)
                VALUES (:sid, :call_sid, :name, :phone, :email)
                ON CONFLICT (call_sid) DO UPDATE SET contact_email = COALESCE(EXCLUDED.contact_email, call_intakes.contact_email)
            """),
            {"sid": submission_id, "call_sid": call_sid, "name": contact_name, "phone": to, "email": contact_email},
        )
        await db.commit()

    return _twiml(f"""
        <Say voice="{VOICE}">
            Hi {contact_name}, this is the Stuff N Things team calling about your free site audit request.
            Thanks for reaching out — we're going to review your website and put together a full report for you.
        </Say>
        <Pause length="1"/>
        <Gather {GATHER_OPTS} action="{BASE_URL}/voice/gather-tasks">
            <Say voice="{VOICE}">
                Before we dive in, I'd love to learn a bit about your business.
                What's your biggest challenge with your website right now?
            </Say>
        </Gather>
        <Say voice="{VOICE}">
            No worries. Let me move on.
        </Say>
        <Redirect>{BASE_URL}/voice/gather-services</Redirect>
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
        <Gather {GATHER_OPTS} action="{BASE_URL}/voice/gather-services">
            <Say voice="{VOICE}">
                What would you most like to improve?
                For example, we can help with website design, speed and performance,
                getting found on Google, or automating parts of your workflow with A I.
            </Say>
        </Gather>
        <Say voice="{VOICE}">
            No worries. Let me move to the next question.
        </Say>
        <Redirect>{BASE_URL}/voice/gather-schedule</Redirect>
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

    # Fetch real availability from Google Calendar
    from app.api.google_calendar import get_available_slots
    slots = await get_available_slots(3)

    # Store slots in intake record so gather-schedule can look them up
    async with leadgen_session() as db:
        await db.execute(
            text("UPDATE public.call_intakes SET raw_data = raw_data || :data::jsonb WHERE call_sid = :sid"),
            {"data": json.dumps({"offered_slots": slots}), "sid": call_sid},
        )
        await db.commit()

    # Build the slot options for the caller
    slot_text = ""
    for i, slot in enumerate(slots, 1):
        slot_text += f'Press {i} for {slot["label"]}. '

    return _twiml(f"""
        <Say voice="{VOICE}">
            Great. We can definitely help with that.
        </Say>
        <Pause length="1"/>
        <Say voice="{VOICE}">
            Let's get you scheduled to walk through your audit results with a member of our team.
            I have a few times available this week.
        </Say>
        <Pause length="1"/>
        <Gather input="dtmf" numDigits="1" timeout="10" action="{BASE_URL}/voice/gather-schedule">
            <Say voice="{VOICE}">
                {slot_text}
                Or press 4 if none of those work and we'll follow up by email.
            </Say>
        </Gather>
        <Say voice="{VOICE}">
            I didn't get a response. No worries, we'll follow up by email to find a time that works.
        </Say>
        <Redirect>{BASE_URL}/voice/complete</Redirect>
    """)


# ── Step 4: Store schedule → Confirm & end call ─────────────────────

@router.post("/voice/gather-schedule")
async def voice_gather_schedule(request: Request):
    """Receives DTMF slot selection, creates calendar event, wraps up."""
    form = await request.form()
    call_sid = form.get("CallSid", "")
    digits = form.get("Digits", "")

    logger.info("Call %s — selected slot: %s", call_sid, digits)

    # Look up the offered slots and intake data
    async with leadgen_session() as db:
        result = await db.execute(
            text("SELECT * FROM public.call_intakes WHERE call_sid = :sid"),
            {"sid": call_sid},
        )
        row = result.fetchone()

    if not row:
        return _twiml(f"""
            <Say voice="{VOICE}">Something went wrong. We'll follow up by email.</Say>
            <Redirect>{BASE_URL}/voice/complete</Redirect>
        """)

    intake = dict(row._mapping)
    raw_data = intake.get("raw_data") or {}
    if isinstance(raw_data, str):
        raw_data = json.loads(raw_data)
    offered_slots = raw_data.get("offered_slots", [])

    # Parse selection
    selected_slot = None
    if digits in ("1", "2", "3"):
        idx = int(digits) - 1
        if idx < len(offered_slots):
            selected_slot = offered_slots[idx]

    if digits == "4" or not selected_slot:
        # None of the times work
        async with leadgen_session() as db:
            await db.execute(
                text("UPDATE public.call_intakes SET schedule_pref = :sched WHERE call_sid = :sid"),
                {"sched": "Requested email follow-up for scheduling", "sid": call_sid},
            )
            await db.commit()

        return _twiml(f"""
            <Say voice="{VOICE}">
                No problem at all. We'll send you an email with a few more options so you can pick a time that works best.
            </Say>
            <Pause length="1"/>
            <Say voice="{VOICE}">
                Thank you so much for your time today. We're excited to work with you. Have a great day!
            </Say>
            <Redirect>{BASE_URL}/voice/complete</Redirect>
        """)

    # Got a valid slot — create the calendar event
    async with leadgen_session() as db:
        await db.execute(
            text("UPDATE public.call_intakes SET schedule_pref = :sched WHERE call_sid = :sid"),
            {"sched": selected_slot["label"], "sid": call_sid},
        )
        await db.commit()

    # Create real Google Calendar event
    from app.api.google_calendar import create_calendar_event
    
    contact_name = intake.get("contact_name", "Contact")
    contact_email = intake.get("contact_email")
    pain_points = intake.get("pain_points", "Not discussed")
    services = intake.get("services", "Not discussed")

    event = await create_calendar_event(
        summary=f"Site Audit Review — {contact_name}",
        start_iso=selected_slot["iso"],
        end_iso=selected_slot["iso_end"],
        attendee_email=contact_email,
        description=(
            f"Site Audit Review with {contact_name}\n\n"
            f"Website Challenges: {pain_points}\n"
            f"Interested In: {services}\n\n"
            f"Auto-scheduled by AI intake call."
        ),
    )

    if event:
        async with leadgen_session() as db:
            await db.execute(
                text("UPDATE public.call_intakes SET calendar_event_created = TRUE WHERE call_sid = :sid"),
                {"sid": call_sid},
            )
            await db.commit()

    slot_label = selected_slot["label"]
    return _twiml(f"""
        <Say voice="{VOICE}">
            Perfect. You're all set for {slot_label}.
            You'll receive a calendar invite at the email you provided with all the details.
            One of our team members will walk you through your full site audit report.
        </Say>
        <Pause length="1"/>
        <Say voice="{VOICE}">
            Thank you so much for your time today. We look forward to working with you. Have a great day!
        </Say>
        <Redirect>{BASE_URL}/voice/complete</Redirect>
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

        # Send notification
        from app.services.notify import send_notification
        await send_notification(
            type="lead",
            title="AI Call Completed",
            message=f"{intake.get('contact_name', 'Contact')} — tasks: {(intake.get('pain_points') or 'n/a')[:80]}",
            data={"call_sid": call_sid, "link": "/prospects"},
        )

        # Send lead notification email to contact@stuffnthings.io with call results
        if intake.get("submission_id"):
            from app.api.contact_webhook import send_lead_notification
            await send_lead_notification(intake["submission_id"], intake)

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

            # On terminal failure, send lead notification with just form data
            if call_status in ("no-answer", "busy", "failed", "canceled"):
                result = await db.execute(
                    text("SELECT * FROM public.call_intakes WHERE call_sid = :sid"),
                    {"sid": call_sid},
                )
                row = result.fetchone()
                if row:
                    intake = dict(row._mapping)
                    if intake.get("submission_id"):
                        from app.api.contact_webhook import send_lead_notification
                        await send_lead_notification(intake["submission_id"], intake)

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
