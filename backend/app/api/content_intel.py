"""Enhanced Content intelligence API endpoints for competitive analysis and script generation."""
import logging
import json
import re
import httpx
import asyncio
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any, Tuple
from collections import Counter, defaultdict
import string

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field
from sqlalchemy import select, text, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.api.auth import get_current_user
from app.db.crm_db import get_tenant_db
from app.services.tenant import get_org_id, get_user_id
from app.models.crm.competitor import Competitor
from app.models.crm.content_script import ContentScript
from app.models.crm.social import SocialAccount
from app.models.crm.user import User
from app.api.scraper import (
    sync_instagram_competitor,
    sync_instagram_competitor_batch,
    calculate_competitor_engagement_score,
)
from app.services.instagram_scraper import scrape_profile, ScrapedProfile
from app.api.contracts import _get_business_settings

# Import NLP libraries for better text processing
try:
    import nltk
    from nltk.corpus import stopwords
    from nltk.tokenize import word_tokenize, sent_tokenize
    from nltk.util import ngrams
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.cluster import KMeans
    NLTK_AVAILABLE = True
    
    # Download required NLTK data
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        nltk.download('punkt', quiet=True)
    
    try:
        nltk.data.find('corpora/stopwords')
    except LookupError:
        nltk.download('stopwords', quiet=True)
        
except ImportError:
    NLTK_AVAILABLE = False

logger = logging.getLogger(__name__)

router = APIRouter()

_competitor_sync_locks: Dict[int, asyncio.Lock] = {}


def _get_competitor_sync_lock(competitor_id: int) -> asyncio.Lock:
    """Return the in-process lock used to dedupe competitor sync requests."""
    lock = _competitor_sync_locks.get(competitor_id)
    if lock is None:
        lock = asyncio.Lock()
        _competitor_sync_locks[competitor_id] = lock
    return lock


# Enhanced Pydantic models
class CompetitorPost(BaseModel):
    """Individual competitor post data."""
    id: Optional[int] = None
    text: str
    likes: int = 0
    comments: int = 0
    shares: int = 0
    timestamp: datetime
    url: str
    engagement_score: float = 0.0
    hook: Optional[str] = None
    media_type: Optional[str] = None
    has_transcript: bool = False
    has_comments: bool = False


class CompetitorContentResponse(BaseModel):
    """Response for competitor content endpoint."""
    competitor_id: int
    platform: str
    handle: str
    posts: List[CompetitorPost]
    total_posts: int
    avg_engagement: float


class TrendingTopic(BaseModel):
    """Enhanced trending topic with clustering and engagement weighting."""
    topic: str
    frequency: int
    avg_engagement: float
    recency_weight: float
    final_score: float
    sources: List[str]
    keywords: List[str]
    related_topics: List[str] = []


class TrendingTopicsResponse(BaseModel):
    """Response for trending topics endpoint."""
    topics: List[TrendingTopic]
    total_analyzed_posts: int
    timeframe_days: int = 30


class TopContentItem(BaseModel):
    """Top performing content item."""
    id: Optional[int] = None
    text: str
    hook: str
    likes: int
    comments: int
    shares: int
    engagement_score: float
    platform: str
    competitor_handle: str
    url: str
    timestamp: datetime
    virality_score: float = 0.0


class TopContentResponse(BaseModel):
    """Response for top content endpoint."""
    posts: List[TopContentItem]
    total_posts: int


class HookItem(BaseModel):
    """Extracted hook with engagement data."""
    hook: str
    engagement_score: float
    platform: str
    competitor_handle: str
    source_url: str
    virality_score: float = 0.0


class HooksResponse(BaseModel):
    """Response for hooks endpoint."""
    hooks: List[HookItem]
    total_hooks: int


class AudienceQuestion(BaseModel):
    question: str
    likes: int = 0


class AudiencePainPoint(BaseModel):
    pain: str
    likes: int = 0


class AudienceTheme(BaseModel):
    theme: str
    count: int = 0


class AudienceProductMention(BaseModel):
    product: str
    count: int = 0


class AudienceCommenter(BaseModel):
    username: str
    count: int = 0


class AudienceIntelResponse(BaseModel):
    posts_analyzed: int = 0
    comments_analyzed: int = 0
    sentiment: str = "neutral"
    sentiment_breakdown: Dict[str, int] = Field(default_factory=dict)
    sentiment_percentages: Dict[str, float] = Field(default_factory=dict)
    questions: List[AudienceQuestion] = Field(default_factory=list)
    pain_points: List[AudiencePainPoint] = Field(default_factory=list)
    themes: List[AudienceTheme] = Field(default_factory=list)
    product_mentions: List[AudienceProductMention] = Field(default_factory=list)
    top_commenters: List[AudienceCommenter] = Field(default_factory=list)
    engagement_quality: Dict[str, int] = Field(default_factory=dict)
    content_formats: Dict[str, int] = Field(default_factory=dict)


class InstagramAdviceItem(BaseModel):
    title: str
    detail: str
    metric: Optional[str] = None
    category: Optional[str] = None  # bio, content, growth, profile, engagement


class ProfilePostSummary(BaseModel):
    """Lightweight summary of a recent post for the frontend."""
    shortcode: str = ""
    caption_preview: str = ""
    hook: str = ""
    likes: int = 0
    comments: int = 0
    views: int = 0
    media_type: str = "image"
    posted_at: Optional[datetime] = None
    engagement_score: float = 0.0


class InstagramProfileAdviceResponse(BaseModel):
    connected: bool = False
    platform: str = "instagram"
    username: Optional[str] = None
    status: str = "not_connected"
    summary: str = ""
    follower_count: int = 0
    following_count: int = 0
    post_count: int = 0
    last_synced: Optional[datetime] = None
    days_analyzed: int = 0
    avg_engagement_rate: float = 0.0
    avg_reach: int = 0
    avg_profile_views: int = 0
    avg_video_views: int = 0
    total_link_clicks: int = 0
    net_followers: int = 0
    # Scraped profile data
    bio: Optional[str] = None
    external_url: Optional[str] = None
    bio_links: List[Dict[str, str]] = Field(default_factory=list)
    profile_pic_url: Optional[str] = None
    is_verified: bool = False
    category: Optional[str] = None
    posting_frequency: Optional[str] = None
    recent_posts: List[ProfilePostSummary] = Field(default_factory=list)
    recommendations: List[InstagramAdviceItem] = Field(default_factory=list)


class ScriptGenerationRequest(BaseModel):
    """Request for script generation."""
    competitor_id: Optional[int] = None
    platform: str
    topic: Optional[str] = None
    hook_style: Optional[str] = None  # comparison, bold_claim, confession, etc.
    count: int = Field(default=6, ge=1, le=12)


class SimilarVideoReference(BaseModel):
    """Reference to a similar competitor video/post used as inspiration."""
    competitor_handle: str
    platform: str
    source_url: str = ""
    hook: str = ""
    engagement_score: float = 0.0


class GeneratedScript(BaseModel):
    """Generated content script."""
    id: Optional[int] = None
    competitor_id: Optional[int] = None
    platform: str
    title: str
    hook: str
    body_outline: str
    cta: str
    topic: Optional[str] = None
    source_post_url: Optional[str] = None
    estimated_duration: Optional[str] = None
    created_at: Optional[datetime] = None
    predicted_views: int = 0
    predicted_engagement: float = 0.0
    predicted_engagement_rate: float = 0.0
    virality_score: float = 0.0
    business_alignment_score: float = 0.0
    business_alignment_label: str = "Low"
    business_alignment_reason: str = ""
    source_competitors: List[str] = Field(default_factory=list)
    similar_videos: List[SimilarVideoReference] = Field(default_factory=list)
    scene_map: List[Dict[str, str]] = Field(default_factory=list)


def calculate_engagement_score(likes: int, comments: int, shares: int) -> float:
    """Calculate engagement score with weighted values."""
    return likes * 1.0 + comments * 3.0 + shares * 5.0


def calculate_recency_weight(posted_at: datetime) -> float:
    """Calculate recency boost factor."""
    if posted_at.tzinfo is not None:
        posted_at = posted_at.astimezone(timezone.utc).replace(tzinfo=None)

    days_ago = (datetime.now() - posted_at).days
    
    if days_ago <= 7:
        return 2.0  # 2x boost for last 7 days
    elif days_ago <= 14:
        return 1.5  # 1.5x boost for last 14 days
    else:
        return 1.0  # No boost for older content


COMMON_STOPWORDS = {
    "about", "after", "again", "also", "because", "been", "being", "between",
    "could", "from", "have", "into", "just", "more", "most", "over", "than",
    "that", "their", "them", "they", "this", "those", "through", "until",
    "very", "what", "when", "where", "which", "while", "with", "your", "you",
    "ours", "ourselves", "into", "onto", "then", "here", "there", "than",
}


def _coerce_posted_at(value: Any) -> datetime:
    """Return a naive datetime for mixed cached/serialized values."""
    if isinstance(value, datetime):
        posted_at = value
    elif isinstance(value, str):
        try:
            posted_at = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            posted_at = datetime.now(timezone.utc)
    else:
        posted_at = datetime.now(timezone.utc)

    if posted_at.tzinfo is not None:
        return posted_at.astimezone(timezone.utc).replace(tzinfo=None)
    return posted_at


def _post_engagement_score(post: Dict[str, Any]) -> float:
    """Recompute engagement from stored interaction counts."""
    return calculate_competitor_engagement_score(
        post.get("likes", 0) or 0,
        post.get("comments", 0) or 0,
        post.get("shares", 0) or 0,
        platform=post.get("platform"),
    )


def _post_engagement_rate(post: Dict[str, Any]) -> float:
    """Estimate engagement rate from cached counts and competitor followers."""
    followers = post.get("followers", 0) or 0
    if followers <= 0:
        return 0.0
    return _post_engagement_score(post) / float(followers)


def _post_virality_score(post: Dict[str, Any]) -> float:
    """Blend raw engagement, engagement rate, and recency for ranking."""
    recency_weight = calculate_recency_weight(_coerce_posted_at(post.get("posted_at")))
    engagement = _post_engagement_score(post)
    engagement_rate = _post_engagement_rate(post)
    return round((engagement * recency_weight) + (engagement_rate * 1000.0), 2)


