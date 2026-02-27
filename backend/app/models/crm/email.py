"""CRM Email models."""

from sqlalchemy import Column, Integer, Text, Boolean, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from . import CrmBase


class Email(CrmBase):
    """CRM Emails."""
    __tablename__ = "emails"
    __table_args__ = {"schema": "crm"}

    id = Column(Integer, primary_key=True)
    subject = Column(Text)
    source = Column(Text, nullable=False)  # web, imap
    name = Column(Text)
    reply = Column(Text)
    is_read = Column(Boolean, default=False)
    folders = Column(JSONB)
    from_addr = Column(JSONB)
    sender = Column(JSONB)
    reply_to = Column(JSONB)
    cc = Column(JSONB)
    bcc = Column(JSONB)
    unique_id = Column(Text, unique=True)
    message_id = Column(Text, unique=True)
    reference_ids = Column(JSONB)
    person_id = Column(Integer, ForeignKey("crm.persons.id", ondelete="SET NULL"))
    deal_id = Column(Integer, ForeignKey("crm.deals.id", ondelete="SET NULL"))
    parent_id = Column(Integer, ForeignKey("crm.emails.id", ondelete="SET NULL"))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    person = relationship("Person", back_populates="emails")
    deal = relationship("Deal", back_populates="emails")
    parent = relationship("Email", remote_side=[id])
    attachments = relationship("EmailAttachment", back_populates="email", cascade="all, delete-orphan")


class EmailAttachment(CrmBase):
    """Email attachments."""
    __tablename__ = "email_attachments"
    __table_args__ = {"schema": "crm"}

    id = Column(Integer, primary_key=True)
    email_id = Column(Integer, ForeignKey("crm.emails.id", ondelete="CASCADE"))
    name = Column(Text)
    content_type = Column(Text)
    size = Column(Integer)
    filepath = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    # Relationships
    email = relationship("Email", back_populates="attachments")


class EmailTemplate(CrmBase):
    """Email templates."""
    __tablename__ = "email_templates"
    __table_args__ = {"schema": "crm"}

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    subject = Column(Text)
    content = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    campaigns = relationship("MarketingCampaign", back_populates="template")