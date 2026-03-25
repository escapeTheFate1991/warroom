"""Profile Intelligence Data Model
Combines OAuth data, scraped profile data, and video analysis for comprehensive profile intel.
"""
from datetime import datetime
from typing import Dict, List, Any, Optional
from sqlalchemy import Column, Integer, String, DateTime, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from . import CrmBase


class ProfileIntelData(CrmBase):
    """Model for storing consolidated profile intelligence data."""
    __tablename__ = "profile_intel_data"
    __table_args__ = (
        {"schema": "crm"},
    )

    id = Column(Integer, primary_key=True)
    org_id = Column(Integer, nullable=False, index=True)
    profile_id = Column(String(255), nullable=False)  # Instagram username or handle
    platform = Column(String(50), nullable=False, default="instagram")
    last_synced_at = Column(DateTime, nullable=True)
    
    # OAuth data from connected accounts
    oauth_data = Column(JSONB, nullable=True, comment="OAuth analytics data: followerCount, followingCount, postCount, reachMetrics, audienceDemographics, topPerformingPosts, engagementRate, replyRate, avgReplyTime")
    
    # Scraped public data
    scraped_data = Column(JSONB, nullable=True, comment="Public profile data: bio, profilePicUrl, linkInBio, highlightCovers, recentPostCaptions, gridAesthetic, postingFrequency, hashtagUsage")
    
    # Video analysis results  
    processed_videos = Column(JSONB, nullable=True, comment="Analyzed videos: [{videoId, grade, strengths, weaknesses}]")
    
    # Grading scores across 6 categories
    grades = Column(JSONB, nullable=True, comment="Profile grades: {profileOptimization: {score, details}, videoMessaging, storyboarding, audienceEngagement, contentConsistency, replyQuality}")
    
    # AI-generated recommendations
    recommendations = Column(JSONB, nullable=True, comment="Actionable recommendations: {profileChanges: [{what, why, priority}], videosToDelete: [{videoId, reason}], keepDoing: [{what, evidence}], stopDoing: [{what, evidence}], nextSteps: [{action, expectedImpact, priority}]}")
    
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<ProfileIntelData(profile_id='{self.profile_id}', platform='{self.platform}', org_id={self.org_id})>"

    @classmethod
    def create_empty_data_structure(cls) -> Dict[str, Any]:
        """Create empty data structures for initialization."""
        return {
            "oauth_data": {
                "followerCount": 0,
                "followingCount": 0,
                "postCount": 0,
                "reachMetrics": {},
                "audienceDemographics": {},
                "topPerformingPosts": [],
                "engagementRate": 0.0,
                "replyRate": 0.0,
                "avgReplyTime": 0.0
            },
            "scraped_data": {
                "bio": "",
                "profilePicUrl": "",
                "linkInBio": "",
                "highlightCovers": [],
                "recentPostCaptions": [],
                "gridAesthetic": "",
                "postingFrequency": "",
                "hashtagUsage": []
            },
            "processed_videos": [],
            "grades": {
                "profileOptimization": {"score": 0, "details": ""},
                "videoMessaging": {"score": 0, "details": ""},
                "storyboarding": {"score": 0, "details": ""},
                "audienceEngagement": {"score": 0, "details": ""},
                "contentConsistency": {"score": 0, "details": ""},
                "replyQuality": {"score": 0, "details": ""}
            },
            "recommendations": {
                "profileChanges": [],
                "videosToDelete": [],
                "keepDoing": [],
                "stopDoing": [],
                "nextSteps": []
            }
        }