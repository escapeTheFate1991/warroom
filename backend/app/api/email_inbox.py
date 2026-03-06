"""Email Inbox — Gmail API + IMAP integration for War Room.

Tables: public.email_accounts, public.email_messages (auto-created on startup).
Gmail uses same Google OAuth client as Calendar/YouTube (different scopes, separate tokens).
IMAP uses imaplib wrapped in asyncio.to_thread().
"""
import asyncio
import base64
import email as email_lib
import email.header
import email.utils
import imaplib
import json
import logging
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

logger = logging.getLogger(__name__)

# ── DB Setup (public schema, knowledge DB) ───────────────────────────
DB_URL = "postgresql+asyncpg://friday:friday-brain2-2026@10.0.0.11:5433/knowledge"
_engine = create_async_engine(DB_URL, echo=False, pool_size=5, max_overflow=10)
_session = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)

router = APIRouter()

# ── Gmail OAuth Config ───────────────────────────────────────────────
GMAIL_TOKEN_FILE = Path("/tmp/warroom_gmail_tokens.json")

GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.labels",
    "https://www.googleapis.com/auth/userinfo.email",
]

GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"


# ── Table DDL ────────────────────────────────────────────────────────
ACCOUNTS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS public.email_accounts (
    id           SERIAL PRIMARY KEY,
    user_id      INTEGER,
    provider     VARCHAR(20) NOT NULL,
    email        TEXT,
    display_name TEXT,
    is_active    BOOLEAN DEFAULT TRUE,
    config       JSONB DEFAULT '{}'::jsonb,
    tokens       JSONB DEFAULT '{}'::jsonb,
    last_sync_at TIMESTAMP WITH TIME ZONE,
    created_at   TIMESTAMP WITH TIME ZONE DEFAULT now()
);
"""

MESSAGES_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS public.email_messages (
    id              SERIAL PRIMARY KEY,
    account_id      INTEGER REFERENCES public.email_accounts(id) ON DELETE CASCADE,
    message_id      TEXT UNIQUE,
    thread_id       TEXT,
    subject         TEXT,
    from_address    TEXT,
    from_name       TEXT,
    to_addresses    JSONB,
    cc_addresses    JSONB,
    date            TIMESTAMP WITH TIME ZONE,
    snippet         TEXT,
    body_text       TEXT,
    body_html       TEXT,
    labels          JSONB DEFAULT '[]'::jsonb,
    is_read         BOOLEAN DEFAULT FALSE,
    has_attachments BOOLEAN DEFAULT FALSE,
    raw_headers     JSONB DEFAULT '{}'::jsonb,
    synced_at       TIMESTAMP WITH TIME ZONE DEFAULT now()
);
"""

INDEX_SQLS = [
    "CREATE INDEX IF NOT EXISTS idx_email_messages_account ON public.email_messages (account_id)",
    "CREATE INDEX IF NOT EXISTS idx_email_messages_date ON public.email_messages (date DESC)",
    "CREATE INDEX IF NOT EXISTS idx_email_messages_thread ON public.email_messages (thread_id)",
    "CREATE INDEX IF NOT EXISTS idx_email_messages_read ON public.email_messages (is_read)",
    "CREATE INDEX IF NOT EXISTS idx_email_accounts_user ON public.email_accounts (user_id)",
]


async def init_email_tables():
    """Create email tables + indexes on startup."""
    async with _engine.begin() as conn:
        await conn.execute(text(ACCOUNTS_TABLE_SQL))
        await conn.execute(text(MESSAGES_TABLE_SQL))
        for idx_sql in INDEX_SQLS:
            await conn.execute(text(idx_sql))
    logger.info("Email inbox tables initialized")


# ── Helpers ──────────────────────────────────────────────────────────

async def _get_setting_value(key: str) -> str | None:
    """Read a setting from the DB (same store as Settings → API Keys)."""
    from app.api.settings import Setting
    from app.db.leadgen_db import leadgen_session
    from sqlalchemy import select

    async with leadgen_session() as db:
        result = await db.execute(select(Setting).where(Setting.key == key))
        setting = result.scalar_one_or_none()
        return setting.value if setting and setting.value else None


