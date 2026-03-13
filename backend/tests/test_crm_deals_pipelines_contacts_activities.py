"""Comprehensive tests for CRM Deals, Pipelines, Contacts, and Activities."""

import os, sys, json
from datetime import datetime, timezone, timedelta, date
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import jwt, pytest, pytest_asyncio, httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-tests")
os.environ.setdefault("POSTGRES_URL", "postgresql+asyncpg://x:x@localhost/fake")
os.environ.setdefault("LEADGEN_DB_URL", "postgresql+asyncpg://x:x@localhost/fake")
sys.modules.setdefault("app.services.notify", MagicMock(send_notification=AsyncMock()))

from sqlalchemy.ext.asyncio import AsyncSession

JWT_SECRET = "test-secret-key-for-tests"
NOW = datetime.now(timezone.utc)


class FakeResult:
    def __init__(self, items=None, scalar_value=None):
        self._items = items or []
        self._scalar_value = scalar_value
    def scalars(self): return self
    def all(self): return self._items
    def scalar_one_or_none(self): return self._scalar_value
    def scalar(self): return self._scalar_value
    def first(self): return self._items[0] if self._items else None
    def fetchall(self): return self._items
    def mappings(self): return self


def auth_hdr(**kw):
    p = {"user_id": 1, "email": "t@t.io", "is_superadmin": True,
         "exp": datetime.now(timezone.utc) + timedelta(hours=1)}
    p.update(kw)
    return {"Authorization": f"Bearer {jwt.encode(p, JWT_SECRET, algorithm='HS256')}"}


def _mk(**a):
    o = MagicMock()
    for k, v in a.items():
        setattr(o, k, v)
    return o


def _populate_defaults(obj):
    """Simulate db.refresh() by setting server-generated fields."""
    if not hasattr(obj, 'id') or getattr(obj, 'id', None) is None:
        obj.id = 1
    if not hasattr(obj, 'created_at') or getattr(obj, 'created_at', None) is None:
        obj.created_at = NOW
    if not hasattr(obj, 'updated_at') or getattr(obj, 'updated_at', None) is None:
        obj.updated_at = NOW
    # Column defaults that are set by DB, not Python
    if hasattr(obj, 'is_done') and getattr(obj, 'is_done', None) is None:
        obj.is_done = False
    if hasattr(obj, 'is_default') and getattr(obj, 'is_default', None) is None:
        obj.is_default = False
    if hasattr(obj, 'rotten_days') and getattr(obj, 'rotten_days', None) is None:
        obj.rotten_days = 30


def _mock_db():
    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock(return_value=FakeResult())
    db.commit = AsyncMock()
    db.refresh = AsyncMock(side_effect=_populate_defaults)
    db.add = MagicMock()
    db.flush = AsyncMock()
    return db


def fake_deal(**ov):
    d = dict(id=1, title="Test Deal", description="desc",
             deal_value=Decimal("5000"), status=None, lost_reason=None,
             expected_close_date=date(2026, 6, 1), closed_at=None,
             user_id=1, person_id=1, organization_id=1,
             source_id=None, type_id=None, pipeline_id=1, stage_id=1,
             leadgen_lead_id=None, deal_metadata={},
             created_at=NOW, updated_at=NOW,
             user=None, person=None, organization=None,
             source=None, type=None, pipeline=None, stage=None)
    d.update(ov)
    return _mk(**d)


def fake_pipeline(**ov):
    d = dict(id=1, name="Sales Pipeline", is_default=True,
             rotten_days=30, created_at=NOW, updated_at=NOW, stages=[])
    d.update(ov)
    return _mk(**d)


def fake_stage(**ov):
    d = dict(id=1, code="lead", name="Lead", probability=10,
             sort_order=0, pipeline_id=1)
    d.update(ov)
    return _mk(**d)


