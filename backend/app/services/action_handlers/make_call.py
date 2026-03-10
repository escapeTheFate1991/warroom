"""Action handler: make_call — initiates a phone call via Twilio."""

import logging

from app.services.twilio_client import make_call as twilio_make_call, TwilioConfigError, TwilioRequestError

logger = logging.getLogger(__name__)


async def handle(step: dict, context: dict, execution: dict) -> dict:
    """Initiate a phone call via Twilio.

    Step config keys:
        to (str, optional): Recipient override. Falls back to context["contact_phone"].
        twiml (str, optional): Inline TwiML for the call.
        url (str, optional): TwiML webhook URL (e.g. IVR flow).
        message (str, optional): Simple spoken message (converted to basic TwiML).
    """
    recipient = step.get("to") or context.get("contact_phone")

    if not recipient:
        return {"success": False, "result": None, "error": "No recipient phone — set 'to' in step config or 'contact_phone' in context"}

    twiml = step.get("twiml")
    url = step.get("url")
    message = step.get("message")

    # If only a message string is provided, wrap it in basic TwiML
    if not twiml and not url and message:
        twiml = f"<Response><Say>{message}</Say></Response>"

    try:
        result = await twilio_make_call(to=recipient, twiml=twiml, url=url)
        sid = result.get("sid", "unknown")
        logger.info("Call initiated to %s (sid=%s)", recipient, sid)
        return {"success": True, "result": {"to": recipient, "sid": sid}, "error": None}
    except (TwilioConfigError, TwilioRequestError) as exc:
        logger.error("make_call handler failed: %s", exc)
        return {"success": False, "result": None, "error": str(exc)}
    except Exception as exc:
        logger.error("make_call handler unexpected error: %s", exc)
        return {"success": False, "result": None, "error": str(exc)}