async def _get_google_client_config() -> dict:
    """Return Google OAuth client config from the settings DB."""
    client_id = await _get_setting_value("google_oauth_client_id")
    client_secret = await _get_setting_value("google_oauth_client_secret")
    redirect_uri = os.environ.get(
        "GMAIL_REDIRECT_URI",
        "https://warroom.stuffnthings.io/api/email/accounts/gmail/callback",
    )
    if not client_id or not client_secret:
        raise HTTPException(
            status_code=503,
            detail="Google OAuth not configured. Add Client ID & Secret in Settings → API Keys.",
        )
    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
    }


def _load_gmail_tokens() -> Optional[dict]:
    """Load stored Gmail tokens from disk."""
    if not GMAIL_TOKEN_FILE.exists():
        return None
    try:
        data = json.loads(GMAIL_TOKEN_FILE.read_text())
        if data.get("refresh_token"):
            return data
    except Exception as exc:
        logger.warning("Failed to read Gmail token file: %s", exc)
    return None


def _save_gmail_tokens(tokens: dict) -> None:
    """Persist Gmail tokens to disk."""
    GMAIL_TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    GMAIL_TOKEN_FILE.write_text(json.dumps(tokens, indent=2))
    logger.info("Gmail tokens saved")


async def _get_gmail_access_token() -> str:
    """Get a valid Gmail access token, refreshing if needed."""
    tokens = _load_gmail_tokens()
    if not tokens:
        raise HTTPException(status_code=401, detail="Gmail not connected")

    # Check if token needs refresh (rough check via stored expiry)
    expiry_str = tokens.get("expiry")
    needs_refresh = True
    if expiry_str:
        try:
            expiry = datetime.fromisoformat(expiry_str)
            needs_refresh = datetime.now(timezone.utc) >= expiry - timedelta(minutes=5)
        except (ValueError, TypeError):
            needs_refresh = True

    if needs_refresh and tokens.get("refresh_token"):
        cfg = await _get_google_client_config()
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": cfg["client_id"],
                    "client_secret": cfg["client_secret"],
                    "refresh_token": tokens["refresh_token"],
                    "grant_type": "refresh_token",
                },
            )
            if resp.status_code == 200:
                new_data = resp.json()
                expires_in = new_data.get("expires_in", 3600)
                expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
                tokens["access_token"] = new_data["access_token"]
                tokens["expiry"] = expiry.isoformat()
                _save_gmail_tokens(tokens)
            else:
                logger.error("Gmail token refresh failed: %s", resp.text)
                raise HTTPException(status_code=401, detail="Gmail token refresh failed — reconnect your account.")

    return tokens["access_token"]


def _decode_base64url(data: str) -> str:
    """Decode base64url-encoded string (Gmail body encoding)."""
    padded = data + "=" * (4 - len(data) % 4)
    try:
        return base64.urlsafe_b64decode(padded).decode("utf-8", errors="replace")
    except Exception:
        return ""


def _parse_email_address(raw: str) -> tuple[str, str]:
    """Parse 'Name <email@example.com>' into (name, email)."""
    if not raw:
        return ("", "")
    name, addr = email_lib.utils.parseaddr(raw)
    return (name or "", addr or raw)


def _extract_gmail_body(payload: dict) -> tuple[str, str]:
    """Extract text and HTML body from Gmail message payload."""
    body_text = ""
    body_html = ""

    def _walk_parts(part: dict):
        nonlocal body_text, body_html
        mime = part.get("mimeType", "")
        body_data = part.get("body", {}).get("data", "")

        if mime == "text/plain" and body_data and not body_text:
            body_text = _decode_base64url(body_data)
        elif mime == "text/html" and body_data and not body_html:
            body_html = _decode_base64url(body_data)

        for sub in part.get("parts", []):
            _walk_parts(sub)

    _walk_parts(payload)
    return body_text, body_html


def _get_header(headers: list[dict], name: str) -> str:
    """Get a header value from Gmail message headers list."""
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


def _parse_address_list(raw: str) -> list[dict]:
    """Parse comma-separated email addresses into list of {name, email}."""
    if not raw:
        return []
    addresses = []
    for addr_str in raw.split(","):
        addr_str = addr_str.strip()
        if addr_str:
            name, addr = _parse_email_address(addr_str)
            addresses.append({"name": name, "email": addr})
    return addresses


# ── Pydantic Models ──────────────────────────────────────────────────

class ImapConnectRequest(BaseModel):
    host: str
    port: int = 993
    username: str
    password: str
    use_ssl: bool = True
    display_name: Optional[str] = None


# ── Gmail OAuth Endpoints ────────────────────────────────────────────

