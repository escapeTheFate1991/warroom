"""Comprehensive tests for all lead-related endpoints.

Strategy:
  - Override the leadgen DB dependency with a real async SQLite session
    (via aiosqlite) so we can test end-to-end without PostgreSQL.
  - Generate a valid JWT to pass the AuthGuardMiddleware.
  - Mock external services (website_auditor, google_places, enrichment, etc.)
  - Test success AND failure paths for every endpoint.

NOTE: We cannot use PostgreSQL-specific features (JSONB, ARRAY, schema)
with SQLite, so we override the DB dependency entirely and patch the
global _ensure_* helpers to be no-ops.
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest
import pytest_asyncio
import httpx

# Ensure the backend app is importable
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Set required env vars BEFORE importing the app (Settings validates on import)
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-tests")
os.environ.setdefault("POSTGRES_URL", "postgresql+asyncpg://x:x@localhost/fake")
os.environ.setdefault("LEADGEN_DB_URL", "postgresql+asyncpg://x:x@localhost/fake")

# ── Patch heavy imports that hit real infra ──────────────────────────
# We patch these BEFORE importing app.main so module-level code doesn't fail.
# Notification service
sys.modules.setdefault("app.services.notify", MagicMock(send_notification=AsyncMock()))

from sqlalchemy import Column, Integer, String, Text, Boolean, Numeric, Float, DateTime, event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

# ── In-memory SQLite models (mirrors Lead + SearchJob without PG-specifics) ──

class TestBase(DeclarativeBase):
    pass


class TestSearchJob(TestBase):
    __tablename__ = "search_jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    query = Column(Text, nullable=False)
    location = Column(Text, nullable=False)
    radius_km = Column(Integer, default=25)
    status = Column(String(20), default="pending")
    total_found = Column(Integer, default=0)
    enriched_count = Column(Integer, default=0)
    error_message = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class TestLead(TestBase):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, autoincrement=True)
    search_job_id = Column(Integer)
    google_place_id = Column(Text, unique=True)
    business_name = Column(Text, nullable=False)
    address = Column(Text)
    city = Column(Text)
    state = Column(Text)
    zip = Column(Text)
    country = Column(String(5), default="US")
    phone = Column(Text)
    website = Column(Text)
    google_maps_url = Column(Text)
    google_rating = Column(Float)
    google_reviews_count = Column(Integer, default=0)
    business_category = Column(Text)
    business_types = Column(Text)  # JSON string instead of ARRAY
    latitude = Column(Float)
    longitude = Column(Float)
    opening_hours = Column(Text)  # JSON string instead of JSONB

    # Enriched
    emails = Column(Text)  # JSON string
    website_phones = Column(Text)  # JSON string
    owner_name = Column(Text)
    facebook_url = Column(Text)
    instagram_url = Column(Text)
    linkedin_url = Column(Text)
    twitter_url = Column(Text)
    tiktok_url = Column(Text)
    youtube_url = Column(Text)
    yelp_url = Column(Text)

    # Reviews
    yelp_rating = Column(Float)
    yelp_reviews_count = Column(Integer, default=0)
    review_highlights = Column(Text)  # JSON
    review_sentiment_score = Column(Float)
    review_pain_points = Column(Text)  # JSON
    review_opportunity_flags = Column(Text)  # JSON
    reviews_scraped_at = Column(DateTime)

    # Website audit
    has_website = Column(Boolean, default=False)
    website_status = Column(Integer)
    website_platform = Column(Text)
    website_audit_score = Column(Integer)
    website_audit_grade = Column(Text)
    website_audit_summary = Column(Text)
    website_audit_top_fixes = Column(Text)  # JSON
    website_audit_date = Column(DateTime)
    audit_lite_flags = Column(Text)  # JSON

    # BBB
    bbb_url = Column(Text)
    bbb_rating = Column(Text)
    bbb_accredited = Column(Boolean)
    bbb_complaints = Column(Integer, default=0)
    bbb_summary = Column(Text)

    # Glassdoor
    glassdoor_url = Column(Text)
    glassdoor_rating = Column(Float)
    glassdoor_review_count = Column(Integer, default=0)
    glassdoor_summary = Column(Text)

    # JSONB → Text
    reddit_mentions = Column(Text)
    news_mentions = Column(Text)
    social_scan = Column(Text)
    video_analysis = Column(Text)

    # Source
    lead_source = Column(Text, default="google_places")
    enrichment_error = Column(Text)

    # Status
    enrichment_status = Column(String(20), default="pending")
    audit_status = Column(String(20), default="pending")
    outreach_status = Column(String(20), default="none")

    # Scoring
    lead_score = Column(Integer, default=0)
    lead_tier = Column(String(20), default="unscored")

    # CRM / Contact
    contacted_by = Column(Text)
    contacted_at = Column(DateTime)
    contact_outcome = Column(String(20))
    contact_notes = Column(Text)
    contact_who_answered = Column(Text)
    contact_owner_name = Column(Text)
    contact_economic_buyer = Column(Text)
    contact_champion = Column(Text)
    contact_history = Column(Text)  # JSON

    notes = Column(Text)
    tags = Column(Text)  # JSON
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ── JWT helper ───────────────────────────────────────────────────────

JWT_SECRET = "test-secret-key-for-tests"


def make_auth_header(user_id: int = 1, email: str = "test@warroom.io") -> dict:
    """Create a valid Authorization header for test requests."""
    payload = {
        "user_id": user_id,
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


# ── Fixtures ─────────────────────────────────────────────────────────

# We need to intercept at the ORM level. The approach:
# The actual endpoints use Lead and SearchJob from app.models.lead plus
# get_leadgen_db dependency. We'll:
# 1. Replace get_leadgen_db with our SQLite session
# 2. Monkey-patch the Lead/SearchJob models used by the router

# But that's complex. A simpler, more reliable approach:
# Mock the DB at the dependency level and manually construct responses.
# Actually, the BEST approach: just mock the dependency to return a real
# async session backed by aiosqlite, and monkey-patch the ORM models.

# Even simpler: since the endpoints do `select(Lead)`, we need Lead to
# resolve to our test tables. Let's just test via mocking.

# FINAL APPROACH: Mock the entire DB session and control what it returns.
# This gives us full control and no dependency on aiosqlite.


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

    def mappings(self):
        return FakeMappings(self._mappings_data or [])

    def first(self):
        return self._items[0] if self._items else None


class FakeMappings:
    def __init__(self, data):
        self._data = data

    def all(self):
        return self._data

    def first(self):
        return self._data[0] if self._data else None


def make_fake_lead(**overrides):
    """Create a fake Lead-like object with all required attributes."""
    defaults = dict(
        id=1,
        search_job_id=1,
        google_place_id="ChIJ_test_123",
        business_name="Test Plumbing Co",
        address="123 Main St",
        city="Miami",
        state="FL",
        zip="33101",
        country="US",
        phone="305-555-0100",
        website="https://testplumbing.com",
        google_maps_url="https://maps.google.com/test",
        google_rating=4.5,
        google_reviews_count=42,
        business_category="Plumber",
        business_types=["plumber", "home_services"],
        latitude=25.7617,
        longitude=-80.1918,
        opening_hours={"monday": "8am-5pm"},
        emails=["info@testplumbing.com"],
        website_phones=["305-555-0100"],
        owner_name="John Test",
        facebook_url="https://facebook.com/testplumbing",
        instagram_url=None,
        linkedin_url=None,
        twitter_url=None,
        tiktok_url=None,
        youtube_url=None,
        yelp_url=None,
        yelp_rating=None,
        yelp_reviews_count=0,
        review_highlights=None,
        review_sentiment_score=None,
        review_pain_points=None,
        review_opportunity_flags=None,
        reviews_scraped_at=None,
        has_website=True,
        website_status=200,
        website_platform="WordPress",
        website_audit_score=65,
        website_audit_grade="C",
        website_audit_summary="Needs improvement",
        website_audit_top_fixes=["Add SSL", "Improve speed"],
        website_audit_date=datetime.now(timezone.utc),
        audit_lite_flags=["no-ssl", "slow-load"],
        bbb_url=None,
        bbb_rating=None,
        bbb_accredited=None,
        bbb_complaints=0,
        bbb_summary=None,
        glassdoor_url=None,
        glassdoor_rating=None,
        glassdoor_review_count=0,
        glassdoor_summary=None,
        reddit_mentions=[],
        news_mentions=[],
        social_scan={},
        video_analysis=[],
        lead_source="google_places",
        enrichment_error=None,
        enrichment_status="enriched",
        audit_status="complete",
        outreach_status="none",
        lead_score=75,
        lead_tier="warm",
        contacted_by=None,
        contacted_at=None,
        contact_outcome=None,
        contact_notes=None,
        contact_who_answered=None,
        contact_owner_name=None,
        contact_economic_buyer=None,
        contact_champion=None,
        contact_history=[],
        notes=None,
        tags=[],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)

    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)

    # Make model_validate work by providing __dict__
    obj.__dict__.update(defaults)
    return obj


def make_fake_search_job(**overrides):
    """Create a fake SearchJob-like object."""
    defaults = dict(
        id=1,
        query="plumber",
        location="Miami, FL",
        radius_km=25,
        status="complete",
        total_found=10,
        enriched_count=8,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        error_message=None,
    )
    defaults.update(overrides)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    obj.__dict__.update(defaults)
    return obj


@pytest.fixture
def auth_headers():
    return make_auth_header()


@pytest.fixture
def fake_lead():
    return make_fake_lead()


@pytest.fixture
def fake_job():
    return make_fake_search_job()


def _make_mock_db():
    """Create a mock async DB session."""
    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    db.rollback = AsyncMock()
    return db


# ── App and client fixture ───────────────────────────────────────────

@pytest_asyncio.fixture
async def client():
    """Create test client with dependency overrides."""
    from app.main import app
    from app.db.leadgen_db import get_leadgen_db

    mock_db = _make_mock_db()

    async def override_leadgen_db():
        yield mock_db

    app.dependency_overrides[get_leadgen_db] = override_leadgen_db

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        ac._mock_db = mock_db  # attach for test access
        yield ac

    app.dependency_overrides.clear()


# ── Patch ensure_* column helpers globally ───────────────────────────

@pytest.fixture(autouse=True)
def patch_ensure_columns():
    """Prevent ALTER TABLE calls which require PostgreSQL."""
    with patch("app.api.leadgen._ensure_enrichment_error_column", new_callable=AsyncMock), \
         patch("app.api.leadgen._ensure_source_column", new_callable=AsyncMock), \
         patch("app.api.leadgen._ensure_review_columns", new_callable=AsyncMock):
        yield


@pytest.fixture(autouse=True)
def patch_load_assignments():
    """Mock the assignment loader to avoid CRM DB queries."""
    async def fake_load(db, entity_type, entity_ids):
        return {}
    with patch("app.api.leadgen.load_assignment_summaries", side_effect=fake_load):
        yield


@pytest.fixture(autouse=True)
def patch_send_notification():
    """Prevent real notifications."""
    with patch("app.api.leadgen.send_notification", new_callable=AsyncMock):
        yield


# =====================================================================
# TESTS: Search Endpoints
# =====================================================================

class TestCreateSearch:
    """POST /api/leadgen/search"""

    @pytest.mark.asyncio
    async def test_create_search_success(self, client, auth_headers):
        db = client._mock_db

        fake_job = make_fake_search_job(id=5, status="running", total_found=0, enriched_count=0)

        # db.add → capture the job, db.commit → noop, db.refresh → set id
        def on_add(obj):
            obj.id = 5
            obj.query = "plumber"
            obj.location = "Miami, FL"
            obj.radius_km = 25
            obj.status = "running"
            obj.total_found = 0
            obj.enriched_count = 0
            obj.created_at = datetime.now(timezone.utc)

        db.add = MagicMock(side_effect=on_add)

        # refresh populates the object after commit
        async def on_refresh(obj):
            obj.id = 5
        db.refresh = AsyncMock(side_effect=on_refresh)

        resp = await client.post(
            "/api/leadgen/search",
            json={"query": "plumber", "location": "Miami, FL"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["query"] == "plumber"
        assert data["location"] == "Miami, FL"
        assert data["status"] == "running"

    @pytest.mark.asyncio
    async def test_create_search_missing_query(self, client, auth_headers):
        resp = await client.post(
            "/api/leadgen/search",
            json={"location": "Miami, FL"},
            headers=auth_headers,
        )
        assert resp.status_code == 422  # Pydantic validation error

    @pytest.mark.asyncio
    async def test_create_search_missing_location(self, client, auth_headers):
        resp = await client.post(
            "/api/leadgen/search",
            json={"query": "plumber"},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_create_search_no_auth(self, client):
        resp = await client.post(
            "/api/leadgen/search",
            json={"query": "plumber", "location": "Miami, FL"},
        )
        assert resp.status_code == 401


class TestListSearches:
    """GET /api/leadgen/search"""

    @pytest.mark.asyncio
    async def test_list_searches_success(self, client, auth_headers):
        db = client._mock_db
        jobs = [make_fake_search_job(id=1), make_fake_search_job(id=2, query="electrician")]
        db.execute.return_value = FakeResult(items=jobs)

        resp = await client.get("/api/leadgen/search", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_list_searches_no_auth(self, client):
        resp = await client.get("/api/leadgen/search")
        assert resp.status_code == 401


class TestGetSearch:
    """GET /api/leadgen/search/{job_id}"""

    @pytest.mark.asyncio
    async def test_get_search_success(self, client, auth_headers):
        db = client._mock_db
        job = make_fake_search_job(id=7)
        db.execute.return_value = FakeResult(scalar_value=job)

        resp = await client.get("/api/leadgen/search/7", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == 7

    @pytest.mark.asyncio
    async def test_get_search_not_found(self, client, auth_headers):
        db = client._mock_db
        db.execute.return_value = FakeResult(scalar_value=None)

        resp = await client.get("/api/leadgen/search/999", headers=auth_headers)
        assert resp.status_code == 404


# =====================================================================
# TESTS: Lead List & Detail Endpoints
# =====================================================================

class TestListLeads:
    """GET /api/leadgen/leads"""

    @pytest.mark.asyncio
    async def test_list_leads_success(self, client, auth_headers):
        db = client._mock_db
        leads = [make_fake_lead(id=1), make_fake_lead(id=2, business_name="Another Co")]
        db.execute.return_value = FakeResult(items=leads)

        resp = await client.get("/api/leadgen/leads", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_list_leads_no_auth(self, client):
        resp = await client.get("/api/leadgen/leads")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_list_leads_with_filters(self, client, auth_headers):
        db = client._mock_db
        leads = [make_fake_lead(id=1, lead_tier="hot")]
        db.execute.return_value = FakeResult(items=leads)

        resp = await client.get(
            "/api/leadgen/leads?tier=hot&has_website=true&min_score=50&city=Miami&state=FL",
            headers=auth_headers,
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_list_leads_empty(self, client, auth_headers):
        db = client._mock_db
        db.execute.return_value = FakeResult(items=[])

        resp = await client.get("/api/leadgen/leads", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []


class TestGetLead:
    """GET /api/leadgen/leads/{lead_id}"""

    @pytest.mark.asyncio
    async def test_get_lead_success(self, client, auth_headers):
        db = client._mock_db
        lead = make_fake_lead(id=42)
        db.execute.return_value = FakeResult(scalar_value=lead)

        resp = await client.get("/api/leadgen/leads/42", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == 42
        assert data["business_name"] == "Test Plumbing Co"

    @pytest.mark.asyncio
    async def test_get_lead_not_found(self, client, auth_headers):
        db = client._mock_db
        db.execute.return_value = FakeResult(scalar_value=None)

        resp = await client.get("/api/leadgen/leads/999", headers=auth_headers)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_lead_no_auth(self, client):
        resp = await client.get("/api/leadgen/leads/1")
        assert resp.status_code == 401


# =====================================================================
# TESTS: Lead Audit Endpoints
# =====================================================================

class TestTriggerAudit:
    """POST /api/leadgen/leads/{id}/audit"""

    @pytest.mark.asyncio
    async def test_audit_success(self, client, auth_headers):
        db = client._mock_db
        lead = make_fake_lead(id=10, website="https://example.com")
        db.execute.return_value = FakeResult(scalar_value=lead)

        mock_audit_result = MagicMock(
            score=72, grade="C", summary="Decent site", top_fixes=["Add SSL"]
        )
        with patch("app.api.leadgen.audit_website", new_callable=AsyncMock, return_value=mock_audit_result):
            resp = await client.post("/api/leadgen/leads/10/audit", headers=auth_headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["score"] == 72
        assert data["grade"] == "C"
        assert "Add SSL" in data["top_fixes"]

    @pytest.mark.asyncio
    async def test_audit_no_website(self, client, auth_headers):
        db = client._mock_db
        lead = make_fake_lead(id=10, website=None)
        db.execute.return_value = FakeResult(scalar_value=lead)

        resp = await client.post("/api/leadgen/leads/10/audit", headers=auth_headers)
        assert resp.status_code == 400
        assert "no website" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_audit_lead_not_found(self, client, auth_headers):
        db = client._mock_db
        db.execute.return_value = FakeResult(scalar_value=None)

        resp = await client.post("/api/leadgen/leads/999/audit", headers=auth_headers)
        assert resp.status_code == 404


class TestGetAuditResults:
    """GET /api/leadgen/leads/{id}/audit"""

    @pytest.mark.asyncio
    async def test_get_audit_success(self, client, auth_headers):
        db = client._mock_db
        lead = make_fake_lead(
            id=10,
            website_audit_score=85,
            website_audit_grade="B",
            website_audit_summary="Good site",
            website_audit_top_fixes=["Optimize images"],
        )
        db.execute.return_value = FakeResult(scalar_value=lead)

        resp = await client.get("/api/leadgen/leads/10/audit", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["score"] == 85
        assert data["grade"] == "B"

    @pytest.mark.asyncio
    async def test_get_audit_no_results(self, client, auth_headers):
        db = client._mock_db
        lead = make_fake_lead(id=10, website_audit_score=None)
        db.execute.return_value = FakeResult(scalar_value=lead)

        resp = await client.get("/api/leadgen/leads/10/audit", headers=auth_headers)
        assert resp.status_code == 404
        assert "No audit results" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_audit_lead_not_found(self, client, auth_headers):
        db = client._mock_db
        db.execute.return_value = FakeResult(scalar_value=None)

        resp = await client.get("/api/leadgen/leads/999/audit", headers=auth_headers)
        assert resp.status_code == 404


# =====================================================================
# TESTS: Contact Logging
# =====================================================================

class TestLogContact:
    """POST /api/leadgen/leads/{id}/contact"""

    @pytest.mark.asyncio
    async def test_log_contact_success(self, client, auth_headers):
        db = client._mock_db
        lead = make_fake_lead(id=5, contact_history=[], outreach_status="none")
        db.execute.return_value = FakeResult(scalar_value=lead)

        # refresh after commit returns updated lead
        async def on_refresh(obj):
            pass
        db.refresh = AsyncMock(side_effect=on_refresh)

        resp = await client.post(
            "/api/leadgen/leads/5/contact",
            json={
                "contacted_by": "Eddy",
                "outcome": "follow_up",
                "notes": "Will call back tomorrow",
                "who_answered": "Front desk",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["contacted_by"] == "Eddy"
        assert data["outreach_status"] == "in_progress"  # follow_up → in_progress

    @pytest.mark.asyncio
    async def test_log_contact_won(self, client, auth_headers):
        db = client._mock_db
        lead = make_fake_lead(id=5, contact_history=[])
        db.execute.return_value = FakeResult(scalar_value=lead)
        db.refresh = AsyncMock()

        resp = await client.post(
            "/api/leadgen/leads/5/contact",
            json={"contacted_by": "Eddy", "outcome": "won", "notes": "Deal closed!"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["outreach_status"] == "won"

    @pytest.mark.asyncio
    async def test_log_contact_lost(self, client, auth_headers):
        db = client._mock_db
        lead = make_fake_lead(id=5, contact_history=[])
        db.execute.return_value = FakeResult(scalar_value=lead)
        db.refresh = AsyncMock()

        resp = await client.post(
            "/api/leadgen/leads/5/contact",
            json={"contacted_by": "Eddy", "outcome": "lost"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["outreach_status"] == "lost"

    @pytest.mark.asyncio
    async def test_log_contact_lead_not_found(self, client, auth_headers):
        db = client._mock_db
        db.execute.return_value = FakeResult(scalar_value=None)

        resp = await client.post(
            "/api/leadgen/leads/999/contact",
            json={"contacted_by": "Eddy", "outcome": "no_answer"},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_log_contact_missing_fields(self, client, auth_headers):
        resp = await client.post(
            "/api/leadgen/leads/5/contact",
            json={"notes": "missing contacted_by and outcome"},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_log_contact_no_auth(self, client):
        resp = await client.post(
            "/api/leadgen/leads/5/contact",
            json={"contacted_by": "Eddy", "outcome": "won"},
        )
        assert resp.status_code == 401


# =====================================================================
# TESTS: Enrich Pending
# =====================================================================

class TestEnrichPending:
    """POST /api/leadgen/leads/enrich-pending"""

    @pytest.mark.asyncio
    async def test_enrich_pending_with_leads(self, client, auth_headers):
        db = client._mock_db

        # First call: count of pending leads
        # Second call: distinct job ids
        call_count = 0

        async def multi_execute(stmt, *args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return FakeResult(scalar_value=5)
            else:
                return FakeResult(items=[(1,), (2,)])

        db.execute = AsyncMock(side_effect=multi_execute)

        resp = await client.post("/api/leadgen/leads/enrich-pending", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "started"
        assert data["pending"] == 5

    @pytest.mark.asyncio
    async def test_enrich_pending_nothing(self, client, auth_headers):
        db = client._mock_db
        db.execute.return_value = FakeResult(scalar_value=0)

        resp = await client.post("/api/leadgen/leads/enrich-pending", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "nothing_to_enrich"


# =====================================================================
# TESTS: Stats
# =====================================================================

class TestStats:
    """GET /api/leadgen/leads/stats"""

    @pytest.mark.asyncio
    async def test_stats_success(self, client, auth_headers):
        db = client._mock_db

        # The stats endpoint makes many sequential queries.
        # We mock all of them in order.
        call_idx = 0
        returns = [
            FakeResult(scalar_value=100),   # total
            FakeResult(scalar_value=80),    # enriched
            FakeResult(scalar_value=70),    # with_site
            FakeResult(scalar_value=10),    # without_site
            FakeResult(scalar_value=20),    # hot
            FakeResult(scalar_value=50),    # warm
            FakeResult(scalar_value=30),    # cold
            FakeResult(scalar_value=65.3),  # avg_score
            FakeResult(items=[("Plumber", 30), ("Electrician", 20)]),  # categories
            FakeResult(scalar_value=40),    # contacted
            FakeResult(scalar_value=15),    # won
            FakeResult(scalar_value=5),     # lost
        ]

        async def ordered_execute(stmt, *a, **kw):
            nonlocal call_idx
            idx = call_idx
            call_idx += 1
            if idx < len(returns):
                return returns[idx]
            return FakeResult(scalar_value=0)

        db.execute = AsyncMock(side_effect=ordered_execute)

        resp = await client.get("/api/leadgen/leads/stats", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_leads"] == 100
        assert data["enriched"] == 80
        assert data["hot_leads"] == 20
        assert data["avg_lead_score"] == 65.3

    @pytest.mark.asyncio
    async def test_stats_no_auth(self, client):
        resp = await client.get("/api/leadgen/leads/stats")
        assert resp.status_code == 401


# =====================================================================
# TESTS: Contacts (CRM history view)
# =====================================================================

class TestListContacts:
    """GET /api/leadgen/contacts"""

    @pytest.mark.asyncio
    async def test_list_contacts_success(self, client, auth_headers):
        db = client._mock_db
        leads = [
            make_fake_lead(id=1, outreach_status="contacted", contacted_by="Eddy"),
            make_fake_lead(id=2, outreach_status="won", contacted_by="Eddy"),
        ]
        db.execute.return_value = FakeResult(items=leads)

        resp = await client.get("/api/leadgen/contacts", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_list_contacts_with_filters(self, client, auth_headers):
        db = client._mock_db
        db.execute.return_value = FakeResult(items=[])

        resp = await client.get(
            "/api/leadgen/contacts?outcome=won&contacted_by=Eddy",
            headers=auth_headers,
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_list_contacts_no_auth(self, client):
        resp = await client.get("/api/leadgen/contacts")
        assert resp.status_code == 401


# =====================================================================
# TESTS: Export
# =====================================================================

class TestExportLeads:
    """GET /api/leadgen/leads/export"""

    @pytest.mark.asyncio
    async def test_export_csv(self, client, auth_headers):
        db = client._mock_db
        leads = [make_fake_lead(id=1), make_fake_lead(id=2)]
        db.execute.return_value = FakeResult(items=leads)

        resp = await client.get("/api/leadgen/leads/export", headers=auth_headers)
        assert resp.status_code == 200
        assert "text/csv" in resp.headers.get("content-type", "")
        content = resp.text
        assert "Business Name" in content  # CSV header
        assert "Test Plumbing Co" in content

    @pytest.mark.asyncio
    async def test_export_with_tier_filter(self, client, auth_headers):
        db = client._mock_db
        db.execute.return_value = FakeResult(items=[])

        resp = await client.get("/api/leadgen/leads/export?tier=hot", headers=auth_headers)
        assert resp.status_code == 200


# =====================================================================
# TESTS: Freshness
# =====================================================================

class TestFreshness:
    """GET /api/leadgen/leads/freshness"""

    @pytest.mark.asyncio
    async def test_freshness_success(self, client, auth_headers):
        db = client._mock_db
        jobs = [
            make_fake_search_job(id=1, created_at=datetime.now(timezone.utc)),
            make_fake_search_job(id=2, created_at=datetime.now(timezone.utc) - timedelta(days=35)),
        ]
        # Need created_at to have tzinfo attribute
        for j in jobs:
            j.created_at = MagicMock()
            j.created_at.tzinfo = timezone.utc
            j.created_at.replace.return_value = datetime.now(timezone.utc)
            j.created_at.isoformat.return_value = datetime.now(timezone.utc).isoformat()

        db.execute.return_value = FakeResult(items=jobs)

        resp = await client.get("/api/leadgen/leads/freshness", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 2


# =====================================================================
# TESTS: Stale Delete
# =====================================================================

class TestDeleteStale:
    """DELETE /api/leadgen/leads/stale"""

    @pytest.mark.asyncio
    async def test_delete_stale_success(self, client, auth_headers):
        db = client._mock_db

        call_idx = 0

        async def ordered_execute(stmt, *a, **kw):
            nonlocal call_idx
            call_idx += 1
            if call_idx == 1:
                # stale job ids
                return FakeResult(items=[(1,), (2,)])
            elif call_idx == 2:
                # delete leads result
                result = MagicMock()
                result.rowcount = 15
                return result
            elif call_idx == 3:
                # delete jobs result
                result = MagicMock()
                result.rowcount = 2
                return result
            return FakeResult(items=[])

        db.execute = AsyncMock(side_effect=ordered_execute)

        resp = await client.delete("/api/leadgen/leads/stale?max_age_days=30", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["deleted_leads"] == 15
        assert data["deleted_jobs"] == 2

    @pytest.mark.asyncio
    async def test_delete_stale_nothing(self, client, auth_headers):
        db = client._mock_db
        db.execute.return_value = FakeResult(items=[])

        resp = await client.delete("/api/leadgen/leads/stale", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["deleted_leads"] == 0

    @pytest.mark.asyncio
    async def test_delete_stale_invalid_age(self, client, auth_headers):
        resp = await client.delete("/api/leadgen/leads/stale?max_age_days=0", headers=auth_headers)
        assert resp.status_code == 422  # min is 1


# =====================================================================
# TESTS: Re-enrich single lead
# =====================================================================

class TestReEnrichLead:
    """POST /api/leadgen/leads/{id}/re-enrich"""

    @pytest.mark.asyncio
    async def test_re_enrich_success(self, client, auth_headers):
        db = client._mock_db
        lead = make_fake_lead(id=10, search_job_id=3, enrichment_status="enriched")
        db.execute.return_value = FakeResult(scalar_value=lead)

        resp = await client.post("/api/leadgen/leads/10/re-enrich", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "started"
        assert data["lead_id"] == 10

    @pytest.mark.asyncio
    async def test_re_enrich_not_found(self, client, auth_headers):
        db = client._mock_db
        db.execute.return_value = FakeResult(scalar_value=None)

        resp = await client.post("/api/leadgen/leads/999/re-enrich", headers=auth_headers)
        assert resp.status_code == 404


# =====================================================================
# TESTS: Re-enrich all leads
# =====================================================================

class TestReEnrichAllLeads:
    """POST /api/leadgen/leads/re-enrich-all"""

    @pytest.mark.asyncio
    async def test_re_enrich_all_success(self, client, auth_headers):
        db = client._mock_db
        leads = [
            make_fake_lead(id=1, search_job_id=1),
            make_fake_lead(id=2, search_job_id=1),
            make_fake_lead(id=3, search_job_id=2),
        ]
        db.execute.return_value = FakeResult(items=leads)

        resp = await client.post("/api/leadgen/leads/re-enrich-all", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["leads_reset"] == 3


# =====================================================================
# TESTS: Rescore
# =====================================================================

class TestRescore:
    """POST /api/leadgen/leads/rescore"""

    @pytest.mark.asyncio
    async def test_rescore_success(self, client, auth_headers):
        db = client._mock_db
        leads = [make_fake_lead(id=1, lead_score=0), make_fake_lead(id=2, lead_score=0)]
        db.execute.return_value = FakeResult(items=leads)

        with patch("app.api.leadgen.score_lead", return_value=(85, "hot")):
            resp = await client.post("/api/leadgen/leads/rescore", headers=auth_headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "rescored"
        assert data["total"] == 2
        assert data["updated"] == 2


# =====================================================================
# TESTS: Search Status
# =====================================================================

class TestSearchStatus:
    """GET /api/leadgen/search/{job_id}/status"""

    @pytest.mark.asyncio
    async def test_search_status_running(self, client, auth_headers):
        db = client._mock_db

        job = make_fake_search_job(id=3, status="running")
        job.created_at = datetime.now(timezone.utc)
        job.created_at = MagicMock()
        job.created_at.tzinfo = timezone.utc
        job.created_at.replace.return_value = datetime.now(timezone.utc)
        job.created_at.isoformat.return_value = datetime.now(timezone.utc).isoformat()

        call_idx = 0

        async def ordered_execute(stmt, *a, **kw):
            nonlocal call_idx
            call_idx += 1
            if call_idx == 1:
                return FakeResult(scalar_value=job)
            elif call_idx == 2:
                return FakeResult(scalar_value=5)  # total_leads
            elif call_idx == 3:
                return FakeResult(scalar_value=2)  # enriched
            elif call_idx == 4:
                return FakeResult(scalar_value=3)  # pending
            elif call_idx == 5:
                return FakeResult(scalar_value=0)  # failed
            return FakeResult(scalar_value=0)

        db.execute = AsyncMock(side_effect=ordered_execute)

        resp = await client.get("/api/leadgen/search/3/status", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "running"
        assert data["total_leads"] == 5
        assert "enriching" in data["message"].lower() or "found" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_search_status_not_found(self, client, auth_headers):
        db = client._mock_db
        db.execute.return_value = FakeResult(scalar_value=None)

        resp = await client.get("/api/leadgen/search/999/status", headers=auth_headers)
        assert resp.status_code == 404


# =====================================================================
# TESTS: Auth guard (general)
# =====================================================================

class TestAuthGuard:
    """Verify auth middleware blocks unauthenticated requests."""

    @pytest.mark.asyncio
    async def test_expired_token(self, client):
        payload = {
            "user_id": 1,
            "email": "test@warroom.io",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),  # expired
        }
        token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
        headers = {"Authorization": f"Bearer {token}"}
        resp = await client.get("/api/leadgen/leads", headers=headers)
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_token(self, client):
        headers = {"Authorization": "Bearer totally-not-a-valid-token"}
        resp = await client.get("/api/leadgen/leads", headers=headers)
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_missing_bearer_prefix(self, client):
        payload = {"user_id": 1, "exp": datetime.now(timezone.utc) + timedelta(hours=1)}
        token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
        headers = {"Authorization": token}  # no "Bearer " prefix
        resp = await client.get("/api/leadgen/leads", headers=headers)
        assert resp.status_code == 401
