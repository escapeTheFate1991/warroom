"""Content Recommendation Engine v2 — embedding-based.

Learns from competitors' top-performing content (captions + transcripts + 
audience intel) to recommend hooks, hashtags, and scripts tailored to our business.

Uses Qdrant vector search for semantic similarity instead of keyword matching.
"""

import json
import logging
import re
from collections import Counter
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.content_embedder import search_similar_content

logger = logging.getLogger(__name__)


async def recommend_content_v2(
    db: AsyncSession,
    topic: Optional[str] = None,
    platform: str = "instagram",
    count: int = 5,
    business_context: Optional[str] = None,
) -> Dict:
    """Generate content recommendations using embedding-based similarity.
    
    Flow:
    1. Build a query from business context + topic
    2. Search Qdrant for semantically similar top content
    3. Extract winning patterns (hooks, hashtags, delivery styles)
    4. Generate recommendations aligned to OUR business
    
    Returns: {recommendations: [...], patterns: {...}, hashtags: [...]}
    """
    # Get business settings
    if not business_context:
        business_context = await _get_business_context(db)
    
    # Build search query
    query = _build_search_query(business_context, topic, platform)
    
    # Search for similar top content
    similar = await search_similar_content(
        query=query,
        platform=platform,
        min_engagement=50,  # Skip low-engagement posts
        limit=30,  # Get enough for pattern extraction
    )
    
    if not similar:
        return {
            "recommendations": [],
            "patterns": {},
            "hashtags": [],
            "message": "No indexed content found. Run content indexing first.",
        }
    
    # Extract winning patterns from top similar content
    patterns = _extract_winning_patterns(similar)
    
    # Generate recommendations
    recommendations = _generate_recommendations(
        similar_content=similar[:count * 3],  # 3x candidates per requested count
        patterns=patterns,
        business_context=business_context,
        topic=topic,
        count=count,
    )
    
    # Extract and rank hashtags
    hashtags = _rank_hashtags(similar, platform)
    
    return {
        "recommendations": recommendations,
        "patterns": patterns,
        "hashtags": hashtags[:20],
        "similar_content_count": len(similar),
        "query_used": query[:200],
    }


def _build_search_query(business_context: str, topic: Optional[str], platform: str) -> str:
    """Build a semantic search query from business context and topic."""
    parts = []
    if topic:
        parts.append(topic)
    if business_context:
        parts.append(business_context)
    parts.append(f"Content for {platform} that drives engagement")
    return " ".join(parts)


def _extract_winning_patterns(similar: List[Dict]) -> Dict:
    """Analyze similar top content to find what works.
    
    Identifies:
    - Hook patterns (opening structures that get engagement)
    - Content length/format preferences
    - Sentiment that works
    - Topic clusters
    - Delivery style (if transcript data available)
    """
    hooks = []
    sentiments = Counter()
    media_types = Counter()
    engagement_by_type = {}
    top_handles = Counter()
    
    for item in similar:
        hook = item.get("hook", "")
        if hook:
            hooks.append({
                "hook": hook,
                "engagement": item.get("engagement_score", 0),
                "handle": item.get("competitor_handle", ""),
            })
        
        sentiments[item.get("sentiment", "unknown")] += 1
        
        mt = item.get("media_type", "image")
        media_types[mt] += 1
        engagement_by_type.setdefault(mt, []).append(item.get("engagement_score", 0))
        
        top_handles[item.get("competitor_handle", "unknown")] += 1
    
    # Sort hooks by engagement
    hooks.sort(key=lambda x: x["engagement"], reverse=True)
    
    # Hook pattern analysis
    hook_patterns = _classify_hook_patterns(hooks)
    
    # Best performing media type
    avg_engagement_by_type = {
        mt: sum(scores) / len(scores)
        for mt, scores in engagement_by_type.items()
        if scores
    }
    best_media_type = max(avg_engagement_by_type, key=avg_engagement_by_type.get) if avg_engagement_by_type else "reel"
    
    return {
        "top_hooks": hooks[:10],
        "hook_patterns": hook_patterns,
        "dominant_sentiment": sentiments.most_common(1)[0][0] if sentiments else "neutral",
        "sentiment_distribution": dict(sentiments),
        "best_media_type": best_media_type,
        "media_type_performance": avg_engagement_by_type,
        "top_competitors": [{"handle": h, "matching_posts": c} for h, c in top_handles.most_common(5)],
        "has_transcript_data": any(item.get("has_transcript") for item in similar),
        "has_audience_intel": any(item.get("has_audience_intel") for item in similar),
    }


