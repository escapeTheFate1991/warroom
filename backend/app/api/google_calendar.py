"""Google Calendar OAuth 2.0 integration for War Room personal calendar."""
import asyncio
import json
import logging
import os
from datetime import datetime, timedelta

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse

logger = logging.getLogger(__name__)
router = APIRouter()

from app.services.token_store import load_tokens, save_tokens, delete_tokens

TOKEN_SERVICE = "google_calendar"

SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/userinfo.email",
]


async def _get_setting_value(key: str) -> str | None:
    """Read a setting from the DB (same store as Settings → API Keys)."""
    from app.api.settings import Setting
    from app.db.leadgen_db import leadgen_session
    from sqlalchemy import select

    async with leadgen_session() as db:
        result = await db.execute(select(Setting).where(Setting.key == key))
        setting = result.scalar_one_or_none()
        return setting.value if setting and setting.value else None


async def _get_client_config() -> dict:
    """Return Google OAuth client config from the settings DB (same creds as YouTube)."""
    client_id = await _get_setting_value("google_oauth_client_id")
    client_secret = await _get_setting_value("google_oauth_client_secret")
    redirect_uri = os.environ.get(
        "GOOGLE_REDIRECT_URI",
        "https://warroom.stuffnthings.io/api/calendar/google/callback",
    )

    if not client_id or not client_secret:
        raise HTTPException(
            status_code=503,
            detail="Google Calendar not configured. Add your Google OAuth Client ID & Secret in Settings → API Keys.",
        )

    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
    }


async def _load_tokens() -> Optional[dict]:
    """Load stored tokens from DB via centralized token store."""
    return await load_tokens(TOKEN_SERVICE)


async def _save_tokens(tokens: dict) -> None:
    """Persist tokens to DB via centralized token store."""
    await save_tokens(TOKEN_SERVICE, tokens)


async def _get_credentials():
    """Build google.oauth2.credentials.Credentials from stored tokens."""
    from google.oauth2.credentials import Credentials

    tokens = await _load_tokens()
    if not tokens:
        return None

    cfg = await _get_client_config()
    creds = Credentials(
        token=tokens.get("access_token"),
        refresh_token=tokens.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=cfg["client_id"],
        client_secret=cfg["client_secret"],
        scopes=SCOPES,
    )

    # Auto-refresh if expired
    if creds.expired and creds.refresh_token:
        from google.auth.transport.requests import Request as GoogleAuthRequest

        try:
            # creds.refresh uses requests (sync/blocking) — run in thread
            await asyncio.to_thread(creds.refresh, GoogleAuthRequest())
            await _save_tokens(
                {
                    **tokens,
                    "access_token": creds.token,
                    "expiry": creds.expiry.isoformat() if creds.expiry else None,
                }
            )
        except Exception as exc:
            logger.error("Token refresh failed: %s", exc)
            return None

    return creds


# ── Endpoints ───────────────────────────────────────────────


@router.get("/calendar/google/auth-url")
async def get_auth_url():
    """Return the Google OAuth authorization URL."""
    from google_auth_oauthlib.flow import Flow

    cfg = await _get_client_config()

    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": cfg["client_id"],
                "client_secret": cfg["client_secret"],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [cfg["redirect_uri"]],
            }
        },
        scopes=SCOPES,
        redirect_uri=cfg["redirect_uri"],
    )

    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )

    return {"auth_url": auth_url}


@router.get("/calendar/google/callback", response_class=HTMLResponse)
async def oauth_callback(code: str = Query(...), error: Optional[str] = Query(None)):
    """Handle the OAuth callback from Google."""
    if error:
        return HTMLResponse(
            f"<html><body><script>window.opener?.postMessage({{type:'google-calendar-error',error:'{error}'}},'*');window.close();</script><p>Error: {error}. You can close this window.</p></body></html>"
        )

    import httpx

    cfg = await _get_client_config()

    # Exchange auth code for tokens directly via HTTP — avoids
    # google-auth-oauthlib's strict scope validation which rejects
    # expanded scopes from include_granted_scopes=true.
    try:
        async with httpx.AsyncClient() as client:
            token_resp = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": cfg["client_id"],
                    "client_secret": cfg["client_secret"],
                    "redirect_uri": cfg["redirect_uri"],
                    "grant_type": "authorization_code",
                },
            )
            if token_resp.status_code != 200:
                logger.error("Token exchange failed: %s", token_resp.text)
                raise Exception(f"HTTP {token_resp.status_code}: {token_resp.text[:200]}")

            token_data = token_resp.json()
    except Exception as exc:
        logger.error("Token exchange failed: %s", exc)
        return HTMLResponse(
            f"<html><body><script>window.opener?.postMessage({{type:'google-calendar-error',error:'token_exchange_failed'}},'*');window.close();</script><p>Token exchange failed. You can close this window.</p></body></html>"
        )

    access_token = token_data["access_token"]
    refresh_token = token_data.get("refresh_token")

    # Fetch user email
    email = None
    try:
        async with httpx.AsyncClient() as client:
            me_resp = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if me_resp.status_code == 200:
                email = me_resp.json().get("email")
    except Exception as exc:
        logger.warning("Could not fetch user email: %s", exc)

    await _save_tokens(
        {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expiry": token_data.get("expires_in"),
            "email": email,
            "connected_at": datetime.now().isoformat(),
        }
    )

    return HTMLResponse(
        "<html><body><script>"
        "window.opener?.postMessage({type:'google-calendar-connected'},'*');"
        "window.close();"
        "</script>"
        "<p>✅ Google Calendar connected! You can close this window.</p>"
        "</body></html>"
    )