def fake_person(**ov):
    d = dict(id=1, name="John Doe",
             emails=[{"value": "j@e.com", "label": "work"}],
             email_addresses=[{"value": "j@e.com", "label": "work"}],
             contact_numbers=[{"value": "555-1234", "label": "mobile"}],
             job_title="CEO", organization_id=1, user_id=1,
             activities=[],
             agent_assignments=[],
             created_at=NOW, updated_at=NOW)
    d.update(ov)
    return _mk(**d)


def fake_org(**ov):
    d = dict(id=1, name="Acme Corp",
             address={"street": "123 Main", "city": "Atlanta", "state": "GA"},
             emails=[{"value": "hello@acme.com", "label": "work"}],
             contact_numbers=[{"value": "555-5555", "label": "main"}],
             user_id=1, leadgen_lead_id=None, created_at=NOW, updated_at=NOW)
    d.update(ov)
    return _mk(**d)


def fake_activity(**ov):
    d = dict(id=1, title="Follow-up", type="call", comment="Discuss",
             additional=None, location=None, schedule_from=NOW,
             schedule_to=NOW + timedelta(hours=1), is_done=False,
             user_id=1, created_at=NOW, updated_at=NOW, participants=[])
    d.update(ov)
    return _mk(**d)


@pytest_asyncio.fixture
async def client():
    from app.main import app
    from app.db.crm_db import get_crm_db
    from app.api.auth import get_current_user
    mdb = _mock_db()
    fu = _mk(id=1, email="t@t.io", name="Test", is_superadmin=True,
             status=True, org=None, role=None,
             has_permission=MagicMock(return_value=True))
    async def ov_db():
        yield mdb
    async def ov_user():
        return fu
    app.dependency_overrides[get_crm_db] = ov_db
    app.dependency_overrides[get_current_user] = ov_user
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        ac._db = mdb
        ac._user = fu
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
def hdr():
    return auth_hdr()


# =====================================================================
# DEALS
# =====================================================================

class TestListDeals:
    @pytest.mark.asyncio
    async def test_list_deals_empty(self, client, hdr):
        client._db.execute = AsyncMock(return_value=FakeResult(items=[]))
        with patch("app.api.crm.deals.load_assignment_summaries", new_callable=AsyncMock, return_value={}):
            r = await client.get("/api/crm/deals", headers=hdr)
        assert r.status_code == 200
        assert r.json() == []

    @pytest.mark.asyncio
    async def test_list_deals_returns_items(self, client, hdr):
        deal = fake_deal()
        client._db.execute = AsyncMock(return_value=FakeResult(items=[deal]))
        with patch("app.api.crm.deals.load_assignment_summaries", new_callable=AsyncMock, return_value={}):
            r = await client.get("/api/crm/deals", headers=hdr)
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 1
        assert data[0]["title"] == "Test Deal"

    @pytest.mark.asyncio
    async def test_list_deals_with_filters(self, client, hdr):
        client._db.execute = AsyncMock(return_value=FakeResult(items=[]))
        with patch("app.api.crm.deals.load_assignment_summaries", new_callable=AsyncMock, return_value={}):
            r = await client.get("/api/crm/deals?pipeline_id=1&status=open&limit=10", headers=hdr)
        assert r.status_code == 200


class TestGetDeal:
    @pytest.mark.asyncio
    async def test_get_deal_success(self, client, hdr):
        deal = fake_deal()
        client._db.execute = AsyncMock(return_value=FakeResult(scalar_value=deal))
        with patch("app.api.crm.deals.load_assignment_summaries", new_callable=AsyncMock, return_value={}):
            r = await client.get("/api/crm/deals/1", headers=hdr)
        assert r.status_code == 200
        assert r.json()["id"] == 1

    @pytest.mark.asyncio
    async def test_get_deal_not_found(self, client, hdr):
        client._db.execute = AsyncMock(return_value=FakeResult(scalar_value=None))
        r = await client.get("/api/crm/deals/999", headers=hdr)
        assert r.status_code == 404


