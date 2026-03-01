"""OAuth flows for social media platform connections."""
import logging
import os
import secrets
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.crm_db import get_crm_db
from app.models.crm.social import SocialAccount

logger = logging.getLogger(__name__)
router = APIRouter()

# Frontend URL for redirects after OAuth
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3300")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8300")

# ── Helpers ──────────────────────────────────────────────────────────

async def _get_setting(db: AsyncSession, key: str) -> Optional[str]:
    """Get a setting value from the settings table (in leadgen DB)."""
    from app.api.settings import Setting
    from app.db.leadgen_db import leadgen_session
    async with leadgen_session() as ldb:
        result = await ldb.execute(select(Setting).where(Setting.key == key))
        setting = result.scalar_one_or_none()
        return setting.value if setting and setting.value else None


async def _upsert_social_account(
    db: AsyncSession, platform: str, username: str,
    access_token: str, refresh_token: Optional[str] = None,
    profile_url: Optional[str] = None,
    follower_count: int = 0, following_count: int = 0, post_count: int = 0,
    token_expires_at: Optional[datetime] = None,
    extra_data: dict = None,
):
    """Create or update a social account."""
    result = await db.execute(
        select(SocialAccount).where(
            SocialAccount.platform == platform,
            SocialAccount.username == username,
        )
    )
    account = result.scalar_one_or_none()

    if account:
        account.access_token = access_token
        account.refresh_token = refresh_token
        account.profile_url = profile_url or account.profile_url
        account.follower_count = follower_count or account.follower_count
        account.following_count = following_count or account.following_count
        account.post_count = post_count or account.post_count
        account.status = "connected"
        account.last_synced = datetime.now()
    else:
        account = SocialAccount(
            user_id=1,  # TODO: get from auth context
            platform=platform,
            username=username,
            access_token=access_token,
            refresh_token=refresh_token,
            profile_url=profile_url,
            follower_count=follower_count,
            following_count=following_count,
            post_count=post_count,
            status="connected",
        )
        db.add(account)

    await db.commit()
    await db.refresh(account)
    return account


# ══════════════════════════════════════════════════════════════════════
# META (Facebook + Instagram + Threads)
# Uses Facebook Graph API — one OAuth flow covers all three
# ══════════════════════════════════════════════════════════════════════

META_AUTH_URL = "https://www.facebook.com/v21.0/dialog/oauth"
META_TOKEN_URL = "https://graph.facebook.com/v21.0/oauth/access_token"
META_GRAPH_URL = "https://graph.facebook.com/v21.0"

# Scopes for Instagram + Facebook + Threads
META_SCOPES = [
    "pages_show_list",
    "pages_read_engagement",
    "instagram_basic",
    "instagram_manage_insights",
    "instagram_content_publish",
    "threads_basic",
    "threads_content_publish",
    "threads_manage_insights",
    "public_profile",
]


@router.get("/oauth/meta/authorize")
async def meta_authorize(db: AsyncSession = Depends(get_crm_db)):
    """Start Meta OAuth flow (Facebook + Instagram + Threads)."""
    client_id = await _get_setting(db, "meta_app_id")
    if not client_id:
        raise HTTPException(400, "Meta App ID not configured. Go to Settings → API Keys.")

    state = secrets.token_urlsafe(32)
    redirect_uri = f"{BACKEND_URL}/api/social/oauth/meta/callback"

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": ",".join(META_SCOPES),
        "response_type": "code",
        "state": state,
    }
    return {"auth_url": f"{META_AUTH_URL}?{urlencode(params)}"}


