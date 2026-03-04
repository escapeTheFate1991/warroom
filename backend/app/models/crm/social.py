"""Social media account and analytics models for CRM."""
from sqlalchemy import Column, Integer, String, DateTime, Date, DECIMAL, Text, ForeignKey
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class SocialAccount(Base):
    """Social media account model."""
    __tablename__ = "social_accounts"
    __table_args__ = {"schema": "crm"}

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("crm.users.id", ondelete="CASCADE"))
    platform = Column(String, nullable=False)  # instagram, facebook, threads, youtube, x
    username = Column(String)
    profile_url = Column(String)
    access_token = Column(Text)  # encrypted later
    refresh_token = Column(Text)
    follower_count = Column(Integer, default=0)
    following_count = Column(Integer, default=0)
    post_count = Column(Integer, default=0)
    connected_at = Column(DateTime, default=func.now())
    last_synced = Column(DateTime)
    status = Column(String, default="connected")  # connected, expired, error

    # Relationships
    analytics = relationship("SocialAnalytics", back_populates="account", cascade="all, delete-orphan")


class SocialAnalytics(Base):
    """Social media analytics model."""
    __tablename__ = "social_analytics"
    __table_args__ = {"schema": "crm"}

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("crm.social_accounts.id", ondelete="CASCADE"))
    metric_date = Column(Date, nullable=False)
    impressions = Column(Integer, default=0)
    reach = Column(Integer, default=0)
    engagement = Column(Integer, default=0)
    engagement_rate = Column(DECIMAL(5, 2), default=0)
    followers_gained = Column(Integer, default=0)
    followers_lost = Column(Integer, default=0)
    profile_views = Column(Integer, default=0)
    link_clicks = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    saves = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    video_views = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())

    # Relationships
    account = relationship("SocialAccount", back_populates="analytics")