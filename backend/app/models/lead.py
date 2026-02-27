from sqlalchemy import (
    Column, Integer, String, Text, Boolean, Numeric, ARRAY,
    TIMESTAMP, CheckConstraint, ForeignKey, Index
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class SearchJob(Base):
    __tablename__ = "search_jobs"

    id = Column(Integer, primary_key=True)
    query = Column(Text, nullable=False)
    location = Column(Text, nullable=False)
    radius_km = Column(Integer, default=25)
    status = Column(String(20), default="pending")
    total_found = Column(Integer, default=0)
    enriched_count = Column(Integer, default=0)
    error_message = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    leads = relationship("Lead", back_populates="search_job")


class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True)
    search_job_id = Column(Integer, ForeignKey("search_jobs.id", ondelete="SET NULL"))

    # Google Maps data
    google_place_id = Column(Text, unique=True)
    business_name = Column(Text, nullable=False)
    address = Column(Text)
    city = Column(Text)
    state = Column(Text)
    zip = Column(Text)
    country = Column(String(5), default="US")
    phone = Column(Text)
    website = Column(Text)
    google_maps_url = Column(Text)
    google_rating = Column(Numeric(2, 1))
    google_reviews_count = Column(Integer, default=0)
    business_category = Column(Text)
    business_types = Column(ARRAY(Text))
    latitude = Column(Numeric(10, 7))
    longitude = Column(Numeric(10, 7))
    opening_hours = Column(JSONB)

    # Enriched contact data
    emails = Column(ARRAY(Text), default=[])
    owner_name = Column(Text)
    facebook_url = Column(Text)
    instagram_url = Column(Text)
    linkedin_url = Column(Text)
    twitter_url = Column(Text)
    tiktok_url = Column(Text)
    youtube_url = Column(Text)
    yelp_url = Column(Text)

    # Website audit data
    has_website = Column(Boolean, default=False)
    website_status = Column(Integer)
    website_platform = Column(Text)
    website_audit_score = Column(Integer)
    website_audit_grade = Column(Text)
    website_audit_summary = Column(Text)
    website_audit_top_fixes = Column(ARRAY(Text))
    website_audit_date = Column(TIMESTAMP(timezone=True))

    # Pipeline status
    enrichment_status = Column(String(20), default="pending")
    audit_status = Column(String(20), default="pending")
    outreach_status = Column(String(20), default="none")

    # Scoring
    lead_score = Column(Integer, default=0)
    lead_tier = Column(String(20), default="unscored")

    # Metadata
    notes = Column(Text)
    tags = Column(ARRAY(Text), default=[])
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    search_job = relationship("SearchJob", back_populates="leads")