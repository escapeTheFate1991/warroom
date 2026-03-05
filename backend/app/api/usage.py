"""Usage & cost tracking — reads OpenClaw session files."""
import os
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

logger = logging.getLogger(__name__)
router = APIRouter()

OPENCLAW_DIR = Path("/openclaw")
SESSIONS_DIR = Path("/openclaw-sessions")
CONFIG_PATH = OPENCLAW_DIR / "openclaw.json"


def _read_config():
    try:
        return json.loads(CONFIG_PATH.read_text())
    except:
        return {}


def _format_duration(ms: float) -> str:
    secs = int(ms / 1000)
    if secs < 60:
        return f"{secs}s"
    mins = secs // 60
    if mins < 60:
        return f"{mins}m {secs % 60}s"
    hrs = mins // 60
    return f"{hrs}h {mins % 60}m"


@router.get("")
async def get_usage():
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=now.weekday())
    month_start = today_start.replace(day=1)
    session_window_start = now - timedelta(hours=5)

    buckets = {
        "today": {"tokens": 0, "cost": 0.0, "sessions": set()},
        "week": {"tokens": 0, "cost": 0.0, "sessions": set()},
        "month": {"tokens": 0, "cost": 0.0, "sessions": set()},
        "session": {"tokens": 0, "cost": 0.0},
    }

    try:
        if SESSIONS_DIR.exists():
            for f in SESSIONS_DIR.glob("*.jsonl"):
                if f.stat().st_mtime < month_start.timestamp():
                    continue
                for line in f.read_text().splitlines():
                    if not line.strip():
                        continue
                    try:
                        entry = json.loads(line)
                        usage = (entry.get("message", {}) or {}).get("usage") or entry.get("usage")
                        if not usage:
                            continue
                        cost_obj = usage.get("cost", {})
                        cost = cost_obj.get("total", 0) if isinstance(cost_obj, dict) else 0
                        tokens = (usage.get("input", 0) or 0) + (usage.get("output", 0) or 0) + (usage.get("cacheRead", 0) or 0)
                        ts_str = entry.get("timestamp")
                        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00")).replace(tzinfo=None) if ts_str else datetime.fromtimestamp(f.stat().st_mtime)

                        if ts >= month_start:
                            buckets["month"]["tokens"] += tokens
                            buckets["month"]["cost"] += cost
                            buckets["month"]["sessions"].add(f.name)
                        if ts >= week_start:
                            buckets["week"]["tokens"] += tokens
                            buckets["week"]["cost"] += cost
                            buckets["week"]["sessions"].add(f.name)
                        if ts >= today_start:
                            buckets["today"]["tokens"] += tokens
                            buckets["today"]["cost"] += cost
                            buckets["today"]["sessions"].add(f.name)
                        if ts >= session_window_start:
                            buckets["session"]["tokens"] += tokens
                            buckets["session"]["cost"] += cost
                    except:
                        continue
    except Exception as e:
        logger.warning(f"Error reading sessions: {e}")

    SESSION_LIMIT = 45_000_000
    WEEKLY_LIMIT = 180_000_000
    session_pct = min(100, round((buckets["session"]["tokens"] / SESSION_LIMIT) * 100))
    weekly_pct = min(100, round((buckets["week"]["tokens"] / WEEKLY_LIMIT) * 100))

    session_reset = session_window_start + timedelta(hours=5)
    tomorrow = today_start + timedelta(days=1)
    next_week = week_start + timedelta(weeks=1)
    next_month = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1)

    config = _read_config()
    model = (config.get("agents", {}).get("defaults", {}).get("model", {}).get("primary", "unknown")).replace("anthropic/", "")

    return {
        "model": model,
        "tiers": [
            {"label": "Current session (5h)", "percent": session_pct, "resetsIn": _format_duration((session_reset - now).total_seconds() * 1000), "tokens": buckets["session"]["tokens"], "cost": buckets["session"]["cost"]},
            {"label": "Weekly (all models)", "percent": weekly_pct, "resetsIn": _format_duration((next_week - now).total_seconds() * 1000), "tokens": buckets["week"]["tokens"], "cost": buckets["week"]["cost"]},
        ],
        "details": {
            "today": {"tokens": buckets["today"]["tokens"], "cost": buckets["today"]["cost"], "sessions": len(buckets["today"]["sessions"])},
            "week": {"tokens": buckets["week"]["tokens"], "cost": buckets["week"]["cost"], "sessions": len(buckets["week"]["sessions"])},
            "month": {"tokens": buckets["month"]["tokens"], "cost": buckets["month"]["cost"], "sessions": len(buckets["month"]["sessions"])},
        },
    }


@router.get("/models")
async def list_models():
    config = _read_config()
    models_config = config.get("agents", {}).get("defaults", {}).get("models", {})
    primary = config.get("agents", {}).get("defaults", {}).get("model", {}).get("primary")
    fallbacks = config.get("agents", {}).get("defaults", {}).get("model", {}).get("fallbacks", [])
    models = list(set(filter(None, [primary] + fallbacks + list(models_config.keys()))))
    return models


@router.post("/model")
async def set_model(body: dict):
    model = body.get("model")
    if not model:
        raise HTTPException(status_code=400, detail="model required")
    config = _read_config()
    config.setdefault("agents", {}).setdefault("defaults", {}).setdefault("model", {})["primary"] = model
    CONFIG_PATH.write_text(json.dumps(config, indent=2))
    return {"success": True, "model": model}