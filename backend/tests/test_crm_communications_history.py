"""Unit tests for the unified CRM communications history helpers."""

import os
import sys
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("POSTGRES_URL", "postgresql+asyncpg://user:pass@localhost/testdb")
os.environ.setdefault("LEADGEN_DB_URL", "postgresql+asyncpg://user:pass@localhost/testdb")

from app.api.crm.activities import (  # noqa: E402
    history_item_sort_timestamp,
    parse_leadgen_prospect_id,
    serialize_activity_history_item,
    serialize_email_history_item,
)


class CommunicationsHistoryHelpersTestCase(unittest.TestCase):
    def test_parse_leadgen_prospect_id_accepts_lead_prefix(self):
        self.assertEqual(parse_leadgen_prospect_id("lead-42"), 42)
        self.assertEqual(parse_leadgen_prospect_id("leadgen-7"), 7)

    def test_parse_leadgen_prospect_id_rejects_unlinked_sources(self):
        with self.assertRaisesRegex(ValueError, "lead-backed prospects"):
            parse_leadgen_prospect_id("form-12")

    def test_serialize_activity_history_item_surfaces_call_artifacts(self):
        activity = SimpleNamespace(
            id=9,
            type="call",
            title="Phone call with +15551234567",
            comment="Telnyx call summary",
            additional={
                "direction": "outbound",
                "status": "hangup",
                "from_number": "+15557654321",
                "to_number": "+15551234567",
                "recording_url": "https://cdn.example.com/call.mp3",
                "transcript": "Customer asked for pricing details.",
            },
            location=None,
            schedule_from=datetime(2026, 3, 1, 12, 0, 0),
            schedule_to=datetime(2026, 3, 1, 12, 5, 0),
            is_done=True,
            user_id=4,
            created_at=datetime(2026, 3, 1, 12, 0, 0),
            persons=[SimpleNamespace(id=11)],
            deals=[SimpleNamespace(id=22)],
            participants=[SimpleNamespace(id=11), SimpleNamespace(id=33)],
        )

        item = serialize_activity_history_item(activity)
        self.assertEqual(item.channel, "call")
        self.assertEqual(item.content, "Customer asked for pricing details.")
        self.assertEqual(item.recording_url, "https://cdn.example.com/call.mp3")
        self.assertEqual(item.transcript, "Customer asked for pricing details.")
        self.assertEqual(item.linked_person_ids, [11])
        self.assertEqual(item.linked_deal_ids, [22])
        self.assertEqual(item.participant_person_ids, [11, 33])

    def test_serialize_email_history_item_includes_attachments_and_addresses(self):
        email = SimpleNamespace(
            id=5,
            subject="Proposal follow-up",
            source="imap",
            name="AE",
            reply="Thanks for the call — proposal attached.",
            is_read=True,
            folders={"inbox": True},
            from_addr={"email": "rep@example.com"},
            sender={"email": "rep@example.com"},
            reply_to=None,
            cc={"email": "manager@example.com"},
            bcc=None,
            message_id="<msg-1@example.com>",
            reference_ids=["<root@example.com>"],
            person_id=11,
            deal_id=22,
            parent_id=None,
            created_at=datetime(2026, 3, 2, 8, 30, 0),
            attachments=[
                SimpleNamespace(
                    name="proposal.pdf",
                    content_type="application/pdf",
                    size=1024,
                    filepath="/tmp/proposal.pdf",
                )
            ],
        )

        item = serialize_email_history_item(email)
        self.assertEqual(item.channel, "email")
        self.assertEqual(item.content, "Thanks for the call — proposal attached.")
        self.assertEqual(item.linked_person_ids, [11])
        self.assertEqual(item.linked_deal_ids, [22])
        self.assertEqual(item.attachments[0]["name"], "proposal.pdf")
        self.assertIn("from_addr", item.addresses)

    def test_history_item_sort_timestamp_prefers_occurred_at(self):
        activity_item = serialize_activity_history_item(
            SimpleNamespace(
                id=1,
                type="task",
                title="Older note",
                comment="Older activity",
                additional={},
                location=None,
                schedule_from=datetime(2026, 3, 1, 9, 0, 0),
                schedule_to=None,
                is_done=False,
                user_id=None,
                created_at=datetime(2026, 3, 1, 9, 0, 0),
                persons=[],
                deals=[],
                participants=[],
            )
        )
        email_item = serialize_email_history_item(
            SimpleNamespace(
                id=2,
                subject="Newer email",
                source="imap",
                name=None,
                reply="Latest touchpoint",
                is_read=False,
                folders=None,
                from_addr=None,
                sender=None,
                reply_to=None,
                cc=None,
                bcc=None,
                message_id=None,
                reference_ids=None,
                person_id=None,
                deal_id=None,
                parent_id=None,
                created_at=datetime(2026, 3, 2, 9, 0, 0),
                attachments=[],
            )
        )

        items = [activity_item, email_item]
        items.sort(key=history_item_sort_timestamp, reverse=True)
        self.assertEqual(items[0].entry_id, "email:2")


if __name__ == "__main__":
    unittest.main()