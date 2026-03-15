"""Telnyx Voice API endpoints and webhook persistence."""

from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import Text as SAText, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.crm_db import crm_engine, get_tenant_db
from app.services.tenant import get_org_id, get_user_id
from app.models.crm.activity import Activity, DealActivity, PersonActivity
from app.models.crm.call_log import CallLog
from app.models.crm.contact import Person
from app.models.crm.deal import Deal
from app.models.crm.sms_message import SMSMessage
from app.services.telnyx_client import (
    answer_call,
    TelnyxConfigError,
    TelnyxRequestError,
    hangup_call,
    make_call,
    reject_call,
    send_sms,
    speak_text,
)

logger = logging.getLogger(__name__)
router = APIRouter()


class TelnyxCallRequest(BaseModel):
    phone_number: str


class TelnyxCallControlRequest(BaseModel):
    call_control_id: str


class TelnyxSpeakRequest(BaseModel):
    call_control_id: str
    text: str


class TelnyxSMSRequest(BaseModel):
    to: str
    body: str
    deal_id: int | None = None
    person_id: int | None = None


def unwrap_telnyx_event(body: dict) -> dict:
    """Support both raw Telnyx events and the nested `data` envelope."""
    if isinstance(body.get("data"), dict) and body["data"].get("event_type"):
        return body["data"]
    return body


