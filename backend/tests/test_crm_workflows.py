"""Unit tests for workflow contract helpers."""

import sys
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from app.api.crm.workflow_contract import normalize_workflow_payload, workflow_contract_fields  # noqa: E402


class WorkflowHelpersTestCase(unittest.TestCase):
    def test_normalize_workflow_payload_defaults_to_step_lists(self):
        payload = normalize_workflow_payload({"name": "Deal created", "entity_type": "deal", "event": "created", "is_active": True})

        self.assertEqual(payload["condition_type"], "and")
        self.assertEqual(payload["conditions"], [])
        self.assertEqual(payload["actions"], [])
        self.assertTrue(payload["is_active"])

    def test_normalize_workflow_payload_preserves_studio_metadata(self):
        payload = normalize_workflow_payload(
            {
                "name": "Studio workflow",
                "entity_type": "deal",
                "event": "created",
                "conditions": [{"field": "stage", "operator": "equals", "value": "proposal", "_studio": {"node_id": "c1"}}],
                "actions": [{"type": "delay", "duration": "1 day", "_studio": {"node_id": "a1", "kind": "delay", "next": None}}],
            }
        )

        self.assertEqual(payload["conditions"][0]["_studio"]["node_id"], "c1")
        self.assertEqual(payload["actions"][0]["_studio"]["kind"], "delay")

    def test_serialize_workflow_coerces_legacy_dict_steps(self):
        now = datetime(2026, 3, 9, 12, 0, 0)
        workflow = SimpleNamespace(
            id=7,
            name="Stage follow-up",
            description="Send an internal follow-up task.",
            entity_type="deal",
            event="stage_changed",
            condition_type=None,
            conditions={"field": "stage", "operator": "equals", "value": "proposal"},
            actions={"type": "create_activity", "title": "Follow up"},
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        serialized = workflow_contract_fields(workflow)

        self.assertEqual(serialized["condition_type"], "and")
        self.assertEqual(serialized["conditions"], [{"field": "stage", "operator": "equals", "value": "proposal"}])
        self.assertEqual(serialized["actions"], [{"type": "create_activity", "title": "Follow up"}])


if __name__ == "__main__":
    unittest.main()