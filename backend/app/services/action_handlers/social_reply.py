"""Action handler: social_reply — replies to an Instagram comment or sends a DM.

Supports two modes:
  - comment_reply: Posts a public reply to the triggering comment.
  - direct_message: Sends a private DM to the commenter.
"""

import logging
import httpx

from sqlalchemy import select
from app.db.crm_db import crm_session
from app.models.crm.social import SocialAccount

logger = logging.getLogger(__name__)

IG_GRAPH_API = "https://graph.instagram.com/v21.0"


async def _get_ig_token() -> str | None:
    """Retrieve Instagram access token from connected social accounts."""
    async with crm_session() as db:
        result = await db.execute(
            select(SocialAccount.access_token)
            .where(SocialAccount.platform == "instagram")
            .where(SocialAccount.status == "connected")
            .limit(1)
        )
        row = result.first()
        return row[0] if row else None


async def handle(step: dict, context: dict, execution: dict) -> dict:
    """Execute a social reply action.

    Step config keys:
        reply_type (str): 'comment_reply' or 'direct_message'
        message (str): The reply / DM text.
    Context keys:
        comment_id (str): Instagram comment ID (for comment_reply).
        commenter_ig_id (str): Instagram user ID (for direct_message).
        media_id (str): Instagram media ID (for comment_reply).
    """
    reply_type = step.get("reply_type", "comment_reply")
    message = step.get("message", "")

    if not message:
        return {"success": False, "result": None, "error": "Missing 'message' in step config"}

    token = await _get_ig_token()
    if not token:
        return {"success": False, "result": None, "error": "No connected Instagram account found"}

    try:
        if reply_type == "direct_message":
            return await _send_dm(token, message, context)
        else:
            return await _reply_comment(token, message, context)
    except Exception as exc:
        logger.error("social_reply handler error: %s", exc)
        return {"success": False, "result": None, "error": str(exc)}


async def _reply_comment(token: str, message: str, context: dict) -> dict:
    """Post a public reply to an Instagram comment."""
    comment_id = context.get("comment_id")
    if not comment_id:
        return {"success": False, "result": None, "error": "No comment_id in context"}

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"{IG_GRAPH_API}/{comment_id}/replies",
            params={"access_token": token},
            data={"message": message},
        )
        if resp.status_code != 200:
            return {"success": False, "result": None, "error": f"IG API {resp.status_code}: {resp.text[:200]}"}

        data = resp.json()
        logger.info("Replied to comment %s: reply_id=%s", comment_id, data.get("id"))
        return {"success": True, "result": {"reply_id": data.get("id"), "comment_id": comment_id}, "error": None}


async def _send_dm(token: str, message: str, context: dict) -> dict:
    """Send a private DM to an Instagram user."""
    recipient_id = context.get("commenter_ig_id")
    if not recipient_id:
        return {"success": False, "result": None, "error": "No commenter_ig_id in context"}

    ig_page_id = context.get("ig_page_id", "me")

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"{IG_GRAPH_API}/{ig_page_id}/messages",
            params={"access_token": token},
            json={
                "recipient": {"id": recipient_id},
                "message": {"text": message},
            },
        )
        if resp.status_code != 200:
            return {"success": False, "result": None, "error": f"IG DM API {resp.status_code}: {resp.text[:200]}"}

        data = resp.json()
        logger.info("DM sent to %s: message_id=%s", recipient_id, data.get("message_id"))
        return {"success": True, "result": {"recipient_id": recipient_id, "message_id": data.get("message_id")}, "error": None}

