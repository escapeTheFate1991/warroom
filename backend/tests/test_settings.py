"""Comprehensive tests for settings + stripe settings endpoints.

Follows the same mock-DB pattern as test_leads.py:
  - Override DB dependencies with mock async sessions
  - Generate valid JWTs to pass AuthGuardMiddleware
  - Mock external services (stripe_service)
  - Test success, failure, auth guard, and edge cases
"""

import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest
import pytest_asyncio
import httpx

# Ensure the backend app is importable
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Set required env vars BEFORE importing the app
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-tests")
os.environ.setdefault("POSTGRES_URL", "postgresql+asyncpg://x:x@localhost/fake")
os.environ.setdefault("LEADGEN_DB_URL", "postgresql+asyncpg://x:x@localhost/fake")

# Patch heavy imports that hit real infra
sys.modules.setdefault("app.services.notify", MagicMock(send_notification=AsyncMock()))

from sqlalchemy.ext.asyncio import AsyncSession


# ── Fake result helpers (mirror test_leads.py) ───────────────────────

class FakeResult:
    """Fake SQLAlchemy result object."""
    def __init__(self, items=None, scalar_value=None, mappings_data=None):
        self._items = items or []
        self._scalar_value = scalar_value
        self._mappings_data = mappings_data

    def scalars(self):
        return self

    def all(self):
        return self._items

    def scalar_one_or_none(self):
        return self._scalar_value

    def scalar(self):
        return self._scalar_value

    def first(self):
        return self._items[0] if self._items else None

    def mappings(self):
        return FakeMappings(self._mappings_data or [])


class FakeMappings:
    def __init__(self, data):
        self._data = data

    def all(self):
        return self._data

    def first(self):
        return self._data[0] if self._data else None


# ── JWT helper ───────────────────────────────────────────────────────

JWT_SECRET = "test-secret-key-for-tests"


