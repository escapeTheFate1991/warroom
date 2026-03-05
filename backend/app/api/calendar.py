"""Activity Calendar — monthly view from memory files."""
import logging
from datetime import datetime, date
from pathlib import Path
from fastapi import APIRouter, HTTPException
from typing import Optional

logger = logging.getLogger(__name__)
router = APIRouter()

MEMORY_DIR = Path.home() / ".openclaw" / "workspace" / "memory"


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