class TestCreateDeal:
    @pytest.mark.asyncio
    async def test_create_deal_success(self, client, hdr):
        deal = fake_deal()
        client._db.execute = AsyncMock(side_effect=[
            FakeResult(scalar_value=fake_pipeline()),   # default pipeline
            FakeResult(scalar_value=fake_stage()),       # first stage
            FakeResult(scalar_value=deal),               # load_deal_with_related
        ])
        client._db.refresh = AsyncMock(side_effect=lambda obj: setattr(obj, 'id', 1))
        with patch("app.services.workflow_triggers.fire_triggers_background"), \
             patch("app.api.crm.deals.load_assignment_summaries", new_callable=AsyncMock, return_value={}):
            r = await client.post("/api/crm/deals", headers=hdr,
                                  json={"title": "New Deal", "deal_value": "5000"})
        assert r.status_code in (200, 201)

    @pytest.mark.asyncio
    async def test_create_deal_missing_title(self, client, hdr):
        r = await client.post("/api/crm/deals", headers=hdr, json={"deal_value": "1000"})
        assert r.status_code == 422


class TestUpdateDeal:
    @pytest.mark.asyncio
    async def test_update_deal_success(self, client, hdr):
        deal = fake_deal()
        client._db.execute = AsyncMock(side_effect=[
            FakeResult(scalar_value=deal),   # select deal
            FakeResult(scalar_value=deal),   # load_deal_with_related
        ])
        with patch("app.services.workflow_triggers.fire_triggers_background"), \
             patch("app.api.crm.deals.load_assignment_summaries", new_callable=AsyncMock, return_value={}):
            r = await client.put("/api/crm/deals/1", headers=hdr,
                                 json={"title": "Updated Deal"})
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_update_deal_not_found(self, client, hdr):
        client._db.execute = AsyncMock(return_value=FakeResult(scalar_value=None))
        r = await client.put("/api/crm/deals/999", headers=hdr, json={"title": "X"})
        assert r.status_code == 404


class TestDeleteDeal:
    @pytest.mark.asyncio
    async def test_delete_deal_success(self, client, hdr):
        deal = fake_deal()
        client._db.execute = AsyncMock(side_effect=[
            FakeResult(scalar_value=deal),  # select
            FakeResult(),                   # delete
        ])
        r = await client.delete("/api/crm/deals/1", headers=hdr)
        assert r.status_code == 200
        assert r.json()["status"] == "deleted"

    @pytest.mark.asyncio
    async def test_delete_deal_not_found(self, client, hdr):
        client._db.execute = AsyncMock(return_value=FakeResult(scalar_value=None))
        r = await client.delete("/api/crm/deals/999", headers=hdr)
        assert r.status_code == 404


class TestMoveDealStage:
    @pytest.mark.asyncio
    async def test_move_stage_success(self, client, hdr):
        deal = fake_deal()
        new_stage = fake_stage(id=2, code="proposal", name="Proposal", pipeline_id=1)
        client._db.execute = AsyncMock(side_effect=[
            FakeResult(scalar_value=deal),       # select deal
            FakeResult(scalar_value=new_stage),  # select stage
            FakeResult(scalar_value=deal),       # load_deal_with_related (after refresh)
        ])
        with patch("app.services.workflow_triggers.fire_triggers_background"), \
             patch("app.services.lead_deal_sync.sync_lead_from_deal", new_callable=AsyncMock), \
             patch("app.api.crm.deals.load_assignment_summaries", new_callable=AsyncMock, return_value={}):
            r = await client.put("/api/crm/deals/1/stage", headers=hdr,
                                 json={"stage_id": 2})
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_move_stage_not_found(self, client, hdr):
        client._db.execute = AsyncMock(return_value=FakeResult(scalar_value=None))
        r = await client.put("/api/crm/deals/999/stage", headers=hdr, json={"stage_id": 2})
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_move_stage_wrong_pipeline(self, client, hdr):
        deal = fake_deal(pipeline_id=1)
        bad_stage = fake_stage(id=5, pipeline_id=99)
        client._db.execute = AsyncMock(side_effect=[
            FakeResult(scalar_value=deal),
            FakeResult(scalar_value=bad_stage),
        ])
        r = await client.put("/api/crm/deals/1/stage", headers=hdr, json={"stage_id": 5})
        assert r.status_code == 400


