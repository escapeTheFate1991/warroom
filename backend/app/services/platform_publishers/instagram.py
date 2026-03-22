"""Instagram publisher — Graph API video/image/carousel posting.

Wraps the existing InstagramPublisher logic but sources tokens from
crm.social_accounts and handles 401 token refresh.
"""

import logging
from typing import Dict, Tuple

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from .base import get_account_credentials, get_setting, update_account_token

logger = logging.getLogger(__name__)

INSTAGRAM_GRAPH = "https://graph.instagram.com"
META_TOKEN_URL = "https://graph.facebook.com/v21.0/oauth/access_token"


async def _refresh_token(db: AsyncSession, account: dict) -> str:
    """Refresh an Instagram/Meta token by exchanging the long-lived token."""
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
        data = resp.json()
        new_token = data["access_token"]
        await update_account_token(db, account["id"], new_token)
        return new_token


class InstagramPublisher:
    """Publish content to Instagram via Graph API."""

    async def publish(
        self, db: AsyncSession, org_id: int, media_url: str, caption: str,
        content_type: str = "video", hashtags: list | None = None,
    ) -> Tuple[bool, Dict]:
        """Publish a post to Instagram.

        Args:
            db: Database session
            org_id: Organization ID
            media_url: Public URL to the media file
            caption: Post caption
            content_type: "video", "image", or "carousel"
            hashtags: Optional hashtags to append to caption

        Returns:
            (success, result_dict) where result_dict has "url" on success or "error" on failure
        """
        account = await get_account_credentials(db, "instagram", org_id)
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
                logger.info("Instagram token expired, refreshing...")
                token = await _refresh_token(db, account)
                result = await self._do_publish(token, media_url, caption, content_type)
                return True, result
            return False, {"error": f"Instagram API error: {e.response.status_code} - {e.response.text[:200]}"}
        except Exception as e:
            logger.error("Instagram publish failed: %s", e)
            return False, {"error": str(e)}

    async def _do_publish(
        self, token: str, media_url: str, caption: str, content_type: str
    ) -> Dict:
        """Execute the actual publish via Graph API."""
        async with httpx.AsyncClient(timeout=60) as client:
            # Step 1: Create media container
            container_params = {
                "caption": caption,
                "access_token": token,
            }

            if content_type == "video":
                container_params["media_type"] = "REELS"
                container_params["video_url"] = media_url
            else:
                container_params["image_url"] = media_url

            resp = await client.post(
                f"{INSTAGRAM_GRAPH}/me/media", params=container_params
            )
            resp.raise_for_status()
            container_id = resp.json()["id"]

            # Step 2: For video, poll until container is ready
            if content_type == "video":
                import asyncio
                for _ in range(30):  # up to ~5 min
                    status_resp = await client.get(
                        f"{INSTAGRAM_GRAPH}/{container_id}",
                        params={"fields": "status_code", "access_token": token},
                    )
                    status_data = status_resp.json()
                    if status_data.get("status_code") == "FINISHED":
                        break
                    if status_data.get("status_code") == "ERROR":
                        raise Exception(f"Container processing failed: {status_data}")
                    await asyncio.sleep(10)

            # Step 3: Publish the container
            pub_resp = await client.post(
                f"{INSTAGRAM_GRAPH}/me/media_publish",
                params={"creation_id": container_id, "access_token": token},
            )
            pub_resp.raise_for_status()
            media_id = pub_resp.json()["id"]

            # Step 4: Get permalink
            link_resp = await client.get(
                f"{INSTAGRAM_GRAPH}/{media_id}",
                params={"fields": "permalink", "access_token": token},
            )
            permalink = ""
            if link_resp.status_code == 200:
                permalink = link_resp.json().get("permalink", "")

            return {"url": permalink, "platform_id": media_id}
