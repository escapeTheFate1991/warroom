"""Twilio Voice & SMS client helpers.

Parallel to telnyx_client.py — reads credentials from settings DB.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx
from sqlalchemy import select, text

from app.db.leadgen_db import leadgen_session
from app.models.settings import Setting

logger = logging.getLogger(__name__)

TWILIO_BASE_URL = "https://api.twilio.com/2010-04-01"


class TwilioConfigError(RuntimeError):
    """Raised when required Twilio settings are missing."""


class TwilioRequestError(RuntimeError):
    """Raised when the Twilio API returns an error."""


@dataclass
class TwilioConfig:
    account_sid: str
    auth_token: str
    phone_number: str | None


async def get_setting_value(key: str) -> str | None:
    async with leadgen_session() as session:
        await session.execute(text("SET search_path TO leadgen, public"))
        result = await session.execute(select(Setting.value).where(Setting.key == key))
        value = result.scalar_one_or_none()
        return value.strip() if isinstance(value, str) and value.strip() else None


async def get_twilio_config() -> TwilioConfig:
    """Load Twilio configuration from settings DB."""
    account_sid = await get_setting_value("twilio_account_sid")
    auth_token = await get_setting_value("twilio_auth_token")
    phone_number = await get_setting_value("twilio_phone_number")

    if not account_sid:
        raise TwilioConfigError("Missing required setting: twilio_account_sid")
    if not auth_token:
        raise TwilioConfigError("Missing required setting: twilio_auth_token")

    return TwilioConfig(
        account_sid=account_sid,
        auth_token=auth_token,
        phone_number=phone_number,
    )


async def send_sms(to: str, body: str, from_number: str | None = None) -> dict:
    """Send an SMS via Twilio."""
    config = await get_twilio_config()
    from_num = from_number or config.phone_number
    if not from_num:
        raise TwilioConfigError("No Twilio phone number configured. Set twilio_phone_number in settings.")

    url = f"{TWILIO_BASE_URL}/Accounts/{config.account_sid}/Messages.json"
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            url,
            auth=(config.account_sid, config.auth_token),
            data={"To": to, "From": from_num, "Body": body},
        )
        if resp.status_code not in (200, 201):
            logger.warning("Twilio SMS failed: %s %s", resp.status_code, resp.text[:200])
            raise TwilioRequestError(f"Twilio SMS failed ({resp.status_code}): {resp.text[:200]}")
        return resp.json()


async def make_call(to: str, twiml: str | None = None, url: str | None = None, from_number: str | None = None) -> dict:
    """Initiate a phone call via Twilio."""
    config = await get_twilio_config()
    from_num = from_number or config.phone_number
    if not from_num:
        raise TwilioConfigError("No Twilio phone number configured.")

    call_url = f"{TWILIO_BASE_URL}/Accounts/{config.account_sid}/Calls.json"
    data: dict = {"To": to, "From": from_num}
    if twiml:
        data["Twiml"] = twiml
    elif url:
        data["Url"] = url
    else:
        data["Twiml"] = "<Response><Say>Hello, this is a call from War Room.</Say></Response>"

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            call_url,
            auth=(config.account_sid, config.auth_token),
            data=data,
        )
        if resp.status_code not in (200, 201):
            logger.warning("Twilio call failed: %s %s", resp.status_code, resp.text[:200])
            raise TwilioRequestError(f"Twilio call failed ({resp.status_code}): {resp.text[:200]}")
        return resp.json()


async def get_call_logs(limit: int = 20) -> list[dict]:
    """Fetch recent call logs from Twilio."""
    config = await get_twilio_config()
    url = f"{TWILIO_BASE_URL}/Accounts/{config.account_sid}/Calls.json?PageSize={limit}"
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(url, auth=(config.account_sid, config.auth_token))
        if resp.status_code != 200:
            raise TwilioRequestError(f"Failed to fetch call logs: {resp.status_code}")
        data = resp.json()
        return data.get("calls", [])


async def get_sms_logs(limit: int = 20) -> list[dict]:
    """Fetch recent SMS messages from Twilio."""
    config = await get_twilio_config()
    url = f"{TWILIO_BASE_URL}/Accounts/{config.account_sid}/Messages.json?PageSize={limit}"
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(url, auth=(config.account_sid, config.auth_token))
        if resp.status_code != 200:
            raise TwilioRequestError(f"Failed to fetch SMS logs: {resp.status_code}")
        data = resp.json()
        return data.get("messages", [])


async def check_connection() -> dict:
    """Verify Twilio credentials work."""
    config = await get_twilio_config()
    url = f"{TWILIO_BASE_URL}/Accounts/{config.account_sid}.json"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, auth=(config.account_sid, config.auth_token))
        if resp.status_code != 200:
            return {"connected": False, "error": f"Auth failed ({resp.status_code})"}
        data = resp.json()
        return {
            "connected": True,
            "friendly_name": data.get("friendly_name"),
            "status": data.get("status"),
            "type": data.get("type"),
        }