@router.get("/calendar/google/status")
async def google_status():
    """Return Google Calendar connection status."""
    tokens = await _load_tokens()
    if not tokens:
        return {"connected": False, "email": None}

    return {
        "connected": True,
        "email": tokens.get("email"),
        "connected_at": tokens.get("connected_at"),
    }


@router.get("/calendar/google/events")
async def get_google_events(month: str = Query(..., description="YYYY-MM")):
    """Fetch events from Google Calendar for a given month."""
    creds = await _get_credentials()
    if not creds:
        raise HTTPException(status_code=401, detail="Google Calendar not connected")

    try:
        year, mon = int(month.split("-")[0]), int(month.split("-")[1])
    except Exception:
        raise HTTPException(status_code=400, detail="month format: YYYY-MM")

    from googleapiclient.discovery import build

    try:
        # build() and execute() use httplib2 (sync/blocking) — run in thread
        def _fetch_events():
            service = build("calendar", "v3", credentials=creds)
            return (
                service.events()
                .list(
                    calendarId="primary",
                    timeMin=time_min,
                    timeMax=time_max,
                    maxResults=250,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )

        time_min = datetime(year, mon, 1).isoformat() + "Z"
        if mon == 12:
            time_max = datetime(year + 1, 1, 1).isoformat() + "Z"
        else:
            time_max = datetime(year, mon + 1, 1).isoformat() + "Z"

        results = await asyncio.to_thread(_fetch_events)

        events = []
        for item in results.get("items", []):
            start = item.get("start", {})
            end = item.get("end", {})

            # All-day events use "date", timed events use "dateTime"
            is_all_day = "date" in start and "dateTime" not in start
            if is_all_day:
                event_date = start["date"]
                event_time = None
                event_end_time = None
            else:
                dt_str = start.get("dateTime", "")
                event_date = dt_str[:10] if dt_str else ""
                event_time = dt_str[11:16] if len(dt_str) > 16 else None
                end_str = end.get("dateTime", "")
                event_end_time = end_str[11:16] if len(end_str) > 16 else None

            events.append(
                {
                    "id": f"gcal-{item['id']}",
                    "title": item.get("summary", "(No title)"),
                    "date": event_date,
                    "time": event_time,
                    "end_time": event_end_time,
                    "description": item.get("description", ""),
                    "location": item.get("location", ""),
                    "type": "event",
                    "source": "google",
                    "all_day": is_all_day,
                    "status": item.get("status", "confirmed"),
                    "html_link": item.get("htmlLink", ""),
                    "created_at": item.get("created", ""),
                }
            )

        return {"events": events, "count": len(events)}

    except Exception as exc:
        logger.error("Failed to fetch Google Calendar events: %s", exc)
        raise HTTPException(status_code=502, detail=f"Failed to fetch events: {exc}")


@router.post("/calendar/google/disconnect")
async def disconnect_google():
    """Revoke token and clear stored credentials."""
    creds = await _get_credentials()

    # Try to revoke the token
    if creds and creds.token:
        try:
            import httpx

            async with httpx.AsyncClient() as client:
                await client.post(
                    "https://oauth2.googleapis.com/revoke",
                    params={"token": creds.token},
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
        except Exception as exc:
            logger.warning("Token revocation failed (continuing anyway): %s", exc)

    # Remove stored tokens
    await delete_tokens(TOKEN_SERVICE)
    logger.info("Google Calendar tokens removed")

    return {"ok": True, "message": "Google Calendar disconnected"}