@router.post("/email/accounts/gmail/connect")
async def gmail_connect(request: Request):
    """Return the Gmail OAuth authorization URL."""
    cfg = await _get_google_client_config()
    scope_str = " ".join(GMAIL_SCOPES)
    params = {
        "client_id": cfg["client_id"],
        "redirect_uri": cfg["redirect_uri"],
        "response_type": "code",
        "scope": scope_str,
        "access_type": "offline",
        "prompt": "consent",
    }
    auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + "&".join(
        f"{k}={httpx.URL('', params={k: v}).params[k]}" for k, v in params.items()
    )
    # Simpler: just use httpx to build the URL
    base = "https://accounts.google.com/o/oauth2/v2/auth"
    async with httpx.AsyncClient() as client:
        req = client.build_request("GET", base, params=params)
        auth_url = str(req.url)

    return {"auth_url": auth_url}


@router.get("/email/accounts/gmail/callback", response_class=HTMLResponse)
async def gmail_callback(
    code: str = Query(...),
    error: Optional[str] = Query(None),
):
    """Handle Gmail OAuth callback — exchange code for tokens."""
    if error:
        return HTMLResponse(
            f"<html><body><script>"
            f"if(window.opener){{window.opener.postMessage({{type:'gmail-error',error:'{error}'}},'*');window.close();}}"
            f"else{{window.location.href='/?error=gmail_' + encodeURIComponent('{error}');}}"
            f"</script>"
            f"<p>Error: {error}. Redirecting...</p></body></html>"
        )

    cfg = await _get_google_client_config()

    # Exchange code for tokens via direct HTTP
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
            logger.error("Gmail token exchange failed: %s", token_resp.text)
            return HTMLResponse(
                "<html><body><script>"
                "if(window.opener){window.opener.postMessage({type:'gmail-error',error:'token_exchange_failed'},'*');window.close();}"
                "else{window.location.href='/?error=gmail_token_exchange_failed';}"
                "</script>"
                "<p>Token exchange failed. You can close this window.</p></body></html>"
            )
        token_data = token_resp.json()

    access_token = token_data["access_token"]
    refresh_token = token_data.get("refresh_token")
    expires_in = token_data.get("expires_in", 3600)
    expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

    # Fetch user email
    email_addr = None
    try:
        async with httpx.AsyncClient() as client:
            me_resp = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if me_resp.status_code == 200:
                email_addr = me_resp.json().get("email")
    except Exception as exc:
        logger.warning("Could not fetch user email: %s", exc)

    # Save tokens to file
    _save_gmail_tokens({
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expiry": expiry.isoformat(),
        "email": email_addr,
        "connected_at": datetime.now(timezone.utc).isoformat(),
    })

    # Upsert email_account in DB
    async with _session() as db:
        # Check if account exists for this email
        existing = await db.execute(
            text("SELECT id FROM public.email_accounts WHERE provider = 'gmail' AND email = :email"),
            {"email": email_addr},
        )
        row = existing.fetchone()
        if row:
            await db.execute(
                text("""
                    UPDATE public.email_accounts
                    SET is_active = TRUE,
                        tokens = :tokens,
                        created_at = now()
                    WHERE id = :id
                """),
                {"id": row[0], "tokens": json.dumps({"token_file": str(GMAIL_TOKEN_FILE)})},
            )
        else:
            await db.execute(
                text("""
                    INSERT INTO public.email_accounts (user_id, provider, email, display_name, tokens)
                    VALUES (1, 'gmail', :email, :display_name, :tokens)
                """),
                {
                    "email": email_addr,
                    "display_name": email_addr,
                    "tokens": json.dumps({"token_file": str(GMAIL_TOKEN_FILE)}),
                },
            )
        await db.commit()

    return HTMLResponse(
        "<html><body><script>"
        "if(window.opener){"
        "  window.opener.postMessage({type:'gmail-connected'},'*');"
        "  window.close();"
        "}else{"
        "  window.location.href='/';"
        "}"
        "</script>"
        "<p>✅ Gmail connected! Redirecting...</p>"
        "</body></html>"
    )


# ── IMAP Connect Endpoint ───────────────────────────────────────────

