"""Unit tests for workflow template cloning/versioning helpers."""

import os
import sys
import unittest
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("POSTGRES_URL", "postgresql+asyncpg://user:pass@localhost/testdb")
os.environ.setdefault("LEADGEN_DB_URL", "postgresql+asyncpg://user:pass@localhost/testdb")

from app.api.crm.workflows import (  # noqa: E402
    WORKFLOW_TEMPLATE_SEEDS,
    build_workflow_clone_from_template,
    build_workflow_clone_from_workflow,
)


class WorkflowTemplateCloneHelpersTestCase(unittest.TestCase):
    def test_starter_pack_catalog_covers_real_estate_and_home_services(self):
        real_estate = [seed for seed in WORKFLOW_TEMPLATE_SEEDS if seed["seed_key"].startswith("starter-real-estate-")]
        home_services = [seed for seed in WORKFLOW_TEMPLATE_SEEDS if seed["seed_key"].startswith("starter-home-services-")]

        self.assertEqual(len(real_estate), 5)
        self.assertEqual(len(home_services), 5)

        for seed in [*real_estate, *home_services]:
            self.assertTrue(any(action["type"].startswith("ai_") for action in seed["actions"]))
            self.assertTrue(
                any(action.get("channel") in {"email", "sms", "inbox", "manual"} for action in seed["actions"])
            )
            self.assertTrue(
                any("sla_duration" in action or "escalation" in action for action in seed["actions"])
            )
            self.assertTrue(
                any(action["type"] == "approval_gate" or action.get("approval_required") for action in seed["actions"])
            )

    def test_clone_from_seed_template_does_not_mutate_seed_payload(self):
        starter_seed = next(seed for seed in WORKFLOW_TEMPLATE_SEEDS if seed["seed_key"] == "starter-real-estate-new-lead-instant-response")
        seed = SimpleNamespace(
            id=101,
            name=starter_seed["name"],
            description="Seed workflow",
            entity_type=starter_seed["entity_type"],
            event=starter_seed["event"],
            condition_type=starter_seed["condition_type"],
            conditions=deepcopy(starter_seed["conditions"]),
            actions=deepcopy(starter_seed["actions"]),
        )
        original_conditions = deepcopy(seed.conditions)
        original_actions = deepcopy(seed.actions)

        payload = build_workflow_clone_from_template(
            seed,
            {
                "name": "My follow-up workflow",
            },
        )
        payload["conditions"][0]["field"] = "changed"
        payload["actions"][0]["escalation"]["after"] = "PT20M"
        payload["actions"][1]["inputs"][0] = "changed"

        self.assertEqual(seed.conditions, original_conditions)
        self.assertEqual(seed.actions, original_actions)
        self.assertEqual(payload["template_id"], 101)
        self.assertEqual(payload["version"], 1)
        self.assertIsNone(payload["derived_from_workflow_id"])

    def test_clone_from_existing_workflow_creates_new_version_without_mutating_source(self):
        workflow = SimpleNamespace(
            id=9,
            template_id=101,
            root_workflow_id=4,
            name="Follow-up v2",
            description="Second revision",
            entity_type="deal",
            event="stage_changed",
            condition_type="and",
            conditions=[{"field": "days_in_stage", "operator": "gte", "value": 7}],
            actions=[{"type": "notify_owner", "channel": "inbox"}],
            is_active=True,
        )
        original_conditions = deepcopy(workflow.conditions)
        original_actions = deepcopy(workflow.actions)

        payload = build_workflow_clone_from_workflow(workflow, {"name": "Follow-up v3"}, next_version=3)
        payload["conditions"][0]["value"] = 14
        payload["actions"][0]["channel"] = "email"

        self.assertEqual(workflow.conditions, original_conditions)
        self.assertEqual(workflow.actions, original_actions)
        self.assertEqual(payload["derived_from_workflow_id"], 9)
        self.assertEqual(payload["root_workflow_id"], 4)
        self.assertEqual(payload["template_id"], 101)
        self.assertEqual(payload["version"], 3)

    def test_clone_from_existing_workflow_keeps_nested_pack_metadata_immutable(self):
        starter_seed = next(seed for seed in WORKFLOW_TEMPLATE_SEEDS if seed["seed_key"] == "starter-home-services-estimate-follow-up")
        workflow = SimpleNamespace(
            id=12,
            template_id=302,
            root_workflow_id=12,
            name=starter_seed["name"],
            description=starter_seed["description"],
            entity_type=starter_seed["entity_type"],
            event=starter_seed["event"],
            condition_type=starter_seed["condition_type"],
            conditions=deepcopy(starter_seed["conditions"]),
            actions=deepcopy(starter_seed["actions"]),
            is_active=False,
        )
        original_actions = deepcopy(workflow.actions)

        payload = build_workflow_clone_from_workflow(workflow, {"name": "Estimate follow-up v2"}, next_version=2)
        payload["actions"][1]["escalation"]["message"] = "Changed"
        payload["actions"][2]["required_for"][0] = "Changed"

        self.assertEqual(workflow.actions, original_actions)
        self.assertEqual(payload["derived_from_workflow_id"], 12)
        self.assertEqual(payload["root_workflow_id"], 12)
        self.assertEqual(payload["version"], 2)


if __name__ == "__main__":
    unittest.main()