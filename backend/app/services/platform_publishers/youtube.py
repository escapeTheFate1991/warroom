"""YouTube publisher — Data API v3 Shorts upload via resumable upload."""

import logging
from typing import Dict, Tuple

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from .base import get_account_credentials, get_setting, update_account_token

logger = logging.getLogger(__name__)

YOUTUBE_UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"


async def _refresh_token(db: AsyncSession, account: dict) -> str:
    """Refresh a Google/YouTube access token."""
    client_id = await get_setting(db, "google_oauth_client_id")
    client_secret = await get_setting(db, "google_oauth_client_secret")
    if not client_id or not client_secret:
        raise ValueError("Google OAuth credentials not configured for token refresh")

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(GOOGLE_TOKEN_URL, data={
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "refresh_token",
            "refresh_token": account["refresh_token"],
        })
        resp.raise_for_status()
        new_token = resp.json()["access_token"]
        await update_account_token(db, account["id"], new_token)
        return new_token


class YouTubePublisher:
    """Publish Shorts to YouTube via Data API v3 resumable upload."""

    async def publish(
        self, db: AsyncSession, org_id: int, media_url: str, caption: str,
        content_type: str = "video", hashtags: list | None = None,
    ) -> Tuple[bool, Dict]:
        """Upload a YouTube Short.

        Uses the resumable upload protocol:
        1. Download video from media_url
        2. Initiate resumable upload with metadata
        3. Upload video bytes
        4. Return video URL
        """
        if content_type != "video":
            return False, {"error": "YouTube Shorts only supports video content"}

        account = await get_account_credentials(db, "youtube", org_id)
        token = account["access_token"]

        title = caption[:100] if caption else "Short"
        description = caption
        if hashtags:
            description = description + "\n\n" + " ".join(f"#{h.lstrip('#')}" for h in hashtags)
            # YouTube uses #Shorts in title/description to identify Shorts
            if "#shorts" not in description.lower():
                description += " #Shorts"
        else:
            if "#shorts" not in description.lower():
                description += "\n\n#Shorts"

        try:
            result = await self._do_publish(token, media_url, title, description)
            return True, result
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                logger.info("YouTube token expired, refreshing...")
                token = await _refresh_token(db, account)
                result = await self._do_publish(token, media_url, title, description)
                return True, result
            return False, {"error": f"YouTube API error: {e.response.status_code} - {e.response.text[:200]}"}
        except Exception as e:
            logger.error("YouTube publish failed: %s", e)
            return False, {"error": str(e)}

    async def _do_publish(
        self, token: str, media_url: str, title: str, description: str
    ) -> Dict:
        """Execute YouTube Shorts upload via resumable upload protocol."""
        import json

        headers = {"Authorization": f"Bearer {token}"}

        async with httpx.AsyncClient(timeout=300) as client:
            # Step 1: Download the video from media_url
            dl_resp = await client.get(media_url, follow_redirects=True)
            dl_resp.raise_for_status()
            video_bytes = dl_resp.content
            content_type = dl_resp.headers.get("content-type", "video/mp4")

            # Step 2: Initiate resumable upload
            metadata = {
                "snippet": {
                    "title": title,
                    "description": description,
                    "categoryId": "22",  # People & Blogs
                },
                "status": {
                    "privacyStatus": "public",
                    "selfDeclaredMadeForKids": False,
                },
            }

            init_resp = await client.post(
                YOUTUBE_UPLOAD_URL,
                params={
                    "uploadType": "resumable",
                    "part": "snippet,status",
                },
                headers={
                    **headers,
                    "Content-Type": "application/json; charset=UTF-8",
                    "X-Upload-Content-Length": str(len(video_bytes)),
                    "X-Upload-Content-Type": content_type,
                },
                content=json.dumps(metadata),
            )
            init_resp.raise_for_status()

            upload_url = init_resp.headers.get("Location")
            if not upload_url:
                raise Exception("YouTube did not return a resumable upload URL")

            # Step 3: Upload video bytes
            upload_resp = await client.put(
                upload_url,
                headers={"Content-Type": content_type},
                content=video_bytes,
            )
            upload_resp.raise_for_status()
            data = upload_resp.json()
            video_id = data.get("id", "")

            return {
                "url": f"https://youtube.com/shorts/{video_id}" if video_id else "",
                "platform_id": video_id,
            }
