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

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select, text, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.db.crm_db import get_crm_db
from app.models.crm.competitor import Competitor
from app.models.crm.content_script import ContentScript
from app.models.crm.social import SocialAccount
from app.api.scraper import (
    sync_instagram_competitor,
    sync_instagram_competitor_batch,
    calculate_competitor_engagement_score,
)
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


async def get_social_account_token(db: AsyncSession, platform: str) -> Optional[str]:
    """Get access token for connected social account."""
    try:
        result = await db.execute(
            select(SocialAccount.access_token)
            .where(SocialAccount.platform == platform)
            .where(SocialAccount.status == "connected")
            .limit(1)
        )
        token_row = result.first()
        return token_row[0] if token_row else None
    except Exception as e:
        logger.error("Failed to get token for %s: %s", platform, e)
        return None


async def save_competitor_posts(db: AsyncSession, competitor_id: int, platform: str, 
                               posts: List[CompetitorPost]) -> bool:
    """Save competitor posts to cache table."""
    try:
        # Delete old posts for this competitor/platform
        await db.execute(
            text("""
                DELETE FROM crm.competitor_posts 
                WHERE competitor_id = :competitor_id AND platform = :platform
            """),
            {"competitor_id": competitor_id, "platform": platform}
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


async def load_cached_posts(db: AsyncSession, competitor_id: int = None,
                           platform: str = None, days: Optional[int] = 30) -> List[Dict]:
    """Load cached competitor posts from database."""
    try:
        query = """
            SELECT cp.*, c.handle, COALESCE(c.followers, 0) AS followers
            FROM crm.competitor_posts cp
            JOIN crm.competitors c ON cp.competitor_id = c.id
            WHERE 1 = 1
        """
        params: Dict[str, Any] = {}

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


async def _get_competitor_or_404(db: AsyncSession, competitor_id: int) -> Competitor:
    """Load a competitor or raise a 404."""
    result = await db.execute(select(Competitor).where(Competitor.id == competitor_id))
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
    cached_posts = await load_cached_posts(db, competitor.id, platform, days=days)
    if cached_posts or platform != "instagram":
        return cached_posts, None

    lock = _get_competitor_sync_lock(competitor.id)
    async with lock:
        cached_posts = await load_cached_posts(db, competitor.id, platform, days=days)
        if cached_posts:
            return cached_posts, None

        sync_result = await sync_instagram_competitor(db, competitor)
        if not sync_result["success"]:
            raise HTTPException(
                status_code=422,
                detail=f"Instagram scrape failed: {sync_result['error']}",
            )

        await db.commit()
        cached_posts = await load_cached_posts(db, competitor.id, platform, days=days)
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
    competitor_id: int,
    db: AsyncSession = Depends(get_crm_db)
):
    """Fetch recent posts from a tracked competitor using the appropriate social API."""
    try:
        competitor = await _get_competitor_or_404(db, competitor_id)
        
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
            token = await get_social_account_token(db, "x")
            if not token:
                raise HTTPException(status_code=422, detail="X account not connected")
            posts = await fetch_x_content(handle, token)
            if posts:
                await save_competitor_posts(db, competitor_id, platform, posts)

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
    platform: Optional[str] = None,
    days: int = 30,
    db: AsyncSession = Depends(get_crm_db)
):
    """Analyze all competitor content to extract common themes/topics ranked by engagement."""
    try:
        # Load cached posts from all competitors
        cached_posts = await load_cached_posts(db, platform=platform, days=days)
        
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
    limit: int = 20,
    days: int = 30,
    platform: Optional[str] = None,
    db: AsyncSession = Depends(get_crm_db)
):
    """Get top performing content across all competitors."""
    try:
        # Load cached posts sorted by engagement
        cached_posts = await load_cached_posts(db, platform=platform, days=days)
        
        if not cached_posts:
            return TopContentResponse(posts=[], total_posts=0)
        
        # Recompute ranking from current counts, follower context, and recency
        top_posts = _sorted_posts_for_analysis(cached_posts)[:limit]
        
        # Convert to response format
        top_content = []
        for post in top_posts:
            top_content.append(TopContentItem(
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
    limit: int = 50,
    days: int = 30,
    platform: Optional[str] = None,
    db: AsyncSession = Depends(get_crm_db)
):
    """Get extracted hooks ranked by engagement score."""
    try:
        # Load cached posts
        cached_posts = await load_cached_posts(db, platform=platform, days=days)
        
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
    competitor_id: Optional[int] = None,
    platform: Optional[str] = None,
    db: AsyncSession = Depends(get_crm_db)
):
    """Re-fetch content for competitors and update cache."""
    try:
        # Get competitors to refresh
        query = select(Competitor)
        
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
            batch_result = await sync_instagram_competitor_batch(db, instagram_competitors)
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
                    token = await get_social_account_token(db, "x")
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
    competitor_id: int,
    request: ScriptGenerationRequest,
    save_to_db: bool = False,
    db: AsyncSession = Depends(get_crm_db)
):
    """Generate competitor-driven script ideas from live cached performance data."""
    try:
        competitor = await _get_competitor_or_404(db, competitor_id)

        if competitor.platform.lower() == "instagram":
            cached_posts, _ = await _ensure_competitor_cached_posts(db, competitor, days=45)
        else:
            cached_posts = await load_cached_posts(db, competitor_id=competitor_id, days=45)

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
            platform=request.platform,
            posts=ranked_posts,
            business_settings=business_settings,
            count=request.count,
            requested_topic=request.topic,
            hook_style=request.hook_style,
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
                platform=request.platform,
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
    platform: Optional[str] = None,
    competitor_id: Optional[int] = None,
    db: AsyncSession = Depends(get_crm_db)
):
    """List all generated content scripts."""
    try:
        query = select(ContentScript).order_by(ContentScript.created_at.desc())
        
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
    script_id: int,
    db: AsyncSession = Depends(get_crm_db)
):
    """Delete a generated script."""
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
    post_url: Optional[str] = None
    title: str
    likes: int = 0
    comments: int = 0
    shares: int = 0
    engagement_score: float = 0.0
    posted_at: Optional[datetime] = None
    hook: Optional[str] = None
    media_type: Optional[str] = None
    has_transcript: bool = False
    has_comments: bool = False


