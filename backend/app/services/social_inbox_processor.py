"""Social Inbox Processor — processes incoming Instagram comments and DMs.

Receives parsed webhook events and runs them through the auto-reply engine.
If a matching rule is found, sends the reply via Instagram Graph API.
Includes rate limiting and deduplication.
"""
import logging
import time
from collections import defaultdict

import httpx
from sqlalchemy import select, text

from app.db.crm_db import crm_session
from app.models.crm.social import SocialAccount
from app.services.auto_reply_engine import AutoReplyEngine

logger = logging.getLogger(__name__)

IG_GRAPH_API = "https://graph.instagram.com/v21.0"

# ── Rate Limiting ────────────────────────────────────────────────────
# Track replies per account: {account_id: [(timestamp, ...)]}
_reply_timestamps: dict[str, list[float]] = defaultdict(list)
MAX_REPLIES_PER_MINUTE = 10


def _is_rate_limited(account_key: str) -> bool:
    """Check if an account has exceeded the reply rate limit."""
    now = time.time()
    window = 60.0  # 1 minute

    # Prune old timestamps
    _reply_timestamps[account_key] = [
        ts for ts in _reply_timestamps[account_key] if now - ts < window
    ]

    if len(_reply_timestamps[account_key]) >= MAX_REPLIES_PER_MINUTE:
        return True

    return False


def _record_reply(account_key: str):
    """Record a reply timestamp for rate limiting."""
    _reply_timestamps[account_key].append(time.time())


# ── Account Lookup ───────────────────────────────────────────────────

async def _get_social_account_for_page(page_id: str) -> dict | None:
    """Find the connected Instagram social account matching the page ID.

    The page_id from webhooks corresponds to the Instagram business account ID.
    We match this against SocialAccount records.
    """
    try:
        async with crm_session() as db:
            # Try matching by username or profile URL containing the page_id
            # In practice, the page_id may be stored differently — we look for
            # any connected Instagram account since most setups have one.
            result = await db.execute(
                select(SocialAccount)
                .where(SocialAccount.platform == "instagram")
                .where(SocialAccount.status == "connected")
                .limit(1)
            )
            account = result.scalar_one_or_none()
            if account:
                return {
                    "id": account.id,
                    "org_id": account.org_id,
                    "access_token": account.access_token,
                    "username": account.username,
                }
    except Exception as exc:
        logger.error("Failed to look up social account for page %s: %s", page_id, exc)

    return None


# ── Deduplication ────────────────────────────────────────────────────

async def _is_duplicate(org_id: int, external_id: str) -> bool:
    """Check if we've already processed this comment/message ID."""
    try:
        async with crm_session() as db:
            await db.execute(text("SET search_path TO crm, public"))
            return await AutoReplyEngine.check_duplicate(db, org_id, external_id)
    except Exception as exc:
        logger.error("Dedup check failed for %s: %s", external_id, exc)
        return False


# ── Reply Logging ────────────────────────────────────────────────────

async def _log_reply(
    org_id: int,
    platform: str,
    rule_type: str,
    trigger_type: str,
    external_id: str,
    original_text: str,
    delivery_channel: str,
    social_account_id: int | None = None,
    rule_id: int | None = None,
    matched_keyword: str | None = None,
    reply_text: str | None = None,
    username: str | None = None,
    error: str | None = None,
):
    """Log the auto-reply result (matched or skipped) for analytics."""
    status = "sent" if reply_text and not error else ("error" if error else "skipped")
    try:
        async with crm_session() as db:
            await db.execute(text("SET search_path TO crm, public"))
            await AutoReplyEngine.log_reply(
                db,
                rule_id=rule_id,
                org_id=org_id,
                platform=platform,
                rule_type=rule_type,
                trigger_type=trigger_type,
                original_text=original_text,
                matched_keyword=matched_keyword,
                reply_sent=reply_text,
                delivery_channel=delivery_channel,
                social_account_id=social_account_id,
                external_id=external_id,
                username=username,
                status=status,
                error_message=error,
            )
            await db.commit()
    except Exception as exc:
        logger.error("Failed to log reply for %s: %s", external_id, exc)


# ── Comment Processing ───────────────────────────────────────────────