# =====================================================================
# PIPELINES
# =====================================================================

class TestListPipelines:
    @pytest.mark.asyncio
    async def test_list_pipelines(self, client, hdr):
        p = fake_pipeline()
        client._db.execute = AsyncMock(return_value=FakeResult(items=[p]))
        r = await client.get("/api/crm/pipelines", headers=hdr)
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_list_pipelines_empty(self, client, hdr):
        client._db.execute = AsyncMock(return_value=FakeResult(items=[]))
        r = await client.get("/api/crm/pipelines", headers=hdr)
        assert r.status_code == 200
        assert r.json() == []


class TestGetPipeline:
    @pytest.mark.asyncio
    async def test_get_pipeline_success(self, client, hdr):
        p = fake_pipeline(stages=[fake_stage()])
        client._db.execute = AsyncMock(return_value=FakeResult(scalar_value=p))
        r = await client.get("/api/crm/pipelines/1", headers=hdr)
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_get_pipeline_not_found(self, client, hdr):
        client._db.execute = AsyncMock(return_value=FakeResult(scalar_value=None))
        r = await client.get("/api/crm/pipelines/999", headers=hdr)
        assert r.status_code == 404


class TestCreatePipeline:
    @pytest.mark.asyncio
    async def test_create_pipeline_success(self, client, hdr):
        def _refresh_pipeline(obj):
            _populate_defaults(obj)
            if not hasattr(obj, 'stages') or getattr(obj, 'stages', None) is None:
                obj.stages = []
        client._db.refresh = AsyncMock(side_effect=_refresh_pipeline)
        r = await client.post("/api/crm/pipelines", headers=hdr,
                              json={"name": "New Pipeline"})
        assert r.status_code in (200, 201)

    @pytest.mark.asyncio
    async def test_create_pipeline_missing_name(self, client, hdr):
        r = await client.post("/api/crm/pipelines", headers=hdr, json={})
        assert r.status_code == 422


class TestDeletePipeline:
    @pytest.mark.asyncio
    async def test_delete_pipeline_success(self, client, hdr):
        p = fake_pipeline(is_default=False)
        client._db.execute = AsyncMock(side_effect=[
            FakeResult(scalar_value=p),  # select
            FakeResult(),                # delete stages
            FakeResult(),                # delete pipeline
        ])
        r = await client.delete("/api/crm/pipelines/1", headers=hdr)
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_delete_pipeline_not_found(self, client, hdr):
        client._db.execute = AsyncMock(return_value=FakeResult(scalar_value=None))
        r = await client.delete("/api/crm/pipelines/999", headers=hdr)
        assert r.status_code == 404


class TestPipelineStages:
    @pytest.mark.asyncio
    async def test_list_stages(self, client, hdr):
        p = fake_pipeline()
        s = fake_stage()
        client._db.execute = AsyncMock(side_effect=[
            FakeResult(scalar_value=p),  # verify pipeline
            FakeResult(items=[s]),       # list stages
        ])
        r = await client.get("/api/crm/pipelines/1/stages", headers=hdr)
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_create_stage(self, client, hdr):
        p = fake_pipeline()
        s = fake_stage()
        client._db.execute = AsyncMock(side_effect=[
            FakeResult(scalar_value=p),  # verify pipeline
            FakeResult(items=[]),        # existing stages count
        ])
        r = await client.post("/api/crm/pipelines/1/stages", headers=hdr,
                              json={"name": "Proposal", "code": "proposal",
                                    "probability": 50, "sort_order": 1})
        assert r.status_code in (200, 201)

    @pytest.mark.asyncio
    async def test_delete_stage(self, client, hdr):
        s = fake_stage()
        client._db.execute = AsyncMock(side_effect=[
            FakeResult(scalar_value=s),  # select stage
            FakeResult(),                # check deals in stage
            FakeResult(),                # delete
        ])
        r = await client.delete("/api/crm/stages/1", headers=hdr)
        assert r.status_code == 200