@router.get("/oauth/meta/callback")
async def meta_callback(code: str, state: str = "", db: AsyncSession = Depends(get_crm_db)):
    """Handle Meta OAuth callback."""
    client_id = await _get_setting(db, "meta_app_id")
    client_secret = await _get_setting(db, "meta_app_secret")

    if not client_id or not client_secret:
        raise HTTPException(400, "Meta credentials not configured")

    redirect_uri = f"{BACKEND_URL}/api/social/oauth/meta/callback"

    # Exchange code for short-lived token
    async with httpx.AsyncClient() as client:
        token_resp = await client.get(META_TOKEN_URL, params={
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "code": code,
        })

        if token_resp.status_code != 200:
            logger.error(f"Meta token exchange failed: {token_resp.text}")
            return RedirectResponse(f"{FRONTEND_URL}/?tab=marketing-social&error=token_failed")

        token_data = token_resp.json()
        short_token = token_data["access_token"]

        # Exchange for long-lived token (60 days)
        ll_resp = await client.get(META_TOKEN_URL, params={
            "grant_type": "fb_exchange_token",
            "client_id": client_id,
            "client_secret": client_secret,
            "fb_exchange_token": short_token,
        })

        if ll_resp.status_code == 200:
            ll_data = ll_resp.json()
            access_token = ll_data["access_token"]
            expires_in = ll_data.get("expires_in", 5184000)
        else:
            access_token = short_token
            expires_in = 3600

        # Get user profile
        me_resp = await client.get(f"{META_GRAPH_URL}/me", params={
            "fields": "id,name",
            "access_token": access_token,
        })
        me_data = me_resp.json()
        fb_name = me_data.get("name", "Unknown")
        fb_id = me_data.get("id")

        # Save Facebook account
        await _upsert_social_account(
            db, "facebook", fb_name, access_token,
            profile_url=f"https://facebook.com/{fb_id}",
        )

        # Try to get Instagram Business account
        accounts_resp = await client.get(f"{META_GRAPH_URL}/me/accounts", params={
            "access_token": access_token,
        })
        pages = accounts_resp.json().get("data", [])

        for page in pages:
            page_token = page.get("access_token", access_token)
            ig_resp = await client.get(
                f"{META_GRAPH_URL}/{page['id']}",
                params={
                    "fields": "instagram_business_account{id,username,followers_count,follows_count,media_count,profile_picture_url}",
                    "access_token": page_token,
                }
            )
            ig_data = ig_resp.json().get("instagram_business_account")
            if ig_data:
                await _upsert_social_account(
                    db, "instagram",
                    ig_data.get("username", ""),
                    page_token,
                    profile_url=f"https://instagram.com/{ig_data.get('username', '')}",
                    follower_count=ig_data.get("followers_count", 0),
                    following_count=ig_data.get("follows_count", 0),
                    post_count=ig_data.get("media_count", 0),
                )

        # Try Threads (if available via same token)
        try:
            threads_resp = await client.get(
                f"https://graph.threads.net/v1.0/me",
                params={
                    "fields": "id,username,threads_profile_picture_url",
                    "access_token": access_token,
                }
            )
            if threads_resp.status_code == 200:
                threads_data = threads_resp.json()
                await _upsert_social_account(
                    db, "threads",
                    threads_data.get("username", fb_name),
                    access_token,
                    profile_url=f"https://threads.net/@{threads_data.get('username', '')}",
                )
        except Exception as e:
            logger.warning(f"Threads API not available: {e}")

    return RedirectResponse(f"{FRONTEND_URL}/?tab=marketing-social&connected=meta")


# ══════════════════════════════════════════════════════════════════════
# X (Twitter) — OAuth 2.0 with PKCE
# ══════════════════════════════════════════════════════════════════════

X_AUTH_URL = "https://twitter.com/i/oauth2/authorize"
X_TOKEN_URL = "https://api.twitter.com/2/oauth2/token"
X_API_URL = "https://api.twitter.com/2"

X_SCOPES = ["tweet.read", "users.read", "follows.read", "offline.access"]

# Store PKCE verifiers temporarily (in production, use Redis)
_pkce_store: dict = {}


@router.get("/oauth/x/authorize")
async def x_authorize(db: AsyncSession = Depends(get_crm_db)):
    """Start X (Twitter) OAuth flow."""
    client_id = await _get_setting(db, "x_client_id")
    if not client_id:
        raise HTTPException(400, "X Client ID not configured. Go to Settings → API Keys.")

    # PKCE
    code_verifier = secrets.token_urlsafe(64)
    import hashlib
    import base64
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).rstrip(b"=").decode()

    state = secrets.token_urlsafe(32)
    _pkce_store[state] = code_verifier

    redirect_uri = f"{BACKEND_URL}/api/social/oauth/x/callback"

    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": " ".join(X_SCOPES),
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    return {"auth_url": f"{X_AUTH_URL}?{urlencode(params)}"}


