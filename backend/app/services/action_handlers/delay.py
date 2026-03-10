"""Action handler: delay — pauses workflow execution for a specified duration."""

import logging
import re

logger = logging.getLogger(__name__)

# Simple ISO 8601 duration parser for common patterns
_DURATION_RE = re.compile(
    r"^P"
    r"(?:(\d+)D)?"
    r"(?:T"
    r"(?:(\d+)H)?"
    r"(?:(\d+)M)?"
    r"(?:(\d+)S)?"
    r")?$"
)


def parse_iso_duration_seconds(duration: str) -> int | None:
    """Parse an ISO 8601 duration string into total seconds.

    Supports: P1D, PT2H, PT30M, PT10S, P1DT2H30M, etc.
    Returns None if unparseable.
    """
    m = _DURATION_RE.match(duration.strip().upper())
    if not m:
        return None
    days = int(m.group(1) or 0)
    hours = int(m.group(2) or 0)
    minutes = int(m.group(3) or 0)
    seconds = int(m.group(4) or 0)
    return days * 86400 + hours * 3600 + minutes * 60 + seconds


async def handle(step: dict, context: dict, execution: dict) -> dict:
    """Return the delay duration so the executor can schedule a resume.

    Step config keys:
        duration (str): ISO 8601 duration like "PT2M", "P1D", "PT24H".
    """
    duration_str = step.get("duration", "")
    if not duration_str:
        return {"success": False, "result": None, "error": "Missing 'duration' in step config"}

    delay_seconds = parse_iso_duration_seconds(duration_str)
    if delay_seconds is None:
        return {"success": False, "result": None, "error": f"Invalid ISO 8601 duration: {duration_str}"}

    logger.info("Delay step: %s (%d seconds)", duration_str, delay_seconds)
    return {
        "success": True,
        "result": {"delay_seconds": delay_seconds, "duration": duration_str},
        "error": None,
    }
