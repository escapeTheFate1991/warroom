"""TikTok publisher — Content Posting API v2 video upload."""

import asyncio
import logging
from typing import Dict, Tuple

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from .base import get_account_credentials, get_setting, update_account_token

logger = logging.getLogger(__name__)

TIKTOK_API = "https://open.tiktokapis.com/v2"
TIKTOK_TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"


async def _refresh_token(db: AsyncSession, account: dict) -> str:
    """Refresh a TikTok access token."""
    client_key = await get_setting(db, "tiktok_client_key")
    client_secret = await get_setting(db, "tiktok_client_secret")
    if not client_key or not client_secret:
        raise ValueError("TikTok credentials not configured for token refresh")

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(TIKTOK_TOKEN_URL, data={
            "client_key": client_key,
            "client_secret": client_secret,
            "grant_type": "refresh_token",
            "refresh_token": account["refresh_token"],
        })
        resp.raise_for_status()
        data = resp.json()
        new_token = data["access_token"]
        new_refresh = data.get("refresh_token")
        await update_account_token(db, account["id"], new_token, new_refresh)
        return new_token


class TikTokPublisher:
    """Publish video content to TikTok via Content Posting API."""

    async def publish(
        self, db: AsyncSession, org_id: int, media_url: str, caption: str,
        content_type: str = "video", hashtags: list | None = None,
    ) -> Tuple[bool, Dict]:
        """Publish a video to TikTok.

        Uses the Content Posting API pull-from-URL approach:
        1. POST /v2/post/publish/video/init/ with video URL
        2. Poll publish status until complete
        """
        if content_type != "video":
            return False, {"error": "TikTok only supports video content"}

        account = await get_account_credentials(db, "tiktok", org_id)
        token = account["access_token"]

        if hashtags:
            caption = caption + " " + " ".join(f"#{h.lstrip('#')}" for h in hashtags)

        try:
            result = await self._do_publish(token, media_url, caption)
            return True, result
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                logger.info("TikTok token expired, refreshing...")
                token = await _refresh_token(db, account)
                result = await self._do_publish(token, media_url, caption)
                return True, result
            return False, {"error": f"TikTok API error: {e.response.status_code} - {e.response.text[:200]}"}
        except Exception as e:
            logger.error("TikTok publish failed: %s", e)
            return False, {"error": str(e)}

    async def _do_publish(self, token: str, media_url: str, caption: str) -> Dict:
        """Execute TikTok video publish via pull-from-URL."""
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=UTF-8",
        }

        async with httpx.AsyncClient(timeout=120) as client:
            # Step 1: Initialize video publish
            init_resp = await client.post(
                f"{TIKTOK_API}/post/publish/video/init/",
                headers=headers,
                json={
                    "post_info": {
                        "title": caption[:150],  # TikTok title limit
                        "privacy_level": "SELF_ONLY",  # Safe default; user can change on TikTok
                        "disable_comment": False,
                        "disable_duet": False,
                        "disable_stitch": False,
                    },
                    "source_info": {
                        "source": "PULL_FROM_URL",
                        "video_url": media_url,
                    },
                },
            )
            init_resp.raise_for_status()
            init_data = init_resp.json()

            if init_data.get("error", {}).get("code") != "ok":
                error_msg = init_data.get("error", {}).get("message", "Unknown error")
                raise Exception(f"TikTok publish init failed: {error_msg}")

            publish_id = init_data.get("data", {}).get("publish_id", "")

            # Step 2: Poll for publish status
            for _ in range(30):  # up to ~5 min
                status_resp = await client.post(
                    f"{TIKTOK_API}/post/publish/status/fetch/",
                    headers=headers,
                    json={"publish_id": publish_id},
                )
                if status_resp.status_code == 200:
                    status_data = status_resp.json()
                    pub_status = status_data.get("data", {}).get("status")
                    if pub_status == "PUBLISH_COMPLETE":
                        video_id = status_data.get("data", {}).get("publicaly_available_post_id", [""])[0]
                        return {
                            "url": f"https://www.tiktok.com/@/video/{video_id}" if video_id else "",
                            "platform_id": publish_id,
                        }
                    if pub_status == "FAILED":
                        fail_reason = status_data.get("data", {}).get("fail_reason", "Unknown")
                        raise Exception(f"TikTok publish failed: {fail_reason}")
                await asyncio.sleep(10)

            raise Exception("TikTok publish timed out waiting for completion")
