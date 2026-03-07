"""OAuth flows for social media platform connections."""
import logging
import os
import secrets
import time
import threading
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import urlencode, quote

import httpx
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.crm_db import get_crm_db
from app.models.crm.social import SocialAccount

logger = logging.getLogger(__name__)
router = APIRouter()

# Frontend URL for redirects after OAuth
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3300")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8300")

# TTL for PKCE verifiers and state nonces (10 minutes)
_OAUTH_TTL_SECONDS = 600

# ── Helpers ──────────────────────────────────────────────────────────

def _oauth_complete_page(success: bool, platform: str, error: str = "") -> HTMLResponse:
    """Return an HTML page that notifies the parent window and closes the popup."""
    status = "connected" if success else "error"
    message = f"{platform} connected successfully!" if success else (error or f"Failed to connect {platform}")
    return HTMLResponse(f"""<!DOCTYPE html>
<html><head><title>OAuth Complete</title></head>
<body style="background:#0a0a0f;color:#e2e8f0;font-family:system-ui;display:flex;align-items:center;justify-content:center;height:100vh;margin:0">
<div style="text-align:center">
  <p style="font-size:18px;margin-bottom:8px">{"✅" if success else "❌"} {message}</p>
  <p style="font-size:13px;color:#64748b">This window will close automatically...</p>
</div>
<script>
  if (window.opener) {{
    window.opener.postMessage({{ type: "oauth_complete", status: "{status}", platform: "{platform}", error: "{error}" }}, "{FRONTEND_URL}");
  }}
  setTimeout(() => window.close(), 1500);
</script>
</body></html>""")


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
    user_id: int = 1,  # TODO: pass real user_id from auth context when OAuth callbacks support auth
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
            user_id=user_id,
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

# Instagram API with Instagram Login — direct OAuth, no Facebook Page required
# Docs: https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login
INSTAGRAM_AUTH_URL = "https://www.instagram.com/oauth/authorize"
INSTAGRAM_TOKEN_URL = "https://api.instagram.com/oauth/access_token"
INSTAGRAM_GRAPH_URL = "https://graph.instagram.com"

# Threads uses a completely separate OAuth flow and API
THREADS_AUTH_URL = "https://threads.net/oauth/authorize"
THREADS_TOKEN_URL = "https://graph.threads.net/oauth/access_token"
THREADS_GRAPH_URL = "https://graph.threads.net/v1.0"

# Facebook scopes (Facebook OAuth dialog)
FACEBOOK_SCOPES = [
    "pages_show_list",
    "pages_read_engagement",
    "public_profile",
]

# Instagram scopes (Instagram OAuth dialog — direct, no Page needed)
INSTAGRAM_SCOPES = [
    "instagram_business_basic",
    "instagram_business_manage_messages",
    "instagram_business_manage_comments",
    "instagram_business_content_publish",
    "instagram_business_manage_insights",
]

# Threads scopes (Threads OAuth dialog — completely separate)
THREADS_SCOPES = [
    "threads_basic",
    "threads_content_publish",
    "threads_manage_insights",
    "threads_manage_replies",
]


@router.get("/oauth/meta/authorize")
async def meta_authorize(
    platform: str = "meta",
    db: AsyncSession = Depends(get_crm_db),
):
    """Start Meta OAuth flow. platform=facebook|instagram|threads (or meta for both FB+IG)."""
    # Each platform has its own App/Client ID in Meta Developer Dashboard
    PLATFORM_SETTINGS = {
        "instagram": "instagram_app_id",
        "threads": "threads_client_id",
        "facebook": "meta_app_id",
        "meta": "meta_app_id",
    }

    setting_key = PLATFORM_SETTINGS.get(platform, "meta_app_id")
    client_id = await _get_setting(db, setting_key)
    
    # Fallback to meta_app_id if platform-specific ID not set
    if not client_id and setting_key != "meta_app_id":
        client_id = await _get_setting(db, "meta_app_id")
    
    if not client_id:
        raise HTTPException(400, f"App ID not configured for {platform}. Go to Settings → API Keys.")

    # Encode requested platform in state so callback knows what to save
    nonce = secrets.token_urlsafe(24)
    state = f"{platform}:{nonce}"
    _nonce_store(state)

    if platform == "instagram":
        # Instagram API with Instagram Login — goes to instagram.com, not facebook.com
        # No Facebook Page required. Works with Professional (Creator + Business) accounts.
        redirect_uri = f"{BACKEND_URL}/api/social/oauth/instagram/callback"
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": ",".join(INSTAGRAM_SCOPES),
            "response_type": "code",
            "state": state,
            "force_reauth": "true",
        }
        return {"auth_url": f"{INSTAGRAM_AUTH_URL}?{urlencode(params)}"}
    elif platform == "threads":
        # Threads uses its own OAuth endpoint
        redirect_uri = f"{BACKEND_URL}/api/social/oauth/threads/callback"
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": ",".join(THREADS_SCOPES),
            "response_type": "code",
            "state": state,
        }
        return {"auth_url": f"{THREADS_AUTH_URL}?{urlencode(params)}"}
    else:
        # Facebook uses the Facebook OAuth dialog
        redirect_uri = f"{BACKEND_URL}/api/social/oauth/meta/callback"
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": ",".join(FACEBOOK_SCOPES),
            "response_type": "code",
            "state": state,
        }
        return {"auth_url": f"{META_AUTH_URL}?{urlencode(params)}"}


