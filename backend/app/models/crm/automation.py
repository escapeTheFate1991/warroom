"""CRM Automation models - Workflows, templates, Webhooks, and Executions."""

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from . import CrmBase


class WorkflowTemplate(CrmBase):
    """Workflow templates shown in the gallery/library."""
    __tablename__ = "workflow_templates"
    __table_args__ = {"schema": "crm"}


    org_id = Column(Integer)
    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    description = Column(Text)
    category = Column(Text)
    entity_type = Column(Text, nullable=False)
    event = Column(Text, nullable=False)
    condition_type = Column(Text, default="and", server_default="and")
    conditions = Column(JSONB, nullable=False)
    actions = Column(JSONB, nullable=False)
    is_seed = Column(Boolean, nullable=False, default=False, server_default="false")
    seed_key = Column(Text, unique=True)
    derived_from_template_id = Column(Integer, ForeignKey("crm.workflow_templates.id", ondelete="SET NULL"))
    root_template_id = Column(Integer, ForeignKey("crm.workflow_templates.id", ondelete="SET NULL"))
    version = Column(Integer, nullable=False, default=1, server_default="1")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())


class Workflow(CrmBase):
    """Automation workflows."""
    __tablename__ = "workflows"
    __table_args__ = {"schema": "crm"}


    org_id = Column(Integer)
    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    description = Column(Text)
    entity_type = Column(Text)  # deal, person, activity, email
    event = Column(Text)        # created, updated, stage_changed, etc.
    condition_type = Column(Text, default='and')  # and, or
    conditions = Column(JSONB)
    actions = Column(JSONB)
    is_active = Column(Boolean, default=True)
    template_id = Column(Integer, ForeignKey("crm.workflow_templates.id", ondelete="SET NULL"))
    derived_from_workflow_id = Column(Integer, ForeignKey("crm.workflows.id", ondelete="SET NULL"))
    root_workflow_id = Column(Integer, ForeignKey("crm.workflows.id", ondelete="SET NULL"))
    assigned_agent_id = Column(Integer)  # Agent responsible for executing this workflow
    version = Column(Integer, nullable=False, default=1, server_default="1")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())


class WorkflowExecution(CrmBase):
    """Tracks individual workflow execution runs."""
    __tablename__ = "workflow_executions"
    __table_args__ = {"schema": "crm"}


    org_id = Column(Integer)
    id = Column(Integer, primary_key=True)
    workflow_id = Column(Integer, ForeignKey("crm.workflows.id", ondelete="CASCADE"))
    trigger_event = Column(Text, nullable=False)
    trigger_entity_type = Column(Text)
    trigger_entity_id = Column(Integer)
    trigger_data = Column(JSONB, default=dict)
    status = Column(String(20), default="pending")  # pending, running, completed, failed, paused
    current_step = Column(Integer, default=0)
    step_results = Column(JSONB, default=list)  # [{step_index, action_type, status, result, error, started_at, completed_at}]
    context = Column(JSONB, default=dict)  # shared context passed between steps
    error = Column(Text)
    started_at = Column(TIMESTAMP(timezone=True))
    completed_at = Column(TIMESTAMP(timezone=True))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


class Webhook(CrmBase):
    """Webhooks for external integrations."""
    __tablename__ = "webhooks"
    __table_args__ = {"schema": "crm"}


    org_id = Column(Integer)
    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    entity_type = Column(Text)
    description = Column(Text)
    method = Column(Text)  # POST, GET, PUT
    end_point = Column(Text)
    query_params = Column(JSONB)
    headers = Column(JSONB)
    payload_type = Column(Text)
    raw_payload_type = Column(Text)
    payload = Column(JSONB)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())