"""Action handler: send_email — sends email via Resend API."""

import logging

from app.services.email import _send_email_async

logger = logging.getLogger(__name__)


async def handle(step: dict, context: dict, execution: dict) -> dict:
    """Send an email using the Resend email service.

    Step config keys:
        subject (str): Email subject line.
        body (str): Email HTML body.
        to (str, optional): Recipient override. Falls back to context["contact_email"].
    """
    subject = step.get("subject", "")
    body = step.get("body", "")
    recipient = step.get("to") or context.get("contact_email")

    if not recipient:
        return {"success": False, "result": None, "error": "No recipient email — set 'to' in step config or 'contact_email' in context"}

    if not subject:
        return {"success": False, "result": None, "error": "Missing 'subject' in step config"}

    try:
        sent = await _send_email_async(to=recipient, subject=subject, html_body=body)
        if sent:
            logger.info("Email sent to %s: %s", recipient, subject)
            return {"success": True, "result": {"to": recipient, "subject": subject}, "error": None}
        else:
            return {"success": False, "result": None, "error": "Resend API returned failure — check API key and recipient"}
    except Exception as exc:
        logger.error("send_email handler failed: %s", exc)
        return {"success": False, "result": None, "error": str(exc)}
