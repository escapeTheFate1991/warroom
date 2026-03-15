"""CRM Marketing models - Campaigns and Events."""

from sqlalchemy import Column, Integer, Text, Boolean, Date, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from . import CrmBase


class MarketingEvent(CrmBase):
    """Marketing events."""
    __tablename__ = "marketing_events"
    __table_args__ = {"schema": "crm"}


    org_id = Column(Integer)
    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    description = Column(Text)
    date = Column(Date)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    # Relationships
    campaigns = relationship("MarketingCampaign", back_populates="event")


class MarketingCampaign(CrmBase):
    """Marketing campaigns with channel-aware delivery foundations."""
    __tablename__ = "marketing_campaigns"
    __table_args__ = {"schema": "crm"}


    org_id = Column(Integer)
    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    channel = Column(Text, nullable=False, default="email", server_default="email")
    subject = Column(Text)
    status = Column(Boolean, default=False)
    type = Column(Text)  # newsletter, event
    use_case = Column(Text)
    mail_to = Column(Text)
    spooling = Column(Text)
    audience = Column(JSONB)
    schedule = Column(JSONB)
    content = Column(JSONB)
    channel_config = Column(JSONB)
    template_id = Column(Integer, ForeignKey("crm.email_templates.id", ondelete="SET NULL"))
    event_id = Column(Integer, ForeignKey("crm.marketing_events.id", ondelete="SET NULL"))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    template = relationship("EmailTemplate", back_populates="campaigns")
    event = relationship("MarketingEvent", back_populates="campaigns")