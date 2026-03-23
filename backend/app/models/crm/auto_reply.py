"""Auto-reply rules and log models for keyword-based social media auto-replies."""

from sqlalchemy import Boolean, Column, ForeignKey, Integer, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.sql import func

from . import CrmBase


class AutoReplyRule(CrmBase):
    """Auto-reply rule for comments, DMs, and follow events."""
    __tablename__ = "auto_reply_rules"
    __table_args__ = {"schema": "crm"}

    id = Column(Integer, primary_key=True)
    org_id = Column(Integer, nullable=False)
    platform = Column(Text, nullable=False, default="instagram", server_default="instagram")
    rule_type = Column(Text, nullable=False)  # 'comment', 'dm', or 'follow'
    name = Column(Text, nullable=False)
    keywords = Column(ARRAY(Text), nullable=True, default=[])  # Optional for follow triggers
    replies = Column(ARRAY(Text), nullable=False)
    match_mode = Column(Text, nullable=True, default="any", server_default="any")  # any, all, exact
    case_sensitive = Column(Boolean, nullable=False, default=False, server_default="false")
    is_active = Column(Boolean, nullable=False, default=True, server_default="true")
    delivery_channels = Column(ARRAY(Text), nullable=False, default=["dm"], server_default="'{dm}'")  # comment, dm
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())


class AutoReplyLog(CrmBase):
    """Log of auto-replies sent."""
    __tablename__ = "auto_reply_log"
    __table_args__ = {"schema": "crm"}

    id = Column(Integer, primary_key=True)
    rule_id = Column(Integer, ForeignKey("crm.auto_reply_rules.id", ondelete="SET NULL"))
    org_id = Column(Integer, nullable=False)
    platform = Column(Text, nullable=False)
    rule_type = Column(Text, nullable=False)
    trigger_type = Column(Text, nullable=False, default="keyword", server_default="keyword")  # keyword, follow
    original_text = Column(Text, nullable=True, default="", server_default="")  # Empty for follow events
    matched_keyword = Column(Text)
    reply_sent = Column(Text)
    delivery_channel = Column(Text, nullable=False)  # comment, dm
    social_account_id = Column(Integer)
    external_id = Column(Text)
    username = Column(Text)  # For follow events
    status = Column(Text, nullable=False, default="sent", server_default="sent")  # sent, failed, skipped
    error_message = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
