"""CRM Activity models - Activities and participants."""

from sqlalchemy import Column, Integer, Text, Boolean, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from . import CrmBase


class Activity(CrmBase):
    """CRM Activities (calls, meetings, notes, tasks)."""
    __tablename__ = "activities"
    __table_args__ = {"schema": "crm"}

    id = Column(Integer, primary_key=True)
    title = Column(Text)
    type = Column(Text, nullable=False)  # call, meeting, note, task, email, lunch
    comment = Column(Text)
    additional = Column(JSONB)
    location = Column(Text)
    schedule_from = Column(TIMESTAMP(timezone=True))
    schedule_to = Column(TIMESTAMP(timezone=True))
    is_done = Column(Boolean, default=False)
    user_id = Column(Integer, ForeignKey("crm.users.id", ondelete="SET NULL"))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="activities")
    
    # Many-to-many relationships
    deals = relationship("Deal", secondary="crm.deal_activities", back_populates="activities")
    persons = relationship("Person", secondary="crm.person_activities", back_populates="activities")
    participants = relationship("Person", secondary="crm.activity_participants")


class ActivityParticipant(CrmBase):
    """Activity participants junction table."""
    __tablename__ = "activity_participants"
    __table_args__ = {"schema": "crm"}

    activity_id = Column(Integer, ForeignKey("crm.activities.id", ondelete="CASCADE"), primary_key=True)
    person_id = Column(Integer, ForeignKey("crm.persons.id", ondelete="CASCADE"), primary_key=True)


class DealActivity(CrmBase):
    """Deal-Activity junction table."""
    __tablename__ = "deal_activities"
    __table_args__ = {"schema": "crm"}

    deal_id = Column(Integer, ForeignKey("crm.deals.id", ondelete="CASCADE"), primary_key=True)
    activity_id = Column(Integer, ForeignKey("crm.activities.id", ondelete="CASCADE"), primary_key=True)


class PersonActivity(CrmBase):
    """Person-Activity junction table."""
    __tablename__ = "person_activities"
    __table_args__ = {"schema": "crm"}

    person_id = Column(Integer, ForeignKey("crm.persons.id", ondelete="CASCADE"), primary_key=True)
    activity_id = Column(Integer, ForeignKey("crm.activities.id", ondelete="CASCADE"), primary_key=True)