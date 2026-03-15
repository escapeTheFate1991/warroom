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
    __table_args__ = {"schema": "leadgen"}

    id = Column(Integer, primary_key=True)
    org_id = Column(Integer)
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
    __table_args__ = {"schema": "leadgen"}

    id = Column(Integer, primary_key=True)
    org_id = Column(Integer)
    search_job_id = Column(Integer, ForeignKey("leadgen.search_jobs.id", ondelete="SET NULL"))

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
    website_phones = Column(ARRAY(Text), default=[])
    owner_name = Column(Text)
    facebook_url = Column(Text)
    instagram_url = Column(Text)
    linkedin_url = Column(Text)
    twitter_url = Column(Text)
    tiktok_url = Column(Text)
    youtube_url = Column(Text)
    yelp_url = Column(Text)

    # Review intelligence
    yelp_rating = Column(Numeric(2, 1))
    yelp_reviews_count = Column(Integer, default=0)
    review_highlights = Column(ARRAY(Text), default=[])  # Top pain-point quotes from reviews
    review_sentiment_score = Column(Numeric(3, 2))  # -1.0 to 1.0
    review_pain_points = Column(ARRAY(Text), default=[])  # Extracted pain points
    review_opportunity_flags = Column(ARRAY(Text), default=[])  # Flags relevant to our services
    reviews_scraped_at = Column(TIMESTAMP(timezone=True))

    # Website audit data
    has_website = Column(Boolean, default=False)
    website_status = Column(Integer)
    website_platform = Column(Text)
    website_audit_score = Column(Integer)
    website_audit_grade = Column(Text)
    website_audit_summary = Column(Text)
    website_audit_top_fixes = Column(ARRAY(Text))
    website_audit_date = Column(TIMESTAMP(timezone=True))

    # Deep AI audit (comprehensive Claude-powered analysis)
    deep_audit_results = Column(JSONB)
    deep_audit_score = Column(Integer)
    deep_audit_grade = Column(String(2))
    deep_audit_date = Column(TIMESTAMP(timezone=True))

    # Audit lite (quick surface-level flags from enrichment crawl)
    audit_lite_flags = Column(ARRAY(Text), default=[])

    # BBB intelligence
    bbb_url = Column(Text)
    bbb_rating = Column(Text)  # A+ to F
    bbb_accredited = Column(Boolean)
    bbb_complaints = Column(Integer, default=0)
    bbb_summary = Column(Text)

    # Glassdoor intelligence
    glassdoor_url = Column(Text)
    glassdoor_rating = Column(Numeric(2, 1))
    glassdoor_review_count = Column(Integer, default=0)
    glassdoor_summary = Column(Text)

    # Reddit mentions
    reddit_mentions = Column(JSONB, default=[])  # [{title, url, subreddit, snippet, date}]

    # News mentions
    news_mentions = Column(JSONB, default=[])  # [{title, url, source, snippet, date}]

    # Social presence scan
    social_scan = Column(JSONB, default={})  # {platform: {url, exists, followers, summary}}

    # Source
    lead_source = Column(Text, default="google_places")
    enrichment_error = Column(Text)

    # Pipeline status
    enrichment_status = Column(String(20), default="pending")
    audit_status = Column(String(20), default="pending")
    outreach_status = Column(String(20), default="none")  # none, contacted, in_progress, won, lost

    # Scoring
    lead_score = Column(Integer, default=0)
    lead_tier = Column(String(20), default="unscored")

    # CRM / Outreach tracking
    contacted_by = Column(Text)                          # Who made the call
    contacted_at = Column(TIMESTAMP(timezone=True))      # When
    contact_outcome = Column(String(20))                 # won, lost, follow_up, no_answer
    contact_notes = Column(Text)                         # Why won/lost, call notes
    contact_who_answered = Column(Text)                  # Name of person who answered
    contact_owner_name = Column(Text)                    # Business owner name
    contact_economic_buyer = Column(Text)                # Economic buyer (decision maker)
    contact_champion = Column(Text)                      # Internal champion for the deal
    contact_history = Column(JSONB, default=[])          # Array of {date, by, notes, outcome}

    # Metadata
    notes = Column(Text)
    tags = Column(ARRAY(Text), default=[])
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    search_job = relationship("SearchJob", back_populates="leads")