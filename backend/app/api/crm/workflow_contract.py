"""Workflow contract helpers shared by API handlers and tests."""

from copy import deepcopy
from typing import Any


def coerce_workflow_steps(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [deepcopy(step) for step in value if isinstance(step, dict)]
    if isinstance(value, dict):
        return [deepcopy(value)]
    return []


def normalize_workflow_payload(workflow_data: Any, *, existing: Any = None) -> dict[str, Any]:
    raw = workflow_data if isinstance(workflow_data, dict) else workflow_data.model_dump(exclude_unset=True)
    data = dict(raw)

    if existing is None or "condition_type" in data:
        data["condition_type"] = data.get("condition_type") or getattr(existing, "condition_type", "and") or "and"
    if existing is None or "conditions" in data:
        data["conditions"] = coerce_workflow_steps(data.get("conditions", getattr(existing, "conditions", [])))
    if existing is None or "actions" in data:
        data["actions"] = coerce_workflow_steps(data.get("actions", getattr(existing, "actions", [])))

    return data


def workflow_contract_fields(workflow: Any) -> dict[str, Any]:
    return {
        "id": workflow.id,
        "name": workflow.name,
        "description": workflow.description,
        "entity_type": workflow.entity_type,
        "event": workflow.event,
        "condition_type": workflow.condition_type or "and",
        "conditions": coerce_workflow_steps(getattr(workflow, "conditions", None)),
        "actions": coerce_workflow_steps(getattr(workflow, "actions", None)),
        "is_active": bool(workflow.is_active),
        "created_at": workflow.created_at,
        "updated_at": workflow.updated_at,
    }