# =====================================================================
# CONTACTS (Persons & Organizations)
# =====================================================================

def _person_row(**ov):
    """Dict-like row matching the raw-SQL person query output."""
    d = dict(id=1, name="John Doe", emails=[{"value": "j@e.com", "label": "work"}],
             contact_numbers=[{"value": "555-1234", "label": "mobile"}],
             job_title="CEO", organization_id=1, organization_name="Acme Corp",
             user_id=1, assigned_to="Test", assigned_email="t@t.io",
             created_at=NOW, updated_at=NOW)
    d.update(ov)
    return d


class TestListPersons:
    @pytest.mark.asyncio
    async def test_list_persons(self, client, hdr):
        row = _person_row()
        client._db.execute = AsyncMock(return_value=FakeResult(items=[row]))
        with patch("app.api.crm.contacts.load_assignment_summaries", new_callable=AsyncMock, return_value={}):
            r = await client.get("/api/crm/persons", headers=hdr)
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_list_persons_empty(self, client, hdr):
        client._db.execute = AsyncMock(return_value=FakeResult(items=[]))
        with patch("app.api.crm.contacts.load_assignment_summaries", new_callable=AsyncMock, return_value={}):
            r = await client.get("/api/crm/persons", headers=hdr)
        assert r.status_code == 200
        assert r.json() == []


class TestGetPerson:
    @pytest.mark.asyncio
    async def test_get_person_success(self, client, hdr):
        row = _person_row()
        client._db.execute = AsyncMock(return_value=FakeResult(items=[row]))
        with patch("app.api.crm.contacts.load_assignment_summaries", new_callable=AsyncMock, return_value={}):
            r = await client.get("/api/crm/persons/1", headers=hdr)
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_get_person_not_found(self, client, hdr):
        client._db.execute = AsyncMock(return_value=FakeResult(items=[]))
        with patch("app.api.crm.contacts.load_assignment_summaries", new_callable=AsyncMock, return_value={}):
            r = await client.get("/api/crm/persons/999", headers=hdr)
        assert r.status_code == 404


class TestCreatePerson:
    @pytest.mark.asyncio
    async def test_create_person_success(self, client, hdr):
        with patch("app.services.workflow_triggers.fire_triggers_background"):
            r = await client.post("/api/crm/persons", headers=hdr,
                                  json={
                                      "name": "Jane Doe",
                                      "emails": [{"value": "jane@corp.com", "label": "work"}],
                                      "contact_numbers": [{"value": "555-9000", "label": "mobile"}],
                                  })
        assert r.status_code in (200, 201)
        d = r.json()
        assert d["emails"][0]["value"] == "jane@corp.com"
        assert d["contact_numbers"][0]["value"] == "555-9000"

    @pytest.mark.asyncio
    async def test_create_person_missing_name(self, client, hdr):
        r = await client.post("/api/crm/persons", headers=hdr, json={})
        assert r.status_code == 422