@router.get("/oauth/x/callback")
async def x_callback(code: str, state: str = "", db: AsyncSession = Depends(get_crm_db)):
    """Handle X OAuth callback."""
    client_id = await _get_setting(db, "x_client_id")
    client_secret = await _get_setting(db, "x_client_secret")
    code_verifier = _pkce_store.pop(state, None)

    if not client_id or not client_secret:
        raise HTTPException(400, "X credentials not configured")
    if not code_verifier:
        raise HTTPException(400, "Invalid OAuth state")

    redirect_uri = f"{BACKEND_URL}/api/social/oauth/x/callback"

    async with httpx.AsyncClient() as client:
        token_resp = await client.post(X_TOKEN_URL, data={
            "code": code,
            "grant_type": "authorization_code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "code_verifier": code_verifier,
        }, auth=(client_id, client_secret))

        if token_resp.status_code != 200:
            logger.error(f"X token exchange failed: {token_resp.text}")
            return RedirectResponse(f"{FRONTEND_URL}/?tab=marketing-social&error=token_failed")

        token_data = token_resp.json()
        access_token = token_data["access_token"]
        refresh_token = token_data.get("refresh_token")

        # Get user profile
        me_resp = await client.get(f"{X_API_URL}/users/me", params={
            "user.fields": "public_metrics,profile_image_url",
        }, headers={"Authorization": f"Bearer {access_token}"})

        me_data = me_resp.json().get("data", {})
        metrics = me_data.get("public_metrics", {})

        await _upsert_social_account(
            db, "x",
            me_data.get("username", ""),
            access_token,
            refresh_token=refresh_token,
            profile_url=f"https://x.com/{me_data.get('username', '')}",
            follower_count=metrics.get("followers_count", 0),
            following_count=metrics.get("following_count", 0),
            post_count=metrics.get("tweet_count", 0),
        )

    return RedirectResponse(f"{FRONTEND_URL}/?tab=marketing-social&connected=x")


# ══════════════════════════════════════════════════════════════════════
# TikTok — Login Kit OAuth 2.0
# ══════════════════════════════════════════════════════════════════════

TIKTOK_AUTH_URL = "https://www.tiktok.com/v2/auth/authorize"
TIKTOK_TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
TIKTOK_API_URL = "https://open.tiktokapis.com/v2"

TIKTOK_SCOPES = ["user.info.basic", "user.info.stats", "video.list"]


