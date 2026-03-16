"""Tests for social OAuth flows — state encoding, nonce validation, callbacks."""

import os, sys, time
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-tests")
os.environ.setdefault("POSTGRES_URL", "postgresql+asyncpg://x:x@localhost/fake")
os.environ.setdefault("LEADGEN_DB_URL", "postgresql+asyncpg://x:x@localhost/fake")
os.environ.setdefault("OPENCLAW_AUTH_TOKEN", "test-token")
sys.modules.setdefault("app.services.notify", MagicMock(send_notification=AsyncMock()))

from app.api.social_oauth import (
    _encode_state,
    _decode_state,
    _nonce_store,
    _nonce_validate,
    _store_put,
    _store_pop,
    _oauth_complete_page,
    _OAUTH_TTL_SECONDS,
    _FALLBACK_USER_ID,
    _FALLBACK_ORG_ID,
)


# ── State encoding / decoding ─────────────────────────────────────────

class TestStateEncoding:
    def test_encode_produces_valid_format(self):
        state = _encode_state("instagram", 9, 1)
        parts = state.split(":")
        assert len(parts) >= 4
        assert parts[0] == "instagram"
        assert parts[1] == "9"
        assert parts[2] == "1"
        assert len(parts[3]) > 0  # nonce

    def test_encode_stores_nonce(self):
        state = _encode_state("x", 11, 2)
        # Nonce should be valid immediately after encode
        assert _nonce_validate(state) is True
        # Should be consumed (one-time use)
        assert _nonce_validate(state) is False

    def test_decode_new_format(self):
        state = _encode_state("tiktok", 9, 1)
        platform, user_id, org_id, nonce = _decode_state(state)
        assert platform == "tiktok"
        assert user_id == 9
        assert org_id == 1
        assert len(nonce) > 0

    def test_decode_old_format_two_parts(self):
        """Old format: platform:nonce — should fallback gracefully."""
        platform, user_id, org_id, nonce = _decode_state("instagram:abc123")
        assert platform == "instagram"
        assert user_id == _FALLBACK_USER_ID
        assert org_id == _FALLBACK_ORG_ID
        assert nonce == "abc123"

    def test_decode_bare_nonce(self):
        """Bare nonce (no colons) — X/Google old format."""
        platform, user_id, org_id, nonce = _decode_state("randomnonce123")
        assert platform == ""
        assert user_id == _FALLBACK_USER_ID
        assert org_id == _FALLBACK_ORG_ID
        assert nonce == "randomnonce123"

    def test_decode_invalid_user_id(self):
        """Non-integer user_id in state should fallback."""
        platform, user_id, org_id, nonce = _decode_state("meta:abc:1:nonce123")
        assert platform == "meta"
        assert user_id == _FALLBACK_USER_ID
        assert org_id == _FALLBACK_ORG_ID

    def test_roundtrip_all_platforms(self):
        for plat in ("meta", "instagram", "threads", "x", "tiktok", "google"):
            state = _encode_state(plat, 42, 7)
            p, u, o, n = _decode_state(state)
            assert p == plat
            assert u == 42
            assert o == 7
            # Consume nonce so next encode doesn't collide
            _nonce_validate(state)


# ── Nonce validation ───────────────────────────────────────────────────

class TestNonceValidation:
    def test_valid_nonce(self):
        _nonce_store("test-nonce-1")
        assert _nonce_validate("test-nonce-1") is True

    def test_nonce_consumed_on_validate(self):
        _nonce_store("test-nonce-2")
        assert _nonce_validate("test-nonce-2") is True
        assert _nonce_validate("test-nonce-2") is False  # already consumed

    def test_missing_nonce(self):
        assert _nonce_validate("nonexistent-nonce") is False

    def test_expired_nonce(self):
        """Manually expire a nonce by patching its timestamp."""
        from app.api.social_oauth import _state_nonces, _store_lock
        nonce = "expired-nonce-test"
        with _store_lock:
            _state_nonces[nonce] = time.monotonic() - _OAUTH_TTL_SECONDS - 1
        assert _nonce_validate(nonce) is False


# ── PKCE store ─────────────────────────────────────────────────────────