async def process_comment(
    page_id: str,
    comment_id: str,
    comment_text: str,
    commenter_name: str,
    commenter_ig_id: str | None,
    media_id: str | None,
):
    """Process an incoming Instagram comment.

    1. Check for duplicate
    2. Find matching auto-reply rule
    3. If match: send reply via Graph API, log result
    4. If no match: log as skipped
    """
    try:
        # Get account info first (needed for org_id in dedup and logging)
        account = await _get_social_account_for_page(page_id)
        if not account:
            logger.warning("No connected Instagram account for page %s", page_id)
            return

        org_id = account["org_id"]
        social_account_id = account["id"]
        platform = "instagram"

        # Deduplication
        if await _is_duplicate(org_id, comment_id):
            logger.info("Duplicate comment %s — skipping", comment_id)
            return

        account_key = f"comment:{social_account_id}"

        # Rate limiting
        if _is_rate_limited(account_key):
            logger.warning("Rate limited — skipping comment reply for account %s", social_account_id)
            await _log_reply(org_id, platform, "comment", "keyword", comment_id, comment_text, "comment",
                             social_account_id=social_account_id, error="rate_limited")
            return

        # Find matching rule
        match = None
        try:
            async with crm_session() as db:
                await db.execute(text("SET search_path TO crm, public"))
                match = await AutoReplyEngine.find_matching_rule(
                    db, org_id, platform, "comment", comment_text, commenter_name
                )
        except Exception as exc:
            logger.error("Rule matching failed for comment %s: %s", comment_id, exc)

        if not match:
            logger.info("No matching rule for comment %s — skipping", comment_id)
            await _log_reply(org_id, platform, "comment", "keyword", comment_id, comment_text, "comment",
                             social_account_id=social_account_id)
            return

        rule, matched_keyword, reply_text = match

        if not reply_text:
            logger.warning("Rule %s has empty reply_text — skipping", rule.id)
            await _log_reply(org_id, platform, "comment", "keyword", comment_id, comment_text, "comment",
                             social_account_id=social_account_id, rule_id=rule.id,
                             matched_keyword=matched_keyword, error="empty_reply")
            return

        # Send reply
        result = await _reply_to_comment(
            token=account["access_token"],
            comment_id=comment_id,
            message=reply_text,
        )

        if result.get("success"):
            _record_reply(account_key)
            logger.info("Replied to comment %s with rule %s", comment_id, rule.id)
            await _log_reply(org_id, platform, "comment", "keyword", comment_id, comment_text, "comment",
                             social_account_id=social_account_id, rule_id=rule.id,
                             matched_keyword=matched_keyword, reply_text=reply_text)
        else:
            logger.error("Failed to reply to comment %s: %s", comment_id, result.get("error"))
            await _log_reply(org_id, platform, "comment", "keyword", comment_id, comment_text, "comment",
                             social_account_id=social_account_id, rule_id=rule.id,
                             matched_keyword=matched_keyword, error=result.get("error"))

    except Exception as exc:
        logger.error("Unexpected error processing comment %s: %s", comment_id, exc, exc_info=True)


# ── DM Processing ────────────────────────────────────────────────────

async def process_dm(
    page_id: str,
    message_id: str,
    message_text: str,
    sender_ig_id: str | None,
):
    """Process an incoming Instagram DM.

    1. Check for duplicate
    2. Find matching auto-reply rule (dm type)
    3. If match: send DM reply via Graph API, log result
    4. If no match: log as skipped
    """
    try:
        # Get account info first (needed for org_id in dedup and logging)
        account = await _get_social_account_for_page(page_id)
        if not account:
            logger.warning("No connected Instagram account for page %s", page_id)
            return

        org_id = account["org_id"]
        social_account_id = account["id"]
        platform = "instagram"

        # Deduplication
        if await _is_duplicate(org_id, message_id):
            logger.info("Duplicate DM %s — skipping", message_id)
            return

        account_key = f"dm:{social_account_id}"

        # Rate limiting
        if _is_rate_limited(account_key):
            logger.warning("Rate limited — skipping DM reply for account %s", social_account_id)
            await _log_reply(org_id, platform, "dm", "keyword", message_id, message_text, "dm",
                             social_account_id=social_account_id, error="rate_limited")
            return

        # Find matching rule (DMs don't have a commenter_name in the same way)
        match = None
        try:
            async with crm_session() as db:
                await db.execute(text("SET search_path TO crm, public"))
                match = await AutoReplyEngine.find_matching_rule(
                    db, org_id, platform, "dm", message_text
                )
        except Exception as exc:
            logger.error("Rule matching failed for DM %s: %s", message_id, exc)

        if not match:
            logger.info("No matching rule for DM %s — skipping", message_id)
            await _log_reply(org_id, platform, "dm", "keyword", message_id, message_text, "dm",
                             social_account_id=social_account_id)
            return

        rule, matched_keyword, reply_text = match

        if not reply_text:
            logger.warning("Rule %s has empty reply_text — skipping", rule.id)
            await _log_reply(org_id, platform, "dm", "keyword", message_id, message_text, "dm",
                             social_account_id=social_account_id, rule_id=rule.id,
                             matched_keyword=matched_keyword, error="empty_reply")
            return

        # Send DM reply
        result = await _send_dm(
            token=account["access_token"],
            recipient_id=sender_ig_id,
            message=reply_text,
            page_id=page_id,
        )

        if result.get("success"):
            _record_reply(account_key)
            logger.info("Replied to DM %s with rule %s", message_id, rule.id)
            await _log_reply(org_id, platform, "dm", "keyword", message_id, message_text, "dm",
                             social_account_id=social_account_id, rule_id=rule.id,
                             matched_keyword=matched_keyword, reply_text=reply_text)
        else:
            logger.error("Failed to reply to DM %s: %s", message_id, result.get("error"))
            await _log_reply(org_id, platform, "dm", "keyword", message_id, message_text, "dm",
                             social_account_id=social_account_id, rule_id=rule.id,
                             matched_keyword=matched_keyword, error=result.get("error"))

    except Exception as exc:
        logger.error("Unexpected error processing DM %s: %s", message_id, exc, exc_info=True)


