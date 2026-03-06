"""Activity Calendar — monthly view from memory files + personal Google Calendar."""
import logging
import os
import json
from datetime import datetime, date
from pathlib import Path
from fastapi import APIRouter, HTTPException
from typing import Optional

logger = logging.getLogger(__name__)
router = APIRouter()

MEMORY_DIR = Path("/openclaw-workspace/memory")
PERSONAL_EVENTS_FILE = Path("/openclaw-workspace/memory/personal-events.json")

# ── Activity Calendar (agent memory files) ──────────────────

@router.get("/calendar")
async def get_calendar(month: Optional[str] = None):
    if month:
        try:
            year, mon = int(month.split("-")[0]), int(month.split("-")[1])
        except:
            raise HTTPException(status_code=400, detail="month format: YYYY-MM")
    else:
        today = date.today()
        year, mon = today.year, today.month
    
    days = {}
    if MEMORY_DIR.exists():
        for f in MEMORY_DIR.glob("*.md"):
            if not f.name[0].isdigit():
                continue
            try:
                file_date = f.name.replace(".md", "")
                parts = file_date.split("-")
                if int(parts[0]) == year and int(parts[1]) == mon:
                    content = f.read_text(errors="replace")
                    days[file_date] = {
                        "has_memory": True,
                        "preview": content[:300].strip(),
                        "size": f.stat().st_size,
                    }
            except:
                continue
    
    return {"year": year, "month": mon, "days": days}


@router.get("/calendar/day/{day}")
async def get_day(day: str):
    fp = MEMORY_DIR / f"{day}.md"
    if not fp.exists():
        raise HTTPException(status_code=404, detail="No memory for this day")
    return {"date": day, "content": fp.read_text(errors="replace")}


# ── Personal Calendar (Google Calendar integration) ─────────

@router.get("/calendar/personal/status")
async def personal_calendar_status():
    """Check if Google Calendar is connected."""
    # TODO: Check for stored Google OAuth tokens
    return {"connected": False, "provider": "google", "message": "Google Calendar not connected. Set up OAuth in Settings > Integrations."}


@router.get("/calendar/personal")
async def get_personal_calendar(month: Optional[str] = None):
    """Get personal calendar events for a month. Returns local events + Google Calendar events when connected."""
    if month:
        try:
            year, mon = int(month.split("-")[0]), int(month.split("-")[1])
        except:
            raise HTTPException(status_code=400, detail="month format: YYYY-MM")
    else:
        today = date.today()
        year, mon = today.year, today.month

    month_prefix = f"{year}-{str(mon).zfill(2)}"
    events = []

    # Load local events
    if PERSONAL_EVENTS_FILE.exists():
        try:
            all_events = json.loads(PERSONAL_EVENTS_FILE.read_text())
            events = [e for e in all_events if e.get("date", "").startswith(month_prefix)]
        except:
            pass

    # TODO: Fetch from Google Calendar API when connected

    return {"year": year, "month": mon, "events": events, "google_connected": False}


@router.post("/calendar/personal/events")
async def create_personal_event(event: dict):
    """Create a local personal calendar event."""
    required = ["title", "date"]
    for field in required:
        if field not in event:
            raise HTTPException(status_code=400, detail=f"Missing field: {field}")

    # Generate ID
    event["id"] = f"evt-{datetime.now().strftime('%Y%m%d%H%M%S')}-{hash(event['title']) % 10000:04d}"
    event["created_at"] = datetime.now().isoformat()
    event["source"] = "local"

    # Load existing events
    all_events = []
    if PERSONAL_EVENTS_FILE.exists():
        try:
            all_events = json.loads(PERSONAL_EVENTS_FILE.read_text())
        except:
            pass

    all_events.append(event)
    PERSONAL_EVENTS_FILE.write_text(json.dumps(all_events, indent=2))

    return {"ok": True, "event": event}


@router.patch("/calendar/personal/events/{event_id}")
async def update_personal_event(event_id: str, updates: dict):
    """Partially update a local personal calendar event."""
    if not PERSONAL_EVENTS_FILE.exists():
        raise HTTPException(status_code=404, detail="Event not found")

    all_events = json.loads(PERSONAL_EVENTS_FILE.read_text())
    found = False
    for i, ev in enumerate(all_events):
        if ev.get("id") == event_id:
            # Don't allow overwriting id, source, created_at
            protected = {"id", "source", "created_at"}
            for key, val in updates.items():
                if key not in protected:
                    all_events[i][key] = val
            all_events[i]["updated_at"] = datetime.now().isoformat()
            found = True
            break

    if not found:
        raise HTTPException(status_code=404, detail="Event not found")

    PERSONAL_EVENTS_FILE.write_text(json.dumps(all_events, indent=2))
    return {"ok": True, "event": all_events[i]}


@router.delete("/calendar/personal/events/{event_id}")
async def delete_personal_event(event_id: str):
    """Delete a local personal calendar event."""
    if not PERSONAL_EVENTS_FILE.exists():
        raise HTTPException(status_code=404, detail="Event not found")

    all_events = json.loads(PERSONAL_EVENTS_FILE.read_text())
    filtered = [e for e in all_events if e.get("id") != event_id]

    if len(filtered) == len(all_events):
        raise HTTPException(status_code=404, detail="Event not found")

    PERSONAL_EVENTS_FILE.write_text(json.dumps(filtered, indent=2))
    return {"ok": True, "deleted": event_id}