@router.get("/oauth/tiktok/authorize")
async def tiktok_authorize(db: AsyncSession = Depends(get_crm_db)):
    """Start TikTok OAuth flow."""
    client_key = await _get_setting(db, "tiktok_client_key")
    if not client_key:
        raise HTTPException(400, "TikTok Client Key not configured. Go to Settings → API Keys.")

    state = secrets.token_urlsafe(32)
    redirect_uri = f"{BACKEND_URL}/api/social/oauth/tiktok/callback"

    # PKCE
    code_verifier = secrets.token_urlsafe(64)
    import hashlib
    import base64
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).rstrip(b"=").decode()

    _pkce_store[f"tiktok_{state}"] = code_verifier

    params = {
        "client_key": client_key,
        "redirect_uri": redirect_uri,
        "scope": ",".join(TIKTOK_SCOPES),
        "response_type": "code",
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    return {"auth_url": f"{TIKTOK_AUTH_URL}?{urlencode(params)}"}


@router.get("/oauth/tiktok/callback")
async def tiktok_callback(code: str, state: str = "", db: AsyncSession = Depends(get_crm_db)):
    """Handle TikTok OAuth callback."""
    client_key = await _get_setting(db, "tiktok_client_key")
    client_secret = await _get_setting(db, "tiktok_client_secret")
    code_verifier = _pkce_store.pop(f"tiktok_{state}", None)

    if not client_key or not client_secret:
        raise HTTPException(400, "TikTok credentials not configured")

    redirect_uri = f"{BACKEND_URL}/api/social/oauth/tiktok/callback"

    async with httpx.AsyncClient() as client:
        token_resp = await client.post(TIKTOK_TOKEN_URL, data={
            "client_key": client_key,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
            "code_verifier": code_verifier or "",
        })

        if token_resp.status_code != 200:
            logger.error(f"TikTok token exchange failed: {token_resp.text}")
            return RedirectResponse(f"{FRONTEND_URL}/?tab=marketing-social&error=token_failed")

        token_data = token_resp.json()
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        open_id = token_data.get("open_id")

        # Get user info
        user_resp = await client.get(
            f"{TIKTOK_API_URL}/user/info/",
            params={"fields": "display_name,avatar_url,follower_count,following_count,video_count,profile_deep_link"},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        user_data = user_resp.json().get("data", {}).get("user", {})

        await _upsert_social_account(
            db, "tiktok",
            user_data.get("display_name", open_id or ""),
            access_token,
            refresh_token=refresh_token,
            profile_url=user_data.get("profile_deep_link", ""),
            follower_count=user_data.get("follower_count", 0),
            following_count=user_data.get("following_count", 0),
            post_count=user_data.get("video_count", 0),
        )

    return RedirectResponse(f"{FRONTEND_URL}/?tab=marketing-social&connected=tiktok")


# ══════════════════════════════════════════════════════════════════════
# Google (YouTube) — OAuth 2.0
# ══════════════════════════════════════════════════════════════════════

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_YT_API = "https://www.googleapis.com/youtube/v3"

GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]


@router.get("/oauth/google/authorize")
async def google_authorize(db: AsyncSession = Depends(get_crm_db)):
    """Start Google/YouTube OAuth flow."""
    client_id = await _get_setting(db, "google_oauth_client_id")
    if not client_id:
        raise HTTPException(400, "Google OAuth Client ID not configured. Go to Settings → API Keys.")

    state = secrets.token_urlsafe(32)
    redirect_uri = f"{BACKEND_URL}/api/social/oauth/google/callback"

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": " ".join(GOOGLE_SCOPES),
        "response_type": "code",
        "state": state,
        "access_type": "offline",
        "prompt": "consent",
    }
    return {"auth_url": f"{GOOGLE_AUTH_URL}?{urlencode(params)}"}


@router.get("/oauth/google/callback")
async def google_callback(code: str, state: str = "", db: AsyncSession = Depends(get_crm_db)):
    """Handle Google OAuth callback."""
    client_id = await _get_setting(db, "google_oauth_client_id")
    client_secret = await _get_setting(db, "google_oauth_client_secret")

    if not client_id or not client_secret:
        raise HTTPException(400, "Google credentials not configured")

    redirect_uri = f"{BACKEND_URL}/api/social/oauth/google/callback"

    async with httpx.AsyncClient() as client:
        token_resp = await client.post(GOOGLE_TOKEN_URL, data={
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        })

        if token_resp.status_code != 200:
            logger.error(f"Google token exchange failed: {token_resp.text}")
            return RedirectResponse(f"{FRONTEND_URL}/?tab=marketing-social&error=token_failed")

        token_data = token_resp.json()
        access_token = token_data["access_token"]
        refresh_token = token_data.get("refresh_token")

        # Get YouTube channel info
        yt_resp = await client.get(f"{GOOGLE_YT_API}/channels", params={
            "part": "snippet,statistics",
            "mine": "true",
        }, headers={"Authorization": f"Bearer {access_token}"})

        channels = yt_resp.json().get("items", [])
        if channels:
            channel = channels[0]
            snippet = channel.get("snippet", {})
            stats = channel.get("statistics", {})

            await _upsert_social_account(
                db, "youtube",
                snippet.get("title", ""),
                access_token,
                refresh_token=refresh_token,
                profile_url=f"https://youtube.com/channel/{channel['id']}",
                follower_count=int(stats.get("subscriberCount", 0)),
                post_count=int(stats.get("videoCount", 0)),
            )
        else:
            # Save with minimal data
            await _upsert_social_account(
                db, "youtube", "YouTube Account", access_token,
                refresh_token=refresh_token,
            )

    return RedirectResponse(f"{FRONTEND_URL}/?tab=marketing-social&connected=google")