class TestUpdatePerson:
    @pytest.mark.asyncio
    async def test_update_person_success(self, client, hdr):
        person = fake_person()
        client._db.execute = AsyncMock(return_value=FakeResult(scalar_value=person))
        with patch("app.services.workflow_triggers.fire_triggers_background"):
            r = await client.put("/api/crm/persons/1", headers=hdr,
                                 json={"name": "Updated Name"})
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_manual_email_correction_creates_activity_history(self, client, hdr):
        from app.models.crm.activity import Activity, PersonActivity

        person = fake_person()
        client._db.execute = AsyncMock(return_value=FakeResult(scalar_value=person))

        with patch("app.api.crm.contacts.log_audit", new_callable=AsyncMock) as log_audit, \
             patch("app.services.workflow_triggers.fire_triggers_background"):
            r = await client.put(
                "/api/crm/persons/1",
                headers=hdr,
                json={"emails": [{"value": "updated@acme.com", "label": "work"}]},
            )

        assert r.status_code == 200
        assert r.json()["emails"][0]["value"] == "updated@acme.com"
        assert person.email_addresses == [{"value": "updated@acme.com", "label": "work"}]

        added = [call.args[0] for call in client._db.add.call_args_list]
        activity = next(obj for obj in added if isinstance(obj, Activity))
        link = next(obj for obj in added if isinstance(obj, PersonActivity))
        assert activity.additional["change_type"] == "manual_contact_correction"
        assert activity.additional["changes"]["emails"]["old"][0]["value"] == "j@e.com"
        assert activity.additional["changes"]["emails"]["new"][0]["value"] == "updated@acme.com"
        assert link.person_id == 1

        audit_args = log_audit.await_args.args
        assert audit_args[5]["emails"][0]["value"] == "j@e.com"
        assert audit_args[6]["emails"][0]["value"] == "updated@acme.com"

    @pytest.mark.asyncio
    async def test_manual_phone_correction_creates_activity_history(self, client, hdr):
        from app.models.crm.activity import Activity

        person = fake_person()
        client._db.execute = AsyncMock(return_value=FakeResult(scalar_value=person))

        with patch("app.api.crm.contacts.log_audit", new_callable=AsyncMock), \
             patch("app.services.workflow_triggers.fire_triggers_background"):
            r = await client.put(
                "/api/crm/persons/1",
                headers=hdr,
                json={"contact_numbers": [{"value": "555-7777", "label": "office"}]},
            )

        assert r.status_code == 200
        assert r.json()["contact_numbers"][0]["value"] == "555-7777"
        added = [call.args[0] for call in client._db.add.call_args_list]
        activity = next(obj for obj in added if isinstance(obj, Activity))
        assert activity.additional["changes"]["contact_numbers"]["new"][0]["value"] == "555-7777"

    @pytest.mark.asyncio
    async def test_noop_contact_update_does_not_create_activity_noise(self, client, hdr):
        from app.models.crm.activity import Activity, PersonActivity

        person = fake_person()
        client._db.execute = AsyncMock(return_value=FakeResult(scalar_value=person))

        with patch("app.api.crm.contacts.log_audit", new_callable=AsyncMock), \
             patch("app.services.workflow_triggers.fire_triggers_background"):
            r = await client.put(
                "/api/crm/persons/1",
                headers=hdr,
                json={
                    "emails": [{"value": "j@e.com", "label": "work"}],
                    "contact_numbers": [{"value": "555-1234", "label": "mobile"}],
                },
            )

        assert r.status_code == 200
        added = [call.args[0] for call in client._db.add.call_args_list]
        assert not any(isinstance(obj, (Activity, PersonActivity)) for obj in added)

    @pytest.mark.asyncio
    async def test_update_person_not_found(self, client, hdr):
        client._db.execute = AsyncMock(return_value=FakeResult(scalar_value=None))
        r = await client.put("/api/crm/persons/999", headers=hdr, json={"name": "X"})
        assert r.status_code == 404


class TestDeletePerson:
    @pytest.mark.asyncio
    async def test_delete_person_success(self, client, hdr):
        person = fake_person()
        client._db.execute = AsyncMock(side_effect=[
            FakeResult(scalar_value=person),
            FakeResult(),  # delete
        ])
        r = await client.delete("/api/crm/persons/1", headers=hdr)
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_delete_person_not_found(self, client, hdr):
        client._db.execute = AsyncMock(return_value=FakeResult(scalar_value=None))
        r = await client.delete("/api/crm/persons/999", headers=hdr)
        assert r.status_code == 404


