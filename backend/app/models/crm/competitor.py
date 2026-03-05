"""Competitor tracking and intelligence models for CRM."""
from sqlalchemy import Column, Integer, String, DateTime, Date, Text, DECIMAL, Boolean
from sqlalchemy.sql import func

from . import CrmBase


class Competitor(CrmBase):
    """Competitor tracking model."""
    __tablename__ = "competitors"
    __table_args__ = {"schema": "crm"}

    id = Column(Integer, primary_key=True, index=True)
    handle = Column(String, nullable=False)
    platform = Column(String, nullable=False)  # instagram, x, youtube, tiktok, facebook, threads
    
    # Auto-fetched metrics
    followers = Column(Integer, default=0)
    following = Column(Integer, default=0)
    post_count = Column(Integer, default=0)
    bio = Column(Text)
    profile_image_url = Column(String)
    
    # Calculated metrics
    posting_frequency = Column(String)  # e.g., "5-6 posts/week"
    avg_engagement_rate = Column(DECIMAL(5, 2), default=0)
    
    # Manual intelligence fields
    top_angles = Column(Text)  # JSON array as text or newline separated
    signature_formula = Column(String)
    notes = Column(Text)
    
    # Auto-population status
    is_auto_populated = Column(Boolean, default=False)
    last_auto_sync = Column(DateTime)
    auto_sync_enabled = Column(Boolean, default=True)
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())