@router.get("/oauth/meta/callback")
async def meta_callback(code: str, state: str = "", db: AsyncSession = Depends(get_crm_db)):
    """Handle Meta OAuth callback. Respects requested platform from state."""
    if not state or not _nonce_validate(state):
        return _oauth_complete_page(False, "meta", "Invalid or expired OAuth state")

    client_id = await _get_setting(db, "meta_app_id")
    client_secret = await _get_setting(db, "meta_app_secret")

    if not client_id or not client_secret:
        raise HTTPException(400, "Meta credentials not configured")

    # Parse requested platform from state (format: "platform:nonce")
    requested_platform = "meta"  # default: save both FB + IG
    if ":" in state:
        requested_platform = state.split(":")[0]

    redirect_uri = f"{BACKEND_URL}/api/social/oauth/meta/callback"

    async with httpx.AsyncClient() as client:
        # Exchange code for short-lived token
        token_resp = await client.get(META_TOKEN_URL, params={
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "code": code,
        })

        if token_resp.status_code != 200:
            logger.error("Meta token exchange failed: %s", token_resp.text)
            return _oauth_complete_page(False, requested_platform, "Token exchange failed")

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
        else:
            access_token = short_token

        # Get user profile (needed for FB save and as fallback)
        me_resp = await client.get(f"{META_GRAPH_URL}/me", params={
            "fields": "id,name",
            "access_token": access_token,
        })
        me_data = me_resp.json()
        fb_name = me_data.get("name", "Unknown")
        fb_id = me_data.get("id")

        connected = []

        # Save Facebook if requested (facebook or meta)
        if requested_platform in ("facebook", "meta"):
            await _upsert_social_account(
                db, "facebook", fb_name, access_token,
                profile_url=f"https://facebook.com/{fb_id}",
            )
            connected.append("facebook")

        # Try Instagram if requested (instagram or meta)
        if requested_platform in ("instagram", "meta"):
            accounts_resp = await client.get(f"{META_GRAPH_URL}/me/accounts", params={
                "access_token": access_token,
            })
            pages_data = accounts_resp.json()
            pages = pages_data.get("data", [])
            logger.info("Pages API returned %d pages: %s", len(pages), [p.get('name') for p in pages])
            if not pages:
                logger.warning("No pages found. Full response: %s", pages_data)
            ig_found = False

            for page in pages:
                page_token = page.get("access_token", access_token)
                ig_resp = await client.get(
                    f"{META_GRAPH_URL}/{page['id']}",
                    params={
                        "fields": "instagram_business_account{id,username,followers_count,follows_count,media_count,profile_picture_url}",
                        "access_token": page_token,
                    }
                )
                ig_result = ig_resp.json()
                logger.info("Page '%s' IG lookup: %s", page.get('name'), ig_result)
                ig_data = ig_result.get("instagram_business_account")
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
                    connected.append("instagram")
                    ig_found = True

            if not ig_found and requested_platform == "instagram":
                logger.warning("Instagram requested but no Instagram Business account found on any Page")
                return _oauth_complete_page(False, "instagram", "No Instagram Business account found. Link your Instagram to a Facebook Page first.")

    platform_str = ",".join(connected) if connected else requested_platform
    return _oauth_complete_page(True, platform_str)


# ══════════════════════════════════════════════════════════════════════
# INSTAGRAM — Direct Instagram OAuth (instagram.com)
# No Facebook Page required. Works with Professional accounts.
# Docs: https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login
# ══════════════════════════════════════════════════════════════════════

