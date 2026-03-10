"""Action handler: send_sms — sends SMS via Twilio."""

import logging

from app.services.twilio_client import send_sms as twilio_send_sms, TwilioConfigError, TwilioRequestError

logger = logging.getLogger(__name__)


async def handle(step: dict, context: dict, execution: dict) -> dict:
    """Send an SMS via Twilio.

    Step config keys:
        message (str): SMS body text.
        to (str, optional): Recipient override. Falls back to context["contact_phone"].
    """
    message = step.get("message", "")
    recipient = step.get("to") or context.get("contact_phone")

    if not recipient:
        return {"success": False, "result": None, "error": "No recipient phone — set 'to' in step config or 'contact_phone' in context"}

    if not message:
        return {"success": False, "result": None, "error": "Missing 'message' in step config"}

    try:
        result = await twilio_send_sms(to=recipient, body=message)
        sid = result.get("sid", "unknown")
        logger.info("SMS sent to %s (sid=%s)", recipient, sid)
        return {"success": True, "result": {"to": recipient, "sid": sid}, "error": None}
    except (TwilioConfigError, TwilioRequestError) as exc:
        logger.error("send_sms handler failed: %s", exc)
        return {"success": False, "result": None, "error": str(exc)}
    except Exception as exc:
        logger.error("send_sms handler unexpected error: %s", exc)
        return {"success": False, "result": None, "error": str(exc)}
