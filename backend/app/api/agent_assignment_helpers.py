"""Shared helpers for loading agent assignment summaries across entity types."""

from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy import text

logger = logging.getLogger(__name__)


async def load_assignment_summaries(
    db,
    entity_type: str,
    entity_ids: list[int | str],
) -> dict[str, list[dict[str, Any]]]:
    """Load agent assignments for a list of entities, keyed by entity_id string.

    Returns a dict mapping entity_id (str) to a list of assignment dicts
    including agent name, emoji, and role.

    Uses fully-qualified `crm.` schema so it works from any DB session
    (leadgen, crm, or public search_path).
    """
    if not entity_ids:
        return {}

    str_ids = [str(eid) for eid in entity_ids]

    try:
        result = await db.execute(text("""
            SELECT
                aa.id, aa.agent_id, aa.entity_id, aa.title, aa.priority,
                aa.status, aa.assigned_at, aa.started_at, aa.completed_at,
                a.name AS agent_name, a.emoji AS agent_emoji, a.role AS agent_role
            FROM crm.agent_assignments aa
            JOIN crm.agents a ON a.id = aa.agent_id
            WHERE aa.entity_type = :entity_type
              AND aa.entity_id = ANY(:entity_ids)
            ORDER BY aa.priority DESC, aa.assigned_at ASC
        """), {"entity_type": entity_type, "entity_ids": str_ids})
    except Exception as exc:
        # If table doesn't exist yet (first boot), return empty gracefully
        logger.warning("agent_assignments query failed (table may not exist yet): %s", exc)
        return {}

    assignments: dict[str, list[dict[str, Any]]] = {}
    for row in result.mappings().all():
        entry = dict(row)
        # Parse JSONB fields if needed
        for key in ("metadata", "result"):
            val = entry.get(key)
            if isinstance(val, str):
                try:
                    entry[key] = json.loads(val)
                except json.JSONDecodeError:
                    entry[key] = {}
        eid = str(entry["entity_id"])
        assignments.setdefault(eid, []).append(entry)

    return assignments