@router.get("/oauth/instagram/callback")
async def instagram_callback(code: str, state: str = "", db: AsyncSession = Depends(get_crm_db)):
    """Handle Instagram OAuth callback (direct Instagram login, no Facebook Page needed)."""
    if not state or not _nonce_validate(state):
        return _oauth_complete_page(False, "instagram", "Invalid or expired OAuth state")

    client_id = await _get_setting(db, "instagram_app_id") or await _get_setting(db, "meta_app_id")
    client_secret = await _get_setting(db, "instagram_app_secret") or await _get_setting(db, "meta_app_secret")

    if not client_id or not client_secret:
        raise HTTPException(400, "Instagram App ID not configured. Go to Settings → API Keys.")

    redirect_uri = f"{BACKEND_URL}/api/social/oauth/instagram/callback"

    async with httpx.AsyncClient() as client:
        # Exchange code for short-lived token (Instagram uses POST with form data)
        token_resp = await client.post(INSTAGRAM_TOKEN_URL, data={
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
            "code": code,
        })

        if token_resp.status_code != 200:
            logger.error("Instagram token exchange failed: %s", token_resp.text)
            return _oauth_complete_page(False, "instagram", "Token exchange failed")

        token_data = token_resp.json()
        short_token = token_data["access_token"]
        ig_user_id = token_data.get("user_id")

        # Exchange for long-lived token (60 days)
        ll_resp = await client.get(f"{INSTAGRAM_GRAPH_URL}/access_token", params={
            "grant_type": "ig_exchange_token",
            "client_secret": client_secret,
            "access_token": short_token,
        })

        if ll_resp.status_code == 200:
            ll_data = ll_resp.json()
            access_token = ll_data["access_token"]
        else:
            logger.warning("Instagram long-lived token exchange failed: %s", ll_resp.text)
            access_token = short_token

        # Get user profile
        me_resp = await client.get(f"{INSTAGRAM_GRAPH_URL}/me", params={
            "fields": "id,username,account_type,media_count,followers_count,follows_count,profile_picture_url",
            "access_token": access_token,
        })

        if me_resp.status_code != 200:
            logger.error("Instagram profile fetch failed: %s", me_resp.text)
            return _oauth_complete_page(False, "instagram", "Failed to fetch profile")

        me_data = me_resp.json()
        logger.info("Instagram profile: %s", me_data)

        await _upsert_social_account(
            db, "instagram",
            me_data.get("username", ""),
            access_token,
            profile_url=f"https://instagram.com/{me_data.get('username', '')}",
            follower_count=me_data.get("followers_count", 0),
            following_count=me_data.get("follows_count", 0),
            post_count=me_data.get("media_count", 0),
        )

    return _oauth_complete_page(True, "instagram")


# ══════════════════════════════════════════════════════════════════════
# THREADS — Separate OAuth flow (threads.net)
# Same Meta App ID but different OAuth endpoint and API
# ══════════════════════════════════════════════════════════════════════

@router.get("/oauth/threads/callback")
async def threads_callback(code: str, state: str = "", db: AsyncSession = Depends(get_crm_db)):
    """Handle Threads OAuth callback (separate from Meta/Facebook)."""
    if not state or not _nonce_validate(state):
        return _oauth_complete_page(False, "threads", "Invalid or expired OAuth state")

    client_id = await _get_setting(db, "threads_client_id") or await _get_setting(db, "meta_app_id")
    client_secret = await _get_setting(db, "threads_client_secret") or await _get_setting(db, "meta_app_secret")

    if not client_id or not client_secret:
        raise HTTPException(400, "Threads Client ID not configured. Go to Settings → API Keys.")

    redirect_uri = f"{BACKEND_URL}/api/social/oauth/threads/callback"

    async with httpx.AsyncClient() as client:
        # Exchange code for short-lived token
        token_resp = await client.post(THREADS_TOKEN_URL, data={
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
            "code": code,
        })

        if token_resp.status_code != 200:
            logger.error("Threads token exchange failed: %s", token_resp.text)
            return _oauth_complete_page(False, "threads", "Threads token exchange failed")

        token_data = token_resp.json()
        short_token = token_data["access_token"]

        # Exchange for long-lived token (60 days)
        ll_resp = await client.get(f"{THREADS_GRAPH_URL}/access_token", params={
            "grant_type": "th_exchange_token",
            "client_secret": client_secret,
            "access_token": short_token,
        })

        if ll_resp.status_code == 200:
            ll_data = ll_resp.json()
            access_token = ll_data["access_token"]
        else:
            access_token = short_token

        # Get Threads user profile
        me_resp = await client.get(f"{THREADS_GRAPH_URL}/me", params={
            "fields": "id,username,threads_profile_picture_url",
            "access_token": access_token,
        })

        if me_resp.status_code == 200:
            me_data = me_resp.json()
            await _upsert_social_account(
                db, "threads",
                me_data.get("username", ""),
                access_token,
                profile_url=f"https://threads.net/@{me_data.get('username', '')}",
            )
        else:
            logger.error("Threads profile fetch failed: %s", me_resp.text)
            return _oauth_complete_page(False, "threads", "Failed to fetch Threads profile")

    return _oauth_complete_page(True, "threads")