def _classify_hook_patterns(hooks: List[Dict]) -> List[Dict]:
    """Classify hooks into pattern categories.
    
    Common viral hook patterns:
    - Question: "Did you know...?" / "What if...?"
    - Controversy: "Stop doing X" / "X is wrong"
    - Story: "I just..." / "Here's what happened..."
    - List: "3 ways to..." / "Top 5..."
    - Authority: "As a X with Y years..."
    - Curiosity gap: "This one trick..." / "The secret to..."
    """
    patterns = Counter()
    examples = {}
    
    for h in hooks:
        hook = h["hook"].lower()
        
        if "?" in hook or any(hook.startswith(w) for w in ["did ", "what ", "how ", "why ", "who ", "where ", "when "]):
            cat = "question"
        elif any(w in hook for w in ["stop ", "don't ", "never ", "wrong", "mistake", "myth"]):
            cat = "controversy"
        elif any(hook.startswith(w) for w in ["i just", "i was", "here's what", "so i", "today i", "last "]):
            cat = "story"
        elif re.search(r"\d+\s+(?:ways?|tips?|things?|reasons?|steps?|secrets?|mistakes?)", hook):
            cat = "list"
        elif any(w in hook for w in ["as a ", "with ", " years", "expert", "founder", "engineer"]):
            cat = "authority"
        elif any(w in hook for w in ["secret", "trick", "hack", "nobody", "most people", "what they"]):
            cat = "curiosity_gap"
        elif any(w in hook for w in ["this ", "here's ", "the "]):
            cat = "statement"
        else:
            cat = "other"
        
        patterns[cat] += 1
        if cat not in examples:
            examples[cat] = h["hook"][:100]
    
    return [
        {"pattern": p, "count": c, "example": examples.get(p, "")}
        for p, c in patterns.most_common()
    ]


def _generate_recommendations(
    similar_content: List[Dict],
    patterns: Dict,
    business_context: str,
    topic: Optional[str],
    count: int,
) -> List[Dict]:
    """Generate content recommendations from similar content patterns.
    
    Each recommendation includes:
    - A hook (inspired by top-performing hooks)
    - Suggested hashtags
    - Script outline
    - Why it should work (data-backed reasoning)
    - Source inspiration (which competitor posts)
    """
    recommendations = []
    used_hooks = set()
    
    top_hooks = patterns.get("top_hooks", [])
    hook_patterns = patterns.get("hook_patterns", [])
    best_type = patterns.get("best_media_type", "reel")
    
    for i, source in enumerate(similar_content):
        if len(recommendations) >= count:
            break
        
        source_hook = source.get("hook", "")
        if not source_hook or source_hook.lower() in used_hooks:
            continue
        used_hooks.add(source_hook.lower())
        
        # Extract hashtags from this source's metadata
        source_hashtags = source.get("hashtags", [])
        
        # Build the recommendation
        rec = {
            "rank": len(recommendations) + 1,
            "suggested_hook": source_hook,
            "hook_pattern": _get_hook_pattern(source_hook),
            "suggested_media_type": best_type,
            "suggested_hashtags": source_hashtags[:10],
            "script_outline": _build_script_outline(source, business_context, topic),
            "reasoning": _build_reasoning(source, patterns),
            "source_inspiration": {
                "competitor": source.get("competitor_handle", ""),
                "post_url": source.get("post_url", ""),
                "engagement_score": source.get("engagement_score", 0),
                "similarity_score": source.get("similarity_score", 0),
                "likes": source.get("likes", 0),
                "comments": source.get("comments_count", 0),
                "views": source.get("views", 0),
            },
            "audience_insights": {
                "sentiment": source.get("sentiment", "unknown"),
                "has_transcript": source.get("has_transcript", False),
                "has_audience_intel": source.get("has_audience_intel", False),
            },
        }
        recommendations.append(rec)
    
    return recommendations


def _get_hook_pattern(hook: str) -> str:
    """Classify a single hook into its pattern type."""
    hook_lower = hook.lower()
    if "?" in hook_lower:
        return "question"
    elif any(w in hook_lower for w in ["stop ", "don't ", "never "]):
        return "controversy"
    elif re.search(r"\d+\s+(?:ways?|tips?|things?)", hook_lower):
        return "list"
    elif any(hook_lower.startswith(w) for w in ["i just", "i was", "here's what"]):
        return "story"
    return "statement"


