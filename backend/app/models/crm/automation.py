"""CRM Automation models - Workflows, templates, and Webhooks."""

from sqlalchemy import Boolean, Column, ForeignKey, Integer, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from . import CrmBase


class WorkflowTemplate(CrmBase):
    """Workflow templates shown in the gallery/library."""
    __tablename__ = "workflow_templates"
    __table_args__ = {"schema": "crm"}

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


class Webhook(CrmBase):
    """Webhooks for external integrations."""
    __tablename__ = "webhooks"
    __table_args__ = {"schema": "crm"}

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