class FollowerAnalysisResponse(BaseModel):
    """Audience/follower analysis summary derived from post content."""
    themes: List[str]
    audience_type: str
    engagement_style: str
    key_interests: List[str]


class HashtagItem(BaseModel):
    """A hashtag with its frequency count."""
    tag: str
    count: int


@router.get("/competitors/{competitor_id}/top-videos", response_model=List[TopVideoItem])
async def get_competitor_top_videos(
    competitor_id: int,
    limit: int = 5,
    db: AsyncSession = Depends(get_crm_db)
):
    """Return the top-performing posts for a competitor, ordered by engagement_score."""
    try:
        competitor = await _get_competitor_or_404(db, competitor_id)
        cached_posts, _ = await _ensure_competitor_cached_posts(
            db,
            competitor,
            days=None,
        )

        return [
            TopVideoItem(
                id=post.get("id"),
                post_url=post.get("post_url", ""),
                title=(post.get("post_text") or "")[:100],
                likes=post.get("likes", 0) or 0,
                comments=post.get("comments", 0) or 0,
                shares=post.get("shares", 0) or 0,
                engagement_score=calculate_competitor_engagement_score(
                    post.get("likes", 0),
                    post.get("comments", 0),
                    post.get("shares", 0),
                    platform=post.get("platform"),
                ),
                posted_at=post.get("posted_at"),
                hook=post.get("hook"),
                media_type=post.get("media_type"),
                has_transcript=bool(post.get("transcript")),
                has_comments=bool(post.get("comments_data")),
            )
            for post in cached_posts[:limit]
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get top videos for competitor %s: %s", competitor_id, e)
        raise HTTPException(status_code=500, detail="Failed to get top videos")


@router.get("/competitors/follower-analysis", response_model=FollowerAnalysisResponse)
async def get_follower_analysis(
    db: AsyncSession = Depends(get_crm_db)
):
    """Analyze themes and audience demographics from all competitor post texts using TF-IDF."""
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
    competitor_id: int,
    db: AsyncSession = Depends(get_crm_db)
):
    """Extract hashtags from all post_text for a competitor, sorted by frequency."""
    try:
        competitor = await _get_competitor_or_404(db, competitor_id)
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


@router.post("/index-content")
async def index_content_for_recommendations(
    body: dict = {},
    db: AsyncSession = Depends(get_crm_db),
):
    """Index top competitor content into Qdrant for the recommendation engine.
    
    Call after syncing competitors or transcribing videos to update the index.
    Only indexes top 20% by engagement — the content worth learning from.
    """
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
async def recommend_content(body: dict = {}, db: AsyncSession = Depends(get_crm_db)):
    """Embedding-based recommendation engine.
    
    Analyzes competitors' top content semantically and generates
    hooks, hashtags, and script recommendations aligned to our business.
    
    Uses Qdrant vector search for content-based filtering.
    Falls back to v1 rule-based engine if index is empty.
    """
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
            select(Competitor).where(Competitor.platform == "instagram")
        )
        competitors = result.scalars().all()

        if not competitors:
            return {"recommendations": [], "message": "No competitors found. Add competitors first."}

        all_posts = []
        for comp in competitors:
            posts = await load_cached_posts(db, comp.id, limit=20)
            for p in posts:
                p["competitor_handle"] = comp.handle
                p["competitor_id"] = comp.id
            all_posts.extend(posts)

        if not all_posts:
            return {"recommendations": [], "message": "No competitor content cached. Sync competitors first."}

        ranked = _sorted_posts_for_analysis(all_posts)[:30]
        candidate_topics = _collect_candidate_topics(ranked, topic)
        business = await _get_business_settings(db)

        scripts = []
        for i, post in enumerate(ranked[:count]):
            t = candidate_topics[i % len(candidate_topics)] if candidate_topics else _derive_topic_label(post)
            script = generate_script_content(
                post=post,
                topic=t,
                business_settings=business,
                all_posts=ranked,
            )
            scripts.append(script)

        return {
            "recommendations": scripts,
            "competitors_analyzed": len(competitors),
            "posts_analyzed": len(all_posts),
            "top_topics": candidate_topics[:5],
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
            
            batch_result = await sync_instagram_competitor_batch(db, competitors)
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
            
            _sync_all_status = {
                "running": False,
                "message": f"Done: {batch_result.success}/{len(competitors)} synced, {batch_result.posts_saved} posts",
                "total": len(competitors),
                "success": batch_result.success,
                "failed": batch_result.failed,
                "posts_saved": batch_result.posts_saved,
                "audience_refreshed": audience_refreshed,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }
    except Exception as e:
        import traceback
        print(f"[SYNC-ALL] FAILED: {e}\n{traceback.format_exc()}", flush=True)
        _sync_all_status = {"running": False, "message": f"Failed: {str(e)[:100]}", "error": True}


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
    competitor_id: int,
    db: AsyncSession = Depends(get_crm_db),
):
    """Get comprehensive dossier for a competitor: bio, links, products, network."""
    competitor = await _get_competitor_or_404(db, competitor_id)
    posts = await load_cached_posts(db, competitor_id)

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
            text("SELECT audience_analysis FROM crm.competitors WHERE id = :cid"),
            {"cid": competitor_id},
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