class TestPKCEStore:
    def test_put_and_pop(self):
        _store_put("pkce-key-1", "verifier-abc")
        assert _store_pop("pkce-key-1") == "verifier-abc"

    def test_pop_consumes(self):
        _store_put("pkce-key-2", "verifier-def")
        _store_pop("pkce-key-2")
        assert _store_pop("pkce-key-2") is None

    def test_pop_missing(self):
        assert _store_pop("nonexistent-pkce") is None

    def test_expired_pkce(self):
        from app.api.social_oauth import _pkce_store, _store_lock
        key = "expired-pkce"
        with _store_lock:
            _pkce_store[key] = ("verifier", time.monotonic() - _OAUTH_TTL_SECONDS - 1)
        assert _store_pop(key) is None


# ── OAuth complete page ────────────────────────────────────────────────

class TestOAuthCompletePage:
    def test_success_page(self):
        resp = _oauth_complete_page(True, "instagram")
        assert resp.status_code == 200
        body = resp.body.decode()
        assert "✅" in body
        assert "instagram connected successfully" in body.lower()
        assert "oauth_complete" in body
        assert 'status: "connected"' in body

    def test_error_page(self):
        resp = _oauth_complete_page(False, "x", "Token exchange failed")
        body = resp.body.decode()
        assert "❌" in body
        assert "Token exchange failed" in body
        assert 'status: "error"' in body


# ── Authorize endpoints (return auth_url with user context in state) ──

def _make_request(user_id=9, org_id=1):
    req = MagicMock()
    req.state = SimpleNamespace(user_id=user_id, org_id=org_id, user_email="test@test.com", is_superadmin=False)
    return req


class FakeResult:
    def __init__(self, item=None):
        self._item = item
    def scalar_one_or_none(self):
        return self._item


class FakeSetting:
    def __init__(self, value):
        self.value = value


@pytest.mark.asyncio
async def test_meta_authorize_includes_user_in_state():
    """Meta authorize should encode user_id/org_id in the OAuth state."""
    req = _make_request(user_id=9, org_id=1)
    db = AsyncMock()

    with patch("app.api.social_oauth._get_setting", new_callable=AsyncMock, return_value="test-app-id"):
        with patch("app.api.social_oauth.get_org_id", return_value=1):
            with patch("app.api.social_oauth.get_user_id", return_value=9):
                result = await _call_meta_authorize(req, db, "instagram")

    assert "auth_url" in result
    # Extract state from the auth_url
    from urllib.parse import urlparse, parse_qs
    url = urlparse(result["auth_url"])
    params = parse_qs(url.query)
    state = params["state"][0]

    platform, user_id, org_id, nonce = _decode_state(state)
    assert platform == "instagram"
    assert user_id == 9
    assert org_id == 1


async def _call_meta_authorize(req, db, platform="instagram"):
    """Helper to call meta_authorize without FastAPI DI."""
    from app.api.social_oauth import meta_authorize
    return await meta_authorize(request=req, platform=platform, db=db)


@pytest.mark.asyncio
async def test_x_authorize_includes_user_in_state():
    req = _make_request(user_id=11, org_id=2)
    db = AsyncMock()

    with patch("app.api.social_oauth._get_setting", new_callable=AsyncMock, return_value="test-x-id"):
        with patch("app.api.social_oauth.get_org_id", return_value=2):
            with patch("app.api.social_oauth.get_user_id", return_value=11):
                from app.api.social_oauth import x_authorize
                result = await x_authorize(request=req, db=db)

    from urllib.parse import urlparse, parse_qs
    url = urlparse(result["auth_url"])
    params = parse_qs(url.query)
    state = params["state"][0]

    platform, user_id, org_id, nonce = _decode_state(state)
    assert platform == "x"
    assert user_id == 11
    assert org_id == 2


@pytest.mark.asyncio
async def test_google_authorize_includes_user_in_state():
    req = _make_request(user_id=9, org_id=1)
    db = AsyncMock()

    with patch("app.api.social_oauth._get_setting", new_callable=AsyncMock, return_value="test-google-id"):
        with patch("app.api.social_oauth.get_org_id", return_value=1):
            with patch("app.api.social_oauth.get_user_id", return_value=9):
                from app.api.social_oauth import google_authorize
                result = await google_authorize(request=req, db=db)

    from urllib.parse import urlparse, parse_qs
    url = urlparse(result["auth_url"])
    params = parse_qs(url.query)
    state = params["state"][0]

    platform, user_id, org_id, nonce = _decode_state(state)
    assert platform == "google"
    assert user_id == 9


