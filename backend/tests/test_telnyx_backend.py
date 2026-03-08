"""Unit tests for the Telnyx backend wiring helpers."""

import asyncio
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("POSTGRES_URL", "postgresql+asyncpg://user:pass@localhost/testdb")
os.environ.setdefault("LEADGEN_DB_URL", "postgresql+asyncpg://user:pass@localhost/testdb")

from app.api.telnyx import (  # noqa: E402
    build_sms_activity_title,
    extract_telnyx_phone_number,
    extract_recording_url,
    normalize_phone_number,
    resolve_call_status,
    unwrap_telnyx_event,
)
from app.models.crm.sms_message import SMSMessage  # noqa: E402
from app.services.telnyx_client import build_call_payload, send_sms  # noqa: E402


class TelnyxHelpersTestCase(unittest.TestCase):
    def test_unwrap_telnyx_event_supports_data_envelope(self):
        wrapped = {"data": {"event_type": "call.hangup", "payload": {"call_session_id": "abc"}}}
        self.assertEqual(unwrap_telnyx_event(wrapped)["event_type"], "call.hangup")

    def test_build_call_payload_includes_webhook_and_optional_connection(self):
        payload = build_call_payload(
            phone_number="+15551234567",
            from_number="+15557654321",
            webhook_url="https://example.com/api/telnyx/webhook",
            connection_id="12345",
        )
        self.assertEqual(payload["to"], "+15551234567")
        self.assertEqual(payload["from"], "+15557654321")
        self.assertEqual(payload["webhook_url_method"], "POST")
        self.assertEqual(payload["connection_id"], "12345")

    def test_extract_recording_url_prefers_public_mp3(self):
        payload = {
            "public_recording_urls": {"mp3": "https://cdn.example.com/recording.mp3", "wav": "https://cdn.example.com/recording.wav"}
        }
        self.assertEqual(extract_recording_url(payload), "https://cdn.example.com/recording.mp3")

    def test_normalize_phone_number_uses_last_ten_digits(self):
        self.assertEqual(normalize_phone_number("+1 (555) 123-4567"), "5551234567")

    def test_resolve_call_status_prefers_payload_state(self):
        self.assertEqual(resolve_call_status("call.answered", {"state": "custom"}), "custom")
        self.assertEqual(resolve_call_status("call.hangup", {}), "hangup")

    def test_extract_telnyx_phone_number_supports_string_and_dict(self):
        self.assertEqual(extract_telnyx_phone_number(" +15551234567 "), "+15551234567")
        self.assertEqual(
            extract_telnyx_phone_number({"phone_number": " +15557654321 "}),
            "+15557654321",
        )

    def test_build_sms_activity_title_uses_counterpart(self):
        outbound = SMSMessage(direction="outbound", to_number="+15551234567")
        inbound = SMSMessage(direction="inbound", from_number="+15557654321")
        self.assertEqual(build_sms_activity_title(outbound), "SMS with +15551234567")
        self.assertEqual(build_sms_activity_title(inbound), "SMS with +15557654321")


class TelnyxClientSmsTestCase(unittest.TestCase):
    def test_send_sms_requires_to(self):
        with self.assertRaisesRegex(ValueError, "to is required"):
            asyncio.run(send_sms(" ", "hello"))

    def test_send_sms_requires_body(self):
        with self.assertRaisesRegex(ValueError, "body is required"):
            asyncio.run(send_sms("+15551234567", " "))

    def test_send_sms_posts_message_payload(self):
        fake_config = AsyncMock(return_value=type("Cfg", (), {"phone_number": "+15557654321", "api_key": "secret"})())
        fake_post = AsyncMock(return_value={"id": "msg_123"})

        with patch("app.services.telnyx_client.get_telnyx_config", fake_config), patch(
            "app.services.telnyx_client._post", fake_post
        ):
            result = asyncio.run(send_sms(" +15551234567 ", " hello there "))

        self.assertEqual(result, {"id": "msg_123"})
        fake_post.assert_awaited_once_with(
            "/messages",
            {"from": "+15557654321", "to": "+15551234567", "text": "hello there"},
            "secret",
        )


if __name__ == "__main__":
    unittest.main()