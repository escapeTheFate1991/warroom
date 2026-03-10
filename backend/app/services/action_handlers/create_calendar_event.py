"""Action handler: create_calendar_event — creates a Google Calendar event."""

import logging
from datetime import datetime, timedelta, timezone

from app.api.google_calendar import create_calendar_event

logger = logging.getLogger(__name__)


async def handle(step: dict, context: dict, execution: dict) -> dict:
    """Create a Google Calendar event.

    Step config keys:
        summary (str): Event title.
        duration (int, optional): Duration in minutes (default 30).
        description (str, optional): Event description.
        start_iso (str, optional): ISO start time. Defaults to now + 1 hour.
    Context keys:
        contact_email (str, optional): Attendee email.
    """
    summary = step.get("summary", "")
    if not summary:
        return {"success": False, "result": None, "error": "Missing 'summary' in step config"}

    duration_min = step.get("duration", 30)
    description = step.get("description", "")
    attendee = step.get("attendee") or context.get("contact_email")

    # Default start: 1 hour from now
    start_iso = step.get("start_iso")
    if not start_iso:
        start = datetime.now(timezone.utc) + timedelta(hours=1)
        start_iso = start.isoformat()

    end = datetime.fromisoformat(start_iso) + timedelta(minutes=duration_min)
    end_iso = end.isoformat()

    try:
        event = await create_calendar_event(
            summary=summary,
            start_iso=start_iso,
            end_iso=end_iso,
            attendee_email=attendee,
            description=description,
        )
        if event:
            event_id = event.get("id", "unknown")
            logger.info("Calendar event created: %s (id=%s)", summary, event_id)
            return {
                "success": True,
                "result": {"event_id": event_id, "summary": summary, "start": start_iso, "end": end_iso},
                "error": None,
            }
        else:
            return {"success": False, "result": None, "error": "Google Calendar not connected or event creation failed"}
    except Exception as exc:
        logger.error("create_calendar_event handler failed: %s", exc)
        return {"success": False, "result": None, "error": str(exc)}