# ══════════════════════════════════════════════════════════════════════
# Token Refresh
# ══════════════════════════════════════════════════════════════════════

@router.post("/oauth/refresh/{account_id}")
async def refresh_token(account_id: int, db: AsyncSession = Depends(get_crm_db)):
    """Refresh an expired OAuth token."""
    result = await db.execute(select(SocialAccount).where(SocialAccount.id == account_id))
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(404, "Account not found")
    if not account.refresh_token:
        raise HTTPException(400, "No refresh token available — re-authorize required")

    refreshers = {
        "x": _refresh_x,
        "tiktok": _refresh_tiktok,
        "youtube": _refresh_google,
        "facebook": _refresh_meta,
        "instagram": _refresh_meta,
        "threads": _refresh_meta,
    }

    refresher = refreshers.get(account.platform)
    if not refresher:
        raise HTTPException(400, f"Token refresh not supported for {account.platform}")

    try:
        new_token = await refresher(db, account)
        return {"status": "refreshed", "platform": account.platform}
    except Exception as e:
        account.status = "expired"
        await db.commit()
        raise HTTPException(500, f"Token refresh failed: {e}")


async def _refresh_x(db: AsyncSession, account: SocialAccount):
    client_id = await _get_setting(db, "x_client_id")
    client_secret = await _get_setting(db, "x_client_secret")
    async with httpx.AsyncClient() as client:
        resp = await client.post(X_TOKEN_URL, data={
            "grant_type": "refresh_token",
            "refresh_token": account.refresh_token,
            "client_id": client_id,
        }, auth=(client_id, client_secret))
        resp.raise_for_status()
        data = resp.json()
        account.access_token = data["access_token"]
        if data.get("refresh_token"):
            account.refresh_token = data["refresh_token"]
        account.status = "connected"
        await db.commit()


async def _refresh_tiktok(db: AsyncSession, account: SocialAccount):
    client_key = await _get_setting(db, "tiktok_client_key")
    client_secret = await _get_setting(db, "tiktok_client_secret")
    async with httpx.AsyncClient() as client:
        resp = await client.post(TIKTOK_TOKEN_URL, data={
            "client_key": client_key,
            "client_secret": client_secret,
            "grant_type": "refresh_token",
            "refresh_token": account.refresh_token,
        })
        resp.raise_for_status()
        data = resp.json()
        account.access_token = data["access_token"]
        if data.get("refresh_token"):
            account.refresh_token = data["refresh_token"]
        account.status = "connected"
        await db.commit()


async def _refresh_google(db: AsyncSession, account: SocialAccount):
    client_id = await _get_setting(db, "google_oauth_client_id")
    client_secret = await _get_setting(db, "google_oauth_client_secret")
    async with httpx.AsyncClient() as client:
        resp = await client.post(GOOGLE_TOKEN_URL, data={
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "refresh_token",
            "refresh_token": account.refresh_token,
        })
        resp.raise_for_status()
        data = resp.json()
        account.access_token = data["access_token"]
        account.status = "connected"
        await db.commit()


async def _refresh_meta(db: AsyncSession, account: SocialAccount):
    # Meta long-lived tokens can be refreshed by exchanging them again
    client_id = await _get_setting(db, "meta_app_id")
    client_secret = await _get_setting(db, "meta_app_secret")
    async with httpx.AsyncClient() as client:
        resp = await client.get(META_TOKEN_URL, params={
            "grant_type": "fb_exchange_token",
            "client_id": client_id,
            "client_secret": client_secret,
            "fb_exchange_token": account.access_token,
        })
        resp.raise_for_status()
        data = resp.json()
        account.access_token = data["access_token"]
        account.status = "connected"
        await db.commit()
