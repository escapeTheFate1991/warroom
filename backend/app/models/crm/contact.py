"""CRM Contact models - Person, Organization, Tags."""

from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from . import CrmBase


class Organization(CrmBase):
    """CRM Organizations/Companies."""
    __tablename__ = "organizations"
    __table_args__ = {"schema": "crm"}

    id = Column(Integer, primary_key=True)
    name = Column(Text, unique=True, nullable=False)
    address = Column(JSONB)
    user_id = Column(Integer, ForeignKey("crm.users.id", ondelete="SET NULL"))
    # Link to leadgen business if originated from lead gen
    leadgen_lead_id = Column(Integer)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="organizations")
    persons = relationship("Person", back_populates="organization")
    deals = relationship("Deal", back_populates="organization")


class Person(CrmBase):
    """CRM Persons/Contacts."""
    __tablename__ = "persons"
    __table_args__ = {"schema": "crm"}

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    emails = Column(JSONB, default=[])  # [{value: "x@y.com", label: "work"}]
    contact_numbers = Column(JSONB)     # [{value: "555-1234", label: "mobile"}]
    job_title = Column(Text)
    organization_id = Column(Integer, ForeignKey("crm.organizations.id", ondelete="SET NULL"))
    user_id = Column(Integer, ForeignKey("crm.users.id", ondelete="SET NULL"))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="persons")
    organization = relationship("Organization", back_populates="persons")
    deals = relationship("Deal", back_populates="person")
    emails = relationship("Email", back_populates="person")
    quotes = relationship("Quote", back_populates="person")
    
    # Many-to-many relationships
    activities = relationship("Activity", secondary="crm.person_activities", back_populates="persons")
    tags = relationship("Tag", secondary="crm.person_tags", back_populates="persons")


class Tag(CrmBase):
    """Tags for various entities."""
    __tablename__ = "tags"
    __table_args__ = {"schema": "crm"}

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    color = Column(Text)
    user_id = Column(Integer, ForeignKey("crm.users.id", ondelete="CASCADE"))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="tags")
    deals = relationship("Deal", secondary="crm.deal_tags", back_populates="tags")
    persons = relationship("Person", secondary="crm.person_tags", back_populates="tags")


class PersonTag(CrmBase):
    """Person-Tag junction table."""
    __tablename__ = "person_tags"
    __table_args__ = {"schema": "crm"}

    person_id = Column(Integer, ForeignKey("crm.persons.id", ondelete="CASCADE"), primary_key=True)
    tag_id = Column(Integer, ForeignKey("crm.tags.id", ondelete="CASCADE"), primary_key=True)


class DealTag(CrmBase):
    """Deal-Tag junction table."""
    __tablename__ = "deal_tags"
    __table_args__ = {"schema": "crm"}

    deal_id = Column(Integer, ForeignKey("crm.deals.id", ondelete="CASCADE"), primary_key=True)
    tag_id = Column(Integer, ForeignKey("crm.tags.id", ondelete="CASCADE"), primary_key=True)