"""Email service — uses Resend HTTP API for all transactional emails.

No SMTP. All email goes through Resend (https://resend.com).
API key stored in settings DB as 'resend_api_key'.
"""
import logging
import os
import random
import string

import httpx

logger = logging.getLogger(__name__)

APP_NAME = os.getenv("APP_NAME", "War Room")
FROM_EMAIL = "Stuff N Things <noreply@stuffnthings.io>"

# Cache the API key after first load
_resend_key: str | None = None


async def _get_resend_key() -> str | None:
    """Load Resend API key from settings DB (cached after first call)."""
    global _resend_key
    if _resend_key:
        return _resend_key

    try:
        from sqlalchemy import text
        from app.db.leadgen_db import leadgen_session

        async with leadgen_session() as db:
            result = await db.execute(
                text("SELECT value FROM settings WHERE key = 'resend_api_key'")
            )
            row = result.fetchone()
            if row and row[0]:
                _resend_key = row[0]
                return _resend_key
    except Exception as exc:
        logger.error("Failed to load Resend API key: %s", exc)

    return None


def _get_resend_key_sync() -> str | None:
    """Synchronous version — reads cached key or returns None."""
    return _resend_key


async def _send_email_async(to: str, subject: str, html_body: str, from_email: str | None = None) -> bool:
    """Send an email via Resend HTTP API. Async version."""
    key = await _get_resend_key()
    if not key:
        logger.warning("Resend API key not configured — email to %s not sent: %s", to, subject)
        return False

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": from_email or FROM_EMAIL,
                    "to": [to],
                    "subject": subject,
                    "html": html_body,
                },
            )
            if resp.status_code in (200, 201):
                data = resp.json()
                logger.info("Email sent to %s: %s (id=%s)", to, subject, data.get("id", "?"))
                return True
            else:
                logger.error("Resend API error %d: %s", resp.status_code, resp.text[:200])
                return False
    except Exception as exc:
        logger.error("Failed to send email to %s: %s", to, exc)
        return False


def _send_email(to: str, subject: str, html_body: str, from_email: str | None = None) -> bool:
    """Send an email via Resend HTTP API. Synchronous wrapper (uses httpx sync).

    This is called from asyncio.to_thread() in the contact webhook.
    """
    key = _resend_key
    if not key:
        logger.warning("Resend API key not cached — email to %s not sent: %s (use _send_email_async instead)", to, subject)
        return False

    try:
        resp = httpx.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            json={
                "from": from_email or FROM_EMAIL,
                "to": [to],
                "subject": subject,
                "html": html_body,
            },
            timeout=15.0,
        )
        if resp.status_code in (200, 201):
            data = resp.json()
            logger.info("Email sent to %s: %s (id=%s)", to, subject, data.get("id", "?"))
            return True
        else:
            logger.error("Resend API error %d: %s", resp.status_code, resp.text[:200])
            return False
    except Exception as exc:
        logger.error("Failed to send email to %s: %s", to, exc)
        return False


def generate_code(length: int = 6) -> str:
    """Generate a random numeric verification code."""
    return ''.join(random.choices(string.digits, k=length))


def send_verification_email(to: str, name: str, code: str) -> bool:
    """Send email verification code."""
    html = f"""
    <div style="font-family:system-ui;max-width:480px;margin:0 auto;padding:32px">
        <h2 style="color:#1a1a2e;margin-bottom:8px">Verify your email</h2>
        <p style="color:#555;font-size:15px">Hey {name},</p>
        <p style="color:#555;font-size:15px">Enter this code in {APP_NAME} to verify your email:</p>
        <div style="background:#f0f0f5;border-radius:12px;padding:24px;text-align:center;margin:24px 0">
            <span style="font-size:36px;font-weight:bold;letter-spacing:8px;color:#1a1a2e">{code}</span>
        </div>
        <p style="color:#888;font-size:13px">This code expires in 15 minutes.</p>
        <p style="color:#888;font-size:13px">If you didn't create an account, ignore this email.</p>
    </div>
    """
    return _send_email(to, f"Your {APP_NAME} verification code: {code}", html)


def send_password_reset_email(to: str, name: str, code: str) -> bool:
    """Send password reset code."""
    html = f"""
    <div style="font-family:system-ui;max-width:480px;margin:0 auto;padding:32px">
        <h2 style="color:#1a1a2e;margin-bottom:8px">Reset your password</h2>
        <p style="color:#555;font-size:15px">Hey {name},</p>
        <p style="color:#555;font-size:15px">Enter this code in {APP_NAME} to reset your password:</p>
        <div style="background:#f0f0f5;border-radius:12px;padding:24px;text-align:center;margin:24px 0">
            <span style="font-size:36px;font-weight:bold;letter-spacing:8px;color:#1a1a2e">{code}</span>
        </div>
        <p style="color:#888;font-size:13px">This code expires in 15 minutes.</p>
        <p style="color:#888;font-size:13px">If you didn't request a reset, ignore this email.</p>
    </div>
    """
    return _send_email(to, f"Your {APP_NAME} password reset code: {code}", html)


def send_invite_email(to: str, org_name: str, inviter_name: str, code: str) -> bool:
    """Send organization invite email."""
    html = f"""
    <div style="font-family:system-ui;max-width:480px;margin:0 auto;padding:32px">
        <h2 style="color:#1a1a2e;margin-bottom:8px">You're invited!</h2>
        <p style="color:#555;font-size:15px">{inviter_name} invited you to join <strong>{org_name}</strong> on {APP_NAME}.</p>
        <p style="color:#555;font-size:15px">Use this invite code when signing up:</p>
        <div style="background:#f0f0f5;border-radius:12px;padding:24px;text-align:center;margin:24px 0">
            <span style="font-size:36px;font-weight:bold;letter-spacing:8px;color:#1a1a2e">{code}</span>
        </div>
        <p style="color:#888;font-size:13px">This invite expires in 7 days.</p>
    </div>
    """
    return _send_email(to, f"You're invited to {org_name} on {APP_NAME}", html)