@pytest.mark.asyncio
async def test_tiktok_authorize_includes_user_in_state():
    req = _make_request(user_id=10, org_id=1)
    db = AsyncMock()

    with patch("app.api.social_oauth._get_setting", new_callable=AsyncMock, return_value="test-tiktok-key"):
        with patch("app.api.social_oauth.get_org_id", return_value=1):
            with patch("app.api.social_oauth.get_user_id", return_value=10):
                from app.api.social_oauth import tiktok_authorize
                result = await tiktok_authorize(request=req, db=db)

    from urllib.parse import urlparse, parse_qs
    url = urlparse(result["auth_url"])
    params = parse_qs(url.query)
    state = params["state"][0]

    platform, user_id, org_id, nonce = _decode_state(state)
    assert platform == "tiktok"
    assert user_id == 10


# ── Callback error handling ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_meta_callback_invalid_state():
    from app.api.social_oauth import meta_callback
    req = MagicMock()
    req.state = SimpleNamespace()
    db = AsyncMock()

    result = await meta_callback(request=req, code="test-code", state="invalid-state", db=db)
    body = result.body.decode()
    assert "Invalid or expired OAuth state" in body
    assert "❌" in body


@pytest.mark.asyncio
async def test_instagram_callback_invalid_state():
    from app.api.social_oauth import instagram_callback
    req = MagicMock()
    req.state = SimpleNamespace()
    db = AsyncMock()

    result = await instagram_callback(request=req, code="test-code", state="bogus", db=db)
    body = result.body.decode()
    assert "Invalid or expired OAuth state" in body


@pytest.mark.asyncio
async def test_x_callback_with_error_param():
    from app.api.social_oauth import x_callback
    req = MagicMock()
    req.state = SimpleNamespace()
    db = AsyncMock()

    result = await x_callback(
        request=req, code="", state="whatever",
        error="access_denied", error_description="User denied", db=db
    )
    body = result.body.decode()
    assert "access_denied" in body
    assert "User denied" in body


# ── Instagram callback full flow (mocked) ─────────────────────────────

@pytest.mark.asyncio
async def test_instagram_callback_success():
    """Full Instagram callback flow with mocked HTTP calls."""
    from app.api.social_oauth import instagram_callback

    # Create valid state
    state = _encode_state("instagram", 9, 1)

    req = MagicMock()
    req.state = SimpleNamespace()

    # Mock DB
    db = AsyncMock()
    fake_result = MagicMock()
    fake_result.scalar_one_or_none.return_value = None  # No existing account
    db.execute = AsyncMock(return_value=fake_result)
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    # Mock settings
    async def mock_get_setting(db, key):
        settings_map = {
            "instagram_app_id": "test-ig-app-id",
            "instagram_app_secret": "test-ig-secret",
            "meta_app_id": "test-meta-id",
            "meta_app_secret": "test-meta-secret",
        }
        return settings_map.get(key)

    # Mock HTTP responses
    mock_token_resp = MagicMock()
    mock_token_resp.status_code = 200
    mock_token_resp.json.return_value = {"access_token": "short-token", "user_id": "12345"}

    mock_ll_resp = MagicMock()
    mock_ll_resp.status_code = 200
    mock_ll_resp.json.return_value = {"access_token": "long-lived-token"}

    mock_me_resp = MagicMock()
    mock_me_resp.status_code = 200
    mock_me_resp.json.return_value = {
        "id": "12345",
        "username": "testuser",
        "account_type": "BUSINESS",
        "media_count": 50,
        "followers_count": 1000,
        "follows_count": 200,
    }

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_token_resp)
    mock_client.get = AsyncMock(side_effect=[mock_ll_resp, mock_me_resp])
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.api.social_oauth._get_setting", side_effect=mock_get_setting):
        with patch("app.api.social_oauth.httpx.AsyncClient", return_value=mock_client):
            result = await instagram_callback(request=req, code="auth-code", state=state, db=db)

    body = result.body.decode()
    assert "✅" in body
    assert "instagram" in body.lower()

    # Verify the account was created with correct user_id
    db.add.assert_called_once()
    added_account = db.add.call_args[0][0]
    assert added_account.user_id == 9
    assert added_account.org_id == 1
    assert added_account.platform == "instagram"
    assert added_account.username == "testuser"