class TestOrganizations:
    @pytest.mark.asyncio
    async def test_list_organizations(self, client, hdr):
        org = fake_org()
        client._db.execute = AsyncMock(return_value=FakeResult(items=[org]))
        r = await client.get("/api/crm/organizations", headers=hdr)
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_get_org_success(self, client, hdr):
        org = fake_org()
        client._db.execute = AsyncMock(return_value=FakeResult(scalar_value=org))
        r = await client.get("/api/crm/organizations/1", headers=hdr)
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_get_org_not_found(self, client, hdr):
        client._db.execute = AsyncMock(return_value=FakeResult(scalar_value=None))
        r = await client.get("/api/crm/organizations/999", headers=hdr)
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_create_org_success(self, client, hdr):
        with patch("app.services.workflow_triggers.fire_triggers_background"):
            r = await client.post("/api/crm/organizations", headers=hdr,
                                  json={
                                      "name": "New Corp",
                                      "emails": [{"value": "team@newcorp.com", "label": "work"}],
                                      "contact_numbers": [{"value": "555-0101", "label": "main"}],
                                  })
        assert r.status_code in (200, 201)
        d = r.json()
        assert d["emails"][0]["value"] == "team@newcorp.com"
        assert d["contact_numbers"][0]["value"] == "555-0101"

    @pytest.mark.asyncio
    async def test_update_org_success(self, client, hdr):
        org = fake_org()
        client._db.execute = AsyncMock(return_value=FakeResult(scalar_value=org))
        with patch("app.services.workflow_triggers.fire_triggers_background"):
            r = await client.put("/api/crm/organizations/1", headers=hdr,
                                 json={"name": "Updated Corp"})
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_manual_org_contact_correction_is_recorded_in_audit_history(self, client, hdr):
        org = fake_org()
        client._db.execute = AsyncMock(return_value=FakeResult(scalar_value=org))

        with patch("app.api.crm.contacts.log_audit", new_callable=AsyncMock) as log_audit:
            r = await client.put(
                "/api/crm/organizations/1",
                headers=hdr,
                json={
                    "emails": [{"value": "ops@acme.com", "label": "work"}],
                    "contact_numbers": [{"value": "555-0000", "label": "support"}],
                },
            )

        assert r.status_code == 200
        d = r.json()
        assert d["emails"][0]["value"] == "ops@acme.com"
        assert d["contact_numbers"][0]["value"] == "555-0000"

        audit_args = log_audit.await_args.args
        assert audit_args[5]["emails"][0]["value"] == "hello@acme.com"
        assert audit_args[5]["contact_numbers"][0]["value"] == "555-5555"
        assert audit_args[6]["emails"][0]["value"] == "ops@acme.com"
        assert audit_args[6]["contact_numbers"][0]["value"] == "555-0000"

    @pytest.mark.asyncio
    async def test_update_org_not_found(self, client, hdr):
        client._db.execute = AsyncMock(return_value=FakeResult(scalar_value=None))
        r = await client.put("/api/crm/organizations/999", headers=hdr, json={"name": "X"})
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_org_success(self, client, hdr):
        org = fake_org()
        client._db.execute = AsyncMock(side_effect=[
            FakeResult(scalar_value=org),
            FakeResult(items=[]),  # check persons
            FakeResult(),          # delete
        ])
        r = await client.delete("/api/crm/organizations/1", headers=hdr)
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_delete_org_not_found(self, client, hdr):
        client._db.execute = AsyncMock(return_value=FakeResult(scalar_value=None))
        r = await client.delete("/api/crm/organizations/999", headers=hdr)
        assert r.status_code == 404


