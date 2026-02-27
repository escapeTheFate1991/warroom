"""CRM Automation models - Workflows and Webhooks."""

from sqlalchemy import Column, Integer, Text, Boolean, TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from . import CrmBase


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