@router.post("/email/accounts/imap/connect")
async def imap_connect(req: ImapConnectRequest, request: Request):
    """Test IMAP connection and store account if successful."""
    user_id = getattr(request.state, "user_id", 1)

    def _test_imap():
        if req.use_ssl:
            conn = imaplib.IMAP4_SSL(req.host, req.port)
        else:
            conn = imaplib.IMAP4(req.host, req.port)
            conn.starttls()
        conn.login(req.username, req.password)
        status, _ = conn.select("INBOX", readonly=True)
        conn.logout()
        return status == "OK"

    try:
        ok = await asyncio.to_thread(_test_imap)
        if not ok:
            raise HTTPException(status_code=400, detail="IMAP connection succeeded but INBOX select failed")
    except imaplib.IMAP4.error as exc:
        raise HTTPException(status_code=400, detail=f"IMAP connection failed: {exc}")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"IMAP connection failed: {exc}")

    # Store account
    async with _session() as db:
        result = await db.execute(
            text("""
                INSERT INTO public.email_accounts (user_id, provider, email, display_name, config)
                VALUES (:user_id, 'imap', :email, :display_name, :config)
                RETURNING id
            """),
            {
                "user_id": user_id,
                "email": req.username,
                "display_name": req.display_name or req.username,
                "config": json.dumps({
                    "host": req.host,
                    "port": req.port,
                    "username": req.username,
                    "password": req.password,
                    "use_ssl": req.use_ssl,
                }),
            },
        )
        account_id = result.fetchone()[0]
        await db.commit()

    return {"ok": True, "account_id": account_id, "email": req.username}


# ── Account Management ──────────────────────────────────────────────

@router.get("/email/accounts")
async def list_accounts(request: Request):
    """List connected email accounts."""
    async with _session() as db:
        result = await db.execute(
            text("""
                SELECT id, provider, email, display_name, is_active, last_sync_at, created_at
                FROM public.email_accounts
                WHERE is_active = TRUE
                ORDER BY created_at DESC
            """)
        )
        rows = result.fetchall()

    return {
        "accounts": [
            {
                "id": r[0],
                "provider": r[1],
                "email": r[2],
                "display_name": r[3],
                "is_active": r[4],
                "last_sync_at": r[5].isoformat() if r[5] else None,
                "created_at": r[6].isoformat() if r[6] else None,
            }
            for r in rows
        ]
    }


@router.delete("/email/accounts/{account_id}")
async def disconnect_account(account_id: int):
    """Disconnect (soft-delete) an email account."""
    async with _session() as db:
        result = await db.execute(
            text("UPDATE public.email_accounts SET is_active = FALSE WHERE id = :id RETURNING id"),
            {"id": account_id},
        )
        if not result.fetchone():
            raise HTTPException(status_code=404, detail="Account not found")
        await db.commit()

    return {"ok": True, "message": f"Account {account_id} disconnected"}


# ── Sync Endpoints ───────────────────────────────────────────────────

@router.post("/email/accounts/{account_id}/sync")
async def sync_account(account_id: int):
    """Trigger email sync for a specific account."""
    async with _session() as db:
        result = await db.execute(
            text("SELECT id, provider, config, last_sync_at FROM public.email_accounts WHERE id = :id AND is_active = TRUE"),
            {"id": account_id},
        )
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Account not found")

    provider = row[1]
    config = row[2] if isinstance(row[2], dict) else json.loads(row[2] or "{}")
    last_sync = row[3]

    if provider == "gmail":
        count = await _sync_gmail(account_id, last_sync)
    elif provider == "imap":
        count = await _sync_imap(account_id, config, last_sync)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")

    # Update last_sync_at
    async with _session() as db:
        await db.execute(
            text("UPDATE public.email_accounts SET last_sync_at = now() WHERE id = :id"),
            {"id": account_id},
        )
        await db.commit()

    return {"ok": True, "synced": count, "account_id": account_id}


