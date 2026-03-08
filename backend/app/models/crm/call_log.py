"""CRM call log model for Telnyx voice events."""

from sqlalchemy import Column, ForeignKey, Integer, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from . import CrmBase


class CallLog(CrmBase):
    """Stored Telnyx call lifecycle record."""

    __tablename__ = "call_logs"
    __table_args__ = {"schema": "crm"}

    id = Column(Integer, primary_key=True)
    call_session_id = Column(Text, unique=True, index=True)
    call_control_id = Column(Text, index=True)
    call_leg_id = Column(Text, index=True)
    from_number = Column(Text)
    to_number = Column(Text)
    direction = Column(Text)
    status = Column(Text)
    started_at = Column(TIMESTAMP(timezone=True))
    answered_at = Column(TIMESTAMP(timezone=True))
    ended_at = Column(TIMESTAMP(timezone=True))
    duration_seconds = Column(Integer)
    recording_url = Column(Text)
    transcript = Column(Text)
    telnyx_payload = Column(JSONB)
    deal_id = Column(Integer, ForeignKey("crm.deals.id", ondelete="SET NULL"))
    person_id = Column(Integer, ForeignKey("crm.persons.id", ondelete="SET NULL"))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    deal = relationship("Deal")
    person = relationship("Person")