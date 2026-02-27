"""Pydantic schemas for LeadGen API request/response."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


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

    # Website audit
    has_website: bool
    website_platform: str | None
    website_audit_score: int | None
    website_audit_grade: str | None
    website_audit_summary: str | None
    website_audit_top_fixes: list[str] | None
    audit_lite_flags: list[str]

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
