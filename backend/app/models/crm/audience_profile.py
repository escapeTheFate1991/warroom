"""Audience profile model for tracking commenter demographics and engagement."""

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Index, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB

from app.models.base import Base


class EngagementLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class AudienceProfile(Base):
    """Tracks profile data for commenters and likers across competitor posts."""
    
    __tablename__ = "audience_profiles"
    __table_args__ = (
        Index('ix_audience_profiles_org_id', 'org_id'),
        Index('ix_audience_profiles_username_platform', 'username', 'platform'),
        Index('ix_audience_profiles_engagement_level', 'engagement_level'),
        Index('ix_audience_profiles_interaction_count', 'interaction_count'),
        UniqueConstraint('org_id', 'username', 'platform', name='uq_audience_profiles_org_username_platform'),
        {'schema': 'crm'}
    )
    
    id = Column(Integer, primary_key=True)
    org_id = Column(Integer, nullable=False)
    username = Column(String(255), nullable=False)
    platform = Column(String(50), nullable=False)
    profile_url = Column(String(500), nullable=True)
    
    # Profile metadata
    display_name = Column(String(255), nullable=True)
    bio = Column(Text, nullable=True)
    followers = Column(Integer, nullable=True)
    following = Column(Integer, nullable=True)
    post_count = Column(Integer, nullable=True)
    is_verified = Column(Boolean, default=False, nullable=False)
    is_business = Column(Boolean, default=False, nullable=False)
    
    # Engagement tracking
    engagement_level = Column(String(10), nullable=False, default="medium")  # high/medium/low based on interaction frequency
    first_seen_at = Column(DateTime, nullable=False)
    last_seen_at = Column(DateTime, nullable=False)
    interaction_count = Column(Integer, default=0, nullable=False)  # Total comments/likes across all competitor posts
    
    # Extensible metadata
    profile_data = Column(JSONB, nullable=True)  # For additional scraped data
    
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<AudienceProfile(username='{self.username}', platform='{self.platform}', engagement_level='{self.engagement_level}')>"