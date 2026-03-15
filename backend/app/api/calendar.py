"""Activity Calendar — monthly view from memory files + personal Google Calendar."""
import logging
import json
from datetime import datetime, date
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.agent_contract import (
    PersonalCalendarEventEnvelope,
    PersonalCalendarResponse,
    load_agent_assignment_map,
)
from app.db.crm_db import get_tenant_db
from app.services.tenant import get_org_id, get_user_id

logger = logging.getLogger(__name__)
router = APIRouter()

MEMORY_DIR = Path("/openclaw-workspace/memory")
PERSONAL_EVENTS_FILE = Path("/openclaw-workspace/memory/personal-events.json")
from app.services.token_store import load_tokens as _load_tokens


async def _attach_event_assignments(db: AsyncSession, events: list[dict]) -> list[dict]:
    if not events:
        return events

    assignment_map = await load_agent_assignment_map(
        db,
        entity_type="calendar_event",
        entity_ids=[str(event.get("id")) for event in events if event.get("id")],
    )
    for event in events:
        event["agent_assignments"] = assignment_map.get(str(event.get("id")), [])
    return events

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
    tokens = await _load_tokens("google_calendar")
    if tokens and tokens.get("refresh_token"):
        return {
            "connected": True,
            "provider": "google",
            "email": tokens.get("email"),
            "message": f"Connected as {tokens.get('email', 'unknown')}",
        }
    return {"connected": False, "provider": "google", "message": "Google Calendar not connected."}


@router.get("/calendar/personal", response_model=PersonalCalendarResponse)
async def get_personal_calendar(request: Request, month: Optional[str] = None, db: AsyncSession = Depends(get_tenant_db)):
    """Get personal calendar events for a month. Returns local events + Google Calendar events when connected."""
    org_id = get_org_id(request)
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

    # Merge Google Calendar events when connected
    google_connected = False
    tokens = await _load_tokens("google_calendar")
    if tokens and tokens.get("refresh_token"):
        google_connected = True
        try:
            from app.api.google_calendar import _get_credentials
            from googleapiclient.discovery import build

            creds = await _get_credentials()
            if creds:
                service = build("calendar", "v3", credentials=creds)
                time_min = datetime(year, mon, 1).isoformat() + "Z"
                if mon == 12:
                    time_max = datetime(year + 1, 1, 1).isoformat() + "Z"
                else:
                    time_max = datetime(year, mon + 1, 1).isoformat() + "Z"

                results = (
                    service.events()
                    .list(
                        calendarId="primary",
                        timeMin=time_min,
                        timeMax=time_max,
                        maxResults=250,
                        singleEvents=True,
                        orderBy="startTime",
                    )
                    .execute()
                )

                for item in results.get("items", []):
                    start = item.get("start", {})
                    end = item.get("end", {})
                    is_all_day = "date" in start and "dateTime" not in start
                    if is_all_day:
                        event_date = start["date"]
                        event_time = None
                        event_end_time = None
                    else:
                        dt_str = start.get("dateTime", "")
                        event_date = dt_str[:10] if dt_str else ""
                        event_time = dt_str[11:16] if len(dt_str) > 16 else None
                        end_str = end.get("dateTime", "")
                        event_end_time = end_str[11:16] if len(end_str) > 16 else None

                    events.append({
                        "id": f"gcal-{item['id']}",
                        "title": item.get("summary", "(No title)"),
                        "date": event_date,
                        "time": event_time,
                        "end_time": event_end_time,
                        "description": item.get("description", ""),
                        "location": item.get("location", ""),
                        "type": "event",
                        "source": "google",
                        "all_day": is_all_day,
                        "status": item.get("status", "confirmed"),
                        "html_link": item.get("htmlLink", ""),
                        "created_at": item.get("created", ""),
                    })
        except Exception as exc:
            logger.warning("Failed to fetch Google Calendar events: %s", exc)

    await _attach_event_assignments(db, events)
    return {"year": year, "month": mon, "events": events, "google_connected": google_connected}


@router.post("/calendar/personal/events", response_model=PersonalCalendarEventEnvelope)
async def create_personal_event(request: Request, event: dict, db: AsyncSession = Depends(get_tenant_db)):
    """Create a local personal calendar event."""
    org_id = get_org_id(request)
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

    await _attach_event_assignments(db, [event])
    return {"ok": True, "event": event}


@router.patch("/calendar/personal/events/{event_id}", response_model=PersonalCalendarEventEnvelope)
async def update_personal_event(request: Request, event_id: str, updates: dict, db: AsyncSession = Depends(get_tenant_db)):
    """Partially update a local personal calendar event."""
    org_id = get_org_id(request)
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
    await _attach_event_assignments(db, [all_events[i]])
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