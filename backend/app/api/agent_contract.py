"""Shared agent assignment contract types."""

import json
from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import bindparam, text

AssignableEntityType = Literal[
    "kanban_task",
    "leadgen_lead",
    "crm_contact",
    "crm_deal",
    "prospect_workflow",
    "crm_email",
    "email_message",
    "calendar_event",
    "marketing_campaign",
    "marketing_template",
    "marketing_event",
    "social_account",
]

AssignmentStatus = Literal["queued", "running", "completed", "failed", "cancelled"]

ASSIGNABLE_ENTITY_TYPES = (
    "kanban_task",
    "leadgen_lead",
    "crm_contact",
    "crm_deal",
    "prospect_workflow",
    "crm_email",
    "email_message",
    "calendar_event",
    "marketing_campaign",
    "marketing_template",
    "marketing_event",
    "social_account",
)
ASSIGNMENT_STATUSES = ("queued", "running", "completed", "failed", "cancelled")
ACTIVE_ASSIGNMENT_STATUSES = ("queued", "running")
TASK_ASSIGNMENT_ENTITY_TYPE = "kanban_task"


class ContractModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class AgentAssignmentSummary(ContractModel):
    id: str
    agent_id: str
    agent_name: Optional[str] = None
    agent_emoji: Optional[str] = None
    agent_role: Optional[str] = None
    entity_type: AssignableEntityType
    entity_id: str
    title: Optional[str] = None
    priority: int = 0
    status: AssignmentStatus = "queued"
    metadata: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] = Field(default_factory=dict)
    assigned_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class AgentAssignmentCreate(BaseModel):
    entity_type: AssignableEntityType
    entity_id: str
    title: Optional[str] = None
    priority: int = 0
    status: AssignmentStatus = "queued"
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentAssignmentUpdate(BaseModel):
    title: Optional[str] = None
    priority: Optional[int] = None
    status: Optional[AssignmentStatus] = None
    metadata: Optional[dict[str, Any]] = None
    result: Optional[dict[str, Any]] = None


class CalendarEventResponse(ContractModel):
    id: str
    title: str
    date: str
    time: Optional[str] = None
    end_time: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    source: str
    created_at: str
    location: Optional[str] = None
    guests: Optional[str] = None
    notification: Optional[str] = None
    recurrence: Optional[str] = None
    all_day: Optional[bool] = None
    visibility: Optional[str] = None
    status: Optional[str] = None
    html_link: Optional[str] = None
    updated_at: Optional[str] = None
    agent_assignments: list[AgentAssignmentSummary] = Field(default_factory=list)


class PersonalCalendarResponse(ContractModel):
    year: int
    month: int
    events: list[CalendarEventResponse]
    google_connected: bool


class PersonalCalendarEventEnvelope(ContractModel):
    ok: bool = True
    event: CalendarEventResponse


def _decode_assignment_json(value: Any, fallback: Any):
    if value is None:
        return fallback
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return fallback
    return value


async def load_agent_assignment_map(db, *, entity_type: AssignableEntityType, entity_ids: list[str]) -> dict[str, list[dict[str, Any]]]:
    normalized_ids = [str(entity_id) for entity_id in entity_ids if entity_id is not None]
    if not normalized_ids:
        return {}

    from app.api.agents import ensure_tables

    await ensure_tables(db)
    query = text("""
        SELECT aa.*, a.name AS agent_name, a.emoji AS agent_emoji, a.role AS agent_role
        FROM agent_assignments aa
        JOIN agents a ON a.id = aa.agent_id
        WHERE aa.entity_type = :entity_type AND aa.entity_id IN :entity_ids
        ORDER BY aa.priority DESC, aa.assigned_at ASC
    """).bindparams(bindparam("entity_ids", expanding=True))

    result = await db.execute(query, {
        "entity_type": entity_type,
        "entity_ids": normalized_ids,
    })

    assignments_by_entity: dict[str, list[dict[str, Any]]] = {entity_id: [] for entity_id in normalized_ids}
    for row in result.mappings().all():
        assignment = dict(row)
        assignment["metadata"] = _decode_assignment_json(assignment.get("metadata"), {})
        assignment["result"] = _decode_assignment_json(assignment.get("result"), {})
        assignments_by_entity.setdefault(str(assignment["entity_id"]), []).append(assignment)

    return assignments_by_entity