def make_auth_header(user_id: int = 1, email: str = "test@warroom.io", is_superadmin: bool = True) -> dict:
    """Create a valid Authorization header for test requests."""
    payload = {
        "user_id": user_id,
        "email": email,
        "is_superadmin": is_superadmin,
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


# ── Fake Setting model ──────────────────────────────────────────────

def make_fake_setting(**overrides):
    """Create a fake Setting-like object."""
    defaults = dict(
        id=1,
        key="company_name",
        value="stuffnthings",
        category="general",
        description="Your company/brand name",
        is_secret=0,
    )
    defaults.update(overrides)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    obj.__dict__.update(defaults)
    return obj


def make_fake_user(is_superadmin=True):
    """Create a fake User object for auth dependency."""
    user = MagicMock()
    user.id = 1
    user.email = "test@warroom.io"
    user.name = "Test User"
    user.is_superadmin = is_superadmin
    user.status = True
    user.org = None
    user.role = None
    user.has_permission = MagicMock(return_value=True)
    return user


# ── Mock DB factory ──────────────────────────────────────────────────

def _make_mock_db():
    """Create a mock async DB session."""
    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    db.delete = AsyncMock()
    db.rollback = AsyncMock()
    return db


# ── App and client fixture ───────────────────────────────────────────

@pytest_asyncio.fixture
async def client():
    """Create test client with dependency overrides."""
    from app.main import app
    from app.db.leadgen_db import get_leadgen_db
    from app.db.crm_db import get_crm_db
    from app.api.auth import get_current_user, require_superadmin

    mock_leadgen_db = _make_mock_db()
    mock_crm_db = _make_mock_db()

    async def override_leadgen_db():
        yield mock_leadgen_db

    async def override_crm_db():
        yield mock_crm_db

    # Override auth dependencies to return fake users
    # The superadmin user is default; tests that need non-superadmin override manually
    fake_superadmin = make_fake_user(is_superadmin=True)

    async def override_get_current_user():
        return fake_superadmin

    def override_require_superadmin():
        async def checker():
            return fake_superadmin
        return checker

    app.dependency_overrides[get_leadgen_db] = override_leadgen_db
    app.dependency_overrides[get_crm_db] = override_crm_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    # Override require_superadmin at the function level — it's a factory
    # We need to patch it differently since it returns a dependency
    # Instead, patch it in the settings module
    original_require_superadmin = None

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        ac._mock_leadgen_db = mock_leadgen_db
        ac._mock_crm_db = mock_crm_db
        ac._fake_user = fake_superadmin
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client_no_auth():
    """Create test client WITHOUT auth overrides (for testing 401s)."""
    from app.main import app

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def auth_headers():
    return make_auth_header()


@pytest.fixture
def non_admin_headers():
    return make_auth_header(is_superadmin=False)


# =====================================================================
# TESTS: General Settings - List All
# =====================================================================

class TestListSettings:
    """GET /api/settings"""

    @pytest.mark.asyncio
    async def test_list_settings_success(self, client, auth_headers):
        db = client._mock_leadgen_db
        settings_list = [
            make_fake_setting(key="company_name", value="stuffnthings", category="general"),
            make_fake_setting(key="google_maps_api_key", value="sk-test-123", category="api_keys", is_secret=1),
        ]
        db.execute.return_value = FakeResult(items=settings_list)

        resp = await client.get("/api/settings", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 2

    @pytest.mark.asyncio
    async def test_list_settings_with_category_filter(self, client, auth_headers):
        db = client._mock_leadgen_db
        settings_list = [
            make_fake_setting(key="google_maps_api_key", category="api_keys"),
        ]
        db.execute.return_value = FakeResult(items=settings_list)

        resp = await client.get("/api/settings?category=api_keys", headers=auth_headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_list_settings_empty(self, client, auth_headers):
        db = client._mock_leadgen_db
        db.execute.return_value = FakeResult(items=[])

        resp = await client.get("/api/settings", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_list_settings_no_auth(self, client_no_auth):
        resp = await client_no_auth.get("/api/settings")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_list_settings_secret_masking_superadmin(self, client, auth_headers):
        """Superadmin should see raw secret values."""
        db = client._mock_leadgen_db
        secret_setting = make_fake_setting(
            key="google_maps_api_key",
            value="AIzaSyB-test-key-12345",
            is_secret=1,
            category="api_keys",
        )
        # Superadmin user is default — user.is_superadmin = True
        db.execute.return_value = FakeResult(items=[secret_setting])

        resp = await client.get("/api/settings", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        # Superadmin sees unmasked value
        assert data[0]["value"] == "AIzaSyB-test-key-12345"


# =====================================================================
# TESTS: General Settings - Get by Key
# =====================================================================

class TestGetSetting:
    """GET /api/settings/{key}"""

    @pytest.mark.asyncio
    async def test_get_setting_success(self, client, auth_headers):
        db = client._mock_leadgen_db
        setting = make_fake_setting(key="company_name", value="stuffnthings")
        db.execute.return_value = FakeResult(items=[setting])

        resp = await client.get("/api/settings/company_name", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["key"] == "company_name"
        assert data["value"] == "stuffnthings"

    @pytest.mark.asyncio
    async def test_get_setting_not_found(self, client, auth_headers):
        db = client._mock_leadgen_db
        db.execute.return_value = FakeResult(items=[])

        resp = await client.get("/api/settings/nonexistent_key", headers=auth_headers)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_setting_legacy_key_normalization(self, client, auth_headers):
        """Legacy key 'openai_api_key' should map to 'openclaw_auth_token'."""
        db = client._mock_leadgen_db
        setting = make_fake_setting(key="openclaw_auth_token", value="tok-123", is_secret=1)
        db.execute.return_value = FakeResult(items=[setting])

        resp = await client.get("/api/settings/openai_api_key", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["key"] == "openclaw_auth_token"

    @pytest.mark.asyncio
    async def test_get_setting_no_auth(self, client_no_auth):
        resp = await client_no_auth.get("/api/settings/company_name")
        assert resp.status_code == 401


# =====================================================================
# TESTS: General Settings - Create / Update
# =====================================================================

class TestCreateSetting:
    """POST /api/settings"""

    @pytest.mark.asyncio
    async def test_create_setting_success(self, client, auth_headers):
        db = client._mock_leadgen_db
        # Check for existing — none found
        db.execute.return_value = FakeResult(items=[])

        async def on_refresh(obj):
            obj.key = "custom_setting"
            obj.value = "custom_value"
            obj.category = "general"
            obj.description = "A custom setting"
            obj.is_secret = 0
        db.refresh = AsyncMock(side_effect=on_refresh)

        resp = await client.post(
            "/api/settings",
            json={
                "key": "custom_setting",
                "value": "custom_value",
                "category": "general",
                "description": "A custom setting",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["key"] == "custom_setting"

    @pytest.mark.asyncio
    async def test_create_setting_duplicate_key(self, client, auth_headers):
        db = client._mock_leadgen_db
        existing = make_fake_setting(key="company_name")
        db.execute.return_value = FakeResult(items=[existing])

        resp = await client.post(
            "/api/settings",
            json={"key": "company_name", "value": "new_val"},
            headers=auth_headers,
        )
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_create_setting_no_auth(self, client_no_auth):
        resp = await client_no_auth.post(
            "/api/settings",
            json={"key": "test", "value": "test"},
        )
        assert resp.status_code == 401


class TestUpdateSetting:
    """PUT /api/settings/{key}"""

    @pytest.mark.asyncio
    async def test_update_setting_existing(self, client, auth_headers):
        db = client._mock_leadgen_db
        setting = make_fake_setting(key="company_name", value="old_val")
        db.execute.return_value = FakeResult(items=[setting])

        async def on_refresh(obj):
            obj.key = "company_name"
            obj.value = "new_company"
            obj.category = "general"
            obj.description = "Your company/brand name"
            obj.is_secret = 0
        db.refresh = AsyncMock(side_effect=on_refresh)

        resp = await client.put(
            "/api/settings/company_name",
            json={"value": "new_company"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["value"] == "new_company"

    @pytest.mark.asyncio
    async def test_update_setting_creates_if_missing(self, client, auth_headers):
        db = client._mock_leadgen_db
        db.execute.return_value = FakeResult(items=[])

        async def on_refresh(obj):
            obj.key = "new_key"
            obj.value = "new_value"
            obj.category = "general"
            obj.description = None
            obj.is_secret = 0
        db.refresh = AsyncMock(side_effect=on_refresh)

        resp = await client.put(
            "/api/settings/new_key",
            json={"value": "new_value"},
            headers=auth_headers,
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_update_setting_missing_value(self, client, auth_headers):
        resp = await client.put(
            "/api/settings/company_name",
            json={},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_update_setting_no_auth(self, client_no_auth):
        resp = await client_no_auth.put(
            "/api/settings/company_name",
            json={"value": "test"},
        )
        assert resp.status_code == 401


class TestDeleteSetting:
    """DELETE /api/settings/{key}"""

    @pytest.mark.asyncio
    async def test_delete_setting_success(self, client, auth_headers):
        db = client._mock_leadgen_db
        setting = make_fake_setting(key="custom_setting")

        call_idx = 0
        async def multi_execute(stmt, *args, **kwargs):
            nonlocal call_idx
            call_idx += 1
            if call_idx == 1:
                # First call: find the setting
                return FakeResult(items=[setting])
            else:
                # Second call: delete
                return FakeResult()
        db.execute = AsyncMock(side_effect=multi_execute)

        resp = await client.delete("/api/settings/custom_setting", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "deleted"
        assert data["key"] == "custom_setting"

    @pytest.mark.asyncio
    async def test_delete_setting_not_found(self, client, auth_headers):
        db = client._mock_leadgen_db
        db.execute.return_value = FakeResult(items=[])

        resp = await client.delete("/api/settings/nonexistent", headers=auth_headers)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_setting_no_auth(self, client_no_auth):
        resp = await client_no_auth.delete("/api/settings/company_name")
        assert resp.status_code == 401


# =====================================================================
# TESTS: Email Settings
# =====================================================================

class TestEmailSettings:
    """GET/PUT /api/settings/email"""

    @pytest.mark.asyncio
    async def test_get_email_settings_defaults(self, client, auth_headers):
        db = client._mock_leadgen_db
        # No email settings stored — should return defaults
        db.execute.return_value = FakeResult(items=[])

        resp = await client.get("/api/settings/email", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "smtp_host" in data
        assert "smtp_port" in data
        assert data["smtp_port"] == "587"
        assert data["from_email"] == ""

    @pytest.mark.asyncio
    async def test_get_email_settings_stored(self, client, auth_headers):
        db = client._mock_leadgen_db
        # Return stored values for each email field
        stored = make_fake_setting(key="email_smtp_host", value="smtp.gmail.com")
        db.execute.return_value = FakeResult(items=[stored])

        resp = await client.get("/api/settings/email", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["smtp_host"] == "smtp.gmail.com"

    @pytest.mark.asyncio
    async def test_put_email_settings(self, client, auth_headers):
        db = client._mock_leadgen_db
        # Each field lookup returns no existing setting
        db.execute.return_value = FakeResult(items=[])

        resp = await client.put(
            "/api/settings/email",
            json={
                "smtp_host": "smtp.example.com",
                "smtp_port": "465",
                "smtp_username": "user@example.com",
                "smtp_password": "secret123",
                "from_name": "War Room",
                "from_email": "noreply@example.com",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"

    @pytest.mark.asyncio
    async def test_put_email_settings_partial(self, client, auth_headers):
        """Should only update fields provided."""
        db = client._mock_leadgen_db
        db.execute.return_value = FakeResult(items=[])

        resp = await client.put(
            "/api/settings/email",
            json={"smtp_host": "new-host.com"},
            headers=auth_headers,
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_get_email_no_auth(self, client_no_auth):
        resp = await client_no_auth.get("/api/settings/email")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_put_email_no_auth(self, client_no_auth):
        resp = await client_no_auth.put(
            "/api/settings/email",
            json={"smtp_host": "test"},
        )
        assert resp.status_code == 401


# =====================================================================
# TESTS: Lead Scoring Settings
# =====================================================================

class TestLeadScoringSettings:
    """GET/PUT /api/settings/lead-scoring"""

    @pytest.mark.asyncio
    async def test_get_lead_scoring_defaults(self, client, auth_headers):
        db = client._mock_leadgen_db
        db.execute.return_value = FakeResult(items=[])

        resp = await client.get("/api/settings/lead-scoring", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "weights" in data
        assert "thresholds" in data
        assert data["thresholds"]["hot"] == 70
        assert data["thresholds"]["warm"] == 40
        assert data["weights"]["no_website"] == 30

    @pytest.mark.asyncio
    async def test_get_lead_scoring_stored(self, client, auth_headers):
        db = client._mock_leadgen_db
        custom_config = {
            "weights": {"no_website": 50, "bad_website_score": 30},
            "thresholds": {"hot": 80, "warm": 50, "cold": 0},
        }
        stored = make_fake_setting(
            key="lead_scoring_config",
            value=json.dumps(custom_config),
        )
        db.execute.return_value = FakeResult(items=[stored])

        resp = await client.get("/api/settings/lead-scoring", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["weights"]["no_website"] == 50
        assert data["thresholds"]["hot"] == 80

    @pytest.mark.asyncio
    async def test_get_lead_scoring_invalid_json(self, client, auth_headers):
        """Should fall back to defaults on bad JSON."""
        db = client._mock_leadgen_db
        stored = make_fake_setting(key="lead_scoring_config", value="not-valid-json{{{")
        db.execute.return_value = FakeResult(items=[stored])

        resp = await client.get("/api/settings/lead-scoring", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        # Should return defaults
        assert "weights" in data
        assert "thresholds" in data

    @pytest.mark.asyncio
    async def test_put_lead_scoring(self, client, auth_headers):
        db = client._mock_leadgen_db
        # No existing config
        db.execute.return_value = FakeResult(items=[])

        new_config = {
            "weights": {"no_website": 40, "bad_website_score": 25},
            "thresholds": {"hot": 75, "warm": 45, "cold": 0},
        }
        resp = await client.put(
            "/api/settings/lead-scoring",
            json=new_config,
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    @pytest.mark.asyncio
    async def test_put_lead_scoring_update_existing(self, client, auth_headers):
        db = client._mock_leadgen_db
        existing = make_fake_setting(key="lead_scoring_config", value="{}")
        db.execute.return_value = FakeResult(items=[existing])

        resp = await client.put(
            "/api/settings/lead-scoring",
            json={"weights": {"no_website": 99}, "thresholds": {"hot": 90}},
            headers=auth_headers,
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_get_lead_scoring_no_auth(self, client_no_auth):
        resp = await client_no_auth.get("/api/settings/lead-scoring")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_put_lead_scoring_no_auth(self, client_no_auth):
        resp = await client_no_auth.put(
            "/api/settings/lead-scoring",
            json={"weights": {}, "thresholds": {}},
        )
        assert resp.status_code == 401


# =====================================================================
# TESTS: Stripe Config
# =====================================================================

class TestStripeConfig:
    """GET/PUT /api/stripe"""

    @pytest.mark.asyncio
    async def test_get_stripe_config(self, client, auth_headers):
        with patch("app.api.stripe_settings.stripe_service") as mock_ss:
            mock_ss.get_mode.return_value = "test"
            mock_ss.get_public_key.return_value = "pk_test_abc123"
            mock_ss.test_connection.return_value = {"connected": True, "mode": "test"}

            resp = await client.get("/api/stripe", headers=auth_headers)
            assert resp.status_code == 200
            data = resp.json()
            assert data["mode"] == "test"
            assert data["public_key"] == "pk_test_abc123"
            assert data["connected"] is True

    @pytest.mark.asyncio
    async def test_get_stripe_config_disconnected(self, client, auth_headers):
        with patch("app.api.stripe_settings.stripe_service") as mock_ss:
            mock_ss.get_mode.return_value = "test"
            mock_ss.get_public_key.return_value = ""
            mock_ss.test_connection.return_value = {
                "connected": False,
                "mode": "test",
                "error": "Invalid API key",
            }

            resp = await client.get("/api/stripe", headers=auth_headers)
            assert resp.status_code == 200
            data = resp.json()
            assert data["connected"] is False
            assert data["error"] == "Invalid API key"

    @pytest.mark.asyncio
    async def test_put_stripe_config_test_mode(self, client, auth_headers):
        with patch("app.api.stripe_settings.stripe_service") as mock_ss:
            mock_ss.get_public_key.return_value = "pk_test_abc"
            resp = await client.put(
                "/api/stripe",
                json={"mode": "test"},
                headers=auth_headers,
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["mode"] == "test"

    @pytest.mark.asyncio
    async def test_put_stripe_config_live_mode(self, client, auth_headers):
        with patch("app.api.stripe_settings.stripe_service") as mock_ss:
            mock_ss.get_public_key.return_value = "pk_live_abc"
            resp = await client.put(
                "/api/stripe",
                json={"mode": "live"},
                headers=auth_headers,
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["mode"] == "live"

    @pytest.mark.asyncio
    async def test_put_stripe_config_invalid_mode(self, client, auth_headers):
        resp = await client.put(
            "/api/stripe",
            json={"mode": "invalid"},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_get_stripe_config_no_auth(self, client_no_auth):
        resp = await client_no_auth.get("/api/stripe")
        assert resp.status_code == 401


# =====================================================================
# TESTS: Stripe Test Connection
# =====================================================================

class TestStripeTestConnection:
    """GET /api/stripe/test-connection"""

    @pytest.mark.asyncio
    async def test_stripe_connection_success(self, client, auth_headers):
        with patch("app.api.stripe_settings.stripe_service") as mock_ss:
            mock_ss.test_connection.return_value = {"connected": True, "mode": "test"}

            resp = await client.get("/api/stripe/test-connection", headers=auth_headers)
            assert resp.status_code == 200
            data = resp.json()
            assert data["connected"] is True

    @pytest.mark.asyncio
    async def test_stripe_connection_failure(self, client, auth_headers):
        with patch("app.api.stripe_settings.stripe_service") as mock_ss:
            mock_ss.test_connection.return_value = {
                "connected": False,
                "mode": "test",
                "error": "Invalid API key",
            }

            resp = await client.get("/api/stripe/test-connection", headers=auth_headers)
            assert resp.status_code == 200
            data = resp.json()
            assert data["connected"] is False

    @pytest.mark.asyncio
    async def test_stripe_connection_no_auth(self, client_no_auth):
        resp = await client_no_auth.get("/api/stripe/test-connection")
        assert resp.status_code == 401


# =====================================================================
# TESTS: Stripe Products - CRUD
# =====================================================================

class TestStripeProducts:
    """CRUD /api/stripe/products"""

    @pytest.mark.asyncio
    async def test_list_products(self, client, auth_headers):
        fake_products = [
            {
                "id": 1, "name": "Foundation", "description": "Basic plan",
                "price_cents": 29900, "interval": "month", "features": ["SSL"],
                "is_active": True, "sort_order": 1,
                "stripe_product_id": None, "stripe_price_id": None,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            {
                "id": 2, "name": "Growth", "description": "Full plan",
                "price_cents": 120000, "interval": "month", "features": ["SSL", "Ads"],
                "is_active": True, "sort_order": 2,
                "stripe_product_id": "prod_abc", "stripe_price_id": "price_abc",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
        ]

        with patch("app.api.stripe_settings.leadgen_session") as mock_session_factory:
            mock_db = AsyncMock()
            mock_db.execute.return_value = FakeResult(mappings_data=fake_products)
            mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

            resp = await client.get("/api/stripe/products", headers=auth_headers)
            assert resp.status_code == 200
            data = resp.json()
            assert isinstance(data, list)
            assert len(data) == 2
            assert data[0]["name"] == "Foundation"

    @pytest.mark.asyncio
    async def test_create_product(self, client, auth_headers):
        new_product = {
            "id": 3, "name": "Enterprise", "description": "Custom plan",
            "price_cents": 500000, "interval": "month", "features": ["Everything"],
            "is_active": True, "sort_order": 3,
            "stripe_product_id": "prod_new", "stripe_price_id": "price_new",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        with patch("app.api.stripe_settings.stripe_service") as mock_ss, \
             patch("app.api.stripe_settings.leadgen_session") as mock_session_factory:
            mock_ss.create_product.return_value = {
                "stripe_product_id": "prod_new",
                "stripe_price_id": "price_new",
            }

            mock_db = AsyncMock()
            mock_db.execute.return_value = FakeResult(mappings_data=[new_product])
            mock_db.commit = AsyncMock()
            mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

            resp = await client.post(
                "/api/stripe/products",
                json={
                    "name": "Enterprise",
                    "description": "Custom plan",
                    "price_cents": 500000,
                    "interval": "month",
                    "features": ["Everything"],
                    "sort_order": 3,
                },
                headers=auth_headers,
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["name"] == "Enterprise"
            assert data["price_cents"] == 500000

    @pytest.mark.asyncio
    async def test_create_product_stripe_fails_saves_locally(self, client, auth_headers):
        """Product should be saved locally even if Stripe API fails."""
        local_product = {
            "id": 4, "name": "Local Only", "description": "No Stripe",
            "price_cents": 10000, "interval": "month", "features": [],
            "is_active": True, "sort_order": 4,
            "stripe_product_id": None, "stripe_price_id": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        with patch("app.api.stripe_settings.stripe_service") as mock_ss, \
             patch("app.api.stripe_settings.leadgen_session") as mock_session_factory:
            mock_ss.create_product.side_effect = Exception("Stripe API down")

            mock_db = AsyncMock()
            mock_db.execute.return_value = FakeResult(mappings_data=[local_product])
            mock_db.commit = AsyncMock()
            mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

            resp = await client.post(
                "/api/stripe/products",
                json={
                    "name": "Local Only",
                    "price_cents": 10000,
                },
                headers=auth_headers,
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["name"] == "Local Only"
            assert data["stripe_product_id"] is None

    @pytest.mark.asyncio
    async def test_update_product(self, client, auth_headers):
        existing = {
            "id": 1, "name": "Foundation", "description": "Basic",
            "price_cents": 29900, "interval": "month", "features": ["SSL"],
            "is_active": True, "sort_order": 1,
            "stripe_product_id": None, "stripe_price_id": None,
        }
        updated = {**existing, "name": "Foundation Pro", "price_cents": 39900,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "created_at": datetime.now(timezone.utc).isoformat()}

        with patch("app.api.stripe_settings.leadgen_session") as mock_session_factory:
            mock_db = AsyncMock()
            call_idx = 0

            async def multi_execute(stmt, *args, **kwargs):
                nonlocal call_idx
                call_idx += 1
                if call_idx == 1:
                    return FakeResult(mappings_data=[existing])
                else:
                    return FakeResult(mappings_data=[updated])
            mock_db.execute = AsyncMock(side_effect=multi_execute)
            mock_db.commit = AsyncMock()
            mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

            resp = await client.put(
                "/api/stripe/products/1",
                json={"name": "Foundation Pro", "price_cents": 39900},
                headers=auth_headers,
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["name"] == "Foundation Pro"

    @pytest.mark.asyncio
    async def test_update_product_not_found(self, client, auth_headers):
        with patch("app.api.stripe_settings.leadgen_session") as mock_session_factory:
            mock_db = AsyncMock()
            mock_db.execute.return_value = FakeResult(mappings_data=[])
            mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

            resp = await client.put(
                "/api/stripe/products/999",
                json={"name": "Nonexistent"},
                headers=auth_headers,
            )
            assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_product_no_changes(self, client, auth_headers):
        existing = {
            "id": 1, "name": "Foundation", "description": "Basic",
            "price_cents": 29900, "interval": "month", "features": ["SSL"],
            "is_active": True, "sort_order": 1,
            "stripe_product_id": None, "stripe_price_id": None,
        }

        with patch("app.api.stripe_settings.leadgen_session") as mock_session_factory:
            mock_db = AsyncMock()
            mock_db.execute.return_value = FakeResult(mappings_data=[existing])
            mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

            resp = await client.put(
                "/api/stripe/products/1",
                json={},  # no changes
                headers=auth_headers,
            )
            assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_delete_product(self, client, auth_headers):
        existing = {
            "id": 1, "name": "Foundation", "stripe_product_id": "prod_abc",
            "is_active": True,
        }

        with patch("app.api.stripe_settings.stripe_service") as mock_ss, \
             patch("app.api.stripe_settings.leadgen_session") as mock_session_factory:
            mock_ss.archive_product = MagicMock()

            mock_db = AsyncMock()
            mock_db.execute.return_value = FakeResult(mappings_data=[existing])
            mock_db.commit = AsyncMock()
            mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

            resp = await client.delete("/api/stripe/products/1", headers=auth_headers)
            assert resp.status_code == 200
            data = resp.json()
            assert data["deleted"] is True
            assert data["id"] == 1
            mock_ss.archive_product.assert_called_once_with("prod_abc")

    @pytest.mark.asyncio
    async def test_delete_product_not_found(self, client, auth_headers):
        with patch("app.api.stripe_settings.leadgen_session") as mock_session_factory:
            mock_db = AsyncMock()
            mock_db.execute.return_value = FakeResult(mappings_data=[])
            mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

            resp = await client.delete("/api/stripe/products/999", headers=auth_headers)
            assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_product_no_stripe_id(self, client, auth_headers):
        """Should still delete locally even if no Stripe product ID."""
        existing = {
            "id": 2, "name": "Local Only", "stripe_product_id": None,
            "is_active": True,
        }

        with patch("app.api.stripe_settings.stripe_service") as mock_ss, \
             patch("app.api.stripe_settings.leadgen_session") as mock_session_factory:
            mock_db = AsyncMock()
            mock_db.execute.return_value = FakeResult(mappings_data=[existing])
            mock_db.commit = AsyncMock()
            mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

            resp = await client.delete("/api/stripe/products/2", headers=auth_headers)
            assert resp.status_code == 200
            mock_ss.archive_product.assert_not_called()

    @pytest.mark.asyncio
    async def test_list_products_no_auth(self, client_no_auth):
        resp = await client_no_auth.get("/api/stripe/products")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_create_product_no_auth(self, client_no_auth):
        resp = await client_no_auth.post(
            "/api/stripe/products",
            json={"name": "Test", "price_cents": 100},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_create_product_missing_name(self, client, auth_headers):
        resp = await client.post(
            "/api/stripe/products",
            json={"price_cents": 100},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_create_product_missing_price(self, client, auth_headers):
        resp = await client.post(
            "/api/stripe/products",
            json={"name": "Test"},
            headers=auth_headers,
        )
        assert resp.status_code == 422


# =====================================================================
# TESTS: Stripe Sync
# =====================================================================

class TestStripeSync:
    """POST /api/stripe/sync"""

    @pytest.mark.asyncio
    async def test_sync_products_success(self, client, auth_headers):
        products = [
            {
                "id": 1, "name": "Foundation", "description": "Basic",
                "price_cents": 29900, "interval": "month",
                "stripe_product_id": None, "stripe_price_id": None,
                "is_active": True, "sort_order": 1,
            },
        ]

        with patch("app.api.stripe_settings.stripe_service") as mock_ss, \
             patch("app.api.stripe_settings.leadgen_session") as mock_session_factory:
            # First call: list products; second+: update DB
            mock_db = AsyncMock()
            mock_db.execute.return_value = FakeResult(mappings_data=products)
            mock_db.commit = AsyncMock()
            mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

            mock_ss.create_product.return_value = {
                "stripe_product_id": "prod_new",
                "stripe_price_id": "price_new",
            }

            resp = await client.post("/api/stripe/sync", headers=auth_headers)
            assert resp.status_code == 200
            data = resp.json()
            assert "synced" in data
            assert "errors" in data
            assert "total" in data

    @pytest.mark.asyncio
    async def test_sync_products_with_errors(self, client, auth_headers):
        products = [
            {
                "id": 1, "name": "Bad Product", "description": "",
                "price_cents": 100, "interval": "month",
                "stripe_product_id": None, "stripe_price_id": None,
                "is_active": True, "sort_order": 1,
            },
        ]

        with patch("app.api.stripe_settings.stripe_service") as mock_ss, \
             patch("app.api.stripe_settings.leadgen_session") as mock_session_factory:
            mock_db = AsyncMock()
            mock_db.execute.return_value = FakeResult(mappings_data=products)
            mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

            mock_ss.create_product.side_effect = Exception("Stripe error")

            resp = await client.post("/api/stripe/sync", headers=auth_headers)
            assert resp.status_code == 200
            data = resp.json()
            assert data["synced"] == 0
            assert len(data["errors"]) == 1

    @pytest.mark.asyncio
    async def test_sync_no_auth(self, client_no_auth):
        resp = await client_no_auth.post("/api/stripe/sync")
        assert resp.status_code == 401


# =====================================================================
# TESTS: Auth Guards (comprehensive)
# =====================================================================

class TestAuthGuards:
    """Verify 401 on unauthenticated requests across all endpoints."""

    @pytest.mark.asyncio
    async def test_expired_token_settings(self, client_no_auth):
        payload = {
            "user_id": 1,
            "email": "test@warroom.io",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        }
        token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
        headers = {"Authorization": f"Bearer {token}"}
        resp = await client_no_auth.get("/api/settings", headers=headers)
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_token_settings(self, client_no_auth):
        headers = {"Authorization": "Bearer totally-not-a-valid-token"}
        resp = await client_no_auth.get("/api/settings", headers=headers)
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_missing_bearer_prefix(self, client_no_auth):
        payload = {"user_id": 1, "exp": datetime.now(timezone.utc) + timedelta(hours=1)}
        token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
        headers = {"Authorization": token}
        resp = await client_no_auth.get("/api/settings", headers=headers)
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_no_header_at_all(self, client_no_auth):
        resp = await client_no_auth.get("/api/settings")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_all_settings_endpoints_require_auth(self, client_no_auth):
        """Batch check: all settings endpoints return 401 without auth."""
        endpoints = [
            ("GET", "/api/settings"),
            ("GET", "/api/settings/email"),
            ("PUT", "/api/settings/email"),
            ("GET", "/api/settings/lead-scoring"),
            ("PUT", "/api/settings/lead-scoring"),
            ("GET", "/api/settings/company_name"),
            ("PUT", "/api/settings/company_name"),
            ("POST", "/api/settings"),
            ("DELETE", "/api/settings/company_name"),
        ]
        for method, url in endpoints:
            if method == "GET":
                resp = await client_no_auth.get(url)
            elif method == "PUT":
                resp = await client_no_auth.put(url, json={"value": "x"})
            elif method == "POST":
                resp = await client_no_auth.post(url, json={"key": "x", "value": "x"})
            elif method == "DELETE":
                resp = await client_no_auth.delete(url)
            assert resp.status_code == 401, f"{method} {url} returned {resp.status_code}, expected 401"

    @pytest.mark.asyncio
    async def test_all_stripe_endpoints_require_auth(self, client_no_auth):
        """Batch check: all stripe endpoints return 401 without auth."""
        endpoints = [
            ("GET", "/api/stripe"),
            ("PUT", "/api/stripe"),
            ("GET", "/api/stripe/test-connection"),
            ("GET", "/api/stripe/products"),
            ("POST", "/api/stripe/products"),
            ("PUT", "/api/stripe/products/1"),
            ("DELETE", "/api/stripe/products/1"),
            ("POST", "/api/stripe/sync"),
        ]
        for method, url in endpoints:
            if method == "GET":
                resp = await client_no_auth.get(url)
            elif method == "PUT":
                resp = await client_no_auth.put(url, json={"mode": "test"})
            elif method == "POST":
                resp = await client_no_auth.post(url, json={"name": "x", "price_cents": 1})
            elif method == "DELETE":
                resp = await client_no_auth.delete(url)
            assert resp.status_code == 401, f"{method} {url} returned {resp.status_code}, expected 401"


# =====================================================================
# TESTS: Edge Cases
# =====================================================================

class TestEdgeCases:
    """Edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_setting_key_with_special_chars(self, client, auth_headers):
        """Test that URL-encoded keys work."""
        db = client._mock_leadgen_db
        db.execute.return_value = FakeResult(items=[])

        resp = await client.get("/api/settings/some-key-with-dashes", headers=auth_headers)
        assert resp.status_code == 404  # Not found is OK — just shouldn't crash

    @pytest.mark.asyncio
    async def test_create_setting_empty_value(self, client, auth_headers):
        db = client._mock_leadgen_db
        db.execute.return_value = FakeResult(items=[])

        async def on_refresh(obj):
            obj.key = "empty_setting"
            obj.value = ""
            obj.category = "general"
            obj.description = None
            obj.is_secret = 0
        db.refresh = AsyncMock(side_effect=on_refresh)

        resp = await client.post(
            "/api/settings",
            json={"key": "empty_setting", "value": ""},
            headers=auth_headers,
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_update_setting_env_sync(self, client, auth_headers):
        """Updating a known API key setting should sync to env."""
        db = client._mock_leadgen_db
        setting = make_fake_setting(
            key="google_maps_api_key", value="old-key", is_secret=1, category="api_keys",
        )
        db.execute.return_value = FakeResult(items=[setting])

        async def on_refresh(obj):
            obj.key = "google_maps_api_key"
            obj.value = "new-api-key-123"
            obj.category = "api_keys"
            obj.description = "Google Maps API Key"
            obj.is_secret = 1
        db.refresh = AsyncMock(side_effect=on_refresh)

        resp = await client.put(
            "/api/settings/google_maps_api_key",
            json={"value": "new-api-key-123"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        # Verify env was updated
        assert os.environ.get("GOOGLE_MAPS_API_KEY") == "new-api-key-123"

    @pytest.mark.asyncio
    async def test_create_product_with_empty_features(self, client, auth_headers):
        product = {
            "id": 5, "name": "Basic", "description": None,
            "price_cents": 5000, "interval": "month", "features": [],
            "is_active": True, "sort_order": 0,
            "stripe_product_id": None, "stripe_price_id": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        with patch("app.api.stripe_settings.stripe_service") as mock_ss, \
             patch("app.api.stripe_settings.leadgen_session") as mock_session_factory:
            mock_ss.create_product.return_value = {
                "stripe_product_id": None,
                "stripe_price_id": None,
            }
            mock_db = AsyncMock()
            mock_db.execute.return_value = FakeResult(mappings_data=[product])
            mock_db.commit = AsyncMock()
            mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

            resp = await client.post(
                "/api/stripe/products",
                json={"name": "Basic", "price_cents": 5000},
                headers=auth_headers,
            )
            assert resp.status_code == 200
            assert resp.json()["features"] == []

    @pytest.mark.asyncio
    async def test_email_test_connection_fail(self, client, auth_headers):
        """Test SMTP connection failure returns 400."""
        with patch("smtplib.SMTP", side_effect=ConnectionRefusedError("Connection refused")):
            resp = await client.post(
                "/api/settings/email/test",
                json={"smtp_host": "bad-host", "smtp_port": "587"},
                headers=auth_headers,
            )
            assert resp.status_code == 400
            assert "Connection failed" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_lead_scoring_empty_value(self, client, auth_headers):
        """Setting with empty value should return defaults."""
        db = client._mock_leadgen_db
        stored = make_fake_setting(key="lead_scoring_config", value="")
        db.execute.return_value = FakeResult(items=[stored])

        resp = await client.get("/api/settings/lead-scoring", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        # Empty value → fall through to defaults
        assert "weights" in data
        assert "thresholds" in data
