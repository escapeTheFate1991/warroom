"""CRM Audit and Data Management models."""

from sqlalchemy import Column, Integer, Text, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from . import CrmBase


class AuditLog(CrmBase):
    """Audit trail for CRM entities."""
    __tablename__ = "audit_log"
    __table_args__ = {"schema": "crm"}

    id = Column(Integer, primary_key=True)
    entity_type = Column(Text, nullable=False)
    entity_id = Column(Integer, nullable=False)
    action = Column(Text, nullable=False)  # created, updated, deleted, stage_changed
    user_id = Column(Integer, ForeignKey("crm.users.id", ondelete="SET NULL"))
    old_values = Column(JSONB)
    new_values = Column(JSONB)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User")


class Import(CrmBase):
    """Data import tracking."""
    __tablename__ = "imports"
    __table_args__ = {"schema": "crm"}

    id = Column(Integer, primary_key=True)
    entity_type = Column(Text, nullable=False)
    file_path = Column(Text)
    status = Column(Text, default='pending')
    total_rows = Column(Integer, default=0)
    processed_rows = Column(Integer, default=0)
    errors = Column(JSONB, default=[])
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())


class SavedFilter(CrmBase):
    """User-saved filters."""
    __tablename__ = "saved_filters"
    __table_args__ = {"schema": "crm"}

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    entity_type = Column(Text, nullable=False)
    filters = Column(JSONB, nullable=False)
    user_id = Column(Integer, ForeignKey("crm.users.id", ondelete="CASCADE"))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="saved_filters")