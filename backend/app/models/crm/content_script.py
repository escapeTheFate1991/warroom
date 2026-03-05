"""Content script generation models for competitive intelligence."""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from . import CrmBase


class ContentScript(CrmBase):
    """Generated content scripts based on competitor analysis."""
    __tablename__ = "content_scripts"
    __table_args__ = {"schema": "crm"}

    id = Column(Integer, primary_key=True, index=True)
    competitor_id = Column(Integer, ForeignKey("crm.competitors.id"), nullable=True)
    platform = Column(String, nullable=False)  # instagram, youtube, x, tiktok, facebook
    title = Column(String)
    hook = Column(Text)
    body = Column(Text)
    cta = Column(Text)
    topic = Column(String)
    source_post_url = Column(String)
    status = Column(String, default='draft')  # draft, generated, saved
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    competitor = relationship("Competitor", back_populates="content_scripts")