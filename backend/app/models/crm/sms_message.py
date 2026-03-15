"""CRM SMS message model for Telnyx messaging events."""

from sqlalchemy import Column, ForeignKey, Integer, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from . import CrmBase


class SMSMessage(CrmBase):
    """Stored Telnyx SMS lifecycle record."""

    __tablename__ = "sms_messages"
    __table_args__ = {"schema": "crm"}


    org_id = Column(Integer)
    id = Column(Integer, primary_key=True)
    telnyx_message_id = Column(Text, unique=True, index=True)
    direction = Column(Text)
    from_number = Column(Text)
    to_number = Column(Text)
    body = Column(Text)
    status = Column(Text)
    deal_id = Column(Integer, ForeignKey("crm.deals.id", ondelete="SET NULL"))
    person_id = Column(Integer, ForeignKey("crm.persons.id", ondelete="SET NULL"))
    telnyx_payload = Column(JSONB)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    deal = relationship("Deal")
    person = relationship("Person")