# =====================================================================
# ACTIVITIES
# =====================================================================

class TestListActivities:
    @pytest.mark.asyncio
    async def test_list_activities(self, client, hdr):
        act = fake_activity()
        client._db.execute = AsyncMock(return_value=FakeResult(items=[act]))
        r = await client.get("/api/crm/activities", headers=hdr)
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_list_activities_empty(self, client, hdr):
        client._db.execute = AsyncMock(return_value=FakeResult(items=[]))
        r = await client.get("/api/crm/activities", headers=hdr)
        assert r.status_code == 200
        assert r.json() == []

    @pytest.mark.asyncio
    async def test_list_activities_with_filters(self, client, hdr):
        client._db.execute = AsyncMock(return_value=FakeResult(items=[]))
        r = await client.get("/api/crm/activities?deal_id=1&type=call", headers=hdr)
        assert r.status_code == 200


class TestGetActivity:
    @pytest.mark.asyncio
    async def test_get_activity_success(self, client, hdr):
        act = fake_activity()
        client._db.execute = AsyncMock(return_value=FakeResult(scalar_value=act))
        r = await client.get("/api/crm/activities/1", headers=hdr)
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_get_activity_not_found(self, client, hdr):
        client._db.execute = AsyncMock(return_value=FakeResult(scalar_value=None))
        r = await client.get("/api/crm/activities/999", headers=hdr)
        assert r.status_code == 404


class TestCreateActivity:
    @pytest.mark.asyncio
    async def test_create_activity_success(self, client, hdr):
        with patch("app.services.workflow_triggers.fire_triggers_background"):
            r = await client.post("/api/crm/activities", headers=hdr,
                                  json={"title": "New Call", "type": "call"})
        assert r.status_code in (200, 201)

    @pytest.mark.asyncio
    async def test_create_activity_missing_type(self, client, hdr):
        r = await client.post("/api/crm/activities", headers=hdr, json={"title": "Call"})
        assert r.status_code == 422


class TestUpdateActivity:
    @pytest.mark.asyncio
    async def test_update_activity_success(self, client, hdr):
        act = fake_activity()
        client._db.execute = AsyncMock(return_value=FakeResult(scalar_value=act))
        with patch("app.services.workflow_triggers.fire_triggers_background"):
            r = await client.put("/api/crm/activities/1", headers=hdr,
                                 json={"title": "Updated Call"})
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_update_activity_not_found(self, client, hdr):
        client._db.execute = AsyncMock(return_value=FakeResult(scalar_value=None))
        r = await client.put("/api/crm/activities/999", headers=hdr, json={"title": "X"})
        assert r.status_code == 404


class TestDeleteActivity:
    @pytest.mark.asyncio
    async def test_delete_activity_success(self, client, hdr):
        act = fake_activity()
        client._db.execute = AsyncMock(side_effect=[
            FakeResult(scalar_value=act),
            FakeResult(),  # delete
        ])
        r = await client.delete("/api/crm/activities/1", headers=hdr)
        assert r.status_code == 200
        assert r.json()["status"] == "deleted"

    @pytest.mark.asyncio
    async def test_delete_activity_not_found(self, client, hdr):
        client._db.execute = AsyncMock(return_value=FakeResult(scalar_value=None))
        r = await client.delete("/api/crm/activities/999", headers=hdr)
        assert r.status_code == 404


class TestMarkActivityDone:
    @pytest.mark.asyncio
    async def test_mark_done_success(self, client, hdr):
        act = fake_activity(is_done=False)
        client._db.execute = AsyncMock(return_value=FakeResult(scalar_value=act))
        r = await client.put("/api/crm/activities/1/done", headers=hdr)
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_mark_done_not_found(self, client, hdr):
        client._db.execute = AsyncMock(return_value=FakeResult(scalar_value=None))
        r = await client.put("/api/crm/activities/999/done", headers=hdr)
        assert r.status_code == 404