def parse_telnyx_datetime(value: str | None) -> datetime | None:
    """Parse ISO8601 datetimes emitted by Telnyx."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def extract_recording_url(payload: dict) -> str | None:
    """Pick the best available recording URL from a webhook payload."""
    urls = payload.get("public_recording_urls") or payload.get("recording_urls") or {}
    for key in ("mp3", "wav"):
        if urls.get(key):
            return urls[key]
    return None


def extract_transcript(payload: dict) -> str | None:
    """Extract transcript text from a transcription webhook payload."""
    transcription = payload.get("transcription_data") or {}
    transcript = transcription.get("transcript") or payload.get("transcript")
    return transcript.strip() if isinstance(transcript, str) and transcript.strip() else None


def normalize_phone_number(phone_number: str | None) -> str:
    """Normalize a phone number to digits for fuzzy DB matching."""
    digits = "".join(ch for ch in (phone_number or "") if ch.isdigit())
    if len(digits) >= 10:
        return digits[-10:]
    return digits


def resolve_call_status(event_type: str, payload: dict, current_status: str | None = None) -> str | None:
    """Map Telnyx events to the persisted call status."""
    event_status_map = {
        "call.initiated": "initiated",
        "call.answered": "answered",
        "call.bridged": "answered",
        "call.hangup": "hangup",
    }
    return payload.get("state") or event_status_map.get(event_type) or current_status or event_type


def build_activity_title(call_log: CallLog) -> str:
    """Create a compact activity title for the CRM timeline."""
    outbound_directions = {"outgoing", "outbound"}
    counterpart = call_log.to_number if call_log.direction in outbound_directions else call_log.from_number
    if counterpart:
        return f"Phone call with {counterpart}"
    return "Phone call"


def build_activity_comment(call_log: CallLog) -> str:
    """Create a human-readable activity summary."""
    details = [
        f"from {call_log.from_number or 'unknown'}",
        f"to {call_log.to_number or 'unknown'}",
        f"status {call_log.status or 'unknown'}",
    ]
    if call_log.duration_seconds is not None:
        details.append(f"duration {call_log.duration_seconds}s")
    return "Telnyx call — " + " • ".join(details)


def extract_telnyx_phone_number(value: object) -> str | None:
    """Extract a phone number from Telnyx string/dict fields."""
    if isinstance(value, dict):
        phone_number = value.get("phone_number")
        if isinstance(phone_number, str) and phone_number.strip():
            return phone_number.strip()
        return None
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def build_sms_activity_title(sms_message: SMSMessage) -> str:
    """Create a compact SMS activity title for the CRM timeline."""
    counterpart = sms_message.to_number if sms_message.direction == "outbound" else sms_message.from_number
    if counterpart:
        return f"SMS with {counterpart}"
    return "SMS message"


def build_sms_activity_comment(sms_message: SMSMessage) -> str:
    """Create a human-readable SMS activity summary."""
    details = [
        f"from {sms_message.from_number or 'unknown'}",
        f"to {sms_message.to_number or 'unknown'}",
        f"status {sms_message.status or 'unknown'}",
    ]
    if sms_message.body:
        details.append(f"body {sms_message.body}")
    return "Telnyx SMS — " + " • ".join(details)


async def init_telnyx_tables() -> None:
    """Ensure the CRM Telnyx tables exist."""
    async with crm_engine.begin() as conn:
        await conn.run_sync(CallLog.__table__.create, checkfirst=True)
        await conn.run_sync(SMSMessage.__table__.create, checkfirst=True)


async def find_person_for_call(db: AsyncSession, *numbers: str | None) -> Person | None:
    """Best-effort person lookup from phone numbers."""
    digits_expr = func.regexp_replace(cast(Person.contact_numbers, SAText), "[^0-9]", "", "g")
    for raw_number in numbers:
        normalized = normalize_phone_number(raw_number)
        if not normalized:
            continue
        result = await db.execute(
            select(Person)
            .where(digits_expr.like(f"%{normalized}%"))
            .order_by(Person.updated_at.desc())
            .limit(1)
        )
        person = result.scalars().first()
        if person:
            return person
    return None


async def find_relevant_deal(db: AsyncSession, person_id: int | None) -> Deal | None:
    """Attach the most relevant deal for the matched person, if one exists."""
    if not person_id:
        return None

    result = await db.execute(
        select(Deal)
        .where(Deal.person_id == person_id)
        .order_by(Deal.status.is_(None).desc(), Deal.updated_at.desc())
        .limit(1)
    )
    return result.scalars().first()


async def ensure_person_activity_link(db: AsyncSession, activity_id: int, person_id: int) -> None:
    """Create the activity-to-person link if it does not already exist."""
    result = await db.execute(
        select(PersonActivity).where(
            PersonActivity.activity_id == activity_id,
            PersonActivity.person_id == person_id,
        )
    )
    if not result.scalar_one_or_none():
        db.add(PersonActivity(activity_id=activity_id, person_id=person_id))


async def ensure_deal_activity_link(db: AsyncSession, activity_id: int, deal_id: int) -> None:
    """Create the activity-to-deal link if it does not already exist."""
    result = await db.execute(
        select(DealActivity).where(
            DealActivity.activity_id == activity_id,
            DealActivity.deal_id == deal_id,
        )
    )
    if not result.scalar_one_or_none():
        db.add(DealActivity(activity_id=activity_id, deal_id=deal_id))


async def sync_call_activity(db: AsyncSession, call_log: CallLog) -> None:
    """Create or update the CRM activity that mirrors the call log."""
    identifier_key = None
    identifier_value = None
    for key, value in (
        ("call_session_id", call_log.call_session_id),
        ("call_leg_id", call_log.call_leg_id),
        ("call_control_id", call_log.call_control_id),
    ):
        if value:
            identifier_key = key
            identifier_value = value
            break

    if not identifier_key or not identifier_value:
        return

    result = await db.execute(
        select(Activity).where(
            Activity.type == "call",
            Activity.additional.contains({identifier_key: identifier_value}),
        )
    )
    activity = result.scalars().first()
    additional = {
        "provider": "telnyx",
        "call_session_id": call_log.call_session_id,
        "call_control_id": call_log.call_control_id,
        "call_leg_id": call_log.call_leg_id,
        "direction": call_log.direction,
        "status": call_log.status,
        "from_number": call_log.from_number,
        "to_number": call_log.to_number,
        "recording_url": call_log.recording_url,
        "transcript": call_log.transcript,
    }

    if activity is None:
        activity = Activity(
            title=build_activity_title(call_log),
            type="call",
            comment=build_activity_comment(call_log),
            additional=additional,
            schedule_from=call_log.started_at or call_log.answered_at,
            schedule_to=call_log.ended_at,
            is_done=call_log.ended_at is not None,
        )
        db.add(activity)
        await db.flush()
    else:
        activity.title = build_activity_title(call_log)
        activity.comment = build_activity_comment(call_log)
        activity.additional = additional
        activity.schedule_from = call_log.started_at or call_log.answered_at or activity.schedule_from
        activity.schedule_to = call_log.ended_at or activity.schedule_to
        activity.is_done = call_log.ended_at is not None

    if call_log.person_id:
        await ensure_person_activity_link(db, activity.id, call_log.person_id)
    if call_log.deal_id:
        await ensure_deal_activity_link(db, activity.id, call_log.deal_id)


async def sync_sms_activity(
    db: AsyncSession,
    sms_message: SMSMessage,
    occurred_at: datetime | None = None,
) -> None:
    """Create or update the CRM activity that mirrors the SMS message."""
    if not sms_message.telnyx_message_id:
        return

    result = await db.execute(
        select(Activity).where(
            Activity.type == "sms",
            Activity.additional.contains({"telnyx_message_id": sms_message.telnyx_message_id}),
        )
    )
    activity = result.scalars().first()
    additional = {
        "provider": "telnyx",
        "telnyx_message_id": sms_message.telnyx_message_id,
        "direction": sms_message.direction,
        "status": sms_message.status,
        "from_number": sms_message.from_number,
        "to_number": sms_message.to_number,
        "body": sms_message.body,
    }
    final_statuses = {"delivered", "received", "receiving_failed", "sending_failed"}

    if activity is None:
        activity = Activity(
            title=build_sms_activity_title(sms_message),
            type="sms",
            comment=build_sms_activity_comment(sms_message),
            additional=additional,
            schedule_from=occurred_at,
            schedule_to=occurred_at if sms_message.status in final_statuses else None,
            is_done=sms_message.status in final_statuses,
        )
        db.add(activity)
        await db.flush()
    else:
        activity.title = build_sms_activity_title(sms_message)
        activity.comment = build_sms_activity_comment(sms_message)
        activity.additional = additional
        activity.schedule_from = occurred_at or activity.schedule_from
        activity.schedule_to = occurred_at if sms_message.status in final_statuses else activity.schedule_to
        activity.is_done = sms_message.status in final_statuses

    if sms_message.person_id:
        await ensure_person_activity_link(db, activity.id, sms_message.person_id)
    if sms_message.deal_id:
        await ensure_deal_activity_link(db, activity.id, sms_message.deal_id)


async def load_call_log(db: AsyncSession, payload: dict) -> CallLog | None:
    """Find an existing call log using the best identifier available."""
    for field, value in (
        (CallLog.call_session_id, payload.get("call_session_id")),
        (CallLog.call_leg_id, payload.get("call_leg_id")),
        (CallLog.call_control_id, payload.get("call_control_id")),
    ):
        if not value:
            continue
        result = await db.execute(select(CallLog).where(field == value).limit(1))
        existing = result.scalars().first()
        if existing:
            return existing
    return None


async def load_sms_message(db: AsyncSession, telnyx_message_id: str) -> SMSMessage | None:
    """Find an existing SMS message by Telnyx message id."""
    result = await db.execute(
        select(SMSMessage).where(SMSMessage.telnyx_message_id == telnyx_message_id).limit(1)
    )
    return result.scalars().first()


async def upsert_call_log(db: AsyncSession, raw_body: dict) -> CallLog:
    """Persist an inbound Telnyx webhook into CRM call/activity records."""
    event = unwrap_telnyx_event(raw_body)
    event_type = event.get("event_type")
    payload = event.get("payload") or {}

    if not event_type:
        raise HTTPException(status_code=400, detail="Missing Telnyx event_type")
    if not any(payload.get(key) for key in ("call_session_id", "call_leg_id", "call_control_id")):
        raise HTTPException(status_code=400, detail="Missing call identifiers in webhook payload")

    call_log = await load_call_log(db, payload)
    if call_log is None:
        call_log = CallLog()
        db.add(call_log)

    occurred_at = parse_telnyx_datetime(event.get("occurred_at"))
    started_at = parse_telnyx_datetime(payload.get("start_time"))
    recording_url = extract_recording_url(payload)
    transcript = extract_transcript(payload)
    raw_duration = payload.get("duration_secs") or payload.get("duration_seconds")

    call_log.call_session_id = payload.get("call_session_id") or call_log.call_session_id
    call_log.call_control_id = payload.get("call_control_id") or call_log.call_control_id
    call_log.call_leg_id = payload.get("call_leg_id") or call_log.call_leg_id
    call_log.from_number = payload.get("from") or call_log.from_number
    call_log.to_number = payload.get("to") or call_log.to_number
    call_log.direction = payload.get("direction") or call_log.direction
    call_log.status = resolve_call_status(event_type, payload, call_log.status)
    call_log.started_at = call_log.started_at or started_at or (occurred_at if event_type == "call.initiated" else None)
    if event_type in {"call.answered", "call.bridged"}:
        call_log.answered_at = call_log.answered_at or occurred_at
    if event_type == "call.hangup":
        call_log.ended_at = occurred_at or call_log.ended_at
    if recording_url:
        call_log.recording_url = recording_url
    if transcript:
        is_final = (payload.get("transcription_data") or {}).get("is_final", True)
        if is_final or not call_log.transcript:
            call_log.transcript = transcript
    call_log.telnyx_payload = raw_body

    if isinstance(raw_duration, int):
        call_log.duration_seconds = raw_duration
    elif isinstance(raw_duration, str) and raw_duration.isdigit():
        call_log.duration_seconds = int(raw_duration)

    if call_log.ended_at and not call_log.duration_seconds:
        baseline = call_log.answered_at or call_log.started_at
        if baseline:
            call_log.duration_seconds = max(int((call_log.ended_at - baseline).total_seconds()), 0)

    if not call_log.person_id:
        person = await find_person_for_call(db, call_log.from_number, call_log.to_number)
        if person:
            call_log.person_id = person.id

    if not call_log.deal_id:
        deal = await find_relevant_deal(db, call_log.person_id)
        if deal:
            call_log.deal_id = deal.id

    await sync_call_activity(db, call_log)
    return call_log


async def upsert_sms_message(db: AsyncSession, raw_body: dict) -> SMSMessage:
    """Persist an inbound Telnyx webhook into CRM SMS/activity records."""
    event = unwrap_telnyx_event(raw_body)
    event_type = event.get("event_type")
    payload = event.get("payload") or {}

    if not event_type:
        raise HTTPException(status_code=400, detail="Missing Telnyx event_type")

    telnyx_message_id = payload.get("id") or payload.get("telnyx_message_id")
    if not telnyx_message_id:
        raise HTTPException(status_code=400, detail="Missing Telnyx message identifier in webhook payload")

    sms_message = await load_sms_message(db, telnyx_message_id)
    if sms_message is None:
        sms_message = SMSMessage(telnyx_message_id=telnyx_message_id)
        db.add(sms_message)

    sms_message.direction = "inbound" if event_type == "messaging.received" else "outbound"
    sms_message.from_number = extract_telnyx_phone_number(payload.get("from")) or sms_message.from_number
    sms_message.to_number = extract_telnyx_phone_number(payload.get("to")) or sms_message.to_number
    sms_message.body = payload.get("body") or payload.get("text") or sms_message.body
    sms_message.status = payload.get("status") or sms_message.status or event_type
    sms_message.telnyx_payload = raw_body

    if not sms_message.person_id:
        person = await find_person_for_call(db, sms_message.from_number, sms_message.to_number)
        if person:
            sms_message.person_id = person.id

    if not sms_message.deal_id:
        deal = await find_relevant_deal(db, sms_message.person_id)
        if deal:
            sms_message.deal_id = deal.id

    await sync_sms_activity(db, sms_message, parse_telnyx_datetime(event.get("occurred_at")))
    return sms_message


@router.post("/telnyx/call")
async def create_telnyx_call(body: TelnyxCallRequest):
    """Dial an outbound call through Telnyx."""
    try:
        return await make_call(body.phone_number)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except TelnyxConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except TelnyxRequestError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/telnyx/answer")
async def answer_telnyx_call(body: TelnyxCallControlRequest):
    """Answer an active incoming Telnyx call."""
    try:
        return await answer_call(body.call_control_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except TelnyxConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except TelnyxRequestError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/telnyx/reject")
async def reject_telnyx_call(body: TelnyxCallControlRequest):
    """Reject an active incoming Telnyx call."""
    try:
        return await reject_call(body.call_control_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except TelnyxConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except TelnyxRequestError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/telnyx/hangup")
async def hangup_telnyx_call(body: TelnyxCallControlRequest):
    """Hang up an active Telnyx call."""
    try:
        return await hangup_call(body.call_control_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except TelnyxConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except TelnyxRequestError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/telnyx/speak")
async def speak_on_telnyx_call(body: TelnyxSpeakRequest):
    """Speak text on an active Telnyx call."""
    try:
        return await speak_text(body.call_control_id, body.text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except TelnyxConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except TelnyxRequestError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/telnyx/sms")
async def send_telnyx_sms(request: Request, body: TelnyxSMSRequest, db: AsyncSession = Depends(get_tenant_db)):
    """Send and persist an outbound SMS through Telnyx."""
    org_id = get_org_id(request)
    try:
        result = await send_sms(body.to, body.body)
        sms = SMSMessage(
            telnyx_message_id=result.get("id"),
            direction="outbound",
            from_number=extract_telnyx_phone_number(result.get("from")),
            to_number=body.to,
            body=body.body,
            status="queued",
            deal_id=body.deal_id,
            person_id=body.person_id,
            telnyx_payload=result,
        )
        db.add(sms)
        await db.commit()
        await db.refresh(sms)
        return {"ok": True, "sms_message_id": sms.id, "telnyx_result": result}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except TelnyxConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except TelnyxRequestError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/telnyx/sms-messages")
async def list_sms_messages(
    request: Request,
    deal_id: int | None = None,
    person_id: int | None = None,
    direction: str | None = None,
    db: AsyncSession = Depends(get_tenant_db),
):
    """List recent persisted Telnyx SMS messages."""
    org_id = get_org_id(request)
    query = select(SMSMessage).order_by(SMSMessage.created_at.desc())
    if deal_id is not None:
        query = query.where(SMSMessage.deal_id == deal_id)
    if person_id is not None:
        query = query.where(SMSMessage.person_id == person_id)
    if direction:
        query = query.where(SMSMessage.direction == direction)
    result = await db.execute(query.limit(100))
    messages = result.scalars().all()
    return [
        {
            "id": message.id,
            "telnyx_message_id": message.telnyx_message_id,
            "direction": message.direction,
            "from_number": message.from_number,
            "to_number": message.to_number,
            "body": message.body,
            "status": message.status,
            "deal_id": message.deal_id,
            "person_id": message.person_id,
            "created_at": str(message.created_at),
        }
        for message in messages
    ]


@router.post("/telnyx/webhook")
async def telnyx_webhook(request: Request, body: dict, db: AsyncSession = Depends(get_tenant_db)):
    """Receive and persist Telnyx voice and messaging webhooks."""
    org_id = get_org_id(request)
    event = unwrap_telnyx_event(body)
    event_type = event.get("event_type", "")

    if event_type.startswith("messaging."):
        sms = await upsert_sms_message(db, body)
        await db.commit()
        await db.refresh(sms)
        return {"ok": True, "sms_message_id": sms.id, "status": sms.status}

    call_log = await upsert_call_log(db, body)
    await db.commit()
    await db.refresh(call_log)
    return {
        "ok": True,
        "call_log_id": call_log.id,
        "call_session_id": call_log.call_session_id,
        "status": call_log.status,
    }