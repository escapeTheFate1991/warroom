"""Instagram Webhook Handler — receives comment and DM events from Meta.

Meta sends webhook events for Instagram comments and messages.
GET  /webhooks/instagram  — verification handshake (returns hub.challenge)
POST /webhooks/instagram  — event delivery (validated via X-Hub-Signature-256)

No auth middleware — webhooks are authenticated via HMAC signature.
"""
import asyncio
import hashlib
import hmac
import logging

from fastapi import APIRouter, Request, Query
from fastapi.responses import PlainTextResponse, JSONResponse

from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/webhooks")


# ── GET: Webhook Verification ────────────────────────────────────────

@router.get("/instagram")
async def verify_webhook(
    request: Request,
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
):
    """Meta webhook verification handshake.

    Meta sends GET with hub.mode=subscribe, hub.verify_token, hub.challenge.
    If verify_token matches our config, return hub.challenge as plain text.
    """
    if (
        hub_mode == "subscribe"
        and hub_verify_token
        and hub_verify_token == settings.INSTAGRAM_WEBHOOK_VERIFY_TOKEN
    ):
        logger.info("Instagram webhook verified successfully")
        return PlainTextResponse(content=hub_challenge, status_code=200)

    logger.warning("Instagram webhook verification failed (mode=%s)", hub_mode)
    return JSONResponse(status_code=403, content={"error": "Verification failed"})


# ── POST: Event Delivery ─────────────────────────────────────────────

@router.post("/instagram")
async def receive_webhook(request: Request):
    """Receive Instagram webhook events from Meta.

    Validates X-Hub-Signature-256 header, parses payload, and processes
    comment/message events asynchronously. Returns 200 immediately
    (Meta expects response within 20 seconds).
    """
    body = await request.body()

    # Validate signature
    if not _verify_signature(request, body):
        logger.warning("Instagram webhook signature validation failed")
        return JSONResponse(status_code=403, content={"error": "Invalid signature"})

    try:
        payload = await request.json()
    except Exception:
        logger.error("Instagram webhook: invalid JSON payload")
        return JSONResponse(status_code=400, content={"error": "Invalid JSON"})

    # Only process Instagram events
    if payload.get("object") != "instagram":
        logger.debug("Ignoring non-instagram webhook object: %s", payload.get("object"))
        return JSONResponse(status_code=200, content={"status": "ignored"})

    # Process entries asynchronously — don't block the webhook response
    for entry in payload.get("entry", []):
        asyncio.create_task(_process_entry(entry))

    return JSONResponse(status_code=200, content={"status": "ok"})


# ── Signature Validation ─────────────────────────────────────────────

def _verify_signature(request: Request, body: bytes) -> bool:
    """Validate X-Hub-Signature-256 using HMAC-SHA256 with app secret."""
    app_secret = settings.INSTAGRAM_APP_SECRET
    if not app_secret:
        # If no app secret configured, skip validation (dev mode)
        logger.warning("INSTAGRAM_APP_SECRET not set — skipping signature validation")
        return True

    signature_header = request.headers.get("x-hub-signature-256", "")
    if not signature_header.startswith("sha256="):
        return False

    expected_signature = signature_header[7:]  # Strip "sha256=" prefix
    computed = hmac.new(
        app_secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(computed, expected_signature)


# ── Entry Processing ─────────────────────────────────────────────────

async def _process_entry(entry: dict):
    """Process a single webhook entry (may contain comments, messages, or follows)."""
    page_id = entry.get("id")

    try:
        # Handle field-based changes (comments, follows, etc.)
        for change in entry.get("changes", []):
            field = change.get("field")
            value = change.get("value", {})

            if field == "comments":
                await _handle_comment_event(page_id, value)
            elif field == "followers":
                await _handle_follow_event(page_id, value)
            else:
                logger.debug("Ignoring webhook field: %s", field)

        # Handle message events (messaging array)
        for messaging in entry.get("messaging", []):
            await _handle_message_event(page_id, messaging)

    except Exception as exc:
        logger.error("Error processing webhook entry for page %s: %s", page_id, exc, exc_info=True)


async def _handle_comment_event(page_id: str, value: dict):
    """Process an incoming Instagram comment event."""
    comment_id = value.get("id")
    comment_text = value.get("text", "")
    commenter = value.get("from", {})
    commenter_ig_id = commenter.get("id")
    commenter_name = commenter.get("username", "")
    media = value.get("media", {})
    media_id = media.get("id")

    if not comment_id:
        logger.warning("Comment event missing comment ID, skipping")
        return

    logger.info(
        "Received comment on page %s: comment_id=%s, from=%s, media=%s",
        page_id, comment_id, commenter_name, media_id,
    )

    try:
        from app.services.social_inbox_processor import process_comment
        await process_comment(
            page_id=page_id,
            comment_id=comment_id,
            comment_text=comment_text,
            commenter_name=commenter_name,
            commenter_ig_id=commenter_ig_id,
            media_id=media_id,
        )
    except Exception as exc:
        logger.error("Failed to process comment %s: %s", comment_id, exc, exc_info=True)


async def _handle_follow_event(page_id: str, value: dict):
    """Process an incoming Instagram follow event."""
    user_id = value.get("user_id")
    username = value.get("username", "")
    action = value.get("action", "")  # 'follow' or 'unfollow'

    if action != "follow":
        logger.debug("Ignoring non-follow action: %s", action)
        return

    if not user_id:
        logger.warning("Follow event missing user_id, skipping")
        return

    logger.info(
        "Received follow event on page %s: user_id=%s, username=%s",
        page_id, user_id, username,
    )

    try:
        from app.services.social_inbox_processor import process_follow
        await process_follow(
            page_id=page_id,
            user_id=user_id,
            username=username,
        )
    except Exception as exc:
        logger.error("Failed to process follow %s: %s", user_id, exc, exc_info=True)


async def _handle_message_event(page_id: str, messaging: dict):
    """Process an incoming Instagram DM event."""
    sender = messaging.get("sender", {})
    sender_ig_id = sender.get("id")
    message = messaging.get("message", {})
    message_id = message.get("mid")
    message_text = message.get("text", "")

    if not message_id:
        logger.debug("Messaging event missing message ID, skipping (could be read receipt)")
        return

    # Ignore echo messages (messages sent by the page itself)
    if sender_ig_id == page_id:
        logger.debug("Ignoring echo message from page %s", page_id)
        return

    logger.info(
        "Received DM on page %s: message_id=%s, from=%s",
        page_id, message_id, sender_ig_id,
    )

    try:
        from app.services.social_inbox_processor import process_dm
        await process_dm(
            page_id=page_id,
            message_id=message_id,
            message_text=message_text,
            sender_ig_id=sender_ig_id,
        )
    except Exception as exc:
        logger.error("Failed to process DM %s: %s", message_id, exc, exc_info=True)