def _build_script_outline(source: Dict, business_context: str, topic: Optional[str]) -> Dict:
    """Build a script outline from source content + business context."""
    hook = source.get("hook", "")
    
    return {
        "opening": f"Adapt hook: \"{hook}\" — reframe for your business",
        "middle": [
            f"Address the topic: {topic or 'your expertise'}",
            "Share a specific insight or transformation",
            "Reference a real result or experience",
        ],
        "close": "End with clear CTA — what should they do next?",
        "delivery_notes": [
            f"Best format: {source.get('media_type', 'reel')}",
            f"Audience sentiment on similar content: {source.get('sentiment', 'positive')}",
            "Keep it under 60 seconds for maximum retention" if source.get("media_type") == "reel" else "Longer form OK for this format",
        ],
    }


def _build_reasoning(source: Dict, patterns: Dict) -> str:
    """Explain WHY this recommendation should work, backed by data."""
    parts = []
    
    eng = source.get("engagement_score", 0)
    likes = source.get("likes", 0)
    comments = source.get("comments_count", 0)
    
    parts.append(f"Based on a post with {likes:,} likes and {comments:,} comments (engagement score: {eng:,.0f}).")
    
    sim = source.get("similarity_score", 0)
    if sim > 0.8:
        parts.append("Extremely relevant to your business context.")
    elif sim > 0.6:
        parts.append("Highly relevant to your business context.")
    elif sim > 0.4:
        parts.append("Moderately relevant — adapt the angle for your audience.")
    
    pattern = _get_hook_pattern(source.get("hook", ""))
    pattern_data = next((p for p in patterns.get("hook_patterns", []) if p["pattern"] == pattern), None)
    if pattern_data:
        parts.append(f"The '{pattern}' hook pattern appears in {pattern_data['count']} of the top posts.")
    
    if source.get("has_transcript"):
        parts.append("Full transcript available — study the delivery and pacing.")
    
    if source.get("has_audience_intel"):
        parts.append("Audience intel available — check questions and pain points.")
    
    return " ".join(parts)


def _rank_hashtags(similar: List[Dict], platform: str) -> List[Dict]:
    """Rank hashtags by co-occurrence and engagement in top content."""
    hashtag_stats: Dict[str, Dict] = {}
    
    for item in similar:
        tags = item.get("hashtags", [])
        eng = item.get("engagement_score", 0)
        
        for tag in tags:
            tag_lower = tag.lower()
            if tag_lower not in hashtag_stats:
                hashtag_stats[tag_lower] = {
                    "tag": tag_lower,
                    "count": 0,
                    "total_engagement": 0,
                    "posts": [],
                }
            hashtag_stats[tag_lower]["count"] += 1
            hashtag_stats[tag_lower]["total_engagement"] += eng
            hashtag_stats[tag_lower]["posts"].append(item.get("competitor_handle", ""))
    
    # Score: frequency × avg engagement
    ranked = []
    for tag, stats in hashtag_stats.items():
        avg_eng = stats["total_engagement"] / max(stats["count"], 1)
        unique_competitors = len(set(stats["posts"]))
        
        ranked.append({
            "hashtag": f"#{tag}",
            "frequency": stats["count"],
            "avg_engagement": round(avg_eng, 0),
            "competitors_using": unique_competitors,
            "score": round(stats["count"] * avg_eng * (1 + unique_competitors * 0.2), 0),
        })
    
    ranked.sort(key=lambda x: x["score"], reverse=True)
    return ranked


async def _get_business_context(db: AsyncSession) -> str:
    """Get business context from settings for query alignment."""
    try:
        result = await db.execute(
            text("SELECT key, value FROM crm.settings WHERE key IN ('business_name', 'business_niche', 'business_description', 'target_audience')")
        )
        settings = {row[0]: row[1] for row in result.fetchall()}
        
        parts = []
        if settings.get("business_name"):
            parts.append(settings["business_name"])
        if settings.get("business_niche"):
            parts.append(f"Niche: {settings['business_niche']}")
        if settings.get("business_description"):
            parts.append(settings["business_description"])
        if settings.get("target_audience"):
            parts.append(f"Target audience: {settings['target_audience']}")
        
        return " | ".join(parts) if parts else "Web development, AI automation, digital marketing agency"
    except Exception:
        return "Web development, AI automation, digital marketing agency"