async def _sync_gmail(account_id: int, last_sync: Optional[datetime]) -> int:
    """Sync messages from Gmail API."""
    access_token = await _get_gmail_access_token()
    headers = {"Authorization": f"Bearer {access_token}"}

    # Build query — first sync gets last 50, incremental gets newer
    params: dict = {"maxResults": 50}
    if last_sync:
        # Gmail query: after:YYYY/MM/DD
        after_date = last_sync.strftime("%Y/%m/%d")
        params["q"] = f"after:{after_date}"

    synced = 0
    async with httpx.AsyncClient(timeout=30) as client:
        # Fetch message IDs
        list_resp = await client.get(
            f"{GMAIL_API_BASE}/messages",
            headers=headers,
            params=params,
        )
        if list_resp.status_code != 200:
            logger.error("Gmail list failed: %s", list_resp.text)
            raise HTTPException(status_code=502, detail="Failed to fetch Gmail messages")

        messages = list_resp.json().get("messages", [])
        if not messages:
            return 0

        # Fetch each message detail
        for msg_stub in messages:
            msg_id = msg_stub["id"]

            # Skip if already synced
            async with _session() as db:
                existing = await db.execute(
                    text("SELECT 1 FROM public.email_messages WHERE message_id = :mid"),
                    {"mid": msg_id},
                )
                if existing.fetchone():
                    continue

            # Fetch full message
            detail_resp = await client.get(
                f"{GMAIL_API_BASE}/messages/{msg_id}",
                headers=headers,
                params={"format": "full"},
            )
            if detail_resp.status_code != 200:
                logger.warning("Failed to fetch message %s: %s", msg_id, detail_resp.status_code)
                continue

            msg_data = detail_resp.json()
            payload = msg_data.get("payload", {})
            msg_headers = payload.get("headers", [])

            subject = _get_header(msg_headers, "Subject")
            from_raw = _get_header(msg_headers, "From")
            to_raw = _get_header(msg_headers, "To")
            cc_raw = _get_header(msg_headers, "Cc")
            date_raw = _get_header(msg_headers, "Date")

            from_name, from_address = _parse_email_address(from_raw)
            to_addresses = _parse_address_list(to_raw)
            cc_addresses = _parse_address_list(cc_raw)

            # Parse date
            msg_date = None
            if date_raw:
                try:
                    parsed = email_lib.utils.parsedate_to_datetime(date_raw)
                    msg_date = parsed.astimezone(timezone.utc)
                except Exception:
                    pass

            snippet = msg_data.get("snippet", "")
            labels = msg_data.get("labelIds", [])
            is_read = "UNREAD" not in labels
            body_text, body_html = _extract_gmail_body(payload)

            # Check for attachments
            has_attachments = False
            def _check_attachments(part):
                nonlocal has_attachments
                if part.get("filename"):
                    has_attachments = True
                for sub in part.get("parts", []):
                    _check_attachments(sub)
            _check_attachments(payload)

            # Insert message
            async with _session() as db:
                try:
                    await db.execute(
                        text("""
                            INSERT INTO public.email_messages
                                (account_id, message_id, thread_id, subject, from_address, from_name,
                                 to_addresses, cc_addresses, date, snippet, body_text, body_html,
                                 labels, is_read, has_attachments, raw_headers)
                            VALUES
                                (:account_id, :message_id, :thread_id, :subject, :from_address, :from_name,
                                 :to_addresses, :cc_addresses, :date, :snippet, :body_text, :body_html,
                                 :labels, :is_read, :has_attachments, :raw_headers)
                            ON CONFLICT (message_id) DO NOTHING
                        """),
                        {
                            "account_id": account_id,
                            "message_id": msg_id,
                            "thread_id": msg_data.get("threadId"),
                            "subject": subject,
                            "from_address": from_address,
                            "from_name": from_name,
                            "to_addresses": json.dumps(to_addresses),
                            "cc_addresses": json.dumps(cc_addresses),
                            "date": msg_date,
                            "snippet": snippet,
                            "body_text": body_text[:50000] if body_text else None,
                            "body_html": body_html[:100000] if body_html else None,
                            "labels": json.dumps(labels),
                            "is_read": is_read,
                            "has_attachments": has_attachments,
                            "raw_headers": json.dumps({h["name"]: h["value"] for h in msg_headers[:20]}),
                        },
                    )
                    await db.commit()
                    synced += 1
                except Exception as exc:
                    logger.warning("Failed to insert message %s: %s", msg_id, exc)
                    await db.rollback()

    return synced


