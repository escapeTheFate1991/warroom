"""Email service for auth flows — verification codes and password resets.

Uses SMTP (configurable). Falls back to logging if SMTP not configured.
"""
import logging
import os
import random
import smtplib
import string
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)

# SMTP Configuration from environment
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
SMTP_FROM = os.getenv("SMTP_FROM", "noreply@stuffnthings.io")
APP_NAME = os.getenv("APP_NAME", "War Room")


def generate_code(length: int = 6) -> str:
    """Generate a random numeric verification code."""
    return ''.join(random.choices(string.digits, k=length))


def _send_email(to: str, subject: str, html_body: str) -> bool:
    """Send an email via SMTP. Returns True on success."""
    if not SMTP_HOST or not SMTP_USER:
        logger.warning("SMTP not configured — would send to %s: %s", to, subject)
        logger.info("Email body preview: %s", html_body[:200])
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{APP_NAME} <{SMTP_FROM}>"
        msg["To"] = to
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_FROM, to, msg.as_string())

        logger.info("Email sent to %s: %s", to, subject)
        return True
    except Exception as e:
        logger.error("Failed to send email to %s: %s", to, e)
        return False


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
