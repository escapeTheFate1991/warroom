"""Minimal Telnyx Voice API client helpers."""

from __future__ import annotations

from dataclasses import dataclass

import httpx
from sqlalchemy import select, text

from app.config import settings
from app.db.leadgen_db import leadgen_session
from app.models.settings import Setting

TELNYX_BASE_URL = "https://api.telnyx.com/v2"


class TelnyxConfigError(RuntimeError):
    """Raised when required Telnyx settings are missing."""


class TelnyxRequestError(RuntimeError):
    """Raised when the Telnyx API returns an error."""


@dataclass
class TelnyxConfig:
    api_key: str
    phone_number: str
    connection_id: str | None
    webhook_url: str


async def get_setting_value(key: str) -> str | None:
    """Fetch a setting from the shared settings table."""
    async with leadgen_session() as session:
        await session.execute(text("SET search_path TO leadgen, public"))
        result = await session.execute(select(Setting.value).where(Setting.key == key))
        value = result.scalar_one_or_none()
        return value.strip() if isinstance(value, str) and value.strip() else None


async def get_telnyx_config() -> TelnyxConfig:
    """Load Telnyx configuration from settings DB."""
    api_key = await get_setting_value("telnyx_api_key")
    phone_number = await get_setting_value("telnyx_phone_number")
    connection_id = await get_setting_value("telnyx_connection_id")

    if not api_key:
        raise TelnyxConfigError("Missing required setting: telnyx_api_key")
    if not phone_number:
        raise TelnyxConfigError("Missing required setting: telnyx_phone_number")

    return TelnyxConfig(
        api_key=api_key,
        phone_number=phone_number,
        connection_id=connection_id,
        webhook_url=f"{settings.BACKEND_URL.rstrip('/')}/api/telnyx/webhook",
    )


def build_call_payload(
    phone_number: str,
    from_number: str,
    webhook_url: str,
    connection_id: str | None = None,
) -> dict:
    """Build the outbound Telnyx call request payload."""
    payload = {
        "to": phone_number.strip(),
        "from": from_number,
        "webhook_url": webhook_url,
        "webhook_url_method": "POST",
    }
    if connection_id:
        payload["connection_id"] = connection_id
    return payload


async def _post(path: str, payload: dict, api_key: str) -> dict:
    """POST to the Telnyx API and return the decoded JSON body."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(base_url=TELNYX_BASE_URL, timeout=30.0) as client:
        response = await client.post(path, json=payload, headers=headers)

    if response.status_code >= 400:
        try:
            detail = response.json()
        except ValueError:
            detail = {"detail": response.text}
        raise TelnyxRequestError(f"Telnyx API request failed ({response.status_code}): {detail}")

    body = response.json()
    return body.get("data", body)


async def make_call(phone_number: str) -> dict:
    """Create an outbound call through Telnyx."""
    if not phone_number or not phone_number.strip():
        raise ValueError("phone_number is required")

    config = await get_telnyx_config()
    payload = build_call_payload(
        phone_number=phone_number,
        from_number=config.phone_number,
        webhook_url=config.webhook_url,
        connection_id=config.connection_id,
    )
    return await _post("/calls", payload, config.api_key)


async def answer_call(call_control_id: str) -> dict:
    """Answer an incoming Telnyx call."""
    if not call_control_id or not call_control_id.strip():
        raise ValueError("call_control_id is required")

    config = await get_telnyx_config()
    return await _post(f"/calls/{call_control_id}/actions/answer", {}, config.api_key)


async def reject_call(call_control_id: str) -> dict:
    """Reject an incoming Telnyx call."""
    if not call_control_id or not call_control_id.strip():
        raise ValueError("call_control_id is required")

    config = await get_telnyx_config()
    return await _post(f"/calls/{call_control_id}/actions/reject", {}, config.api_key)


async def send_sms(to: str, body: str) -> dict:
    """Send an SMS through Telnyx."""
    if not to or not to.strip():
        raise ValueError("to is required")
    if not body or not body.strip():
        raise ValueError("body is required")

    config = await get_telnyx_config()
    payload = {
        "from": config.phone_number,
        "to": to.strip(),
        "text": body.strip(),
    }
    return await _post("/messages", payload, config.api_key)


async def hangup_call(call_control_id: str) -> dict:
    """Hang up a live Telnyx call."""
    if not call_control_id or not call_control_id.strip():
        raise ValueError("call_control_id is required")

    config = await get_telnyx_config()
    return await _post(f"/calls/{call_control_id}/actions/hangup", {}, config.api_key)


async def speak_text(call_control_id: str, text_to_speak: str) -> dict:
    """Speak text on an active Telnyx call."""
    if not call_control_id or not call_control_id.strip():
        raise ValueError("call_control_id is required")
    if not text_to_speak or not text_to_speak.strip():
        raise ValueError("text is required")

    config = await get_telnyx_config()
    payload = {
        "payload": text_to_speak.strip(),
        "payload_type": "text",
        "language": "en-US",
        "voice": "female",
    }
    return await _post(f"/calls/{call_control_id}/actions/speak", payload, config.api_key)