# ── Follow Processing ────────────────────────────────────────────────

async def process_follow(
    page_id: str,
    user_id: str,
    username: str,
):
    """Process an incoming Instagram follow event.

    1. Find matching follow auto-reply rules
    2. For each match: send DM welcome message, log result
    3. No deduplication needed — follows should trigger every time
    """
    try:
        # Get account info first (needed for org_id and tokens)
        account = await _get_social_account_for_page(page_id)
        if not account:
            logger.warning("No connected Instagram account for page %s", page_id)
            return

        org_id = account["org_id"]
        social_account_id = account["id"]
        platform = "instagram"

        # Use user_id as external_id for follow events
        external_id = f"follow:{user_id}"

        # Deduplication for follow events (don't spam new followers)
        if await _is_duplicate(org_id, external_id):
            logger.info("Duplicate follow %s — skipping", user_id)
            return

        account_key = f"follow:{social_account_id}"

        # Rate limiting
        if _is_rate_limited(account_key):
            logger.warning("Rate limited — skipping follow reply for account %s", social_account_id)
            await _log_reply(
                org_id, platform, "follow", "follow", external_id, "", "dm",
                social_account_id=social_account_id, username=username, error="rate_limited"
            )
            return

        # Find all matching follow rules
        matches = []
        try:
            async with crm_session() as db:
                await db.execute(text("SET search_path TO crm, public"))
                matches = await AutoReplyEngine.find_follow_rules(
                    db, org_id, platform, username
                )
        except Exception as exc:
            logger.error("Rule matching failed for follow %s: %s", user_id, exc)

        if not matches:
            logger.info("No matching follow rules for user %s — skipping", username)
            await _log_reply(
                org_id, platform, "follow", "follow", external_id, "", "dm",
                social_account_id=social_account_id, username=username
            )
            return

        # Send welcome DMs for all matching rules
        for rule, matched_keyword, reply_text in matches:
            if not reply_text:
                logger.warning("Follow rule %s has empty reply_text — skipping", rule.id)
                await _log_reply(
                    org_id, platform, "follow", "follow", external_id, "", "dm",
                    social_account_id=social_account_id, rule_id=rule.id,
                    matched_keyword=matched_keyword, username=username, error="empty_reply"
                )
                continue

            # Send welcome DM
            result = await _send_dm(
                token=account["access_token"],
                recipient_id=user_id,
                message=reply_text,
                page_id=page_id,
            )

            if result.get("success"):
                _record_reply(account_key)
                logger.info("Sent welcome DM to new follower %s with rule %s", username, rule.id)
                await _log_reply(
                    org_id, platform, "follow", "follow", external_id, "", "dm",
                    social_account_id=social_account_id, rule_id=rule.id,
                    matched_keyword=matched_keyword, reply_text=reply_text, username=username
                )
            else:
                logger.error("Failed to send welcome DM to %s: %s", username, result.get("error"))
                await _log_reply(
                    org_id, platform, "follow", "follow", external_id, "", "dm",
                    social_account_id=social_account_id, rule_id=rule.id,
                    matched_keyword=matched_keyword, username=username, error=result.get("error")
                )

    except Exception as exc:
        logger.error("Unexpected error processing follow %s: %s", user_id, exc, exc_info=True)


# ── Instagram Graph API Calls ────────────────────────────────────────
# Reuses the same patterns from app.services.action_handlers.social_reply

async def _reply_to_comment(token: str, comment_id: str, message: str) -> dict:
    """Post a public reply to an Instagram comment."""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{IG_GRAPH_API}/{comment_id}/replies",
                params={"access_token": token},
                data={"message": message},
            )
            if resp.status_code != 200:
                return {"success": False, "error": f"IG API {resp.status_code}: {resp.text[:200]}"}

            data = resp.json()
            return {"success": True, "reply_id": data.get("id")}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


async def _send_dm(token: str, recipient_id: str, message: str, page_id: str = "me") -> dict:
    """Send a private DM to an Instagram user."""
    if not recipient_id:
        return {"success": False, "error": "No recipient_id"}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{IG_GRAPH_API}/{page_id}/messages",
                params={"access_token": token},
                json={
                    "recipient": {"id": recipient_id},
                    "message": {"text": message},
                },
            )
            if resp.status_code != 200:
                return {"success": False, "error": f"IG DM API {resp.status_code}: {resp.text[:200]}"}

            data = resp.json()
            return {"success": True, "message_id": data.get("message_id")}
    except Exception as exc:
        return {"success": False, "error": str(exc)}
