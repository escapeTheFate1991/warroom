"""Pydantic schemas for LeadGen API request/response."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

from app.api.agent_contract import AgentAssignmentSummary


class SearchRequest(BaseModel):
    query: str
    location: str
    radius_km: int = 25
    max_results: int = 60


class SearchJobResponse(BaseModel):
    id: int
    query: str
    location: str
    status: str
    total_found: int
    enriched_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class LeadResponse(BaseModel):
    id: int
    search_job_id: int | None
    business_name: str
    address: str | None
    city: str | None
    state: str | None
    zip: str | None
    phone: str | None
    website: str | None
    google_maps_url: str | None
    google_rating: float | None
    google_reviews_count: int
    business_category: str | None

    # Enriched
    emails: list[str]
    website_phones: list[str]
    owner_name: str | None
    facebook_url: str | None
    instagram_url: str | None
    linkedin_url: str | None
    twitter_url: str | None
    tiktok_url: str | None
    youtube_url: str | None
    yelp_url: str | None

    # Reviews
    yelp_rating: float | None = None
    yelp_reviews_count: int = 0
    review_highlights: list[str] | None = None
    review_sentiment_score: float | None = None
    review_pain_points: list[str] | None = None
    review_opportunity_flags: list[str] | None = None

    # Website audit
    has_website: bool
    website_platform: str | None
    website_audit_score: int | None
    website_audit_grade: str | None
    website_audit_summary: str | None
    website_audit_top_fixes: list[str] | None
    audit_lite_flags: list[str]

    # Deep AI audit
    deep_audit_results: dict | None = None
    deep_audit_score: int | None = None
    deep_audit_grade: str | None = None
    deep_audit_date: datetime | None = None

    # BBB
    bbb_url: str | None = None
    bbb_rating: str | None = None
    bbb_accredited: bool | None = None
    bbb_complaints: int = 0
    bbb_summary: str | None = None

    # Glassdoor
    glassdoor_url: str | None = None
    glassdoor_rating: float | None = None
    glassdoor_review_count: int = 0
    glassdoor_summary: str | None = None

    # Reddit mentions
    reddit_mentions: list[dict] | None = None

    # News mentions
    news_mentions: list[dict] | None = None

    # Social presence scan
    social_scan: dict | None = None

    # Status
    enrichment_status: str
    audit_status: str
    outreach_status: str
    lead_score: int
    lead_tier: str
    tags: list[str]
    notes: str | None

    # CRM
    contacted_by: str | None
    contacted_at: datetime | None
    contact_outcome: str | None
    contact_notes: str | None
    contact_who_answered: str | None
    contact_owner_name: str | None
    contact_economic_buyer: str | None
    contact_champion: str | None
    contact_history: list[dict] | None

    agent_assignments: list[AgentAssignmentSummary] = Field(default_factory=list)
    created_at: datetime

    class Config:
        from_attributes = True


class LeadUpdate(BaseModel):
    notes: str | None = None
    tags: list[str] | None = None
    outreach_status: str | None = None
    lead_tier: str | None = None


class ContactLogRequest(BaseModel):
    """Log a contact attempt / call result."""
    contacted_by: str
    outcome: str  # won, lost, follow_up, no_answer, voicemail, callback
    notes: Optional[str] = None
    who_answered: Optional[str] = None
    owner_name: Optional[str] = None
    economic_buyer: Optional[str] = None
    champion: Optional[str] = None


class StatsResponse(BaseModel):
    total_leads: int
    enriched: int
    with_website: int
    without_website: int
    hot_leads: int
    warm_leads: int
    cold_leads: int
    avg_lead_score: float
    top_categories: list[dict]
    contacted: int
    won: int
    lost: int


class WebsiteAuditResult(BaseModel):
    score: int
    grade: str
    summary: str
    top_fixes: list[str]


class DeepAuditRequest(BaseModel):
    """Request body for triggering a deep AI audit."""
    competitor_urls: list[dict] | None = None  # [{"url": "...", "name": "..."}]
    industry: str | None = None  # Override business_category


class DeepAuditResponse(BaseModel):
    """Response for deep audit results."""
    url: str
    overall_score: int
    overall_grade: str
    audited_at: str
    duration_seconds: float = 0
    categories: dict = {}
    findings: list[dict] = []
    ai_summary: str = ""
    ai_recommendations: list[str] = []
    competitor_analysis: list[dict] = []
    competitor_comparison: dict = {}
    extraction: dict = {}
    error: str = ""
