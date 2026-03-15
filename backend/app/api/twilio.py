"""Twilio Voice & SMS API endpoints."""

from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.crm_db import get_tenant_db
from app.services.tenant import get_org_id, get_user_id
from app.services.twilio_client import (
    TwilioConfigError,
    TwilioRequestError,
    check_connection,
    get_call_logs,
    get_sms_logs,
    make_call,
    send_sms,
)

logger = logging.getLogger(__name__)
router = APIRouter()


class SMSRequest(BaseModel):
    to: str
    body: str
    from_number: str | None = None


class CallRequest(BaseModel):
    to: str
    twiml: str | None = None
    url: str | None = None
    from_number: str | None = None


# ── Status ────────────────────────────────────────────────

@router.get("/twilio/status")
async def twilio_status():
    """Check Twilio connection status."""
    try:
        return await check_connection()
    except TwilioConfigError as e:
        return {"connected": False, "error": str(e)}
    except Exception as e:
        logger.warning("Twilio status check failed: %s", e)
        return {"connected": False, "error": "Connection check failed"}


# ── SMS ───────────────────────────────────────────────────

@router.post("/twilio/sms")
async def send_sms_endpoint(body: SMSRequest):
    """Send an SMS message via Twilio."""
    try:
        result = await send_sms(to=body.to, body=body.body, from_number=body.from_number)
        return {
            "success": True,
            "sid": result.get("sid"),
            "status": result.get("status"),
            "to": result.get("to"),
        }
    except TwilioConfigError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except TwilioRequestError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/twilio/sms/logs")
async def sms_logs(limit: int = 20):
    """Get recent SMS messages."""
    try:
        messages = await get_sms_logs(limit=limit)
        return [
            {
                "sid": m.get("sid"),
                "to": m.get("to"),
                "from": m.get("from"),
                "body": m.get("body"),
                "status": m.get("status"),
                "direction": m.get("direction"),
                "date_sent": m.get("date_sent"),
            }
            for m in messages
        ]
    except TwilioConfigError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except TwilioRequestError as e:
        raise HTTPException(status_code=502, detail=str(e))


# ── Calls ─────────────────────────────────────────────────

@router.post("/twilio/call")
async def make_call_endpoint(body: CallRequest):
    """Initiate a phone call via Twilio."""
    try:
        result = await make_call(to=body.to, twiml=body.twiml, url=body.url, from_number=body.from_number)
        return {
            "success": True,
            "sid": result.get("sid"),
            "status": result.get("status"),
            "to": result.get("to"),
        }
    except TwilioConfigError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except TwilioRequestError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/twilio/calls/logs")
async def call_logs(limit: int = 20):
    """Get recent call logs."""
    try:
        calls = await get_call_logs(limit=limit)
        return [
            {
                "sid": c.get("sid"),
                "to": c.get("to"),
                "from": c.get("from_formatted", c.get("from")),
                "status": c.get("status"),
                "direction": c.get("direction"),
                "duration": c.get("duration"),
                "start_time": c.get("start_time"),
                "end_time": c.get("end_time"),
            }
            for c in calls
        ]
    except TwilioConfigError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except TwilioRequestError as e:
        raise HTTPException(status_code=502, detail=str(e))