def _sorted_posts_for_analysis(posts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Sort cached posts by virality, engagement, and recency."""
    return sorted(
        posts,
        key=lambda post: (
            _post_virality_score(post),
            _post_engagement_score(post),
            _post_engagement_rate(post),
            _coerce_posted_at(post.get("posted_at")),
        ),
        reverse=True,
    )


def _post_hook(post: Dict[str, Any]) -> str:
    """Return a reliable hook for a cached post."""
    stored_hook = str(post.get("hook") or "").strip()
    if stored_hook:
        return stored_hook
    return extract_hook_from_text(post.get("post_text", "") or "")


def _estimate_predicted_views(post: Dict[str, Any]) -> int:
    """Estimate likely views from the best available cached signals."""
    direct_views = int(post.get("views", 0) or 0)
    if direct_views > 0:
        return direct_views

    shares_or_views = int(post.get("shares", 0) or 0)
    if shares_or_views > 0:
        return shares_or_views

    engagement = _post_engagement_score(post)
    followers = int(post.get("followers", 0) or 0)
    engagement_rate = _post_engagement_rate(post)

    if followers > 0:
        modeled_reach = followers * min(max(engagement_rate * 6.0, 0.08), 0.45)
        return int(max(modeled_reach, engagement * 4.0, (post.get("likes", 0) or 0) * 6.0))

    return int(max(engagement * 4.0, (post.get("likes", 0) or 0) * 6.0))


def _build_similar_video_references(
    posts: List[Dict[str, Any]],
    limit: int = 3,
) -> List[SimilarVideoReference]:
    """Create similar-video references from ranked competitor posts."""
    references: List[SimilarVideoReference] = []
    seen: set[str] = set()

    for post in _sorted_posts_for_analysis(posts):
        signature = str(post.get("post_url") or _post_hook(post) or "").strip()
        if not signature or signature in seen:
            continue

        seen.add(signature)
        references.append(
            SimilarVideoReference(
                competitor_handle=post.get("handle", ""),
                platform=post.get("platform", ""),
                source_url=post.get("post_url", "") or "",
                hook=_post_hook(post),
                engagement_score=round(_post_engagement_score(post), 1),
            )
        )

        if len(references) >= limit:
            break

    return references


def _estimated_duration_for_platform(platform: str) -> str:
    """Return a default runtime based on the output platform."""
    platform_name = (platform or "instagram").lower()
    if platform_name == "youtube":
        return "6-8 minutes"
    if platform_name == "x":
        return "8-post thread"
    if platform_name == "tiktok":
        return "30-45 seconds"
    return "45-60 seconds"


def _collect_candidate_topics(
    posts: List[Dict[str, Any]],
    trending_topics: List[str],
    requested_topic: Optional[str],
    max_topics: int,
) -> List[str]:
    """Collect unique topic candidates from request, trends, and source posts."""
    topics: List[str] = []
    seen: set[str] = set()

    def add_topic(topic: Optional[str]) -> None:
        cleaned = str(topic or "").strip()
        if not cleaned:
            return
        key = cleaned.lower()
        if key in seen:
            return
        seen.add(key)
        topics.append(cleaned)

    add_topic(requested_topic)
    for topic in trending_topics:
        add_topic(topic)
    for post in posts:
        add_topic(_derive_topic_label(post))

    if not topics:
        topics.append("Competitive content angle")

    return topics[: max(1, max_topics)]


def _extract_keywords(text: str, limit: int = 8) -> List[str]:
    """Extract stable lowercase keywords without requiring external services."""
    if not text:
        return []

    cleaned = re.sub(r"#[A-Za-z0-9_]+", " ", text.lower())
    tokens = re.findall(r"[a-z0-9]+", cleaned)
    keywords: List[str] = []

    for token in tokens:
        if len(token) < 3 or token in COMMON_STOPWORDS:
            continue
        if token not in keywords:
            keywords.append(token)
        if len(keywords) >= limit:
            break

    return keywords


def classify_post_format(post_text: str, hook: str = "", content_analysis: dict = None) -> str:
    """Classify a post into one of the 8 viral formats based on text patterns."""
    text = f"{hook} {post_text}".lower()
    
    # Enhanced rules-based classification with more patterns per format
    
    # Myth Buster - challenging beliefs/misconceptions
    myth_patterns = [
        "myth", "everyone thinks", "they told you", "actually wrong", "lie", 
        "misconception", "false", "debunk", "truth is", "reality is", 
        "stop believing", "common mistake", "actually", "wrong about",
        "don't believe", "not true", "fact check", "busted"
    ]
    if any(w in text for w in myth_patterns):
        return "myth_buster"
    
    # Exposé - revealing secrets/insider information
    expose_patterns = [
        "nobody talks about", "secret", "they don't want you to know", "hidden", 
        "behind the scenes", "what really happens", "insider", "truth about",
        "exposed", "reveal", "industry secret", "never tell you", "won't admit",
        "dirty secret", "what they hide", "real story", "leaked", "confession"
    ]
    if any(w in text for w in expose_patterns):
        return "expose"
    
    # Transformation - before/after journey
    transformation_patterns = [
        "before", "after", "transformed", "went from", "journey", "change",
        "transformation", "from zero to", "how i became", "evolution",
        "progress", "growth", "metamorphosis", "makeover", "upgrade",
        "before vs after", "then vs now", "my story", "changed everything"
    ]
    if any(w in text for w in transformation_patterns):
        return "transformation"
    
    # POV - relatable scenarios
    pov_patterns = [
        "pov:", "pov ", "when you", "that moment when", "imagine", "picture this",
        "you know that feeling", "we've all been there", "relatable", "me when",
        "anyone else", "is it just me", "that awkward moment", "scenario"
    ]
    if any(w in text for w in pov_patterns):
        return "pov"
    
    # Speed Run - fast tutorials/processes
    speed_patterns = [
        "step by step", "tutorial", "how to", "guide", "in under", "quick way",
        "fast", "speed", "rapid", "minutes", "seconds", "steps", "process",
        "method", "technique", "shortcut", "hack", "easy way", "simple steps"
    ]
    if any(w in text for w in speed_patterns):
        return "speed_run"
    
    # Challenge - dares and participation
    challenge_patterns = [
        "try this", "challenge", "for 7 days", "for 30 days", "dare", "bet you",
        "can you", "challenge accepted", "who else", "join me", "attempt",
        "test", "experiment", "see if you can", "i dare you", "let's see"
    ]
    if any(w in text for w in challenge_patterns):
        return "challenge"
    
    # Show Don't Tell - visual demonstrations
    visual_patterns = [
        "watch this", "look at this", "see what happens", "no words needed",
        "just watch", "observe", "check this out", "visual", "demonstration",
        "see the difference", "watch how", "look closely", "notice", "witness"
    ]
    if any(w in text for w in visual_patterns):
        return "show_dont_tell"
    
    # Direct-to-Camera - opinions/authentic commentary
    opinion_patterns = [
        "hot take", "unpopular opinion", "hear me out", "i think", "rant",
        "honestly", "real talk", "truth bomb", "let me tell you", "my take",
        "controversial", "bold statement", "authentic", "raw", "unfiltered"
    ]
    if any(w in text for w in opinion_patterns):
        return "direct_to_camera"
    
    # Enhanced classification using content_analysis if available
    if content_analysis:
        format_hints = content_analysis.get("content_format", "").lower()
        if format_hints in ["transformation", "before_after"]:
            return "transformation"
        elif format_hints in ["tutorial", "how_to", "educational"]:
            return "speed_run"
        elif format_hints in ["opinion", "commentary", "rant"]:
            return "direct_to_camera"
        elif format_hints in ["demonstration", "visual_proof"]:
            return "show_dont_tell"
    
    return "unclassified"


def _derive_topic_label(post: Dict[str, Any]) -> str:
    """Derive a compact topic label from a cached post."""
    text = post.get("post_text", "") or ""
    phrases = extract_ngrams(text, 3) + extract_ngrams(text, 2)
    if phrases:
        return phrases[0].title()

    keywords = _extract_keywords(text, limit=4)
    if keywords:
        return " ".join(keywords).title()

    hook = post.get("hook") or extract_hook_from_text(text)
    return (hook or "Competitive content angle")[:60].strip()


def _alignment_label(score: float) -> str:
    """Map alignment score to a user-facing label."""
    if score >= 80:
        return "High"
    if score >= 60:
        return "Medium"
    return "Low"


def _score_business_alignment(topic: str, hook: str, business_settings: Dict[str, Any]) -> Tuple[float, str, str]:
    """Score how well a script concept aligns to business messaging settings."""
    business_text = " ".join(
        str(value or "")
        for value in business_settings.values()
        if isinstance(value, str) and value.strip()
    )
    business_keywords = _extract_keywords(business_text, limit=12)
    script_keywords = set(_extract_keywords(f"{topic} {hook}", limit=10))

    if not business_keywords:
        score = 55.0
        reason = "Business settings are sparse, so this idea is scored on reusable educational messaging rather than named offers."
        return score, _alignment_label(score), reason

    overlap = [keyword for keyword in business_keywords if keyword in script_keywords]
    score = min(100.0, 35.0 + (len(overlap) / max(1, len(set(business_keywords)))) * 65.0)

    if overlap:
        reason = "Aligned with business messaging via: %s." % ", ".join(overlap[:4])
    else:
        reason = "This concept is strong on hook performance, but it may need your offer, proof, or CTA tightened to match business messaging."

    return round(score, 1), _alignment_label(score), reason


def _build_script_cta(platform: str, business_settings: Dict[str, Any]) -> str:
    """Create a platform-specific CTA using business settings when possible."""
    platform_name = (platform or "instagram").lower()
    business_name = business_settings.get("business_name") or "your brand"

    if platform_name == "youtube":
        return "Comment your biggest question, then subscribe for the next %s breakdown." % business_name
    if platform_name == "x":
        return "Reply with your take and repost if you want more %s-style breakdowns." % business_name
    if platform_name == "tiktok":
        return "Comment 'script' if you want a follow-up angle tailored to %s." % business_name
    return "Save this for your next shoot and DM %s if you want the full playbook." % business_name


def _build_script_body(
    hook: str,
    topic: str,
    platform: str,
    business_settings: Dict[str, Any],
    source_competitors: List[str],
) -> str:
    """Build a detailed, data-driven short-form script body."""
    business_name = business_settings.get("business_name") or "your brand"
    business_tagline = business_settings.get("business_tagline") or "your positioning"
    source_line = ", ".join(source_competitors[:3]) if source_competitors else "top competitors"

    return (
        f"Hook: {hook}\n\n"
        f"Scene 1 — Pattern interrupt:\n"
        f"Open on the pain, mistake, or curiosity gap around {topic.lower()}. Keep it tight enough that the viewer knows exactly why they should stop scrolling.\n\n"
        f"Scene 2 — Proof from the market:\n"
        f"Reference what is already working across {source_line}. Show the repeated angle, objection, or transformation these competitor videos are proving in-market.\n\n"
        f"Scene 3 — Your spin:\n"
        f"Translate that same angle into the {business_name} point of view. Tie it back to {business_tagline} so the script sounds like your brand, not a copy of the source material.\n\n"
        f"Scene 4 — Tactical takeaway:\n"
        f"Give the viewer one concrete move they can apply immediately about {topic.lower()}. Make it specific enough to feel valuable before the CTA arrives.\n\n"
        f"Scene 5 — CTA:\n"
        f"{_build_script_cta(platform, business_settings)}"
    )


def score_hook(hook_text: str, posts: list, format_slug: str = None) -> dict:
    """Score a hook's 'stop the scroll' potential (1-10) based on competitor data."""
    # Baseline score
    score = 5.0
    reasons = []
    
    if not hook_text or len(hook_text.strip()) < 5:
        return {"score": 1.0, "reasons": ["Hook too short or empty"]}
    
    hook_lower = hook_text.lower()
    hook_words = hook_text.split()
    
    # Length check (5-15 words is sweet spot)
    word_count = len(hook_words)
    if 5 <= word_count <= 15:
        score += 1.0
        reasons.append(f"Optimal length ({word_count} words)")
    elif word_count < 5:
        score -= 1.0
        reasons.append("Too short - may lack impact")
    elif word_count > 20:
        score -= 1.5
        reasons.append("Too long - may lose attention")
    
    # Power words detection
    power_words = [
        "secret", "exposed", "truth", "revealed", "shocking", "proven", "mistake", 
        "wrong", "lie", "scam", "never", "always", "everyone", "nobody", "only",
        "first", "last", "best", "worst", "ultimate", "complete", "simple", "easy",
        "fast", "quick", "instant", "immediately", "guaranteed", "free", "new"
    ]
    power_word_count = sum(1 for word in power_words if word in hook_lower)
    if power_word_count >= 2:
        score += 1.5
        reasons.append(f"Strong power words ({power_word_count} found)")
    elif power_word_count == 1:
        score += 0.5
        reasons.append("Contains power word")
    
    # Emotional triggers
    emotion_triggers = {
        "curiosity": ["what", "how", "why", "when", "where", "which", "secret", "hidden", "unknown"],
        "urgency": ["now", "today", "immediately", "before", "after", "until", "deadline"],
        "exclusivity": ["only", "exclusive", "private", "insider", "member", "select"],
        "controversy": ["wrong", "lie", "scam", "myth", "fake", "truth", "exposed", "revealed"],
        "social_proof": ["everyone", "nobody", "most people", "experts", "studies", "proven"]
    }
    
    triggered_emotions = []
    for emotion, triggers in emotion_triggers.items():
        if any(trigger in hook_lower for trigger in triggers):
            triggered_emotions.append(emotion)
    
    if len(triggered_emotions) >= 2:
        score += 1.0
        reasons.append(f"Multiple emotional triggers ({', '.join(triggered_emotions)})")
    elif triggered_emotions:
        score += 0.5
        reasons.append(f"Emotional trigger: {triggered_emotions[0]}")
    
    # Pattern match against high-engagement hooks from competitor data
    if posts:
        median_eng = sorted([p.get("engagement_score", 0) for p in posts])[len(posts)//2] if posts else 0
        high_eng_hooks = [p.get("hook", "") for p in posts if p.get("engagement_score", 0) > median_eng]
        
        # Simple n-gram overlap calculation
        hook_ngrams = set()
        words = hook_lower.split()
        for i in range(len(words)):
            for j in range(i+1, min(i+4, len(words)+1)):  # 2-4 word phrases
                hook_ngrams.add(" ".join(words[i:j]))
        
        similarity_scores = []
        for comp_hook in high_eng_hooks:
            if not comp_hook:
                continue
            comp_words = comp_hook.lower().split()
            comp_ngrams = set()
            for i in range(len(comp_words)):
                for j in range(i+1, min(i+4, len(comp_words)+1)):
                    comp_ngrams.add(" ".join(comp_words[i:j]))
            
            if hook_ngrams and comp_ngrams:
                overlap = len(hook_ngrams & comp_ngrams) / len(hook_ngrams | comp_ngrams)
                similarity_scores.append(overlap)
        
        if similarity_scores:
            max_similarity = max(similarity_scores)
            if max_similarity > 0.3:
                score += 1.0
                reasons.append(f"Similar to high-performing competitor hooks ({max_similarity:.1%} overlap)")
            elif max_similarity > 0.15:
                score += 0.5
                reasons.append("Some similarity to successful hooks")
    
    # Format-specific pattern matching
    if format_slug:
        format_bonuses = {
            "myth_buster": ["wrong", "myth", "lie", "actually", "truth", "reality"],
            "expose": ["secret", "hidden", "revealed", "nobody", "insider", "behind"],
            "transformation": ["before", "after", "from", "to", "became", "changed"],
            "pov": ["pov", "when you", "imagine", "picture", "moment when"],
            "speed_run": ["how to", "step by step", "quick", "fast", "easy", "simple"],
            "challenge": ["try this", "dare", "challenge", "can you", "test"],
            "show_dont_tell": ["watch", "look", "see", "check out", "observe"],
            "direct_to_camera": ["honestly", "real talk", "truth", "opinion", "take"]
        }
        
        format_words = format_bonuses.get(format_slug, [])
        if any(word in hook_lower for word in format_words):
            score += 0.5
            reasons.append(f"Matches {format_slug.replace('_', ' ')} format patterns")
    
    # Specific anti-patterns (reduce score)
    weak_starters = ["so", "um", "hey", "hi", "hello", "today i", "in this"]
    if any(hook_lower.startswith(starter) for starter in weak_starters):
        score -= 1.0
        reasons.append("Weak opening - avoid generic starters")
    
    if "?" in hook_text and hook_text.count("?") > 2:
        score -= 0.5
        reasons.append("Too many questions - may seem indecisive")
    
    # Final score normalization
    final_score = round(min(max(score, 1.0), 10.0), 1)
    
    # Add overall assessment
    if final_score >= 8.0:
        reasons.insert(0, "Excellent hook - high scroll-stopping potential")
    elif final_score >= 6.5:
        reasons.insert(0, "Strong hook - good engagement potential")
    elif final_score >= 5.0:
        reasons.insert(0, "Decent hook - room for improvement")
    else:
        reasons.insert(0, "Weak hook - needs significant revision")
    
    return {"score": final_score, "reasons": reasons[:6]}  # Limit to 6 reasons


def _build_script_scenes(
    hook: str,
    topic: str,
    platform: str,
    business_settings: Dict[str, Any],
) -> List[Dict[str, str]]:
    """Build structured scene metadata for drill-down display and persistence."""
    business_name = business_settings.get("business_name") or "your brand"
    return [
        {"scene": "Hook", "direction": hook, "goal": "Stop the scroll in the first second."},
        {"scene": "Problem", "direction": f"Name the pain point tied to {topic.lower()}.", "goal": "Create relevance."},
        {"scene": "Proof", "direction": "Show what competitors are already proving with real market traction.", "goal": "Build credibility."},
        {"scene": "Brand angle", "direction": f"Connect the lesson back to {business_name}.", "goal": "Align with business messaging."},
        {"scene": "CTA", "direction": _build_script_cta(platform, business_settings), "goal": "Convert attention into action."},
    ]


def _serialize_script_metadata(script: GeneratedScript) -> str:
    """Pack richer script metadata into ContentScript.scene_map JSON."""
    return json.dumps({
        "estimated_duration": script.estimated_duration,
        "predicted_views": script.predicted_views,
        "predicted_engagement": script.predicted_engagement,
        "predicted_engagement_rate": script.predicted_engagement_rate,
        "virality_score": script.virality_score,
        "business_alignment_score": script.business_alignment_score,
        "business_alignment_label": script.business_alignment_label,
        "business_alignment_reason": script.business_alignment_reason,
        "source_competitors": script.source_competitors,
        "similar_videos": [video.model_dump() for video in script.similar_videos],
        "scenes": script.scene_map,
    })


def _parse_script_metadata(scene_map_text: Optional[str]) -> Dict[str, Any]:
    """Parse JSON stored in ContentScript.scene_map, supporting older rows gracefully."""
    if not scene_map_text:
        return {}

    try:
        parsed = json.loads(scene_map_text)
    except (TypeError, json.JSONDecodeError):
        return {}

    if isinstance(parsed, list):
        return {"scenes": parsed}
    if isinstance(parsed, dict):
        return parsed
    return {}


def _content_script_to_response(script: ContentScript) -> GeneratedScript:
    """Convert stored script rows into the richer API response shape."""
    metadata = _parse_script_metadata(script.scene_map)
    similar_videos = [
        SimilarVideoReference(**video)
        for video in metadata.get("similar_videos", [])
        if isinstance(video, dict)
    ]

    return GeneratedScript(
        id=script.id,
        competitor_id=script.competitor_id,
        platform=script.platform,
        title=script.title or script.hook or "Generated script",
        hook=script.hook or script.title or "",
        body_outline=script.body or "",
        cta=script.cta or "",
        topic=script.topic,
        source_post_url=script.source_post_url,
        estimated_duration=(metadata.get("estimated_duration") or "45-60 seconds"),
        created_at=script.created_at,
        predicted_views=int(metadata.get("predicted_views", 0) or 0),
        predicted_engagement=float(metadata.get("predicted_engagement", 0.0) or 0.0),
        predicted_engagement_rate=float(metadata.get("predicted_engagement_rate", 0.0) or 0.0),
        virality_score=float(metadata.get("virality_score", 0.0) or 0.0),
        business_alignment_score=float(metadata.get("business_alignment_score", 0.0) or 0.0),
        business_alignment_label=str(metadata.get("business_alignment_label", "Low") or "Low"),
        business_alignment_reason=str(metadata.get("business_alignment_reason", "") or ""),
        source_competitors=list(metadata.get("source_competitors", []) or []),
        similar_videos=similar_videos,
        scene_map=list(metadata.get("scenes", []) or []),
    )


def extract_hook_from_text(text: str) -> str:
    """Extract hook (first sentence) from post text."""
    if not text:
        return ""
    
    # Clean text
    text = text.strip()
    lines = text.split('\n')
    first_line = lines[0].strip()
    
    if NLTK_AVAILABLE:
        try:
            sentences = sent_tokenize(first_line)
            if sentences:
                hook = sentences[0].strip()
                # Return hook if it's reasonable length
                if 10 <= len(hook) <= 200:
                    return hook
        except Exception:
            pass
    
    # Fallback: extract until first punctuation
    for delimiter in ['.', '!', '?']:
        if delimiter in first_line:
            hook = first_line.split(delimiter)[0].strip()
            if 10 <= len(hook) <= 200:
                return hook
    
    # Return first 150 chars if no good hook found
    return first_line[:150] + "..." if len(first_line) > 150 else first_line


def extract_ngrams(text: str, n: int = 2) -> List[str]:
    """Extract n-grams from text using NLTK if available."""
    if not text or not NLTK_AVAILABLE:
        return []
    
    try:
        # Clean and tokenize
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)  # Remove punctuation
        tokens = word_tokenize(text)
        
        # Remove stopwords
        stop_words = set(stopwords.words('english'))
        tokens = [token for token in tokens if token not in stop_words and len(token) > 2]
        
        # Generate n-grams
        n_grams = list(ngrams(tokens, n))
        return [' '.join(gram) for gram in n_grams if len(' '.join(gram)) > 5]
    except Exception as e:
        logger.warning("Error extracting n-grams: %s", e)
        return []


def cluster_topics(topics: List[str], max_clusters: int = 5) -> Dict[str, List[str]]:
    """Cluster similar topics together using TF-IDF and K-means."""
    if not topics or not NLTK_AVAILABLE or len(topics) < 2:
        return {topic: [topic] for topic in topics}
    
    try:
        # Use TF-IDF to vectorize topics
        vectorizer = TfidfVectorizer(
            max_features=100,
            ngram_range=(1, 2),
            stop_words='english'
        )
        
        # Fit and transform topics
        topic_vectors = vectorizer.fit_transform(topics)
        
        # Determine optimal number of clusters (min of topics/2 and max_clusters)
        n_clusters = min(max(len(topics) // 2, 1), max_clusters)
        
        # Cluster topics
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        cluster_labels = kmeans.fit_predict(topic_vectors)
        
        # Group topics by cluster
        clusters = defaultdict(list)
        for i, label in enumerate(cluster_labels):
            clusters[f"cluster_{label}"].append(topics[i])
        
        # Convert to regular dict with representative topic names
        result = {}
        for cluster_id, cluster_topics in clusters.items():
            # Use most frequent topic as cluster name
            cluster_name = Counter(cluster_topics).most_common(1)[0][0]
            result[cluster_name] = cluster_topics
        
        return result
        
    except Exception as e:
        logger.warning("Error clustering topics: %s", e)
        # Fallback: group by first word
        clusters = defaultdict(list)
        for topic in topics:
            first_word = topic.split()[0] if topic else "other"
            clusters[first_word].append(topic)
        return dict(clusters)


async def get_social_account_token(db: AsyncSession, user_id: int, org_id: int, platform: str) -> Optional[str]:
    """Get access token for connected social account that user can access."""
    try:
        from app.services.oauth_scoping import get_accessible_accounts
        
        # Get accounts user can access for this platform
        accounts = await get_accessible_accounts(db, user_id, org_id, platform)
        
        if not accounts:
            logger.warning("No accessible %s accounts for user %s in org %s", platform, user_id, org_id)
            return None
            
        # Return the first available access token
        for account in accounts:
            if account.access_token and account.status == "connected":
                return account.access_token
                
        return None
    except Exception as e:
        logger.error("Failed to get token for %s: %s", platform, e)
        return None


async def save_competitor_posts(db: AsyncSession, competitor_id: int, org_id: int, platform: str, 
                               posts: List[CompetitorPost]) -> bool:
    """Save competitor posts to cache table."""
    try:
        # Delete old posts for this competitor/platform (with org_id check via competitor)
        await db.execute(
            text("""
                DELETE FROM crm.competitor_posts 
                WHERE competitor_id = :competitor_id AND platform = :platform 
                AND competitor_id IN (SELECT id FROM crm.competitors WHERE id = :competitor_id AND org_id = :org_id)
            """),
            {"competitor_id": competitor_id, "platform": platform, "org_id": org_id}
        )
        
        # Insert new posts
        for post in posts:
            await db.execute(
                text("""
                    INSERT INTO crm.competitor_posts 
                    (competitor_id, platform, post_text, likes, comments, shares, 
                     engagement_score, hook, post_url, posted_at, fetched_at)
                    VALUES (:competitor_id, :platform, :post_text, :likes, :comments, :shares,
                            :engagement_score, :hook, :post_url, :posted_at, NOW())
                """),
                {
                    "competitor_id": competitor_id,
                    "platform": platform,
                    "post_text": post.text,
                    "likes": post.likes,
                    "comments": post.comments,
                    "shares": post.shares,
                    "engagement_score": post.engagement_score,
                    "hook": extract_hook_from_text(post.text),
                    "post_url": post.url,
                    "posted_at": post.timestamp
                }
            )
        
        await db.commit()
        return True
        
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error("Failed to save competitor posts: %s", e)
        return False


async def load_cached_posts(db: AsyncSession, org_id: int, competitor_id: int = None,
                           platform: str = None, days: Optional[int] = 30) -> List[Dict]:
    """Load cached competitor posts from database."""
    try:
        query = """
            SELECT cp.*, c.handle, COALESCE(c.followers, 0) AS followers
            FROM crm.competitor_posts cp
            JOIN crm.competitors c ON cp.competitor_id = c.id
            WHERE c.org_id = :org_id
        """
        params: Dict[str, Any] = {"org_id": org_id}

        if days is not None:
            query += " AND cp.posted_at >= :cutoff_date"
            params["cutoff_date"] = datetime.now() - timedelta(days=days)
        
        if competitor_id:
            query += " AND cp.competitor_id = :competitor_id"
            params["competitor_id"] = competitor_id
            
        if platform:
            query += " AND cp.platform = :platform"
            params["platform"] = platform
            
        query += (
            " ORDER BY (COALESCE(cp.likes, 0) + COALESCE(cp.comments, 0) + "
            "CASE WHEN lower(cp.platform) = 'instagram' THEN 0 ELSE COALESCE(cp.shares, 0) END) DESC, "
            "cp.posted_at DESC"
        )
        
        result = await db.execute(text(query), params)
        return [dict(row._mapping) for row in result.fetchall()]
        
    except SQLAlchemyError as e:
        logger.error("Failed to load cached posts: %s", e)
        return []


def _cached_rows_to_posts(cached_posts: List[Dict[str, Any]]) -> List[CompetitorPost]:
    """Convert cached post rows into API response models."""
    posts: List[CompetitorPost] = []

    for cached_post in cached_posts:
        posts.append(CompetitorPost(
            id=cached_post.get("id"),
            text=cached_post.get("post_text", ""),
            likes=cached_post.get("likes", 0),
            comments=cached_post.get("comments", 0),
            shares=cached_post.get("shares", 0),
            timestamp=cached_post.get("posted_at", datetime.now()),
            url=cached_post.get("post_url", ""),
            engagement_score=calculate_competitor_engagement_score(
                cached_post.get("likes", 0),
                cached_post.get("comments", 0),
                cached_post.get("shares", 0),
                platform=cached_post.get("platform"),
            ),
            hook=cached_post.get("hook", ""),
            media_type=cached_post.get("media_type"),
            has_transcript=bool(cached_post.get("transcript")),
            has_comments=bool(cached_post.get("comments_data")),
        ))

    return posts


def _scraped_profile_to_posts(profile: Any) -> List[CompetitorPost]:
    """Convert a scraped Instagram profile payload into competitor posts."""
    posts: List[CompetitorPost] = []

    for post in profile.posts:
        posts.append(CompetitorPost(
            text=post.caption,
            likes=post.likes,
            comments=post.comments,
            shares=post.views,
            timestamp=post.posted_at or datetime.now(),
            url=post.post_url,
            engagement_score=calculate_competitor_engagement_score(
                post.likes,
                post.comments,
                post.views,
                platform="instagram",
            ),
            hook=post.hook or extract_hook_from_text(post.caption),
        ))

    return posts


async def _get_competitor_or_404(db: AsyncSession, competitor_id: int, org_id: int) -> Competitor:
    """Load a competitor or raise a 404."""
    result = await db.execute(select(Competitor).where(Competitor.id == competitor_id, Competitor.org_id == org_id))
    competitor = result.scalar_one_or_none()

    if not competitor:
        raise HTTPException(status_code=404, detail="Competitor not found")

    return competitor


async def _ensure_competitor_cached_posts(
    db: AsyncSession,
    competitor: Competitor,
    days: Optional[int] = None,
) -> Tuple[List[Dict[str, Any]], Optional[Any]]:
    """Ensure Instagram competitors have cached posts for drill-down reads."""
    platform = competitor.platform.lower()
    cached_posts = await load_cached_posts(db, competitor.org_id, competitor.id, platform, days=days)
    if cached_posts or platform != "instagram":
        return cached_posts, None

    lock = _get_competitor_sync_lock(competitor.id)
    async with lock:
        cached_posts = await load_cached_posts(db, competitor.org_id, competitor.id, platform, days=days)
        if cached_posts:
            return cached_posts, None

        sync_result = await sync_instagram_competitor(db, competitor)
        if not sync_result["success"]:
            raise HTTPException(
                status_code=422,
                detail=f"Instagram scrape failed: {sync_result['error']}",
            )

        await db.commit()
        cached_posts = await load_cached_posts(db, competitor.org_id, competitor.id, platform, days=days)
        return cached_posts, sync_result["profile"]


# Social media fetching functions (keep existing implementations but enhance error handling)
async def fetch_instagram_content(handle: str, access_token: str) -> List[CompetitorPost]:
    """Fetch recent content from Instagram competitor."""
    try:
        posts = []
        async with httpx.AsyncClient() as client:
            # Get recent media
            url = "https://graph.instagram.com/me"
            params = {
                "fields": f"business_discovery.username({handle}){{media{{caption,like_count,comments_count,timestamp,permalink}}}}",
                "access_token": access_token
            }
            
            response = await client.get(url, params=params, timeout=30.0)
            response.raise_for_status()
            
            data = response.json()
            business_data = data.get("business_discovery", {})
            media_data = business_data.get("media", {}).get("data", [])
            
            for post in media_data:
                engagement_score = calculate_engagement_score(
                    post.get("like_count", 0),
                    post.get("comments_count", 0),
                    0  # Instagram doesn't provide shares
                )
                
                posts.append(CompetitorPost(
                    text=post.get("caption", ""),
                    likes=post.get("like_count", 0),
                    comments=post.get("comments_count", 0),
                    shares=0,
                    timestamp=datetime.fromisoformat(post.get("timestamp", "").replace("Z", "+00:00")),
                    url=post.get("permalink", ""),
                    engagement_score=engagement_score,
                    hook=extract_hook_from_text(post.get("caption", ""))
                ))
            
            return posts
            
    except Exception as e:
        logger.error("Failed to fetch Instagram content for %s: %s", handle, e)
        return []


async def fetch_x_content(handle: str, access_token: str) -> List[CompetitorPost]:
    """Fetch recent content from X competitor."""
    try:
        posts = []
        async with httpx.AsyncClient() as client:
            # Get user ID first
            user_url = f"https://api.x.com/2/users/by/username/{handle}"
            headers = {"Authorization": f"Bearer {access_token}"}
            
            user_response = await client.get(user_url, headers=headers, timeout=30.0)
            user_response.raise_for_status()
            
            user_data = user_response.json()
            user_id = user_data.get("data", {}).get("id")
            
            if not user_id:
                return []
            
            # Get recent tweets
            tweets_url = f"https://api.x.com/2/users/{user_id}/tweets"
            params = {
                "tweet.fields": "created_at,public_metrics,text",
                "max_results": 20
            }
            
            tweets_response = await client.get(tweets_url, headers=headers, params=params, timeout=30.0)
            tweets_response.raise_for_status()
            
            tweets_data = tweets_response.json()
            tweets = tweets_data.get("data", [])
            
            for tweet in tweets:
                metrics = tweet.get("public_metrics", {})
                engagement_score = calculate_engagement_score(
                    metrics.get("like_count", 0),
                    metrics.get("reply_count", 0),
                    metrics.get("retweet_count", 0)
                )
                
                posts.append(CompetitorPost(
                    text=tweet.get("text", ""),
                    likes=metrics.get("like_count", 0),
                    comments=metrics.get("reply_count", 0),
                    shares=metrics.get("retweet_count", 0),
                    timestamp=datetime.fromisoformat(tweet.get("created_at", "").replace("Z", "+00:00")),
                    url=f"https://twitter.com/{handle}/status/{tweet.get('id')}",
                    engagement_score=engagement_score,
                    hook=extract_hook_from_text(tweet.get("text", ""))
                ))
            
            return posts
            
    except Exception as e:
        logger.error("Failed to fetch X content for %s: %s", handle, e)
        return []


async def fetch_youtube_content(handle: str, api_key: str) -> List[CompetitorPost]:
    """Fetch recent content from YouTube competitor."""
    try:
        posts = []
        async with httpx.AsyncClient() as client:
            # Search for channel
            search_url = "https://www.googleapis.com/youtube/v3/search"
            search_params = {
                "q": handle,
                "type": "channel",
                "part": "snippet",
                "maxResults": 1,
                "key": api_key
            }
            
            response = await client.get(search_url, params=search_params, timeout=30.0)
            response.raise_for_status()
            
            search_data = response.json()
            items = search_data.get("items", [])
            
            if not items:
                return []
            
            channel_id = items[0]["id"]["channelId"]
            
            # Get recent videos
            videos_url = "https://www.googleapis.com/youtube/v3/search"
            videos_params = {
                "channelId": channel_id,
                "part": "snippet",
                "order": "date",
                "maxResults": 20,
                "key": api_key
            }
            
            videos_response = await client.get(videos_url, params=videos_params, timeout=30.0)
            videos_response.raise_for_status()
            
            videos_data = videos_response.json()
            videos = videos_data.get("items", [])
            
            for video in videos:
                snippet = video.get("snippet", {})
                video_id = video.get("id", {}).get("videoId")
                
                if video_id:
                    # Get video statistics
                    stats_url = "https://www.googleapis.com/youtube/v3/videos"
                    stats_params = {
                        "id": video_id,
                        "part": "statistics",
                        "key": api_key
                    }
                    
                    stats_response = await client.get(stats_url, params=stats_params, timeout=30.0)
                    stats_response.raise_for_status()
                    
                    stats_data = stats_response.json()
                    stats_items = stats_data.get("items", [])
                    
                    if stats_items:
                        stats = stats_items[0].get("statistics", {})
                        
                        engagement_score = calculate_engagement_score(
                            int(stats.get("likeCount", 0)),
                            int(stats.get("commentCount", 0)),
                            0  # YouTube doesn't provide shares
                        )
                        
                        title_desc = snippet.get("title", "") + " " + snippet.get("description", "")[:200]
                        
                        posts.append(CompetitorPost(
                            text=title_desc,
                            likes=int(stats.get("likeCount", 0)),
                            comments=int(stats.get("commentCount", 0)),
                            shares=0,
                            timestamp=datetime.fromisoformat(snippet.get("publishedAt", "").replace("Z", "+00:00")),
                            url=f"https://www.youtube.com/watch?v={video_id}",
                            engagement_score=engagement_score,
                            hook=extract_hook_from_text(title_desc)
                        ))
            
            return posts
            
    except Exception as e:
        logger.error("Failed to fetch YouTube content for %s: %s", handle, e)
        return []


async def analyze_trending_topics(posts: List[Dict], enable_clustering: bool = True) -> List[TrendingTopic]:
    """Enhanced topic analysis with n-grams, engagement weighting, and recency boost."""
    if not posts:
        return []
    
    # Extract meaningful phrases (bigrams and trigrams)
    phrase_data = defaultdict(lambda: {
        'posts': [],
        'engagement_scores': [],
        'recency_weights': []
    })
    
    for post in posts:
        text = post.get('post_text', '')
        if not text:
            continue
            
        posted_at = post.get('posted_at', datetime.now())
        if isinstance(posted_at, str):
            try:
                posted_at = datetime.fromisoformat(posted_at.replace('Z', '+00:00'))
            except:
                posted_at = datetime.now()
        
        engagement_score = _post_engagement_score(post)
        recency_weight = calculate_recency_weight(posted_at)
        
        # Extract bigrams and trigrams
        bigrams = extract_ngrams(text, 2)
        trigrams = extract_ngrams(text, 3)
        
        # Combine all phrases
        phrases = bigrams + trigrams
        
        for phrase in phrases:
            # Filter out generic phrases
            if len(phrase.split()) >= 2 and not any(word in phrase.lower() for word in 
                ['the', 'and', 'for', 'with', 'this', 'that', 'you', 'your', 'how']):
                phrase_data[phrase]['posts'].append(post)
                phrase_data[phrase]['engagement_scores'].append(engagement_score)
                phrase_data[phrase]['recency_weights'].append(recency_weight)
    
    # Calculate trending topics
    trending = []
    
    for phrase, data in phrase_data.items():
        frequency = len(data['posts'])
        
        # Only consider phrases that appear in at least 2 posts
        if frequency >= 2:
            avg_engagement = sum(data['engagement_scores']) / len(data['engagement_scores'])
            avg_recency = sum(data['recency_weights']) / len(data['recency_weights'])
            
            # Calculate final score: frequency * avg_engagement * recency_boost
            final_score = frequency * avg_engagement * avg_recency
            
            # Get source handles
            sources = list(set([post.get('handle', 'Unknown') for post in data['posts']]))
            
            trending.append(TrendingTopic(
                topic=phrase.title(),
                frequency=frequency,
                avg_engagement=avg_engagement,
                recency_weight=avg_recency,
                final_score=final_score,
                sources=sources[:5],  # Limit to 5 sources
                keywords=phrase.split()
            ))
    
    # Sort by final score
    trending.sort(key=lambda x: x.final_score, reverse=True)
    
    # Cluster related topics if requested
    if enable_clustering and trending:
        topic_names = [t.topic for t in trending[:20]]  # Top 20 topics
        clusters = cluster_topics(topic_names)
        
        # Add related topics to each trending topic
        for topic in trending[:20]:
            for cluster_name, cluster_members in clusters.items():
                if topic.topic in cluster_members:
                    related = [t for t in cluster_members if t != topic.topic]
                    topic.related_topics = related[:3]  # Max 3 related topics
                    break
    
    return trending[:15]  # Return top 15 topics


# API Endpoints

@router.get("/competitors/{competitor_id}/content", response_model=CompetitorContentResponse)
async def get_competitor_content(
    request: Request,
    competitor_id: int,
    db: AsyncSession = Depends(get_tenant_db)
):
    """Fetch recent posts from a tracked competitor using the appropriate social API."""
    org_id = get_org_id(request)
    try:
        competitor = await _get_competitor_or_404(db, competitor_id, org_id)
        
        posts = []
        platform = competitor.platform.lower()
        handle = competitor.handle
        
        if platform == "instagram":
            cached_posts, synced_profile = await _ensure_competitor_cached_posts(
                db,
                competitor,
                days=30,
            )
            if cached_posts:
                posts = _cached_rows_to_posts(cached_posts)
            elif synced_profile is not None:
                posts = _scraped_profile_to_posts(synced_profile)

        elif platform == "x":
            user_id = get_user_id(request)
            token = await get_social_account_token(db, user_id, org_id, "x")
            if not token:
                raise HTTPException(status_code=422, detail="X account not connected or not accessible")
            posts = await fetch_x_content(handle, token)
            if posts:
                await save_competitor_posts(db, competitor_id, org_id, platform, posts)

        elif platform == "youtube":
            raise HTTPException(status_code=422, detail="YouTube content fetching not configured")

        else:
            raise HTTPException(status_code=422, detail=f"Content fetching not supported for {platform}")
        
        # Calculate average engagement
        avg_engagement = sum(p.engagement_score for p in posts) / len(posts) if posts else 0
        
        return CompetitorContentResponse(
            competitor_id=competitor_id,
            platform=platform,
            handle=handle,
            posts=posts,
            total_posts=len(posts),
            avg_engagement=avg_engagement
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to fetch competitor content: %s", e)
        raise HTTPException(status_code=500, detail="Failed to fetch competitor content")


@router.get("/competitors/trending-topics", response_model=TrendingTopicsResponse)
async def get_trending_topics(
    request: Request,
    platform: Optional[str] = None,
    days: int = 30,
    db: AsyncSession = Depends(get_tenant_db)
):
    """Analyze all competitor content to extract common themes/topics ranked by engagement."""
    org_id = get_org_id(request)
    try:
        # Load cached posts from all competitors
        cached_posts = await load_cached_posts(db, org_id, platform=platform, days=days)
        
        if not cached_posts:
            # If no cached posts, we need to refresh data
            return TrendingTopicsResponse(
                topics=[],
                total_analyzed_posts=0,
                timeframe_days=days
            )
        
        # Analyze trending topics
        trending_topics = await analyze_trending_topics(cached_posts)
        
        return TrendingTopicsResponse(
            topics=trending_topics,
            total_analyzed_posts=len(cached_posts),
            timeframe_days=days
        )
        
    except Exception as e:
        logger.error("Failed to analyze trending topics: %s", e)
        raise HTTPException(status_code=500, detail="Failed to analyze trending topics")


@router.get("/competitors/top-content", response_model=TopContentResponse)
async def get_top_content(
    request: Request,
    limit: int = 20,
    days: int = 30,
    platform: Optional[str] = None,
    db: AsyncSession = Depends(get_tenant_db)
):
    """Get top performing content across all competitors."""
    org_id = get_org_id(request)
    try:
        # Load cached posts sorted by engagement
        cached_posts = await load_cached_posts(db, org_id, platform=platform, days=days)
        
        if not cached_posts:
            return TopContentResponse(posts=[], total_posts=0)
        
        # Recompute ranking from current counts, follower context, and recency
        top_posts = _sorted_posts_for_analysis(cached_posts)[:limit]
        
        # Convert to response format
        top_content = []
        for post in top_posts:
            top_content.append(TopContentItem(
                id=post.get('id'),
                text=post.get('post_text', ''),
                hook=post.get('hook', ''),
                likes=post.get('likes', 0),
                comments=post.get('comments', 0),
                shares=post.get('shares', 0),
                engagement_score=_post_engagement_score(post),
                platform=post.get('platform', ''),
                competitor_handle=post.get('handle', ''),
                url=post.get('post_url', ''),
                timestamp=post.get('posted_at', datetime.now()),
                virality_score=_post_virality_score(post),
            ))
        
        return TopContentResponse(
            posts=top_content,
            total_posts=len(cached_posts)
        )
        
    except Exception as e:
        logger.error("Failed to get top content: %s", e)
        raise HTTPException(status_code=500, detail="Failed to get top content")


@router.get("/competitors/hooks", response_model=HooksResponse)
async def get_hooks(
    request: Request,
    limit: int = 50,
    days: int = 30,
    platform: Optional[str] = None,
    db: AsyncSession = Depends(get_tenant_db)
):
    """Get extracted hooks ranked by engagement score."""
    org_id = get_org_id(request)
    try:
        # Load cached posts
        cached_posts = await load_cached_posts(db, org_id, platform=platform, days=days)
        
        if not cached_posts:
            return HooksResponse(hooks=[], total_hooks=0)
        
        # Extract hooks and rank them from the current post performance snapshot
        hooks = []
        seen_hooks: set[str] = set()
        for post in cached_posts:
            hook = _post_hook(post)
            if hook and len(hook.strip()) > 10:  # Filter out short/empty hooks
                hook_key = hook.strip().lower()
                if hook_key in seen_hooks:
                    continue
                seen_hooks.add(hook_key)
                hooks.append(HookItem(
                    hook=hook,
                    engagement_score=_post_engagement_score(post),
                    platform=post.get('platform', ''),
                    competitor_handle=post.get('handle', ''),
                    source_url=post.get('post_url', ''),
                    virality_score=_post_virality_score(post),
                ))
        
        # Sort by virality first so refreshes reflect changing winner content
        hooks.sort(key=lambda x: (x.virality_score, x.engagement_score), reverse=True)
        top_hooks = hooks[:limit]
        
        return HooksResponse(
            hooks=top_hooks,
            total_hooks=len(hooks)
        )
        
    except Exception as e:
        logger.error("Failed to get hooks: %s", e)
        raise HTTPException(status_code=500, detail="Failed to get hooks")


@router.post("/competitors/refresh")
async def refresh_competitor_content(
    request: Request,
    competitor_id: Optional[int] = None,
    platform: Optional[str] = None,
    db: AsyncSession = Depends(get_tenant_db)
):
    """Re-fetch content for competitors and update cache."""
    org_id = get_org_id(request)
    try:
        # Get competitors to refresh
        query = select(Competitor).where(Competitor.org_id == org_id)
        
        if competitor_id:
            query = query.where(Competitor.id == competitor_id)
        if platform:
            query = query.where(Competitor.platform == platform.lower())
            
        result = await db.execute(query)
        competitors = result.scalars().all()
        
        refreshed = 0
        errors = []

        instagram_competitors = [
            competitor
            for competitor in competitors
            if competitor.platform.lower() == "instagram"
        ]

        if instagram_competitors:
            batch_result = await sync_instagram_competitor_batch(db, instagram_competitors, org_id)
            refreshed += batch_result.success

            for profile in batch_result.profiles:
                if profile.error:
                    errors.append(f"Error refreshing {profile.handle}: {profile.error}")
        
        for competitor in competitors:
            try:
                platform_name = competitor.platform.lower()
                handle = competitor.handle

                if platform_name == "instagram":
                    continue
                
                posts = []
                if platform_name == "x":
                    user_id = get_user_id(request)
                    token = await get_social_account_token(db, user_id, org_id, "x")
                    if token:
                        posts = await fetch_x_content(handle, token)
                elif platform_name == "youtube":
                    # Add YouTube implementation when API key is available
                    pass
                
                if posts:
                    success = await save_competitor_posts(db, competitor.id, platform_name, posts)
                    if success:
                        refreshed += 1
                    else:
                        errors.append(f"Failed to save posts for {handle}")
                else:
                    errors.append(f"No posts fetched for {handle}")
                    
            except Exception as e:
                logger.warning("Failed to refresh competitor %s: %s", competitor.handle, e)
                errors.append(f"Error refreshing {competitor.handle}: {str(e)}")

        await db.commit()
        
        return {
            "message": f"Refreshed content for {refreshed} competitors",
            "refreshed_competitors": refreshed,
            "total_competitors": len(competitors),
            "errors": errors
        }
        
    except Exception as e:
        logger.error("Failed to refresh competitor content: %s", e)
        raise HTTPException(status_code=500, detail="Failed to refresh competitor content")


# Keep existing script generation endpoints
@router.post("/competitors/{competitor_id}/generate-script", response_model=List[GeneratedScript])
async def generate_content_script(
    request: Request,
    competitor_id: int,
    body: ScriptGenerationRequest,
    save_to_db: bool = False,
    db: AsyncSession = Depends(get_tenant_db)
):
    """Generate competitor-driven script ideas from live cached performance data."""
    org_id = get_org_id(request)
    try:
        competitor = await _get_competitor_or_404(db, competitor_id, org_id)

        if competitor.platform.lower() == "instagram":
            cached_posts, _ = await _ensure_competitor_cached_posts(db, competitor, days=45)
        else:
            cached_posts = await load_cached_posts(db, org_id, competitor_id=competitor_id, days=45)

        if not cached_posts:
            raise HTTPException(
                status_code=422,
                detail="No cached competitor content is available yet. Refresh competitor data first.",
            )

        ranked_posts = _sorted_posts_for_analysis(cached_posts)
        trending_topics = await analyze_trending_topics(ranked_posts, enable_clustering=False)
        business_settings = await _get_business_settings()
        scripts = build_competitor_script_ideas(
            competitor_handle=competitor.handle,
            platform=body.platform,
            posts=ranked_posts,
            business_settings=business_settings,
            count=body.count,
            requested_topic=body.topic,
            hook_style=body.hook_style,
            trending_topics=[topic.topic for topic in trending_topics],
        )

        if not scripts:
            raise HTTPException(status_code=422, detail="Unable to build scripts from the available competitor data")

        for script in scripts:
            script.competitor_id = competitor_id

        if not save_to_db:
            return scripts

        persisted_scripts: List[GeneratedScript] = []
        content_rows: List[ContentScript] = []

        for script in scripts:
            content_script = ContentScript(
                competitor_id=competitor_id,
                platform=body.platform,
                title=script.title,
                hook=script.hook,
                body=script.body_outline,
                cta=script.cta,
                topic=script.topic,
                source_post_url=script.source_post_url,
                scene_map=_serialize_script_metadata(script),
                status='generated',
            )
            db.add(content_script)
            content_rows.append(content_script)

        await db.commit()

        for content_script in content_rows:
            await db.refresh(content_script)
            persisted_scripts.append(_content_script_to_response(content_script))

        return persisted_scripts
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to generate script: %s", e)
        raise HTTPException(status_code=500, detail="Failed to generate script")


@router.post("/generate-scripts", response_model=List[GeneratedScript])
async def generate_aggregated_scripts(
    request: Request,
    body: ScriptGenerationRequest,
    save_to_db: bool = False,
    db: AsyncSession = Depends(get_tenant_db),
):
    """Generate script ideas aggregated from ALL competitors' top-performing posts."""
    org_id = get_org_id(request)
    try:
        # Load all cached posts across every competitor for the requested platform
        all_posts = await load_cached_posts(db, org_id, platform=body.platform, days=45)
        if not all_posts:
            raise HTTPException(
                status_code=422,
                detail="No cached competitor content available. Sync your competitors first.",
            )

        # Rank by engagement across all competitors, take top 30
        ranked_posts = _sorted_posts_for_analysis(all_posts)[:30]

        # Build a combined handle label from unique source competitors
        source_handles = list(dict.fromkeys(
            post.get("handle", "unknown") for post in ranked_posts if post.get("handle")
        ))
        combined_handle = ", ".join(source_handles[:5]) or "all competitors"

        trending_topics = await analyze_trending_topics(ranked_posts, enable_clustering=False)
        business_settings = await _get_business_settings()

        scripts = build_competitor_script_ideas(
            competitor_handle=combined_handle,
            platform=body.platform,
            posts=ranked_posts,
            business_settings=business_settings,
            count=body.count,
            requested_topic=body.topic,
            hook_style=body.hook_style,
            trending_topics=[t.topic for t in trending_topics],
        )

        if not scripts:
            raise HTTPException(
                status_code=422,
                detail="Unable to build scripts from the available competitor data.",
            )

        # Ensure source_competitors lists all unique handles across all scripts
        for script in scripts:
            if not script.source_competitors or script.source_competitors == [combined_handle]:
                script.source_competitors = source_handles[:8]

        if not save_to_db:
            return scripts

        # Persist to DB
        persisted: List[GeneratedScript] = []
        rows: List[ContentScript] = []
        for script in scripts:
            row = ContentScript(
                competitor_id=None,
                platform=body.platform,
                title=script.title,
                hook=script.hook,
                body=script.body_outline,
                cta=script.cta,
                topic=script.topic,
                source_post_url=script.source_post_url,
                scene_map=_serialize_script_metadata(script),
                status="generated",
            )
            db.add(row)
            rows.append(row)

        await db.commit()
        for row in rows:
            await db.refresh(row)
            persisted.append(_content_script_to_response(row))

        return persisted

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to generate aggregated scripts: %s", e)
        raise HTTPException(status_code=500, detail="Failed to generate scripts")


def generate_script_content(
    competitor_handle: str,
    platform: str,
    topic: str,
    source_post: Dict[str, Any],
    similar_posts: List[Dict[str, Any]],
    business_settings: Dict[str, Any],
    hook_style: Optional[str] = None,
) -> GeneratedScript:
    """Generate a single competitor-driven content script from cached winning posts."""
    best_hook = _post_hook(source_post) or f"Here's the {topic.lower()} pattern {competitor_handle} is proving right now"
    similar_videos = _build_similar_video_references(similar_posts, limit=3)
    source_competitors = list(dict.fromkeys(
        [competitor_handle] + [video.competitor_handle for video in similar_videos if video.competitor_handle]
    ))
    alignment_score, alignment_label, alignment_reason = _score_business_alignment(topic, best_hook, business_settings)
    title = best_hook[:90]
    if hook_style and hook_style.strip():
        title = f"{title[:68]} — {hook_style.replace('_', ' ').title()} angle"

    body_outline = _build_script_body(best_hook, topic, platform, business_settings, source_competitors)
    if hook_style and hook_style.strip():
        body_outline += (
            "\n\nDelivery note:\n"
            f"Keep the performance framing close to a {hook_style.replace('_', ' ')} while preserving the proven opening language."
        )

    return GeneratedScript(
        platform=platform,
        title=title,
        hook=best_hook,
        body_outline=body_outline,
        cta=_build_script_cta(platform, business_settings),
        topic=topic,
        source_post_url=source_post.get("post_url", "") or None,
        estimated_duration=_estimated_duration_for_platform(platform),
        created_at=datetime.now(timezone.utc),
        predicted_views=_estimate_predicted_views(source_post),
        predicted_engagement=round(_post_engagement_score(source_post), 1),
        predicted_engagement_rate=round(_post_engagement_rate(source_post) * 100.0, 2),
        virality_score=round(_post_virality_score(source_post), 1),
        business_alignment_score=alignment_score,
        business_alignment_label=alignment_label,
        business_alignment_reason=alignment_reason,
        source_competitors=source_competitors,
        similar_videos=similar_videos,
        scene_map=_build_script_scenes(best_hook, topic, platform, business_settings),
    )


def build_competitor_script_ideas(
    competitor_handle: str,
    platform: str,
    posts: List[Dict[str, Any]],
    business_settings: Dict[str, Any],
    count: int = 6,
    requested_topic: Optional[str] = None,
    hook_style: Optional[str] = None,
    trending_topics: Optional[List[str]] = None,
) -> List[GeneratedScript]:
    """Build a set of script ideas from ranked competitor content and current trends."""
    ranked_posts = _sorted_posts_for_analysis(posts)
    if not ranked_posts:
        return []

    candidate_topics = _collect_candidate_topics(
        ranked_posts,
        trending_topics or [],
        requested_topic,
        max_topics=max(count * 2, 6),
    )

    scripts: List[GeneratedScript] = []
    used_signatures: set[Tuple[str, str]] = set()
    post_cursor = 0
    topic_cursor = 0
    max_attempts = max(count * 6, 12)

    while len(scripts) < count and max_attempts > 0:
        source_post = ranked_posts[post_cursor % len(ranked_posts)]
        topic = requested_topic.strip() if requested_topic and requested_topic.strip() else candidate_topics[topic_cursor % len(candidate_topics)]
        hook = _post_hook(source_post) or topic
        signature = (hook.lower(), topic.lower())

        if signature not in used_signatures:
            used_signatures.add(signature)
            similar_posts = [source_post] + [
                post for post in ranked_posts
                if post.get("post_url") != source_post.get("post_url")
            ]
            scripts.append(generate_script_content(
                competitor_handle=competitor_handle,
                platform=platform,
                topic=topic,
                source_post=source_post,
                similar_posts=similar_posts,
                business_settings=business_settings,
                hook_style=hook_style,
            ))

        post_cursor += 1
        if not requested_topic or len(ranked_posts) == 1:
            topic_cursor += 1
        max_attempts -= 1

    return scripts


@router.get("/competitors/scripts", response_model=List[GeneratedScript])
async def list_generated_scripts(
    request: Request,
    platform: Optional[str] = None,
    competitor_id: Optional[int] = None,
    db: AsyncSession = Depends(get_tenant_db)
):
    """List all generated content scripts."""
    org_id = get_org_id(request)
    try:
        query = select(ContentScript).where(ContentScript.org_id == org_id).order_by(ContentScript.created_at.desc())
        
        if platform:
            query = query.where(ContentScript.platform == platform.lower())
        if competitor_id:
            query = query.where(ContentScript.competitor_id == competitor_id)
        
        result = await db.execute(query)
        scripts = result.scalars().all()
        
        return [_content_script_to_response(script) for script in scripts]
        
    except Exception as e:
        logger.error("Failed to list scripts: %s", e)
        raise HTTPException(status_code=500, detail="Failed to list scripts")


@router.delete("/competitors/scripts/{script_id}")
async def delete_script(
    request: Request,
    script_id: int,
    db: AsyncSession = Depends(get_tenant_db)
):
    """Delete a generated script."""
    org_id = get_org_id(request)
    try:
        result = await db.execute(
            select(ContentScript).where(ContentScript.id == script_id)
        )
        script = result.scalar_one_or_none()
        
        if not script:
            raise HTTPException(status_code=404, detail="Script not found")
        
        await db.delete(script)
        await db.commit()
        
        return {"message": "Script deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("Failed to delete script: %s", e)
        raise HTTPException(status_code=500, detail="Failed to delete script")


# ── New endpoints: Top Videos, Follower Analysis, Hashtags ──────────────


class TopVideoItem(BaseModel):
    """Top-performing video/post for a competitor."""
    id: Optional[int] = None
    competitor_id: Optional[int] = None
    competitor_handle: Optional[str] = None
    platform: Optional[str] = None
    post_url: Optional[str] = None
    title: str
    likes: int = 0
    comments: int = 0
    shares: int = 0
    engagement_score: float = 0.0
    virality_score: float = 0.0
    posted_at: Optional[datetime] = None
    hook: Optional[str] = None
    media_type: Optional[str] = None
    has_transcript: bool = False
    has_comments: bool = False
    analysis: "TopVideoAnalysis" = Field(default_factory=lambda: TopVideoAnalysis())


class TopVideoSection(BaseModel):
    """Timed chunk of a top-video analysis."""
    text: str = ""
    start: float = 0.0
    end: float = 0.0


class TopVideoStoryboardScene(BaseModel):
    """Storyboard scene derived from the source video structure."""
    scene: str
    direction: str
    goal: str
    timing: Optional[str] = None


class TopVideoProductionSpec(BaseModel):
    """Reusable creative spec for future generation workflows."""
    creative_angle: str = ""
    pacing_label: str = "unknown"
    pacing_notes: str = ""
    scene_pattern: List[str] = Field(default_factory=list)
    production_notes: List[str] = Field(default_factory=list)
    cta_strategy: str = ""


class TopVideoAnalysis(BaseModel):
    """Derived structure analysis for a top-performing competitor video."""
    content_format: Optional[str] = None
    duration_seconds: float = 0.0
    structure_score: float = 0.0
    hook_type: Optional[str] = None
    hook_strength: float = 0.0
    cta_type: Optional[str] = None
    cta_phrase: Optional[str] = None
    pacing_label: str = "unknown"
    pacing_reason: str = ""
    key_points: List[str] = Field(default_factory=list)
    scene_pattern: List[str] = Field(default_factory=list)
    hook_window: TopVideoSection = Field(default_factory=TopVideoSection)
    value_window: TopVideoSection = Field(default_factory=TopVideoSection)
    cta_window: TopVideoSection = Field(default_factory=TopVideoSection)
    storyboard: List[TopVideoStoryboardScene] = Field(default_factory=list)
    production_spec: TopVideoProductionSpec = Field(default_factory=TopVideoProductionSpec)


class FollowerAnalysisResponse(BaseModel):
    """Audience/follower analysis summary derived from post content."""
    themes: List[str]
    audience_type: str
    engagement_style: str
    key_interests: List[str]


def _empty_audience_intel_response() -> AudienceIntelResponse:
    return AudienceIntelResponse(
        posts_analyzed=0,
        comments_analyzed=0,
        sentiment="neutral",
        sentiment_breakdown={},
        sentiment_percentages={},
        questions=[],
        pain_points=[],
        themes=[],
        product_mentions=[],
        top_commenters=[],
        engagement_quality={},
        content_formats={},
    )


def _row_value(row: Any, index: int, key: str) -> Any:
    if isinstance(row, dict):
        return row.get(key)

    mapping = getattr(row, "_mapping", None)
    if mapping is not None and key in mapping:
        return mapping[key]

    value = getattr(row, key, None)
    if value is not None:
        return value

    try:
        return row[index]
    except (IndexError, KeyError, TypeError):
        return None


def _coerce_int(value: Any) -> int:
    try:
        return int(float(value or 0))
    except (TypeError, ValueError):
        return 0


def _coerce_float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _percent_change(current: float, previous: float) -> float:
    if previous <= 0:
        return 100.0 if current > 0 else 0.0
    return ((current - previous) / previous) * 100.0


def _build_instagram_profile_advice(
    account_row: Any,
    analytics_rows: List[Any],
    scraped: Optional[ScrapedProfile] = None,
) -> InstagramProfileAdviceResponse:
    username = str(_row_value(account_row, 1, "username") or "") or None
    follower_count = _coerce_int(_row_value(account_row, 2, "follower_count"))
    following_count = _coerce_int(_row_value(account_row, 3, "following_count"))
    post_count = _coerce_int(_row_value(account_row, 4, "post_count"))
    last_synced = _row_value(account_row, 5, "last_synced")

    if not analytics_rows:
        return InstagramProfileAdviceResponse(
            connected=True,
            username=username,
            status="needs_sync",
            summary=(
                f"@{username or 'your account'} is connected, but there isn't enough synced Instagram analytics yet "
                "to review your profile. Run a fresh sync and come back for profile-specific advice."
            ),
            follower_count=follower_count,
            following_count=following_count,
            post_count=post_count,
            last_synced=last_synced,
            recommendations=[
                InstagramAdviceItem(
                    title="Sync your Instagram analytics",
                    detail="Pull at least a week of Instagram account analytics so War Room can review your profile performance instead of competitor data.",
                )
            ],
        )

    days_analyzed = len(analytics_rows)
    avg_engagement_rate = round(
        sum(_coerce_float(_row_value(row, 3, "engagement_rate")) for row in analytics_rows) / days_analyzed,
        2,
    )
    avg_reach = int(round(sum(_coerce_int(_row_value(row, 2, "reach")) for row in analytics_rows) / days_analyzed))
    avg_profile_views = int(round(sum(_coerce_int(_row_value(row, 6, "profile_views")) for row in analytics_rows) / days_analyzed))
    avg_video_views = int(round(sum(_coerce_int(_row_value(row, 12, "video_views")) for row in analytics_rows) / days_analyzed))
    total_link_clicks = sum(_coerce_int(_row_value(row, 7, "link_clicks")) for row in analytics_rows)
    total_profile_views = sum(_coerce_int(_row_value(row, 6, "profile_views")) for row in analytics_rows)
    total_saves = sum(_coerce_int(_row_value(row, 9, "saves")) for row in analytics_rows)
    total_shares = sum(_coerce_int(_row_value(row, 8, "shares")) for row in analytics_rows)
    net_followers = sum(
        _coerce_int(_row_value(row, 4, "followers_gained")) - _coerce_int(_row_value(row, 5, "followers_lost"))
        for row in analytics_rows
    )

    recent_rows = analytics_rows[:7]
    prior_rows = analytics_rows[7:14]
    recent_avg_engagement = (
        sum(_coerce_float(_row_value(row, 3, "engagement_rate")) for row in recent_rows) / len(recent_rows)
        if recent_rows else avg_engagement_rate
    )
    prior_avg_engagement = (
        sum(_coerce_float(_row_value(row, 3, "engagement_rate")) for row in prior_rows) / len(prior_rows)
        if prior_rows else recent_avg_engagement
    )
    engagement_trend = _percent_change(recent_avg_engagement, prior_avg_engagement)
    profile_ctr = (total_link_clicks / total_profile_views) if total_profile_views > 0 else 0.0

    recommendations: List[InstagramAdviceItem] = []

    # ── Bio & Link Strategy ──
    if total_profile_views > 0 and profile_ctr < 0.08:
        recommendations.append(InstagramAdviceItem(
            title="Rewrite your bio around one clear outcome",
            detail=(
                f"You're getting ~{avg_profile_views} profile views/day but only {profile_ctr * 100:.1f}% click your link. "
                "Your bio should answer one question in under 5 words: 'What do I get by following?' "
                "Remove filler lines, add a single CTA like 'Free guide ↓' or 'DM me KEYWORD', and make sure your link-in-bio "
                "landing page matches that exact promise. Pin your best-performing post as proof."
            ),
            metric=f"{profile_ctr * 100:.1f}% profile → link click rate",
        ))
    elif total_profile_views > 0 and total_link_clicks == 0:
        recommendations.append(InstagramAdviceItem(
            title="Add a link and CTA to your bio",
            detail=(
                f"You had {total_profile_views} profile views in the last {days_analyzed} days but zero link clicks. "
                "You're leaving traffic on the table. Add a Linktree or direct link, write a one-line CTA in your bio "
                "explaining what's behind the link, and mention it in your next 3 posts."
            ),
            metric="0 link clicks",
        ))

    # ── Follower Growth Diagnosis ──
    if net_followers < -5:
        recent_lost = sum(_coerce_int(_row_value(row, 5, "followers_lost")) for row in recent_rows)
        recommendations.append(InstagramAdviceItem(
            title="You're losing followers — diagnose the content shift",
            detail=(
                f"You lost a net {abs(net_followers)} followers over the last {days_analyzed} days "
                f"({recent_lost} lost in the last 7 days alone). "
                "Common causes: posting off-topic content, inconsistent schedule, or a viral post that attracted the wrong audience. "
                "Review your last 5 posts — if any topic was new or different from your usual niche, that's likely the trigger. "
                "Double down on your proven topic for the next 7 posts before experimenting again."
            ),
            metric=f"{net_followers} net followers ({days_analyzed}d)",
        ))
    elif net_followers == 0:
        recommendations.append(InstagramAdviceItem(
            title="Break the follower plateau with a content series",
            detail=(
                "Your follower count hasn't moved. Single posts don't build follow-worthy profiles — series do. "
                "Pick your best-performing topic and turn it into a numbered series (Part 1, Part 2…). "
                "This gives new visitors a reason to follow: they want the next part."
            ),
            metric="0 net followers",
        ))

    # ── Engagement & Content Quality ──
    if avg_engagement_rate < 2.0:
        recommendations.append(InstagramAdviceItem(
            title="Your content isn't stopping the scroll — fix the first frame",
            detail=(
                f"At {avg_engagement_rate:.2f}% engagement, most viewers are scrolling past. "
                "The first 1-2 seconds decide everything. Use bold on-screen text with a surprising claim or question. "
                "Start talking immediately (no intro), and make the opening visual pattern-interrupt (zoom, movement, face close-up). "
                "Test rewriting just the hook on your last 3 reels and reposting — same content, different opener."
            ),
            metric=f"{avg_engagement_rate:.2f}% engagement rate",
        ))
    elif engagement_trend < -15:
        recommendations.append(InstagramAdviceItem(
            title="Engagement is dropping — your format may be going stale",
            detail=(
                f"Your engagement dropped {abs(engagement_trend):.0f}% compared to the previous week. "
                "Instagram's algorithm deprioritizes repetitive formats. Try switching between talking head → B-roll → "
                "screen recording → carousel within the same topic. Keep the subject, change the packaging."
            ),
            metric=f"{engagement_trend:.0f}% week-over-week engagement change",
        ))

    # ── Video Performance ──
    if avg_video_views > 0 and avg_reach > 0:
        view_to_reach = avg_video_views / max(avg_reach, 1)
        if view_to_reach < 0.5:
            recommendations.append(InstagramAdviceItem(
                title="Your videos aren't being watched — shorten and front-load value",
                detail=(
                    f"You're reaching ~{avg_reach} people/day but only {avg_video_views} watch your videos. "
                    "That means people see the thumbnail or first frame and skip. "
                    "Keep reels under 30 seconds, put the payoff in the first 3 seconds, and use captions — "
                    "most people watch on mute. If your average reel is over 60 seconds, cut it in half."
                ),
                metric=f"{view_to_reach * 100:.0f}% view-to-reach ratio",
            ))
        elif view_to_reach >= 1.0:
            recommendations.append(InstagramAdviceItem(
                title="Your reels are outperforming your reach — scale this format",
                detail=(
                    "Your video views exceed your follower reach, meaning Instagram is pushing your reels to non-followers. "
                    "This is your growth lever. Post reels at least 4x/week in the same format, "
                    "and add a verbal CTA ('follow for part 2') in the last 2 seconds of each."
                ),
                metric=f"{avg_video_views} views vs {avg_reach} reach/day",
            ))

    # ── Saves & Shares (virality signals) ──
    if total_saves + total_shares < days_analyzed * 2:
        recommendations.append(InstagramAdviceItem(
            title="Make your posts worth saving — add frameworks and checklists",
            detail=(
                f"Only {total_saves + total_shares} saves + shares in {days_analyzed} days. "
                "Saves and shares are the strongest algorithm signals. To earn them, end each post with a "
                "downloadable-feeling takeaway: a 3-step framework, a before/after comparison, or a 'save this for later' checklist. "
                "Carousels with actionable slides get 2-3x more saves than single images."
            ),
            metric=f"{total_saves + total_shares} saves + shares ({days_analyzed}d)",
        ))

    # ── Scraped-profile-based recommendations ──
    bio_text = ""
    external_url = ""
    bio_links: List[Dict[str, str]] = []
    profile_pic_url = ""
    is_verified = False
    category_str = ""
    posting_frequency = ""
    recent_posts_summary: List[ProfilePostSummary] = []

    if scraped:
        bio_text = scraped.bio or ""
        external_url = scraped.external_url or ""
        bio_links = scraped.bio_links or []
        profile_pic_url = scraped.profile_pic_url or ""
        is_verified = scraped.is_verified
        category_str = scraped.category or ""

        # Posting frequency estimation
        if scraped.posts:
            dates = [p.posted_at for p in scraped.posts if p.posted_at]
            if len(dates) >= 2:
                span_days = max((max(dates) - min(dates)).days, 1)
                posts_per_week = round(len(dates) / span_days * 7, 1)
                posting_frequency = f"~{posts_per_week} posts/week"

        # Recent posts summaries for frontend
        for p in scraped.posts[:6]:
            recent_posts_summary.append(ProfilePostSummary(
                shortcode=p.shortcode,
                caption_preview=(p.caption or "")[:120],
                hook=p.hook or "",
                likes=p.likes,
                comments=p.comments,
                views=p.views,
                media_type=p.media_type,
                posted_at=p.posted_at,
                engagement_score=p.engagement_score,
            ))

        # ── Bio quality ──
        if not bio_text.strip():
            recommendations.append(InstagramAdviceItem(
                title="Your bio is empty — you're invisible to new visitors",
                detail=(
                    "Every profile visit without a bio is a missed follow. Write 2-3 lines that answer: "
                    "who you are, what you post about, and why someone should follow. "
                    "Include one emoji-led CTA line like '📩 DM me KEYWORD for [thing]' or '⬇️ Free [resource]'."
                ),
                category="bio",
            ))
        else:
            bio_lower = bio_text.lower()
            has_cta = any(kw in bio_lower for kw in ["dm", "link", "tap", "click", "free", "get", "download", "join", "sign up", "⬇", "👇", "📩"])
            if not has_cta:
                recommendations.append(InstagramAdviceItem(
                    title="Your bio is missing a call-to-action",
                    detail=(
                        f"Current bio: \"{bio_text[:100]}{'…' if len(bio_text) > 100 else ''}\"\n\n"
                        "There's no clear CTA telling visitors what to do next. Add a line like "
                        "'⬇️ Grab my free [resource]' or '📩 DM me GROWTH for a free audit'. "
                        "Bios with a CTA convert 30-50% more profile visitors into followers or link clicks."
                    ),
                    category="bio",
                    metric=f"{avg_profile_views} profile views/day with no CTA",
                ))
            bio_word_count = len(bio_text.split())
            if bio_word_count > 25:
                recommendations.append(InstagramAdviceItem(
                    title="Your bio is too long — tighten it to under 20 words",
                    detail=(
                        f"Current bio ({bio_word_count} words): \"{bio_text[:120]}{'…' if len(bio_text) > 120 else ''}\"\n\n"
                        "Instagram bios get scanned in 2 seconds. Cut filler words, use line breaks, "
                        "and lead with the strongest identity statement. Format: Line 1 = who you are, "
                        "Line 2 = what you share, Line 3 = CTA."
                    ),
                    category="bio",
                ))

        # ── Links ──
        if not external_url and not bio_links:
            recommendations.append(InstagramAdviceItem(
                title="You have no link in your profile — add one now",
                detail=(
                    "You're getting profile visits but there's nowhere for people to go. "
                    "Add a Linktree, Stan Store, or direct URL. Then mention 'link in bio' in your next 3 post captions. "
                    "Even a simple link to your best content or a free resource will start converting visitors."
                ),
                category="profile",
                metric=f"{total_profile_views} profile views with no link",
            ))

        # ── Content hooks quality ──
        if scraped.posts:
            hooks = [p.hook for p in scraped.posts if p.hook]
            weak_hooks = [h for h in hooks if len(h.split()) < 4 or h.lower().startswith(("hey", "so", "um", "today", "hi"))]
            if len(weak_hooks) > len(hooks) * 0.5 and len(hooks) >= 3:
                examples = weak_hooks[:2]
                recommendations.append(InstagramAdviceItem(
                    title="Most of your hooks are weak — rewrite the first line",
                    detail=(
                        f"Examples from your recent posts: \"{examples[0]}\"" +
                        (f", \"{examples[1]}\"" if len(examples) > 1 else "") +
                        ".\n\nStrong hooks use specificity, curiosity, or controversy: "
                        "'I gained 10K followers in 30 days doing this one thing' or "
                        "'Stop doing [common mistake] — here's why'. "
                        "Rewrite just the first sentence of your next post and watch saves go up."
                    ),
                    category="content",
                ))

            # Reel vs non-reel ratio
            reels = [p for p in scraped.posts if p.is_reel or p.media_type == "reel"]
            if len(reels) < len(scraped.posts) * 0.5 and len(scraped.posts) >= 4:
                recommendations.append(InstagramAdviceItem(
                    title="You're not posting enough Reels — Instagram is pushing them",
                    detail=(
                        f"Only {len(reels)} of your last {len(scraped.posts)} posts are Reels. "
                        "Instagram's algorithm currently gives Reels 2-3x more reach than static posts or carousels. "
                        "Aim for at least 60-70% Reels in your content mix. Repurpose your best carousel ideas as "
                        "short talking-head or text-overlay Reels."
                    ),
                    category="content",
                    metric=f"{len(reels)}/{len(scraped.posts)} posts are Reels",
                ))

    # ── Fallback ──
    if not recommendations:
        recommendations.append(InstagramAdviceItem(
            title="Your profile is performing well — test one variable at a time",
            detail=(
                "Your metrics look solid. To keep growing, pick one thing to test each week: a new hook style, "
                "posting time, or CTA format. Track which change moves saves and shares (not just likes). "
                "Don't change your core topic — just refine the packaging."
            ),
            metric=f"{avg_engagement_rate:.2f}% engagement · {net_followers:+d} followers",
            category="engagement",
        ))

    trend_label = "up" if engagement_trend > 10 else "down" if engagement_trend < -10 else "steady"
    growth_label = "growing" if net_followers > 0 else "flat" if net_followers == 0 else "slipping"

    return InstagramProfileAdviceResponse(
        connected=True,
        username=username,
        status="ready",
        summary=(
            f"Reviewing @{username or 'your account'} using {days_analyzed} days of analytics"
            + (f" + a live profile scan" if scraped else "")
            + f". Engagement is {trend_label}, follower growth is {growth_label}."
        ),
        follower_count=follower_count,
        following_count=following_count,
        post_count=post_count,
        last_synced=last_synced,
        days_analyzed=days_analyzed,
        avg_engagement_rate=avg_engagement_rate,
        avg_reach=avg_reach,
        avg_profile_views=avg_profile_views,
        avg_video_views=avg_video_views,
        total_link_clicks=total_link_clicks,
        net_followers=net_followers,
        bio=bio_text or None,
        external_url=external_url or None,
        bio_links=bio_links,
        profile_pic_url=profile_pic_url or None,
        is_verified=is_verified,
        category=category_str or None,
        posting_frequency=posting_frequency or None,
        recent_posts=recent_posts_summary,
        recommendations=recommendations[:6],
    )


def _aggregate_audience_intel_rows(rows: List[Any]) -> AudienceIntelResponse:
    if not rows:
        return _empty_audience_intel_response()

    total_analyzed = 0
    sentiment_totals = {"positive": 0, "negative": 0, "neutral": 0}
    all_questions: list[Dict[str, Any]] = []
    all_pain_points: list[Dict[str, Any]] = []
    all_themes: Counter = Counter()
    all_products: Counter = Counter()
    all_commenters: Counter = Counter()
    total_engagement_quality = {"high": 0, "moderate": 0, "low": 0}
    format_counts: Counter = Counter()

    for row in rows:
        comments_data = _row_value(row, 0, "comments_data")
        content_analysis = _row_value(row, 1, "content_analysis")
        engagement_score = _row_value(row, 2, "engagement_score")

        data = json.loads(comments_data) if isinstance(comments_data, str) else comments_data
        if not data:
            continue

        total_analyzed += data.get("analyzed", 0)

        sentiment_breakdown = data.get("sentiment_breakdown", {})
        sentiment_totals["positive"] += sentiment_breakdown.get("positive", 0)
        sentiment_totals["negative"] += sentiment_breakdown.get("negative", 0)
        sentiment_totals["neutral"] += sentiment_breakdown.get("neutral", 0)

        weighted_engagement = float(engagement_score or 0)

        for question in data.get("questions", []):
            all_questions.append({
                "question": question.get("question", ""),
                "likes": question.get("likes", 0),
                "weight": weighted_engagement,
            })

        for pain_point in data.get("pain_points", []):
            all_pain_points.append({
                "pain": pain_point.get("pain", ""),
                "likes": pain_point.get("likes", 0),
                "weight": weighted_engagement,
            })

        for theme in data.get("themes", []):
            theme_name = theme.get("theme")
            if theme_name:
                all_themes[theme_name] += theme.get("count", 0)

        for product in data.get("product_mentions", []):
            product_name = product.get("product")
            if product_name:
                all_products[product_name] += product.get("count", 0)

        for commenter in data.get("top_commenters", []):
            username = commenter.get("username")
            if username:
                all_commenters[username] += commenter.get("count", 0)

        engagement_quality = data.get("engagement_quality", "moderate")
        total_engagement_quality[engagement_quality] = total_engagement_quality.get(engagement_quality, 0) + 1

        analysis = json.loads(content_analysis) if isinstance(content_analysis, str) else content_analysis
        if analysis:
            format_name = analysis.get("content_format", "unknown")
            format_counts[format_name] += 1

    seen_questions = set()
    unique_questions = []
    for question in sorted(all_questions, key=lambda item: item["weight"] + item["likes"], reverse=True):
        question_text = question.get("question", "")
        question_key = question_text[:50].lower()
        if question_text and question_key not in seen_questions:
            seen_questions.add(question_key)
            unique_questions.append({"question": question_text, "likes": question.get("likes", 0)})

    seen_pain_points = set()
    unique_pain_points = []
    for pain_point in sorted(all_pain_points, key=lambda item: item["weight"] + item["likes"], reverse=True):
        pain_text = pain_point.get("pain", "")
        pain_key = pain_text[:50].lower()
        if pain_text and pain_key not in seen_pain_points:
            seen_pain_points.add(pain_key)
            unique_pain_points.append({"pain": pain_text, "likes": pain_point.get("likes", 0)})

    total_sentiment = sum(sentiment_totals.values()) or 1
    positive_pct = sentiment_totals["positive"] / total_sentiment
    negative_pct = sentiment_totals["negative"] / total_sentiment
    if positive_pct > 0.6:
        overall_sentiment = "very_positive"
    elif positive_pct > 0.4:
        overall_sentiment = "positive"
    elif negative_pct > 0.6:
        overall_sentiment = "very_negative"
    elif negative_pct > 0.4:
        overall_sentiment = "negative"
    else:
        overall_sentiment = "neutral"

    return AudienceIntelResponse(
        posts_analyzed=len(rows),
        comments_analyzed=total_analyzed,
        sentiment=overall_sentiment,
        sentiment_breakdown=sentiment_totals,
        sentiment_percentages={
            "positive": round(positive_pct * 100, 1),
            "negative": round(negative_pct * 100, 1),
            "neutral": round((1 - positive_pct - negative_pct) * 100, 1),
        },
        questions=[AudienceQuestion(**item) for item in unique_questions[:15]],
        pain_points=[AudiencePainPoint(**item) for item in unique_pain_points[:15]],
        themes=[AudienceTheme(theme=theme, count=count) for theme, count in all_themes.most_common(20)],
        product_mentions=[AudienceProductMention(product=product, count=count) for product, count in all_products.most_common(15)],
        top_commenters=[AudienceCommenter(username=username, count=count) for username, count in all_commenters.most_common(15)],
        engagement_quality=total_engagement_quality,
        content_formats=dict(format_counts),
    )


@router.get("/competitors/audience-intel", response_model=AudienceIntelResponse)
async def get_global_audience_intel(
    request: Request,
    days: int = 1,
    db: AsyncSession = Depends(get_tenant_db),
):
    """Aggregate audience intelligence across all tracked competitor posts."""
    org_id = get_org_id(request)
    try:
        result = await db.execute(
            text("""
                SELECT comments_data, content_analysis, engagement_score
                FROM crm.competitor_posts
                WHERE comments_data IS NOT NULL
                  AND (comments_data->>'analyzed')::int > 0
                  AND posted_at >= NOW() - MAKE_INTERVAL(days => :days)
                  AND org_id = :org_id
                ORDER BY engagement_score DESC
            """),
            {"days": days, "org_id": org_id},
        )
        return _aggregate_audience_intel_rows(result.fetchall())
    except Exception as e:
        logger.error("Failed to aggregate global audience intelligence: %s", e)
        raise HTTPException(status_code=500, detail="Failed to aggregate audience intelligence")


class HashtagItem(BaseModel):
    """A hashtag with its frequency count."""
    tag: str
    count: int


def _is_video_like_post(post: Dict[str, Any]) -> bool:
    media_type = str(post.get("media_type") or "").strip().lower()
    if media_type in {"video", "reel", "igtv", "short", "shorts"}:
        return True
    if post.get("transcript"):
        return True
    return _coerce_int(post.get("video_views")) > 0


def _json_dict(value: Any) -> Dict[str, Any]:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (TypeError, json.JSONDecodeError):
            return {}
    return value if isinstance(value, dict) else {}


def _humanize_token(token: Any) -> str:
    text_value = str(token or "").replace("_", " ").strip()
    return text_value.title() if text_value else ""


def _clip_text(text_value: Any, limit: int = 180) -> str:
    text_value = str(text_value or "").strip()
    if len(text_value) <= limit:
        return text_value
    return text_value[: max(limit - 1, 0)].rstrip() + "…"


def _extract_caption_key_points(text_value: Any, limit: int = 3) -> List[str]:
    text_value = str(text_value or "").strip()
    if not text_value:
        return []

    seen: set[str] = set()
    points: List[str] = []
    for sentence in re.split(r"[.!?\n]+", text_value):
        sentence = sentence.strip(" -•\t")
        if len(sentence) < 15:
            continue
        key = sentence.lower()[:80]
        if key in seen:
            continue
        seen.add(key)
        points.append(_clip_text(sentence, 180))
        if len(points) >= limit:
            break
    return points


def _estimate_video_duration_seconds(post: Dict[str, Any], analysis: Dict[str, Any]) -> float:
    explicit_duration = _coerce_float(analysis.get("total_duration"))
    if explicit_duration > 0:
        return round(explicit_duration, 1)

    full_script = str(analysis.get("full_script") or post.get("post_text") or _post_hook(post) or "").strip()
    word_count = len(full_script.split())
    if word_count <= 0:
        return 0.0

    estimated = min(max(word_count * 0.45, 12.0), 90.0)
    return round(estimated, 1)


def _window_from_payload(payload: Dict[str, Any], default_text: str, default_start: float, default_end: float) -> TopVideoSection:
    start = round(_coerce_float(payload.get("start", default_start)), 1)
    end = round(max(_coerce_float(payload.get("end", default_end)), start), 1)
    return TopVideoSection(
        text=_clip_text(payload.get("text") or default_text, 240),
        start=start,
        end=end,
    )


def _format_storyboard_timing(start: float, end: float) -> Optional[str]:
    if end <= 0 and start <= 0:
        return None
    return f"{round(start, 1):.1f}s-{round(max(end, start), 1):.1f}s"


def _derive_pacing(duration_seconds: float, beat_count: int, structure_score: float, content_format: str) -> Tuple[str, str]:
    if duration_seconds <= 0:
        return "unknown", "Precise pacing needs transcript timing or richer post analysis."

    if content_format == "text_overlay" or duration_seconds < 15:
        return "rapid", f"A {duration_seconds:.0f}s clip that lands the payoff almost immediately."

    if beat_count >= 5 and duration_seconds <= 45:
        return "fast", f"Roughly {beat_count} beats are compressed into {duration_seconds:.0f}s, so the edit cadence stays quick."

    if structure_score >= 0.75 and duration_seconds <= 90:
        return "balanced", "Clear hook-to-value-to-CTA sequencing with enough space for each beat to land."

    return "deliberate", "Longer runtime gives each section more breathing room than a fast-cut short-form reel."


def _storyboard_scene(scene: str, direction: str, goal: str, start: float, end: float) -> TopVideoStoryboardScene:
    return TopVideoStoryboardScene(
        scene=scene,
        direction=_clip_text(direction, 220),
        goal=goal,
        timing=_format_storyboard_timing(start, end),
    )


def _build_top_video_analysis(post: Dict[str, Any]) -> TopVideoAnalysis:
    analysis = _json_dict(post.get("content_analysis"))
    duration_seconds = _estimate_video_duration_seconds(post, analysis)

    raw_hook = _json_dict(analysis.get("hook"))
    raw_value = _json_dict(analysis.get("value"))
    raw_cta = _json_dict(analysis.get("cta"))

    hook_text = str(raw_hook.get("text") or _post_hook(post) or "").strip()
    hook_end = _coerce_float(raw_hook.get("end")) or min(duration_seconds or 3.0, 3.0)
    hook_window = _window_from_payload(raw_hook, hook_text, 0.0, hook_end)

    value_text = str(raw_value.get("text") or post.get("post_text") or "").strip()
    value_start_default = hook_window.end if hook_window.end > 0 else 0.0
    value_end_default = max(duration_seconds - min(5.0, duration_seconds * 0.2), value_start_default)
    value_window = _window_from_payload(raw_value, value_text, value_start_default, value_end_default)

    cta_text = str(raw_cta.get("text") or "").strip()
    cta_start_default = max(duration_seconds - min(5.0, duration_seconds * 0.2), value_window.end)
    cta_window = _window_from_payload(raw_cta, cta_text, cta_start_default, duration_seconds)

    duration_seconds = max(duration_seconds, hook_window.end, value_window.end, cta_window.end)
    if duration_seconds > 0:
        duration_seconds = round(duration_seconds, 1)

    key_points = [
        _clip_text(point, 180)
        for point in raw_value.get("key_points", [])
        if str(point or "").strip()
    ]
    if not key_points:
        key_points = _extract_caption_key_points(value_window.text)

    content_format = str(analysis.get("content_format") or "").strip().lower()
    if not content_format:
        media_type = str(post.get("media_type") or "").strip().lower()
        content_format = "short_form" if media_type in {"reel", "video", "igtv", "short", "shorts"} else media_type or "unknown"

    hook_type = str(raw_hook.get("type") or ("statement" if hook_window.text else "none"))
    cta_type = str(raw_cta.get("type") or ("soft" if cta_window.text else "none"))
    cta_phrase = str(raw_cta.get("phrase") or "").strip() or None
    structure_score = round(_coerce_float(analysis.get("structure_score")), 2)
    hook_strength = round(_coerce_float(raw_hook.get("strength")), 2)

    scene_pattern: List[str] = []
    if hook_window.text:
        scene_pattern.append(f"{_humanize_token(hook_type) or 'Opening'} hook")
    if content_format == "text_overlay":
        scene_pattern.append("Text-overlay payoff")
    if key_points:
        scene_pattern.append(f"{len(key_points)}-beat value stack")
    elif value_window.text:
        scene_pattern.append("Single value explanation")
    if cta_type != "none":
        scene_pattern.append(f"{_humanize_token(cta_type) or 'Closing'} CTA")
    elif cta_window.text:
        scene_pattern.append("Soft CTA")
    if not scene_pattern:
        scene_pattern = ["Hook", "Value", "Close"]

    beat_count = (1 if hook_window.text else 0) + max(len(key_points), 1 if value_window.text else 0) + (1 if cta_type != "none" or cta_window.text else 0)
    pacing_label, pacing_reason = _derive_pacing(duration_seconds, beat_count, structure_score, content_format)

    storyboard: List[TopVideoStoryboardScene] = []
    if hook_window.text:
        storyboard.append(_storyboard_scene(
            "Hook",
            hook_window.text,
            f"Pattern interrupt with a {_humanize_token(hook_type).lower() or 'strong'} opening.",
            hook_window.start,
            hook_window.end,
        ))

    if key_points:
        span = max(value_window.end - value_window.start, 0.0)
        chunk = span / len(key_points) if span > 0 else 0.0
        for index, point in enumerate(key_points, start=1):
            scene_start = value_window.start + (chunk * (index - 1)) if chunk else value_window.start
            scene_end = value_window.start + (chunk * index) if chunk else value_window.end
            storyboard.append(_storyboard_scene(
                f"Value beat {index}",
                point,
                "Deliver a concrete lesson, example, or demonstration before moving to the next point.",
                scene_start,
                scene_end,
            ))
    elif value_window.text:
        storyboard.append(_storyboard_scene(
            "Value",
            value_window.text,
            "Deliver the core teaching, proof, or demo segment.",
            value_window.start,
            value_window.end,
        ))

    if cta_type != "none" or cta_window.text:
        storyboard.append(_storyboard_scene(
            "CTA",
            cta_phrase or cta_window.text or "Restate the payoff and invite the next action.",
            "Convert attention into a reply, click, save, share, or follow.",
            cta_window.start,
            cta_window.end,
        ))

    production_notes = [
        f"Edit for a {_humanize_token(content_format).lower() or 'short-form'} delivery pattern.",
        f"Use a {pacing_label} cadence so each beat lands without dead air.",
    ]
    if key_points:
        production_notes.append(f"Give each of the {len(key_points)} value beat(s) a distinct visual, caption, or proof point.")
    if post.get("transcript"):
        production_notes.append("Transcript timing is available, so these windows can be used as a storyboard baseline.")
    else:
        production_notes.append("Transcript timing is estimated from captions, so refine the beats after a fresh sync/transcription pass.")

    if _coerce_float(post.get("virality_score") or _post_virality_score(post)) >= 70:
        production_notes.append("The performance signals suggest this angle is already earning broad distribution, so preserve the opening premise.")

    cta_strategy = (
        f"Close with a {_humanize_token(cta_type).lower()} CTA using '{cta_phrase}' as the anchor phrase."
        if cta_phrase and cta_type != "none"
        else f"Close with a {_humanize_token(cta_type).lower()} CTA that restates the promised payoff."
        if cta_type != "none"
        else "Restate the promised outcome, then ask for the lowest-friction next step (reply, save, share, or follow)."
    )

    creative_angle = _clip_text(hook_window.text or value_window.text or post.get("post_text") or "", 180)

    return TopVideoAnalysis(
        content_format=content_format,
        duration_seconds=duration_seconds,
        structure_score=structure_score,
        hook_type=hook_type,
        hook_strength=hook_strength,
        cta_type=cta_type,
        cta_phrase=cta_phrase,
        pacing_label=pacing_label,
        pacing_reason=pacing_reason,
        key_points=key_points,
        scene_pattern=scene_pattern,
        hook_window=hook_window,
        value_window=value_window,
        cta_window=cta_window,
        storyboard=storyboard,
        production_spec=TopVideoProductionSpec(
            creative_angle=creative_angle,
            pacing_label=pacing_label,
            pacing_notes=pacing_reason,
            scene_pattern=scene_pattern,
            production_notes=production_notes[:5],
            cta_strategy=cta_strategy,
        ),
    )


def _top_video_item_from_post(post: Dict[str, Any]) -> TopVideoItem:
    return TopVideoItem(
        id=post.get("id"),
        competitor_id=post.get("competitor_id"),
        competitor_handle=post.get("handle"),
        platform=post.get("platform"),
        post_url=post.get("post_url", ""),
        title=((post.get("post_text") or _post_hook(post) or "Untitled")[:100]).strip(),
        likes=_coerce_int(post.get("likes")),
        comments=_coerce_int(post.get("comments")),
        shares=_coerce_int(post.get("shares")),
        engagement_score=round(_post_engagement_score(post), 1),
        virality_score=round(_post_virality_score(post), 1),
        posted_at=post.get("posted_at"),
        hook=_post_hook(post) or None,
        media_type=post.get("media_type"),
        has_transcript=bool(post.get("transcript")),
        has_comments=bool(post.get("comments_data")),
        analysis=_build_top_video_analysis(post),
    )


@router.get("/instagram/account-advice", response_model=InstagramProfileAdviceResponse)
async def get_instagram_account_advice(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Review only the authenticated user's connected Instagram account."""
    org_id = get_org_id(request)
    try:
        account_result = await db.execute(
            text("""
                SELECT id, username, follower_count, following_count, post_count, last_synced, status
                FROM crm.social_accounts
                WHERE user_id = :user_id
                  AND org_id = :org_id
                  AND lower(platform) = 'instagram'
                ORDER BY COALESCE(last_synced, connected_at) DESC NULLS LAST, id DESC
                LIMIT 1
            """),
            {"user_id": user.id, "org_id": org_id},
        )
        account_row = account_result.mappings().first()

        if not account_row:
            return InstagramProfileAdviceResponse(
                connected=False,
                status="not_connected",
                summary="Connect your Instagram account to get profile-specific advice for your own profile.",
                recommendations=[
                    InstagramAdviceItem(
                        title="Connect your Instagram account",
                        detail="Once your account is connected and synced, War Room will review only your Instagram profile instead of competitor accounts.",
                    )
                ],
            )

        analytics_result = await db.execute(
            text("""
                SELECT metric_date, impressions, reach, engagement_rate, followers_gained, followers_lost,
                       profile_views, link_clicks, shares, saves, comments, likes, video_views
                FROM crm.social_analytics
                WHERE account_id = :account_id
                ORDER BY metric_date DESC
                LIMIT 30
            """),
            {"account_id": _row_value(account_row, 0, "id")},
        )
        analytics_rows = analytics_result.fetchall()

        # Scrape the user's own public profile for bio, links, posts, etc.
        username = str(_row_value(account_row, 1, "username") or "")
        scraped: Optional[ScrapedProfile] = None
        if username:
            try:
                scraped = await scrape_profile(username)
                if scraped and scraped.error:
                    logger.warning("Scrape of own profile @%s failed: %s", username, scraped.error)
                    scraped = None
            except Exception as e:
                logger.warning("Could not scrape own profile @%s: %s", username, e)

        return _build_instagram_profile_advice(account_row, analytics_rows, scraped)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to build Instagram account advice for user %s: %s", user.id, e)
        raise HTTPException(status_code=500, detail="Failed to review Instagram account")


@router.get("/competitors/top-videos", response_model=List[TopVideoItem])
async def get_top_competitor_videos(
    request: Request,
    days: int = 30,
    limit: int = 5,
    db: AsyncSession = Depends(get_tenant_db),
):
    """Return one top video-like post per leading Instagram competitor."""
    org_id = get_org_id(request)
    try:
        result = await db.execute(
            select(Competitor).where(Competitor.platform == "instagram")
        )
        competitors = sorted(
            result.scalars().all(),
            key=lambda comp: (
                getattr(comp, "followers", 0) or 0,
                _coerce_float(getattr(comp, "avg_engagement_rate", 0)),
            ),
            reverse=True,
        )

        top_videos: List[TopVideoItem] = []
        for competitor in competitors[: max(limit * 3, limit)]:
            cached_posts, _ = await _ensure_competitor_cached_posts(db, competitor, days=days)
            video_posts = [post for post in cached_posts if _is_video_like_post(post)]
            if not video_posts:
                continue

            best_post = _sorted_posts_for_analysis(video_posts)[0]
            top_videos.append(_top_video_item_from_post(best_post))
            if len(top_videos) >= limit:
                break

        return sorted(
            top_videos,
            key=lambda item: (item.virality_score, item.engagement_score),
            reverse=True,
        )[:limit]

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get aggregate top competitor videos: %s", e)
        raise HTTPException(status_code=500, detail="Failed to get top competitor videos")


@router.get("/competitors/{competitor_id}/top-videos", response_model=List[TopVideoItem])
async def get_competitor_top_videos(
    request: Request,
    competitor_id: int,
    limit: int = 5,
    db: AsyncSession = Depends(get_tenant_db)
):
    """Return the top-performing posts for a competitor, ordered by engagement_score."""
    org_id = get_org_id(request)
    try:
        competitor = await _get_competitor_or_404(db, competitor_id, org_id)
        cached_posts, _ = await _ensure_competitor_cached_posts(
            db,
            competitor,
            days=None,
        )

        ranked_posts = [post for post in cached_posts if _is_video_like_post(post)]
        if not ranked_posts:
            ranked_posts = cached_posts

        return [_top_video_item_from_post(post) for post in _sorted_posts_for_analysis(ranked_posts)[:limit]]
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get top videos for competitor %s: %s", competitor_id, e)
        raise HTTPException(status_code=500, detail="Failed to get top videos")


@router.get("/competitors/follower-analysis", response_model=FollowerAnalysisResponse)
async def get_follower_analysis(
    request: Request,
    db: AsyncSession = Depends(get_tenant_db)
):
    """Analyze themes and audience demographics from all competitor post texts using TF-IDF."""
    org_id = get_org_id(request)
    try:
        result = await db.execute(
            text("SELECT post_text, likes, comments, shares FROM crm.competitor_posts WHERE post_text IS NOT NULL")
        )
        rows = result.fetchall()

        if not rows:
            return FollowerAnalysisResponse(
                themes=[], audience_type="Unknown", engagement_style="Unknown", key_interests=[]
            )

        texts = [r.post_text for r in rows if r.post_text and len(r.post_text.strip()) > 10]
        total_likes = sum(r.likes or 0 for r in rows)
        total_comments = sum(r.comments or 0 for r in rows)
        total_shares = sum(r.shares or 0 for r in rows)
        post_count = len(rows)

        # ── Extract themes via TF-IDF ──
        themes: List[str] = []
        if NLTK_AVAILABLE and texts:
            try:
                vectorizer = TfidfVectorizer(
                    max_features=200,
                    ngram_range=(1, 2),
                    stop_words="english",
                    min_df=2,
                    max_df=0.8,
                )
                tfidf_matrix = vectorizer.fit_transform(texts)
                feature_names = vectorizer.get_feature_names_out()

                # Sum TF-IDF scores per term across all docs and pick top 8
                scores = tfidf_matrix.sum(axis=0).A1
                top_indices = scores.argsort()[-8:][::-1]
                themes = [str(feature_names[i]).title() for i in top_indices]
            except Exception as nlp_err:
                logger.warning("TF-IDF theme extraction failed: %s", nlp_err)

        # Fallback: simple word frequency if TF-IDF failed
        if not themes:
            all_words: Counter = Counter()
            stop = set(string.punctuation) | {"the", "a", "an", "and", "or", "is", "to", "in", "for", "of", "on", "it", "this", "that", "with", "you", "your", "i", "my", "we"}
            for t in texts:
                for w in t.lower().split():
                    w = w.strip(string.punctuation)
                    if len(w) > 3 and w not in stop:
                        all_words[w] += 1
            themes = [word.title() for word, _ in all_words.most_common(8)]

        # ── Derive audience type ──
        avg_comments = total_comments / post_count if post_count else 0
        avg_likes = total_likes / post_count if post_count else 0
        if avg_comments > 50:
            audience_type = "Highly Engaged Community"
        elif avg_comments > 20:
            audience_type = "Active Niche Audience"
        elif avg_likes > 500:
            audience_type = "Broad Passive Audience"
        else:
            audience_type = "Growing Micro-Audience"

        # ── Derive engagement style ──
        if total_comments and total_likes:
            ratio = total_comments / total_likes
            if ratio > 0.1:
                engagement_style = "Conversation-driven (high comment-to-like ratio)"
            elif ratio > 0.03:
                engagement_style = "Balanced engagement (likes + comments)"
            else:
                engagement_style = "Like-heavy (passive consumption)"
        else:
            engagement_style = "Insufficient data"

        # ── Key interests (hashtag + bigram mix) ──
        hashtag_counter: Counter = Counter()
        for t in texts:
            for tag in re.findall(r"#(\w+)", t):
                hashtag_counter[tag.lower()] += 1
        key_interests = [f"#{tag}" for tag, _ in hashtag_counter.most_common(6)]
        # Pad with top themes if not enough hashtags
        if len(key_interests) < 4:
            key_interests += [th for th in themes if th not in key_interests][: 4 - len(key_interests)]

        return FollowerAnalysisResponse(
            themes=themes,
            audience_type=audience_type,
            engagement_style=engagement_style,
            key_interests=key_interests,
        )

    except Exception as e:
        logger.error("Failed to run follower analysis: %s", e)
        raise HTTPException(status_code=500, detail="Failed to run follower analysis")


@router.get("/competitors/{competitor_id}/hashtags", response_model=List[HashtagItem])
async def get_competitor_hashtags(
    request: Request,
    competitor_id: int,
    db: AsyncSession = Depends(get_tenant_db)
):
    """Extract hashtags from all post_text for a competitor, sorted by frequency."""
    org_id = get_org_id(request)
    try:
        competitor = await _get_competitor_or_404(db, competitor_id, org_id)
        cached_posts, _ = await _ensure_competitor_cached_posts(
            db,
            competitor,
            days=None,
        )

        counter: Counter = Counter()
        for post in cached_posts:
            for tag in re.findall(r"#\w+", post.get("post_text") or ""):
                counter[tag.lower()] += 1

        return [HashtagItem(tag=tag, count=count) for tag, count in counter.most_common(50)]

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get hashtags for competitor %s: %s", competitor_id, e)
        raise HTTPException(status_code=500, detail="Failed to get hashtags")


@router.get("/competitors/{competitor_id}/audience-intel", response_model=AudienceIntelResponse)
async def get_aggregated_audience_intel(
    request: Request,
    competitor_id: int,
    db: AsyncSession = Depends(get_tenant_db),
):
    """Aggregate audience intelligence across ALL posts for a competitor.
    
    Combines individual post comment analyses into a unified view:
    - Overall sentiment distribution
    - Top questions audiences are asking
    - Top pain points across all posts
    - Common themes
    - Product/tool mentions
    - Most engaged commenters
    - Content format breakdown
    """
    org_id = get_org_id(request)
    try:
        result = await db.execute(
            text("""
                SELECT comments_data, content_analysis, engagement_score
                FROM crm.competitor_posts
                WHERE competitor_id = :cid 
                  AND comments_data IS NOT NULL
                  AND (comments_data->>'analyzed')::int > 0
                  AND org_id = :org_id
                ORDER BY engagement_score DESC
            """),
            {"cid": competitor_id, "org_id": org_id},
        )
        return _aggregate_audience_intel_rows(result.fetchall())
    
    except Exception as e:
        logger.error("Failed to aggregate audience intel for competitor %s: %s", competitor_id, e)
        raise HTTPException(status_code=500, detail="Failed to aggregate audience intelligence")


@router.post("/index-content")
async def index_content_for_recommendations(
    request: Request,
    body: dict = {},
    db: AsyncSession = Depends(get_tenant_db),
):
    """Index top competitor content into Qdrant for the recommendation engine.
    
    Call after syncing competitors or transcribing videos to update the index.
    Only indexes top 20% by engagement — the content worth learning from.
    """
    org_id = get_org_id(request)
    from app.services.content_embedder import index_top_content
    
    days = body.get("days", 90)
    limit = body.get("limit", 200)
    
    stats = await index_top_content(db, days=days, limit=limit)
    return stats


@router.get("/recommendation-status")
async def get_recommendation_status():
    """Get the current state of the content recommendation index."""
    from app.services.content_embedder import get_index_status
    return await get_index_status()


@router.post("/recommend")
async def recommend_content(request: Request, body: dict = {}, db: AsyncSession = Depends(get_tenant_db)):
    """Embedding-based recommendation engine.
    
    Analyzes competitors' top content semantically and generates
    hooks, hashtags, and script recommendations aligned to our business.
    
    Uses Qdrant vector search for content-based filtering.
    Falls back to v1 rule-based engine if index is empty.
    """
    org_id = get_org_id(request)
    from app.services.recommendation_engine import recommend_content_v2
    from app.services.content_embedder import get_index_status
    
    count = body.get("count", 5)
    topic = body.get("topic", None)
    platform = body.get("platform", "instagram")
    
    # Check if we have indexed content
    status = await get_index_status()
    
    if status.get("points_count", 0) > 0:
        # v2: embedding-based recommendations
        return await recommend_content_v2(
            db=db,
            topic=topic,
            platform=platform,
            count=count,
        )
    
    # Fallback: v1 rule-based (for when index hasn't been built yet)
    try:
        result = await db.execute(
            select(Competitor).where(Competitor.platform == platform, Competitor.org_id == org_id)
        )
        competitors = result.scalars().all()

        if not competitors:
            return {"recommendations": [], "message": "No competitors found. Add competitors first."}

        all_posts = await load_cached_posts(db, org_id, platform=platform, days=45)

        if not all_posts:
            return {"recommendations": [], "message": "No competitor content cached. Sync competitors first."}

        ranked = _sorted_posts_for_analysis(all_posts)[:30]
        trending_topics = await analyze_trending_topics(ranked, enable_clustering=False)
        business = await _get_business_settings()
        source_handles = list(dict.fromkeys(
            post.get("handle", "unknown") for post in ranked if post.get("handle")
        ))
        combined_handle = ", ".join(source_handles[:5]) or "all competitors"

        scripts = build_competitor_script_ideas(
            competitor_handle=combined_handle,
            platform=platform,
            posts=ranked,
            business_settings=business,
            count=count,
            requested_topic=topic,
            trending_topics=[t.topic for t in trending_topics],
        )

        for script in scripts:
            if not script.source_competitors or script.source_competitors == [combined_handle]:
                script.source_competitors = source_handles[:8]

        return {
            "recommendations": jsonable_encoder(scripts),
            "competitors_analyzed": len(competitors),
            "posts_analyzed": len(all_posts),
            "top_topics": [topic.topic for topic in trending_topics[:5]],
            "engine": "v1_fallback",
            "message": "Using rule-based engine. Run POST /index-content to enable v2 embedding-based recommendations.",
        }

    except Exception as e:
        logger.error("Recommendation engine failed: %s", e)
        raise HTTPException(status_code=500, detail="Recommendation engine failed")


_sync_all_task: Optional[asyncio.Task] = None
_sync_all_status: Dict[str, Any] = {"running": False}


async def _run_sync_all():
    """Background task: sync all competitors."""
    global _sync_all_status
    _sync_all_status = {"running": True, "started_at": datetime.now(timezone.utc).isoformat(), "message": "Syncing..."}
    print("[SYNC-ALL] Background task started", flush=True)
    
    try:
        from app.db.crm_db import crm_session
        from sqlalchemy import text as sa_text
        async with crm_session() as db:
            await db.execute(sa_text("SET search_path TO crm, public"))
            print("[SYNC-ALL] DB session open, search_path set", flush=True)
            result = await db.execute(
                select(Competitor)
                .where(Competitor.platform == "instagram")
                .where(Competitor.auto_sync_enabled == True)
            )
            competitors = result.scalars().all()
            
            if not competitors:
                _sync_all_status = {"running": False, "message": "No active competitors", "total": 0}
                return
            
            _sync_all_status["total"] = len(competitors)
            _sync_all_status["message"] = f"Scraping {len(competitors)} competitors..."
            print(f"[SYNC-ALL] Found {len(competitors)} competitors, starting batch scrape", flush=True)
            
            # Use org_id from first competitor (background task has no request context)
            bg_org_id = competitors[0].org_id if competitors else 1
            batch_result = await sync_instagram_competitor_batch(db, competitors, bg_org_id)
            print(f"[SYNC-ALL] Batch complete — success={batch_result.success} failed={batch_result.failed} posts={batch_result.posts_saved}", flush=True)
            await db.commit()
            
            # Audience analysis
            audience_refreshed = 0
            for comp in competitors:
                try:
                    posts = await load_cached_posts(db, comp.id)
                    if posts:
                        topics = await analyze_trending_topics(posts)
                        await db.execute(
                            text(
                                "UPDATE crm.competitors SET audience_analysis = :analysis, updated_at = NOW() "
                                "WHERE id = :cid"
                            ),
                            {"cid": comp.id, "analysis": json.dumps({
                                "themes": [t.topic for t in topics[:5]] if topics else [],
                                "audience_type": "Engaged" if len(posts) > 5 else "Unknown",
                                "engagement_style": "Active" if sum(p.get("engagement_score", 0) for p in posts) / max(len(posts), 1) > 100 else "Moderate",
                                "key_interests": [t.topic for t in topics[:3]] if topics else [],
                                "refreshed_at": datetime.now(timezone.utc).isoformat(),
                            })},
                        )
                        audience_refreshed += 1
                except Exception as e:
                    logger.warning("Audience refresh failed for %s: %s", comp.handle, e)
            await db.commit()
            
            # Phase 2: Transcription + Comment analysis (parallel, non-blocking)
            _sync_all_status["message"] = f"Synced {batch_result.success}/{len(competitors)}. Enriching content..."
            print(f"[SYNC-ALL] Starting parallel enrichment (transcription + comments)", flush=True)
            
            enriched = {"transcribed": 0, "comments_analyzed": 0}
            try:
                from app.services.video_transcriber import transcribe_competitor_videos_batch
                from app.services.comment_scraper import analyze_competitor_comments_batch
                
                # Get competitor IDs that synced successfully
                synced_ids = [c.id for c in competitors]
                
                # Run transcription and comment analysis in parallel
                # Transcribe up to 10 videos per competitor, analyze up to 15 comment threads
                results = await asyncio.gather(
                    _safe_enrich(lambda db, ids: transcribe_competitor_videos_batch(db, ids, limit_per_competitor=10), db, synced_ids, "transcription"),
                    _safe_enrich(lambda db, ids: analyze_competitor_comments_batch(db, ids, top_n_per_competitor=15), db, synced_ids, "comments"),
                    return_exceptions=True,
                )
                
                for r in results:
                    if isinstance(r, dict):
                        enriched["transcribed"] += r.get("transcribed", 0)
                        enriched["comments_analyzed"] += r.get("analyzed", 0)
                
                await db.commit()
                
                # Phase 3: Content structure analysis (Hook/Value/CTA) on transcribed posts
                enriched["content_analyzed"] = 0
                try:
                    from app.services.content_analyzer import analyze_competitor_content_batch
                    print(f"[SYNC-ALL] Analyzing content structure (Hook/Value/CTA)...", flush=True)
                    ca_result = await _safe_enrich(analyze_competitor_content_batch, db, synced_ids, "content_analysis")
                    if isinstance(ca_result, dict):
                        enriched["content_analyzed"] = ca_result.get("analyzed", 0)
                    await db.commit()
                except Exception as ca_err:
                    print(f"[SYNC-ALL] Content analysis error (non-fatal): {ca_err}", flush=True)
                
                print(f"[SYNC-ALL] Enrichment done — {enriched}", flush=True)
            except Exception as enrich_err:
                print(f"[SYNC-ALL] Enrichment error (non-fatal): {enrich_err}", flush=True)
            
            summary = f"Done: {batch_result.success}/{len(competitors)} synced, {batch_result.posts_saved} new posts"
            if enriched["transcribed"]:
                summary += f", {enriched['transcribed']} transcribed"
            if enriched.get("content_analyzed"):
                summary += f", {enriched['content_analyzed']} scripts analyzed"
            if enriched["comments_analyzed"]:
                summary += f", {enriched['comments_analyzed']} comments analyzed"
            
            _sync_all_status = {
                "running": False,
                "message": summary,
                "total": len(competitors),
                "success": batch_result.success,
                "failed": batch_result.failed,
                "posts_saved": batch_result.posts_saved,
                "audience_refreshed": audience_refreshed,
                "enriched": enriched,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }
            
            # Create notification
            await _create_sync_notification(summary, batch_result, enriched)
            
    except Exception as e:
        import traceback
        print(f"[SYNC-ALL] FAILED: {e}\n{traceback.format_exc()}", flush=True)
        _sync_all_status = {"running": False, "message": f"Failed: {str(e)[:100]}", "error": True}
        await _create_sync_notification(f"Sync failed: {str(e)[:80]}", None, None, is_error=True)


async def _create_sync_notification(message: str, batch_result=None, enriched=None, is_error=False):
    """Create a notification for sync completion/failure."""
    try:
        from app.db.leadgen_db import leadgen_session
        async with leadgen_session() as ndb:
            data = {}
            if batch_result:
                data = {"success": batch_result.success, "failed": batch_result.failed, "posts": batch_result.posts_saved}
            if enriched:
                data["enriched"] = enriched
            
            await ndb.execute(
                text("""
                    INSERT INTO public.notifications (user_id, type, title, message, data)
                    VALUES (1, :type, :title, :message, CAST(:data AS jsonb))
                """),
                {
                    "type": "alert" if is_error else "success",
                    "title": "❌ Competitor Sync Failed" if is_error else "✅ Competitor Sync Complete",
                    "message": message,
                    "data": json.dumps(data),
                },
            )
            await ndb.commit()
            print(f"[SYNC-ALL] Notification created: {message}", flush=True)
    except Exception as e:
        print(f"[SYNC-ALL] Failed to create notification: {e}", flush=True)


async def _safe_enrich(fn, db, competitor_ids, label):
    """Run an enrichment function safely, catching errors."""
    try:
        return await fn(db, competitor_ids)
    except Exception as e:
        print(f"[SYNC-ALL] {label} enrichment failed: {e}", flush=True)
        return {}


@router.post("/backfill-formats")
async def backfill_post_formats(
    request: Request,
    db: AsyncSession = Depends(get_tenant_db)
):
    """Backfill detected_format for existing competitor posts using the format classifier."""
    org_id = get_org_id(request)
    try:
        # Get all competitor posts without detected_format
        result = await db.execute(
            text("""
                SELECT cp.id, cp.post_text, cp.hook, cp.content_analysis
                FROM crm.competitor_posts cp
                JOIN crm.competitors c ON cp.competitor_id = c.id
                WHERE c.org_id = :org_id 
                  AND cp.detected_format IS NULL
                  AND cp.post_text IS NOT NULL
                ORDER BY cp.id
            """),
            {"org_id": org_id}
        )
        posts_to_update = result.fetchall()
        
        if not posts_to_update:
            return {
                "message": "No posts need format classification",
                "updated": 0,
                "total": 0
            }
        
        updated_count = 0
        format_counts = Counter()
        
        for post_row in posts_to_update:
            post_id = post_row[0]
            post_text = post_row[1] or ""
            hook = post_row[2] or ""
            content_analysis = post_row[3]
            
            # Parse content_analysis if it's JSON
            analysis_dict = None
            if content_analysis:
                try:
                    if isinstance(content_analysis, str):
                        analysis_dict = json.loads(content_analysis)
                    elif isinstance(content_analysis, dict):
                        analysis_dict = content_analysis
                except (json.JSONDecodeError, TypeError):
                    analysis_dict = None
            
            # Classify the post
            detected_format = classify_post_format(post_text, hook, analysis_dict)
            format_counts[detected_format] += 1
            
            # Update the post
            await db.execute(
                text("""
                    UPDATE crm.competitor_posts 
                    SET detected_format = :format 
                    WHERE id = :post_id
                """),
                {"format": detected_format, "post_id": post_id}
            )
            updated_count += 1
        
        await db.commit()
        
        return {
            "message": f"Successfully classified {updated_count} posts",
            "updated": updated_count,
            "total": len(posts_to_update),
            "format_distribution": dict(format_counts)
        }
        
    except Exception as e:
        await db.rollback()
        logger.error("Failed to backfill post formats: %s", e)
        raise HTTPException(status_code=500, detail="Failed to backfill post formats")


@router.post("/score-hook")
async def score_hook_endpoint(
    request: Request,
    body: dict,
    db: AsyncSession = Depends(get_tenant_db)
):
    """Score a hook's 'stop the scroll' potential using competitor data."""
    org_id = get_org_id(request)
    
    hook_text = body.get("hook_text", "").strip()
    format_slug = body.get("format_slug")
    
    if not hook_text:
        raise HTTPException(status_code=422, detail="hook_text is required")
    
    try:
        # Load competitor posts for comparison
        posts = await load_cached_posts(db, org_id, days=60)  # Last 60 days for context
        
        # Score the hook
        result = score_hook(hook_text, posts, format_slug)
        
        return {
            "hook_text": hook_text,
            "format_slug": format_slug,
            "score": result["score"],
            "reasons": result["reasons"],
            "competitor_posts_analyzed": len(posts)
        }
        
    except Exception as e:
        logger.error("Failed to score hook: %s", e)
        raise HTTPException(status_code=500, detail="Failed to score hook")


@router.post("/sync-all")
async def sync_all_competitors():
    """Kick off a background sync of all competitors. Returns immediately."""
    global _sync_all_task
    
    if _sync_all_status.get("running"):
        return {"accepted": True, "message": "Sync already running", **_sync_all_status}
    
    _sync_all_task = asyncio.create_task(_run_sync_all())
    return {"accepted": True, "message": "Sync started in background", "total": 0, "success": 0}


@router.get("/sync-all/status")
async def get_sync_all_status():
    """Check the status of the background sync."""
    return _sync_all_status


# ── Phase 4: Performance Feedback Loop Backend ──────────────────────────────

class CollectPerformanceRequest(BaseModel):
    """Request body for collecting performance metrics from a published post."""
    distribution_post_id: int
    video_project_id: Optional[int] = None
    format_slug: Optional[str] = None
    hook_text: Optional[str] = None
    competitor_inspiration_ids: Optional[List[int]] = None
    metrics: Dict[str, int] = Field(
        description="Performance metrics: likes, comments, shares, saves, reach, views"
    )


class PerformanceFeedbackResponse(BaseModel):
    """Response for performance feedback endpoints."""
    id: int
    org_id: int
    scheduled_post_id: Optional[int] = None
    format_slug: Optional[str] = None
    hook_text: Optional[str] = None
    hook_score: Optional[float] = None
    likes: int = 0
    comments: int = 0
    shares: int = 0
    saves: int = 0
    reach: int = 0
    views: int = 0
    engagement_score: float = 0.0
    competitor_avg_engagement: Optional[float] = None
    performance_delta: Optional[float] = None
    performance_tier: Optional[str] = None
    created_at: datetime


class FeedbackWeights(BaseModel):
    """Weights for competitor vs own data in script generation."""
    competitor_weight: float
    own_weight: float
    feedback_records_count: int


class GenerationContext(BaseModel):
    """Enhanced context for script generation including performance feedback."""
    competitor_weight: float
    own_weight: float
    top_competitor_hooks: List[str]
    top_own_hooks: List[str]
    format_performance: Dict[str, Dict[str, Any]]
    audience_demands: List[str]
    recommendations: List[str]


class FormatLeaderboardItem(BaseModel):
    """Format performance leaderboard item."""
    format: str
    avg_engagement: float
    count: int
    avg_delta: str


class HookLeaderboardItem(BaseModel):
    """Hook performance leaderboard item."""
    hook: str
    engagement: float
    format: str
    delta: str


class PerformanceDashboardResponse(BaseModel):
    """Performance dashboard aggregated data."""
    format_leaderboard: List[FormatLeaderboardItem]
    hook_leaderboard: List[HookLeaderboardItem]
    time_heatmap: Dict[str, Dict[str, float]]
    format_trends: Dict[str, List[Dict[str, Any]]]
    total_posts: int
    avg_engagement: float
    best_format: str
    best_time: str


def get_feedback_weights(org_id: int, feedback_count: int) -> FeedbackWeights:
    """Calculate the competitor vs own-data weight based on how much performance data exists.
    
    Day 1 (0 posts):   competitor=1.0, own=0.0
    Day 30 (10 posts):  competitor=0.7, own=0.3
    Day 90 (50 posts):  competitor=0.4, own=0.6
    Day 180 (100+ posts): competitor=0.2, own=0.8
    """
    if feedback_count == 0:
        competitor_weight = 1.0
        own_weight = 0.0
    elif feedback_count <= 10:
        competitor_weight = 0.7
        own_weight = 0.3
    elif feedback_count <= 50:
        competitor_weight = 0.4
        own_weight = 0.6
    else:
        competitor_weight = 0.2
        own_weight = 0.8
    
    return FeedbackWeights(
        competitor_weight=competitor_weight,
        own_weight=own_weight,
        feedback_records_count=feedback_count
    )


@router.post("/collect-performance", response_model=PerformanceFeedbackResponse)
async def collect_performance(
    request: Request,
    body: CollectPerformanceRequest,
    db: AsyncSession = Depends(get_tenant_db),
):
    """Collect 48hr performance metrics for a published post and score against competitor benchmarks."""
    org_id = get_org_id(request)
    
    try:
        # 1. Calculate engagement_score using existing formula
        metrics = body.metrics
        engagement_score = calculate_engagement_score(
            metrics.get("likes", 0),
            metrics.get("comments", 0), 
            metrics.get("shares", 0)
        )
        
        # 2. Pull competitor inspiration posts from DB if provided
        competitor_avg_engagement = None
        if body.competitor_inspiration_ids:
            competitor_result = await db.execute(
                text("""
                    SELECT AVG(engagement_score) as avg_engagement
                    FROM crm.competitor_posts cp
                    JOIN crm.competitors c ON cp.competitor_id = c.id
                    WHERE cp.id = ANY(:inspiration_ids) AND c.org_id = :org_id
                """),
                {
                    "inspiration_ids": body.competitor_inspiration_ids,
                    "org_id": org_id
                }
            )
            competitor_row = competitor_result.first()
            if competitor_row and competitor_row.avg_engagement:
                competitor_avg_engagement = float(competitor_row.avg_engagement)
        
        # 3. Compute performance_delta and classify tier
        performance_delta = None
        performance_tier = "unknown"
        
        if competitor_avg_engagement is not None:
            performance_delta = engagement_score - competitor_avg_engagement
            delta_percent = (performance_delta / competitor_avg_engagement) * 100 if competitor_avg_engagement > 0 else 0
            
            if delta_percent > 20:
                performance_tier = "outperform"
            elif delta_percent < -20:
                performance_tier = "underperform" 
            else:
                performance_tier = "match"
        
        # 4. Score the hook if provided
        hook_score = None
        if body.hook_text:
            # Load competitor posts for hook scoring context
            competitor_posts = await load_cached_posts(db, org_id, days=60)
            hook_result = score_hook(body.hook_text, competitor_posts, body.format_slug)
            hook_score = hook_result["score"]
        
        # 5. Store in content_performance_feedback table
        feedback_result = await db.execute(
            text("""
                INSERT INTO crm.content_performance_feedback (
                    org_id, scheduled_post_id, competitor_inspiration_ids, format_slug, hook_text, hook_score,
                    likes, comments, shares, saves, reach, views, engagement_score,
                    competitor_avg_engagement, performance_delta, performance_tier
                ) VALUES (
                    :org_id, :scheduled_post_id, :competitor_inspiration_ids, :format_slug, :hook_text, :hook_score,
                    :likes, :comments, :shares, :saves, :reach, :views, :engagement_score,
                    :competitor_avg_engagement, :performance_delta, :performance_tier
                ) RETURNING id, created_at
            """),
            {
                "org_id": org_id,
                "scheduled_post_id": body.distribution_post_id,
                "competitor_inspiration_ids": body.competitor_inspiration_ids,
                "format_slug": body.format_slug,
                "hook_text": body.hook_text,
                "hook_score": hook_score,
                "likes": metrics.get("likes", 0),
                "comments": metrics.get("comments", 0),
                "shares": metrics.get("shares", 0),
                "saves": metrics.get("saves", 0),
                "reach": metrics.get("reach", 0),
                "views": metrics.get("views", 0),
                "engagement_score": engagement_score,
                "competitor_avg_engagement": competitor_avg_engagement,
                "performance_delta": performance_delta,
                "performance_tier": performance_tier,
            }
        )
        
        feedback_row = feedback_result.first()
        await db.commit()
        
        # 6. Return the feedback record
        return PerformanceFeedbackResponse(
            id=feedback_row.id,
            org_id=org_id,
            scheduled_post_id=body.distribution_post_id,
            format_slug=body.format_slug,
            hook_text=body.hook_text,
            hook_score=hook_score,
            likes=metrics.get("likes", 0),
            comments=metrics.get("comments", 0),
            shares=metrics.get("shares", 0),
            saves=metrics.get("saves", 0),
            reach=metrics.get("reach", 0),
            views=metrics.get("views", 0),
            engagement_score=engagement_score,
            competitor_avg_engagement=competitor_avg_engagement,
            performance_delta=performance_delta,
            performance_tier=performance_tier,
            created_at=feedback_row.created_at
        )
        
    except Exception as e:
        logger.error("Failed to collect performance feedback: %s", e)
        raise HTTPException(status_code=500, detail="Failed to collect performance feedback")


@router.get("/generation-context", response_model=GenerationContext)
async def get_generation_context(
    request: Request,
    db: AsyncSession = Depends(get_tenant_db),
):
    """Returns the full context needed for script generation, including both competitor data AND own performance data with proper weighting."""
    org_id = get_org_id(request)
    
    try:
        # Get feedback records count for weight calculation
        feedback_count_result = await db.execute(
            text("SELECT COUNT(*) as count FROM crm.content_performance_feedback WHERE org_id = :org_id"),
            {"org_id": org_id}
        )
        feedback_count = feedback_count_result.scalar() or 0
        
        # Calculate weights
        weights = get_feedback_weights(org_id, feedback_count)
        
        # Get top competitor hooks from cached posts
        competitor_posts = await load_cached_posts(db, org_id, days=45)
        ranked_competitor_posts = _sorted_posts_for_analysis(competitor_posts)
        top_competitor_hooks = [_post_hook(post) for post in ranked_competitor_posts[:10] if _post_hook(post)]
        
        # Get top own hooks from performance feedback
        own_hooks_result = await db.execute(
            text("""
                SELECT hook_text, engagement_score
                FROM crm.content_performance_feedback
                WHERE org_id = :org_id AND hook_text IS NOT NULL
                ORDER BY engagement_score DESC
                LIMIT 10
            """),
            {"org_id": org_id}
        )
        top_own_hooks = [row.hook_text for row in own_hooks_result.fetchall()]
        
        # Get format performance from own data
        format_performance = {}
        format_result = await db.execute(
            text("""
                SELECT 
                    format_slug,
                    AVG(engagement_score) as avg_engagement,
                    COUNT(*) as count,
                    (SELECT hook_text FROM crm.content_performance_feedback cpf2 
                     WHERE cpf2.org_id = :org_id AND cpf2.format_slug = cpf.format_slug 
                     ORDER BY cpf2.engagement_score DESC LIMIT 1) as best_hook
                FROM crm.content_performance_feedback cpf
                WHERE org_id = :org_id AND format_slug IS NOT NULL
                GROUP BY format_slug
                ORDER BY avg_engagement DESC
            """),
            {"org_id": org_id}
        )
        
        for row in format_result.fetchall():
            format_performance[row.format_slug] = {
                "avg_engagement": round(row.avg_engagement, 1),
                "count": row.count,
                "best_hook": row.best_hook
            }
        
        # Get audience demands from trending topics
        trending_topics = await analyze_trending_topics(competitor_posts)
        audience_demands = [topic.topic for topic in trending_topics[:8]]
        
        # Generate recommendations based on performance data
        recommendations = []
        
        if feedback_count > 0:
            # Analyze format performance
            if format_performance:
                best_format = max(format_performance.items(), key=lambda x: x[1]["avg_engagement"])
                recommendations.append(f"{best_format[0].replace('_', ' ').title()} format outperforms by {int(best_format[1]['avg_engagement'] - 1000):+d} points for your audience")
        
            # Hook pattern analysis
            if len(top_own_hooks) >= 3:
                # Find common starting patterns in successful hooks
                starts = [hook.split()[0].lower() for hook in top_own_hooks if hook and len(hook.split()) > 0]
                if starts:
                    from collections import Counter
                    common_start = Counter(starts).most_common(1)[0]
                    if common_start[1] >= 2:
                        recommendations.append(f"Hooks starting with '{common_start[0].title()}' get {common_start[1]}x more engagement for you")
        
        if not recommendations:
            recommendations = [
                "Build performance history by collecting metrics from your next 5 posts",
                "Focus on competitor data until you have 10+ performance records"
            ]
        
        return GenerationContext(
            competitor_weight=weights.competitor_weight,
            own_weight=weights.own_weight,
            top_competitor_hooks=top_competitor_hooks,
            top_own_hooks=top_own_hooks,
            format_performance=format_performance,
            audience_demands=audience_demands,
            recommendations=recommendations
        )
        
    except Exception as e:
        logger.error("Failed to get generation context: %s", e)
        raise HTTPException(status_code=500, detail="Failed to get generation context")


@router.get("/performance-dashboard", response_model=PerformanceDashboardResponse)
async def get_performance_dashboard(
    request: Request,
    db: AsyncSession = Depends(get_tenant_db),
):
    """Returns aggregated performance data for the frontend dashboard."""
    org_id = get_org_id(request)
    
    try:
        # Format leaderboard
        format_result = await db.execute(
            text("""
                SELECT 
                    format_slug,
                    AVG(engagement_score) as avg_engagement,
                    COUNT(*) as count,
                    AVG(CASE WHEN competitor_avg_engagement IS NOT NULL AND competitor_avg_engagement > 0 
                        THEN ((engagement_score - competitor_avg_engagement) / competitor_avg_engagement) * 100 
                        ELSE NULL END) as avg_delta_percent
                FROM crm.content_performance_feedback
                WHERE org_id = :org_id AND format_slug IS NOT NULL
                GROUP BY format_slug
                ORDER BY avg_engagement DESC
            """),
            {"org_id": org_id}
        )
        
        format_leaderboard = []
        for row in format_result.fetchall():
            delta_str = f"{row.avg_delta_percent:+.0f}%" if row.avg_delta_percent is not None else "N/A"
            format_leaderboard.append(FormatLeaderboardItem(
                format=row.format_slug,
                avg_engagement=round(row.avg_engagement, 1),
                count=row.count,
                avg_delta=delta_str
            ))
        
        # Hook leaderboard
        hook_result = await db.execute(
            text("""
                SELECT 
                    hook_text,
                    engagement_score,
                    format_slug,
                    CASE WHEN competitor_avg_engagement IS NOT NULL AND competitor_avg_engagement > 0 
                         THEN ((engagement_score - competitor_avg_engagement) / competitor_avg_engagement) * 100 
                         ELSE NULL END as delta_percent
                FROM crm.content_performance_feedback
                WHERE org_id = :org_id AND hook_text IS NOT NULL
                ORDER BY engagement_score DESC
                LIMIT 10
            """),
            {"org_id": org_id}
        )
        
        hook_leaderboard = []
        for row in hook_result.fetchall():
            delta_str = f"{row.delta_percent:+.0f}%" if row.delta_percent is not None else "N/A"
            hook_leaderboard.append(HookLeaderboardItem(
                hook=row.hook_text[:50] + "..." if len(row.hook_text) > 50 else row.hook_text,
                engagement=round(row.engagement_score, 1),
                format=row.format_slug or "unknown",
                delta=delta_str
            ))
        
        # Time heatmap - using created_at as proxy for posting time
        time_result = await db.execute(
            text("""
                SELECT 
                    EXTRACT(DOW FROM created_at) as day_of_week,
                    EXTRACT(HOUR FROM created_at) as hour_of_day,
                    AVG(engagement_score) as avg_engagement
                FROM crm.content_performance_feedback
                WHERE org_id = :org_id
                GROUP BY day_of_week, hour_of_day
                HAVING COUNT(*) >= 2
                ORDER BY day_of_week, hour_of_day
            """),
            {"org_id": org_id}
        )
        
        days = ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]
        time_heatmap = {}
        for row in time_result.fetchall():
            day_name = days[int(row.day_of_week)]
            hour = str(int(row.hour_of_day))
            if day_name not in time_heatmap:
                time_heatmap[day_name] = {}
            time_heatmap[day_name][hour] = round(row.avg_engagement, 1)
        
        # Format trends by week
        format_trends = {}
        if format_leaderboard:
            trends_result = await db.execute(
                text("""
                    SELECT 
                        format_slug,
                        EXTRACT(YEAR FROM created_at) || '-W' || LPAD(EXTRACT(WEEK FROM created_at)::text, 2, '0') as week,
                        AVG(engagement_score) as avg_engagement
                    FROM crm.content_performance_feedback
                    WHERE org_id = :org_id AND format_slug IS NOT NULL
                        AND created_at >= NOW() - INTERVAL '8 weeks'
                    GROUP BY format_slug, week
                    ORDER BY format_slug, week
                """),
                {"org_id": org_id}
            )
            
            for row in trends_result.fetchall():
                format_slug = row.format_slug
                if format_slug not in format_trends:
                    format_trends[format_slug] = []
                format_trends[format_slug].append({
                    "week": row.week,
                    "avg": round(row.avg_engagement, 1)
                })
        
        # Overall stats
        overall_result = await db.execute(
            text("""
                SELECT 
                    COUNT(*) as total_posts,
                    AVG(engagement_score) as avg_engagement,
                    MODE() WITHIN GROUP (ORDER BY format_slug) as best_format
                FROM crm.content_performance_feedback
                WHERE org_id = :org_id
            """),
            {"org_id": org_id}
        )
        
        overall_row = overall_result.first()
        total_posts = overall_row.total_posts if overall_row else 0
        avg_engagement = round(overall_row.avg_engagement, 1) if overall_row and overall_row.avg_engagement else 0.0
        best_format = overall_row.best_format or "unknown"
        
        # Find best posting time from heatmap
        best_time = "Unknown"
        if time_heatmap:
            best_score = 0
            for day, hours in time_heatmap.items():
                for hour, score in hours.items():
                    if score > best_score:
                        best_score = score
                        hour_12 = "12pm" if hour == "12" else f"{int(hour)}pm" if int(hour) > 12 else f"{hour}am"
                        best_time = f"{day.title()} {hour_12}"
        
        return PerformanceDashboardResponse(
            format_leaderboard=format_leaderboard,
            hook_leaderboard=hook_leaderboard,
            time_heatmap=time_heatmap,
            format_trends=format_trends,
            total_posts=total_posts,
            avg_engagement=avg_engagement,
            best_format=best_format,
            best_time=best_time
        )
        
    except Exception as e:
        logger.error("Failed to get performance dashboard: %s", e)
        raise HTTPException(status_code=500, detail="Failed to get performance dashboard")


@router.post("/auto-collect-performance")
async def auto_collect_performance(
    request: Request,
    db: AsyncSession = Depends(get_tenant_db),
):
    """Finds all distribution_posts that are 48+ hours old and haven't been scored yet, 
    collects their metrics from the social sync data, and creates feedback records automatically.
    
    This should be callable from a cron job.
    """
    org_id = get_org_id(request)
    
    try:
        # Find posts that need performance collection
        # This is a placeholder query - adjust table names and schema based on your actual social sync structure
        pending_posts_result = await db.execute(
            text("""
                SELECT 
                    sp.id as post_id,
                    sp.platform,
                    sp.content_text as post_text,
                    sp.scheduled_at,
                    sp.posted_at,
                    sp.format_slug,
                    sp.hook_text,
                    sm.likes,
                    sm.comments,
                    sm.shares,
                    sm.saves,
                    sm.reach,
                    sm.views
                FROM crm.scheduled_posts sp
                LEFT JOIN crm.social_metrics sm ON sm.post_id = sp.id
                LEFT JOIN crm.content_performance_feedback cpf ON cpf.scheduled_post_id = sp.id
                WHERE sp.org_id = :org_id
                    AND sp.posted_at IS NOT NULL
                    AND sp.posted_at < NOW() - INTERVAL '48 hours'
                    AND cpf.id IS NULL
                    AND sm.likes IS NOT NULL
                ORDER BY sp.posted_at DESC
                LIMIT 50
            """),
            {"org_id": org_id}
        )
        
        pending_posts = pending_posts_result.fetchall()
        
        if not pending_posts:
            return {
                "message": "No posts found that need performance collection",
                "collected": 0,
                "total_eligible": 0
            }
        
        collected = 0
        errors = []
        
        for post in pending_posts:
            try:
                # Calculate engagement score
                engagement_score = calculate_engagement_score(
                    post.likes or 0,
                    post.comments or 0,
                    post.shares or 0
                )
                
                # Score hook if available
                hook_score = None
                if post.hook_text:
                    competitor_posts = await load_cached_posts(db, org_id, days=60)
                    hook_result = score_hook(post.hook_text, competitor_posts, post.format_slug)
                    hook_score = hook_result["score"]
                
                # Get competitor average for format (if format is known)
                competitor_avg_engagement = None
                if post.format_slug:
                    competitor_result = await db.execute(
                        text("""
                            SELECT AVG(engagement_score) as avg_engagement
                            FROM crm.competitor_posts cp
                            JOIN crm.competitors c ON cp.competitor_id = c.id
                            WHERE c.org_id = :org_id AND cp.detected_format = :format_slug
                        """),
                        {"org_id": org_id, "format_slug": post.format_slug}
                    )
                    comp_row = competitor_result.first()
                    if comp_row and comp_row.avg_engagement:
                        competitor_avg_engagement = float(comp_row.avg_engagement)
                
                # Calculate performance delta
                performance_delta = None
                performance_tier = "unknown"
                if competitor_avg_engagement is not None:
                    performance_delta = engagement_score - competitor_avg_engagement
                    delta_percent = (performance_delta / competitor_avg_engagement) * 100 if competitor_avg_engagement > 0 else 0
                    
                    if delta_percent > 20:
                        performance_tier = "outperform"
                    elif delta_percent < -20:
                        performance_tier = "underperform"
                    else:
                        performance_tier = "match"
                
                # Insert feedback record
                await db.execute(
                    text("""
                        INSERT INTO crm.content_performance_feedback (
                            org_id, scheduled_post_id, format_slug, hook_text, hook_score,
                            likes, comments, shares, saves, reach, views, engagement_score,
                            competitor_avg_engagement, performance_delta, performance_tier
                        ) VALUES (
                            :org_id, :scheduled_post_id, :format_slug, :hook_text, :hook_score,
                            :likes, :comments, :shares, :saves, :reach, :views, :engagement_score,
                            :competitor_avg_engagement, :performance_delta, :performance_tier
                        )
                    """),
                    {
                        "org_id": org_id,
                        "scheduled_post_id": post.post_id,
                        "format_slug": post.format_slug,
                        "hook_text": post.hook_text,
                        "hook_score": hook_score,
                        "likes": post.likes or 0,
                        "comments": post.comments or 0,
                        "shares": post.shares or 0,
                        "saves": post.saves or 0,
                        "reach": post.reach or 0,
                        "views": post.views or 0,
                        "engagement_score": engagement_score,
                        "competitor_avg_engagement": competitor_avg_engagement,
                        "performance_delta": performance_delta,
                        "performance_tier": performance_tier,
                    }
                )
                
                collected += 1
                
            except Exception as e:
                logger.warning("Failed to collect performance for post %s: %s", post.post_id, e)
                errors.append(f"Post {post.post_id}: {str(e)[:100]}")
        
        await db.commit()
        
        return {
            "message": f"Auto-collected performance data for {collected} posts",
            "collected": collected,
            "total_eligible": len(pending_posts),
            "errors": errors[:10] if errors else []
        }
        
    except Exception as e:
        logger.error("Failed to auto-collect performance data: %s", e)
        raise HTTPException(status_code=500, detail="Failed to auto-collect performance data")


# ── Linked Account Detection + Dossier ───────────────────────────

def _extract_social_links(bio: str, captions: list[str]) -> dict:
    """Extract social platform handles and links from bio and post captions."""
    import re

    results = {
        "handles": [],
        "links": [],
        "affiliate_links": [],
        "products": [],
    }

    all_text = bio + " " + " ".join(captions[:20])

    # Extract @mentions (potential linked accounts)
    mentions = set(re.findall(r"@([a-zA-Z0-9_.]{1,30})", all_text))
    results["handles"] = sorted(mentions)

    # Extract URLs
    urls = re.findall(r"https?://[^\s<>\"')\]]+", all_text)
    for url in urls:
        url_lower = url.lower()
        if any(aff in url_lower for aff in ["amzn.to", "bit.ly", "linktr.ee", "stan.store", "gumroad", "shopify", "etsy", "beacons.ai", "tap.bio"]):
            results["affiliate_links"].append(url)
        else:
            results["links"].append(url)

    # Extract linktree/bio link patterns
    link_patterns = re.findall(r"(?:linktr\.ee|link\.bio|beacons\.ai|stan\.store)/([a-zA-Z0-9_.]+)", all_text)
    for lp in link_patterns:
        if lp not in results["handles"]:
            results["handles"].append(lp)

    # Detect product mentions (common commerce keywords)
    product_keywords = ["shop", "store", "buy", "order", "discount", "code", "coupon", "sale", "launch", "available now", "link in bio", "dm to order"]
    for caption in captions[:20]:
        cap_lower = caption.lower()
        if any(kw in cap_lower for kw in product_keywords):
            # Extract first sentence as product hint
            first_line = caption.split("\n")[0][:100]
            if first_line not in results["products"]:
                results["products"].append(first_line)

    return results


@router.get("/competitors/{competitor_id}/dossier")
async def get_competitor_dossier(
    request: Request,
    competitor_id: int,
    db: AsyncSession = Depends(get_tenant_db),
):
    """Get comprehensive dossier for a competitor: bio, links, products, network."""
    org_id = get_org_id(request)
    competitor = await _get_competitor_or_404(db, competitor_id, org_id)
    posts = await load_cached_posts(db, org_id, competitor_id)

    # Extract social links from bio and captions
    captions = [p.get("caption", "") or p.get("text", "") for p in posts if p.get("caption") or p.get("text")]
    social_data = _extract_social_links(competitor.bio or "", captions)
    
    # Merge stored dossier_data (bio_links, threads, business intel from scraper)
    dossier_data = {}
    if hasattr(competitor, 'dossier_data') and competitor.dossier_data:
        dossier_data = competitor.dossier_data if isinstance(competitor.dossier_data, dict) else {}
    
    # Add bio_links from stored dossier data
    stored_bio_links = dossier_data.get("bio_links", [])
    for link in stored_bio_links:
        url = link.get("url", "") if isinstance(link, dict) else str(link)
        if url and url not in social_data["links"]:
            social_data["links"].append(url)
    
    # Add threads handle as linked account
    threads_handle = dossier_data.get("threads_handle", "")
    if threads_handle and f"@{threads_handle}" not in social_data["handles"]:
        social_data["handles"].append(f"threads:@{threads_handle}")
    
    # Business intel from bio parsing
    business_intel = dossier_data.get("business_intel", {})

    # Audience analysis (stored or computed)
    audience = None
    try:
        result = await db.execute(
            text("SELECT audience_analysis FROM crm.competitors WHERE id = :cid AND org_id = :org_id"),
            {"cid": competitor_id, "org_id": org_id},
        )
        row = result.first()
        if row and row[0]:
            audience = json.loads(row[0]) if isinstance(row[0], str) else row[0]
    except Exception:
        pass

    if not audience and posts:
        try:
            topics = await analyze_trending_topics(posts)
            # analyze_trending_topics returns a list of TrendingTopic, extract audience info
            audience = {
                "themes": [t.topic for t in topics[:5]] if topics else [],
                "audience_type": "Engaged" if len(posts) > 5 else "Unknown",
                "engagement_style": "Active" if sum(p.get("engagement_score", 0) for p in posts) / max(len(posts), 1) > 100 else "Moderate",
                "key_interests": [t.topic for t in topics[:3]] if topics else [],
            }
        except Exception:
            audience = {
                "themes": [],
                "audience_type": "Unknown",
                "engagement_style": "Unknown",
                "key_interests": [],
            }

    return {
        "competitor_id": competitor_id,
        "handle": competitor.handle,
        "bio": competitor.bio or "",
        "full_name": dossier_data.get("full_name", ""),
        "is_verified": dossier_data.get("is_verified", False),
        "category": dossier_data.get("category", ""),
        "followers": competitor.followers or 0,
        "following": getattr(competitor, 'following', 0) or 0,
        "post_count": len(posts),
        "linked_handles": social_data["handles"],
        "links": social_data["links"],
        "bio_links": stored_bio_links,
        "affiliate_links": social_data["affiliate_links"],
        "product_mentions": social_data["products"],
        "business_intel": business_intel,
        "audience": audience,
        "content_summary": {
            "total_posts": len(posts),
            "avg_engagement": sum(p.get("engagement_score", 0) for p in posts) / max(len(posts), 1),
            "top_hashtags": _get_top_hashtags(posts, 10),
            "post_frequency": _estimate_post_frequency(posts),
        },
    }


def _get_top_hashtags(posts: list, limit: int = 10) -> list[dict]:
    """Extract top hashtags from posts."""
    counter: Counter = Counter()
    for p in posts:
        tags = p.get("hashtags", [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]
        counter.update(tags)
    return [{"tag": t, "count": c} for t, c in counter.most_common(limit)]


def _estimate_post_frequency(posts: list) -> str:
    """Estimate how often the competitor posts."""
    if len(posts) < 2:
        return "Unknown"
    dates = sorted(
        [p["posted_at"] for p in posts if p.get("posted_at")],
        reverse=True,
    )
    if len(dates) < 2:
        return "Unknown"
    # Calculate average days between posts
    try:
        if isinstance(dates[0], str):
            from dateutil.parser import parse
            dates = [parse(d) for d in dates]
        gaps = [(dates[i] - dates[i + 1]).days for i in range(min(len(dates) - 1, 10))]
        avg_gap = sum(gaps) / len(gaps) if gaps else 0
        if avg_gap <= 1:
            return "Daily"
        elif avg_gap <= 3:
            return "Every 2-3 days"
        elif avg_gap <= 7:
            return "Weekly"
        elif avg_gap <= 14:
            return "Bi-weekly"
        else:
            return f"Every ~{int(avg_gap)} days"
    except Exception:
        return "Unknown"