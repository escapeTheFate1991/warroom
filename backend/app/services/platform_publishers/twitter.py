"""Twitter/X publisher — X API v2 media upload + tweet creation."""

import asyncio
import logging
from typing import Dict, Tuple

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from .base import get_account_credentials, get_setting, update_account_token

logger = logging.getLogger(__name__)

X_API = "https://api.x.com/2"
X_UPLOAD_API = "https://upload.x.com/1.1"
X_TOKEN_URL = "https://api.x.com/2/oauth2/token"


async def _refresh_token(db: AsyncSession, account: dict) -> str:
    """Refresh an X (Twitter) access token."""
    client_id = await get_setting(db, "x_client_id")
    client_secret = await get_setting(db, "x_client_secret")
    if not client_id or not client_secret:
        raise ValueError("X credentials not configured for token refresh")

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(X_TOKEN_URL, data={
            "grant_type": "refresh_token",
            "refresh_token": account["refresh_token"],
            "client_id": client_id,
        }, auth=(client_id, client_secret))
        resp.raise_for_status()
        data = resp.json()
        new_token = data["access_token"]
        new_refresh = data.get("refresh_token")
        await update_account_token(db, account["id"], new_token, new_refresh)
        return new_token


class TwitterPublisher:
    """Publish content to X (Twitter) via API v2."""

    async def publish(
        self, db: AsyncSession, org_id: int, media_url: str, caption: str,
        content_type: str = "video", hashtags: list | None = None,
    ) -> Tuple[bool, Dict]:
        """Publish a tweet with optional media.

        For video: uses chunked media upload API (v1.1) then creates tweet (v2).
        For image: uses simple media upload then creates tweet.
        """
        account = await get_account_credentials(db, "x", org_id)
        token = account["access_token"]

        tweet_text = caption
        if hashtags:
            tweet_text = tweet_text + "\n\n" + " ".join(f"#{h.lstrip('#')}" for h in hashtags)

        # X has 280 char limit for text
        if len(tweet_text) > 280:
            tweet_text = tweet_text[:277] + "..."

        try:
            result = await self._do_publish(token, media_url, tweet_text, content_type)
            return True, result
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                logger.info("X token expired, refreshing...")
                token = await _refresh_token(db, account)
                result = await self._do_publish(token, media_url, tweet_text, content_type)
                return True, result
            return False, {"error": f"X API error: {e.response.status_code} - {e.response.text[:200]}"}
        except Exception as e:
            logger.error("X publish failed: %s", e)
            return False, {"error": str(e)}

    async def _do_publish(
        self, token: str, media_url: str, tweet_text: str, content_type: str
    ) -> Dict:
        """Upload media and create tweet."""
        headers = {"Authorization": f"Bearer {token}"}

        async with httpx.AsyncClient(timeout=120) as client:
            # Step 1: Download media
            dl_resp = await client.get(media_url, follow_redirects=True)
            dl_resp.raise_for_status()
            media_bytes = dl_resp.content
            media_type = dl_resp.headers.get("content-type", "video/mp4")

            # Step 2: Upload media via chunked upload (v1.1 API)
            media_id = await self._chunked_upload(client, headers, media_bytes, media_type, content_type)

            # Step 3: Create tweet with media (v2 API)
            tweet_payload = {"text": tweet_text}
            if media_id:
                tweet_payload["media"] = {"media_ids": [media_id]}

            tweet_resp = await client.post(
                f"{X_API}/tweets",
                headers={**headers, "Content-Type": "application/json"},
                json=tweet_payload,
            )
            tweet_resp.raise_for_status()
            tweet_data = tweet_resp.json().get("data", {})
            tweet_id = tweet_data.get("id", "")

            return {
                "url": f"https://x.com/i/status/{tweet_id}" if tweet_id else "",
                "platform_id": tweet_id,
            }

    async def _chunked_upload(
        self, client: httpx.AsyncClient, headers: dict,
        media_bytes: bytes, media_type: str, content_type: str
    ) -> str:
        """Upload media using X's chunked upload API (v1.1).

        Three-phase process: INIT → APPEND → FINALIZE.
        """
        media_category = "tweet_video" if content_type == "video" else "tweet_image"

        # INIT
        init_resp = await client.post(
            f"{X_UPLOAD_API}/media/upload.json",
            headers=headers,
            data={
                "command": "INIT",
                "total_bytes": str(len(media_bytes)),
                "media_type": media_type,
                "media_category": media_category,
            },
        )
        init_resp.raise_for_status()
        media_id = init_resp.json()["media_id_string"]

        # APPEND (upload in 5MB chunks)
        chunk_size = 5 * 1024 * 1024
        for i in range(0, len(media_bytes), chunk_size):
            chunk = media_bytes[i:i + chunk_size]
            segment = i // chunk_size
            append_resp = await client.post(
                f"{X_UPLOAD_API}/media/upload.json",
                headers=headers,
                data={
                    "command": "APPEND",
                    "media_id": media_id,
                    "segment_index": str(segment),
                },
                files={"media_data": ("chunk", chunk, media_type)},
            )
            if append_resp.status_code not in (200, 204):
                raise Exception(f"X media APPEND failed: {append_resp.text[:200]}")

        # FINALIZE
        fin_resp = await client.post(
            f"{X_UPLOAD_API}/media/upload.json",
            headers=headers,
            data={"command": "FINALIZE", "media_id": media_id},
        )
        fin_resp.raise_for_status()
        fin_data = fin_resp.json()

        # For video, wait for processing
        processing = fin_data.get("processing_info")
        if processing:
            for _ in range(30):
                wait_secs = processing.get("check_after_secs", 5)
                await asyncio.sleep(wait_secs)
                status_resp = await client.get(
                    f"{X_UPLOAD_API}/media/upload.json",
                    headers=headers,
                    params={"command": "STATUS", "media_id": media_id},
                )
                if status_resp.status_code == 200:
                    status_data = status_resp.json()
                    processing = status_data.get("processing_info")
                    if not processing or processing.get("state") == "succeeded":
                        break
                    if processing.get("state") == "failed":
                        raise Exception(f"X media processing failed: {processing.get('error', {})}")

        return media_id