async def _sync_imap(account_id: int, config: dict, last_sync: Optional[datetime]) -> int:
    """Sync messages from IMAP server."""
    host = config["host"]
    port = config.get("port", 993)
    username = config["username"]
    password = config["password"]
    use_ssl = config.get("use_ssl", True)

    def _fetch_imap_messages():
        """Blocking IMAP fetch — runs in thread."""
        if use_ssl:
            conn = imaplib.IMAP4_SSL(host, port)
        else:
            conn = imaplib.IMAP4(host, port)
            conn.starttls()

        conn.login(username, password)
        conn.select("INBOX", readonly=True)

        # Search criteria: last 7 days on first sync, since last_sync otherwise
        if last_sync:
            since_date = last_sync.strftime("%d-%b-%Y")
        else:
            since_date = (datetime.now() - timedelta(days=7)).strftime("%d-%b-%Y")

        _status, msg_nums = conn.search(None, f'(SINCE "{since_date}")')
        if not msg_nums or not msg_nums[0]:
            conn.logout()
            return []

        num_list = msg_nums[0].split()
        # Limit to last 50 on first sync
        if not last_sync and len(num_list) > 50:
            num_list = num_list[-50:]

        messages = []
        for num in num_list:
            try:
                _status, data = conn.fetch(num, "(RFC822 FLAGS)")
                if not data or not data[0] or not isinstance(data[0], tuple):
                    continue

                raw_email = data[0][1]
                msg = email_lib.message_from_bytes(raw_email)

                # Parse flags for read status
                flag_data = data[0][0].decode("utf-8", errors="replace") if isinstance(data[0][0], bytes) else str(data[0][0])
                is_read = "\\Seen" in flag_data

                # Extract body
                body_text = ""
                body_html = ""
                has_attachments = False

                if msg.is_multipart():
                    for part in msg.walk():
                        content_type = part.get_content_type()
                        disposition = str(part.get("Content-Disposition", ""))
                        if "attachment" in disposition:
                            has_attachments = True
                            continue
                        if content_type == "text/plain" and not body_text:
                            payload_bytes = part.get_payload(decode=True)
                            if payload_bytes:
                                charset = part.get_content_charset() or "utf-8"
                                body_text = payload_bytes.decode(charset, errors="replace")
                        elif content_type == "text/html" and not body_html:
                            payload_bytes = part.get_payload(decode=True)
                            if payload_bytes:
                                charset = part.get_content_charset() or "utf-8"
                                body_html = payload_bytes.decode(charset, errors="replace")
                else:
                    payload_bytes = msg.get_payload(decode=True)
                    if payload_bytes:
                        charset = msg.get_content_charset() or "utf-8"
                        if msg.get_content_type() == "text/html":
                            body_html = payload_bytes.decode(charset, errors="replace")
                        else:
                            body_text = payload_bytes.decode(charset, errors="replace")

                # Decode subject
                subject_raw = msg.get("Subject", "")
                subject_parts = email_lib.header.decode_header(subject_raw)
                subject = ""
                for part_bytes, charset in subject_parts:
                    if isinstance(part_bytes, bytes):
                        subject += part_bytes.decode(charset or "utf-8", errors="replace")
                    else:
                        subject += part_bytes

                from_raw = msg.get("From", "")
                from_name, from_address = _parse_email_address(from_raw)
                to_addresses = _parse_address_list(msg.get("To", ""))
                cc_addresses = _parse_address_list(msg.get("Cc", ""))

                msg_date = None
                date_raw = msg.get("Date", "")
                if date_raw:
                    try:
                        msg_date = email_lib.utils.parsedate_to_datetime(date_raw)
                    except Exception:
                        pass

                message_id = msg.get("Message-ID", f"imap-{num.decode()}")

                messages.append({
                    "message_id": message_id,
                    "thread_id": msg.get("In-Reply-To", message_id),
                    "subject": subject,
                    "from_address": from_address,
                    "from_name": from_name,
                    "to_addresses": to_addresses,
                    "cc_addresses": cc_addresses,
                    "date": msg_date,
                    "snippet": (body_text or "")[:200],
                    "body_text": body_text,
                    "body_html": body_html,
                    "is_read": is_read,
                    "has_attachments": has_attachments,
                })
            except Exception as exc:
                logger.warning("Failed to parse IMAP message %s: %s", num, exc)
                continue

        conn.logout()
        return messages

    # Run blocking IMAP in thread
    imap_messages = await asyncio.to_thread(_fetch_imap_messages)

    synced = 0
    for msg in imap_messages:
        async with _session() as db:
            try:
                await db.execute(
                    text("""
                        INSERT INTO public.email_messages
                            (account_id, message_id, thread_id, subject, from_address, from_name,
                             to_addresses, cc_addresses, date, snippet, body_text, body_html,
                             labels, is_read, has_attachments)
                        VALUES
                            (:account_id, :message_id, :thread_id, :subject, :from_address, :from_name,
                             :to_addresses, :cc_addresses, :date, :snippet, :body_text, :body_html,
                             '[]'::jsonb, :is_read, :has_attachments)
                        ON CONFLICT (message_id) DO NOTHING
                    """),
                    {
                        "account_id": account_id,
                        "message_id": msg["message_id"],
                        "thread_id": msg["thread_id"],
                        "subject": msg["subject"],
                        "from_address": msg["from_address"],
                        "from_name": msg["from_name"],
                        "to_addresses": json.dumps(msg["to_addresses"]),
                        "cc_addresses": json.dumps(msg["cc_addresses"]),
                        "date": msg["date"],
                        "snippet": msg["snippet"],
                        "body_text": msg["body_text"][:50000] if msg["body_text"] else None,
                        "body_html": msg["body_html"][:100000] if msg["body_html"] else None,
                        "is_read": msg["is_read"],
                        "has_attachments": msg["has_attachments"],
                    },
                )
                await db.commit()
                synced += 1
            except Exception as exc:
                logger.warning("Failed to insert IMAP message: %s", exc)
                await db.rollback()

    return synced