# ══════════════════════════════════════════════════════════════════════
# X (Twitter) — OAuth 2.0 with PKCE
# ══════════════════════════════════════════════════════════════════════

X_AUTH_URL = "https://x.com/i/oauth2/authorize"
X_TOKEN_URL = "https://api.x.com/2/oauth2/token"
X_API_URL = "https://api.x.com/2"

X_SCOPES = ["tweet.read", "users.read", "offline.access"]

# Store PKCE verifiers and state nonces with TTL (in production, use Redis)
_pkce_store: dict[str, tuple[str, float]] = {}  # key -> (verifier, timestamp)
_state_nonces: dict[str, float] = {}  # nonce -> timestamp
_store_lock = threading.Lock()


def _store_put(key: str, value: str):
    """Store a PKCE verifier with timestamp."""
    with _store_lock:
        now = time.monotonic()
        # Cleanup expired entries
        expired = [k for k, (_, ts) in _pkce_store.items() if now - ts > _OAUTH_TTL_SECONDS]
        for k in expired:
            del _pkce_store[k]
        expired_nonces = [k for k, ts in _state_nonces.items() if now - ts > _OAUTH_TTL_SECONDS]
        for k in expired_nonces:
            del _state_nonces[k]
        _pkce_store[key] = (value, now)


def _store_pop(key: str) -> Optional[str]:
    """Pop a PKCE verifier, returning None if expired or missing."""
    with _store_lock:
        entry = _pkce_store.pop(key, None)
        if entry is None:
            return None
        value, ts = entry
        if time.monotonic() - ts > _OAUTH_TTL_SECONDS:
            return None
        return value


def _nonce_store(nonce: str):
    """Store a state nonce with timestamp."""
    with _store_lock:
        _state_nonces[nonce] = time.monotonic()


def _nonce_validate(nonce: str) -> bool:
    """Validate and consume a state nonce. Returns False if expired/missing."""
    with _store_lock:
        ts = _state_nonces.pop(nonce, None)
        if ts is None:
            return False
        if time.monotonic() - ts > _OAUTH_TTL_SECONDS:
            return False
        return True


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
    _store_put(state, code_verifier)
    _nonce_store(state)

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
    return {"auth_url": f"{X_AUTH_URL}?{urlencode(params, quote_via=quote)}"}


@router.get("/oauth/x/callback")
async def x_callback(code: str = "", state: str = "", error: str = "", error_description: str = "", db: AsyncSession = Depends(get_crm_db)):
    if error:
        logger.error("X OAuth error: %s — %s", error, error_description)
        return _oauth_complete_page(False, "x", f"{error}: {error_description}")
    """Handle X OAuth callback."""
    if not _nonce_validate(state):
        return _oauth_complete_page(False, "x", "Invalid or expired OAuth state")

    client_id = await _get_setting(db, "x_client_id")
    client_secret = await _get_setting(db, "x_client_secret")
    code_verifier = _store_pop(state)

    if not client_id or not client_secret:
        raise HTTPException(400, "X credentials not configured")
    if not code_verifier:
        return _oauth_complete_page(False, "x", "Invalid or expired OAuth state")

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
            logger.error("X token exchange failed: %s", token_resp.text)
            return _oauth_complete_page(False, "x", f"Token exchange failed: {token_resp.text[:200]}")

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

    return _oauth_complete_page(True, "x")


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

    _store_put(f"tiktok_{state}", code_verifier)
    _nonce_store(f"tiktok_{state}")

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
    if not _nonce_validate(f"tiktok_{state}"):
        return _oauth_complete_page(False, "tiktok", "Invalid or expired OAuth state")

    client_key = await _get_setting(db, "tiktok_client_key")
    client_secret = await _get_setting(db, "tiktok_client_secret")
    code_verifier = _store_pop(f"tiktok_{state}")

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
            logger.error("TikTok token exchange failed: %s", token_resp.text)
            return _oauth_complete_page(False, requested_platform, "Token exchange failed")

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

    return _oauth_complete_page(True, "tiktok")


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
    _nonce_store(state)
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
    if not state or not _nonce_validate(state):
        return _oauth_complete_page(False, "youtube", "Invalid or expired OAuth state")

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
            logger.error("Google token exchange failed: %s", token_resp.text)
            return _oauth_complete_page(False, "youtube", "Token exchange failed")

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

    return _oauth_complete_page(True, "youtube")


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
