"""Facebook publisher — Graph API video/photo posting to Pages."""

import logging
from typing import Dict, Tuple

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from .base import get_account_credentials, get_setting, update_account_token

logger = logging.getLogger(__name__)

FB_GRAPH = "https://graph.facebook.com/v21.0"
META_TOKEN_URL = "https://graph.facebook.com/v21.0/oauth/access_token"


async def _refresh_token(db: AsyncSession, account: dict) -> str:
    """Refresh a Facebook/Meta token."""
    client_id = await get_setting(db, "meta_app_id")
    client_secret = await get_setting(db, "meta_app_secret")
    if not client_id or not client_secret:
        raise ValueError("Meta app credentials not configured for token refresh")

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(META_TOKEN_URL, params={
            "grant_type": "fb_exchange_token",
            "client_id": client_id,
            "client_secret": client_secret,
            "fb_exchange_token": account["access_token"],
        })
        resp.raise_for_status()
        new_token = resp.json()["access_token"]
        await update_account_token(db, account["id"], new_token)
        return new_token


class FacebookPublisher:
    """Publish content to Facebook via Graph API."""

    async def publish(
        self, db: AsyncSession, org_id: int, media_url: str, caption: str,
        content_type: str = "video", hashtags: list | None = None,
    ) -> Tuple[bool, Dict]:
        """Publish a post to Facebook.

        Supports video (uploaded via URL) and image (photo URL) posting.
        Posts to the user's feed. For Page posting, the account token should
        already be a Page token (set during OAuth).
        """
        account = await get_account_credentials(db, "facebook", org_id)
        token = account["access_token"]

        if hashtags:
            caption = caption + "\n\n" + " ".join(f"#{h.lstrip('#')}" for h in hashtags)

        try:
            result = await self._do_publish(token, media_url, caption, content_type)
            return True, result
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401 or (
                e.response.status_code == 400
                and "token" in e.response.text.lower()
            ):
                logger.info("Facebook token expired, refreshing...")
                token = await _refresh_token(db, account)
                result = await self._do_publish(token, media_url, caption, content_type)
                return True, result
            return False, {"error": f"Facebook API error: {e.response.status_code} - {e.response.text[:200]}"}
        except Exception as e:
            logger.error("Facebook publish failed: %s", e)
            return False, {"error": str(e)}

    async def _do_publish(
        self, token: str, media_url: str, caption: str, content_type: str
    ) -> Dict:
        """Post to Facebook via Graph API."""
        async with httpx.AsyncClient(timeout=120) as client:
            if content_type == "video":
                # Video upload via URL
                resp = await client.post(
                    f"{FB_GRAPH}/me/videos",
                    params={
                        "file_url": media_url,
                        "description": caption,
                        "access_token": token,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                video_id = data.get("id", "")
                return {
                    "url": f"https://www.facebook.com/video.php?v={video_id}" if video_id else "",
                    "platform_id": video_id,
                }
            else:
                # Photo upload via URL
                resp = await client.post(
                    f"{FB_GRAPH}/me/photos",
                    params={
                        "url": media_url,
                        "caption": caption,
                        "access_token": token,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                post_id = data.get("post_id", data.get("id", ""))
                return {
                    "url": f"https://www.facebook.com/{post_id}" if post_id else "",
                    "platform_id": post_id,
                }