# ── Message Endpoints ────────────────────────────────────────────────

@router.get("/email/messages")
async def list_messages(
    account_id: Optional[int] = Query(None),
    is_read: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
):
    """List email messages with pagination and filtering."""
    conditions = []
    params: dict = {}

    if account_id is not None:
        conditions.append("m.account_id = :account_id")
        params["account_id"] = account_id
    if is_read is not None:
        conditions.append("m.is_read = :is_read")
        params["is_read"] = is_read
    if search:
        conditions.append("(m.subject ILIKE :search OR m.from_address ILIKE :search OR m.from_name ILIKE :search)")
        params["search"] = f"%{search}%"

    where_clause = " AND ".join(conditions) if conditions else "TRUE"
    offset = (page - 1) * per_page
    params["limit"] = per_page
    params["offset"] = offset

    async with _session() as db:
        # Count total
        count_result = await db.execute(
            text(f"SELECT COUNT(*) FROM public.email_messages m WHERE {where_clause}"),
            params,
        )
        total = count_result.scalar()

        # Fetch page (exclude body for list view)
        result = await db.execute(
            text(f"""
                SELECT m.id, m.account_id, m.message_id, m.thread_id, m.subject,
                       m.from_address, m.from_name, m.to_addresses, m.date, m.snippet,
                       m.labels, m.is_read, m.has_attachments, m.synced_at,
                       a.provider, a.email as account_email
                FROM public.email_messages m
                JOIN public.email_accounts a ON a.id = m.account_id
                WHERE {where_clause}
                ORDER BY m.date DESC NULLS LAST
                LIMIT :limit OFFSET :offset
            """),
            params,
        )
        rows = result.fetchall()

    return {
        "messages": [
            {
                "id": r[0],
                "account_id": r[1],
                "message_id": r[2],
                "thread_id": r[3],
                "subject": r[4],
                "from_address": r[5],
                "from_name": r[6],
                "to_addresses": r[7],
                "date": r[8].isoformat() if r[8] else None,
                "snippet": r[9],
                "labels": r[10],
                "is_read": r[11],
                "has_attachments": r[12],
                "synced_at": r[13].isoformat() if r[13] else None,
                "provider": r[14],
                "account_email": r[15],
            }
            for r in rows
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page if total else 0,
    }


@router.get("/email/messages/{message_id}")
async def get_message(message_id: int):
    """Get full message including body."""
    async with _session() as db:
        result = await db.execute(
            text("""
                SELECT m.*, a.provider, a.email as account_email
                FROM public.email_messages m
                JOIN public.email_accounts a ON a.id = m.account_id
                WHERE m.id = :id
            """),
            {"id": message_id},
        )
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Message not found")

        # Map columns by name
        cols = result.keys()
        msg = dict(zip(cols, row))

    # Format dates
    for date_field in ("date", "synced_at"):
        if msg.get(date_field) and hasattr(msg[date_field], "isoformat"):
            msg[date_field] = msg[date_field].isoformat()

    return msg


@router.patch("/email/messages/{message_id}/read")
async def mark_as_read(message_id: int):
    """Mark a message as read."""
    async with _session() as db:
        result = await db.execute(
            text("UPDATE public.email_messages SET is_read = TRUE WHERE id = :id RETURNING id"),
            {"id": message_id},
        )
        if not result.fetchone():
            raise HTTPException(status_code=404, detail="Message not found")
        await db.commit()

    return {"ok": True, "message_id": message_id, "is_read": True}
