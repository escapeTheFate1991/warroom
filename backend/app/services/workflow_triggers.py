"""Workflow trigger system — matches CRM events to active workflows and fires execution.

When a CRM entity is created/updated, call ``fire_triggers`` with the entity type,
event name, and a dict of the entity's current data.  The function:

1. Queries all active workflows whose ``entity_type`` + ``event`` match.
2. Evaluates each workflow's conditions (``condition_type`` = "and" | "or").
3. Starts execution (via ``start_execution``) for every workflow whose conditions pass.

All executions are kicked off as background tasks so the calling endpoint
returns immediately.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.crm_db import crm_session
from app.models.crm.automation import Workflow
from app.services.workflow_executor import start_execution

logger = logging.getLogger(__name__)


# ── Condition evaluation ─────────────────────────────────────────────

def _resolve_field(entity_data: dict, field: str) -> Any:
    """Resolve a possibly-nested field path like ``emails.0.value``."""
    parts = field.split(".")
    current: Any = entity_data
    for part in parts:
        if current is None:
            return None
        if isinstance(current, dict):
            current = current.get(part)
        elif isinstance(current, (list, tuple)):
            try:
                current = current[int(part)]
            except (ValueError, IndexError):
                return None
        else:
            return None
    return current


def _coerce_numeric(value: Any) -> float | None:
    """Try to coerce a value to a float for numeric comparisons."""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def evaluate_condition(condition: dict, entity_data: dict) -> bool:
    """Evaluate a single condition dict against entity data.

    Condition shape: ``{"field": "...", "operator": "...", "value": "..."}``
    """
    field = condition.get("field", "")
    operator = condition.get("operator", "equals")
    expected = condition.get("value")

    actual = _resolve_field(entity_data, field)

    if operator == "equals":
        return str(actual).lower() == str(expected).lower() if actual is not None and expected is not None else actual == expected

    if operator == "not_equals":
        if actual is None and expected is None:
            return False
        if actual is None or expected is None:
            return True
        return str(actual).lower() != str(expected).lower()

    if operator == "gte":
        a, b = _coerce_numeric(actual), _coerce_numeric(expected)
        return a >= b if a is not None and b is not None else False

    if operator == "lte":
        a, b = _coerce_numeric(actual), _coerce_numeric(expected)
        return a <= b if a is not None and b is not None else False

    if operator == "in":
        # expected should be a list; actual value must be in it
        if isinstance(expected, list):
            return str(actual).lower() in [str(v).lower() for v in expected]
        # Fallback: comma-separated string
        if isinstance(expected, str):
            return str(actual).lower() in [v.strip().lower() for v in expected.split(",")]
        return False

    if operator == "not_in":
        if isinstance(expected, list):
            return str(actual).lower() not in [str(v).lower() for v in expected]
        if isinstance(expected, str):
            return str(actual).lower() not in [v.strip().lower() for v in expected.split(",")]
        return True

    if operator == "is_set":
        return actual is not None

    if operator == "not_empty":
        if actual is None:
            return False
        if isinstance(actual, (str, list, dict)):
            return len(actual) > 0
        return True

    if operator == "contains":
        if actual is None or expected is None:
            return False
        return str(expected).lower() in str(actual).lower()

    logger.warning("Unknown condition operator '%s' — treating as failed", operator)
    return False


def evaluate_conditions(
    conditions: list[dict] | None,
    condition_type: str | None,
    entity_data: dict,
) -> bool:
    """Evaluate a workflow's full condition set.

    * No conditions → always passes.
    * ``condition_type == "and"`` → ALL must pass.
    * ``condition_type == "or"`` → ANY must pass.
    """
    if not conditions:
        return True

    results = [evaluate_condition(c, entity_data) for c in conditions]

    if (condition_type or "and").lower() == "or":
        return any(results)
    return all(results)


# ── Trigger matcher ──────────────────────────────────────────────────

async def _find_matching_workflows(
    db: AsyncSession,
    entity_type: str,
    event: str,
) -> list[Workflow]:
    """Return all active workflows that match the given entity_type + event."""
    result = await db.execute(
        select(Workflow).where(
            Workflow.is_active == True,  # noqa: E712
            Workflow.entity_type == entity_type,
            Workflow.event == event,
        )
    )
    return list(result.scalars().all())


async def _start_workflow_execution(
    workflow: Workflow,
    entity_type: str,
    event: str,
    entity_data: dict,
    entity_id: int | None,
) -> int | None:
    """Start a single workflow execution, returning the execution ID or None on error."""
    try:
        execution_id = await start_execution(
            workflow_id=workflow.id,
            trigger_event=event,
            trigger_entity_type=entity_type,
            trigger_entity_id=entity_id,
            trigger_data=entity_data,
            initial_context=entity_data,
        )
        logger.info(
            "Triggered workflow %d (%s) → execution %d for %s.%s",
            workflow.id, workflow.name, execution_id, entity_type, event,
        )
        return execution_id
    except Exception:
        logger.exception(
            "Failed to start execution for workflow %d (%s) on %s.%s",
            workflow.id, workflow.name, entity_type, event,
        )
        return None


async def fire_triggers(
    entity_type: str,
    event: str,
    entity_data: dict,
    entity_id: int | None = None,
) -> list[int]:
    """Find active workflows matching entity_type + event, evaluate conditions,
    and kick off execution for each match.

    Returns a list of execution IDs that were started.
    """
    execution_ids: list[int] = []
    try:
        async with crm_session() as db:
            await db.execute(text("SET search_path TO crm, public"))
            workflows = await _find_matching_workflows(db, entity_type, event)

        if not workflows:
            return execution_ids

        logger.info(
            "Found %d candidate workflow(s) for %s.%s",
            len(workflows), entity_type, event,
        )

        for workflow in workflows:
            if not evaluate_conditions(workflow.conditions, workflow.condition_type, entity_data):
                logger.debug(
                    "Workflow %d (%s) conditions not met — skipping",
                    workflow.id, workflow.name,
                )
                continue

            exec_id = await _start_workflow_execution(
                workflow, entity_type, event, entity_data, entity_id,
            )
            if exec_id is not None:
                execution_ids.append(exec_id)

    except Exception:
        logger.exception("fire_triggers crashed for %s.%s", entity_type, event)

    return execution_ids


def fire_triggers_background(
    entity_type: str,
    event: str,
    entity_data: dict,
    entity_id: int | None = None,
) -> None:
    """Non-blocking wrapper — schedules ``fire_triggers`` as a background task.

    Call this from API endpoints so they return immediately.
    Uses asyncio.create_task since fire_triggers itself will enqueue arq jobs
    via start_execution (which handles the arq/asyncio dispatch internally).
    """
    asyncio.create_task(
        fire_triggers(entity_type, event, entity_data, entity_id),
        name=f"trigger:{entity_type}.{event}:{entity_id or 'none'}",
    )
