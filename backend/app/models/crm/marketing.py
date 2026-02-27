"""CRM Marketing models - Campaigns and Events."""

from sqlalchemy import Column, Integer, Text, Boolean, Date, TIMESTAMP, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from . import CrmBase


class MarketingEvent(CrmBase):
    """Marketing events."""
    __tablename__ = "marketing_events"
    __table_args__ = {"schema": "crm"}

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    description = Column(Text)
    date = Column(Date)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    # Relationships
    campaigns = relationship("MarketingCampaign", back_populates="event")


class MarketingCampaign(CrmBase):
    """Marketing campaigns."""
    __tablename__ = "marketing_campaigns"
    __table_args__ = {"schema": "crm"}

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    subject = Column(Text)
    status = Column(Boolean, default=False)
    type = Column(Text)  # newsletter, event
    mail_to = Column(Text)
    spooling = Column(Text)
    template_id = Column(Integer, ForeignKey("crm.email_templates.id", ondelete="SET NULL"))
    event_id = Column(Integer, ForeignKey("crm.marketing_events.id", ondelete="SET NULL"))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    template = relationship("EmailTemplate", back_populates="campaigns")
    event = relationship("MarketingEvent", back_populates="campaigns")