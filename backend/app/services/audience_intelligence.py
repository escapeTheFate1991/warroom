"""
Audience Intelligence Data Model - Extracts actionable insights from comments.

Replaces the old audience_psychology module with a focused data model that provides:
1. Objections - What audiences resist or question
2. Desires - What they want (with exact verbatim language)  
3. Questions - Unanswered questions that could become content
4. Emotional Triggers - What makes them share/save/comment
5. Competitor Gaps - What competitors aren't addressing

All insights link back to source comments with usage hints for content creation.
"""

import asyncio
import json
import logging
import re
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime

import httpx
import numpy as np

logger = logging.getLogger(__name__)

# FastEmbed endpoint configuration
FASTEMBED_URL = "http://10.0.0.11:11435/api/embed"
FASTEMBED_TIMEOUT = 30.0


@dataclass
class SampleComment:
    """Source comment for an insight."""
    comment_id: str
    text: str
    author: str
    timestamp: Optional[datetime] = None
    likes: int = 0


@dataclass
class Objection:
    """Audience objection with source evidence."""
    text: str
    frequency: int
    sample_comments: List[SampleComment]
    usage_hint: str


@dataclass
class Desire:
    """Audience desire with exact verbatim phrases."""
    text: str
    language: List[str]  # Exact verbatim phrases from comments
    frequency: int
    sample_comments: List[SampleComment]
    usage_hint: str


@dataclass
class Question:
    """Unanswered question from audience."""
    text: str
    frequency: int
    sample_comments: List[SampleComment]
    usage_hint: str


@dataclass
class EmotionalTrigger:
    """What triggers emotional engagement."""
    trigger: str
    type: str  # share|save|comment|tag
    video_timestamp: Optional[str] = None
    sample_comments: List[SampleComment] = None


@dataclass
class CompetitorGap:
    """Gap in competitor's content coverage."""
    gap: str
    frequency: int
    sample_comments: List[SampleComment]
    usage_hint: str


@dataclass
class AudienceIntelligence:
    """Complete audience intelligence for a video/post."""
    objections: List[Objection]
    desires: List[Desire]
    questions: List[Question]
    emotional_triggers: List[EmotionalTrigger]
    competitor_gaps: List[CompetitorGap]
    total_comments_analyzed: int
    analysis_timestamp: datetime


# Pattern matching for different insight types
OBJECTION_PATTERNS = [
    r"but\s+(.*?)(?:\.|$)",
    r"however\s+(.*?)(?:\.|$)",
    r"(?:i\s+)?disagree\s+(?:with\s+)?(.*?)(?:\.|$)",
    r"(?:that's\s+)?not\s+true\s+(.*?)(?:\.|$)",
    r"(?:you're\s+)?wrong\s+(?:about\s+)?(.*?)(?:\.|$)",
    r"actually\s+(.*?)(?:\.|$)",
    r"(?:i\s+)?don't\s+(?:think|believe)\s+(.*?)(?:\.|$)",
    r"(?:that\s+)?doesn't\s+work\s+(?:for\s+)?(.*?)(?:\.|$)",
    r"(?:i\s+)?can't\s+(?:do|afford|get)\s+(.*?)(?:\.|$)"
]

DESIRE_PATTERNS = [
    r"(?:i\s+)?want\s+(?:to\s+)?(.*?)(?:\.|$)",
    r"(?:i\s+)?need\s+(?:to\s+)?(.*?)(?:\.|$)", 
    r"(?:i\s+)?wish\s+(?:i\s+could\s+)?(.*?)(?:\.|$)",
    r"(?:i'm\s+)?looking\s+for\s+(.*?)(?:\.|$)",
    r"(?:help\s+me\s+(?:with\s+)?)(.*?)(?:\.|$)",
    r"(?:how\s+(?:do\s+i|can\s+i)\s+)(.*?)(?:\?|$)",
    r"(?:i\s+)?hope\s+(?:to\s+)?(.*?)(?:\.|$)",
    r"(?:my\s+)?goal\s+is\s+(?:to\s+)?(.*?)(?:\.|$)"
]

QUESTION_KEYWORDS = [
    "how", "what", "where", "when", "why", "which", "who", 
    "can", "could", "would", "should", "is", "are", "do", "does", "did"
]

EMOTIONAL_SHARE_TRIGGERS = {
    "share": ["tag", "share", "send this", "everyone needs", "show this"],
    "save": ["save", "bookmark", "keep this", "screenshot"],
    "comment": ["relate", "same", "exactly", "me too", "story of my life"],
    "tag": ["@", "tag your", "someone who", "that friend who"]
}

USAGE_HINTS = {
    "objections": [
        "Address in hook",
        "Handle in value beat", 
        "Preemptive rebuttal",
        "FAQ section content",
        "Comparison angle"
    ],
    "desires": [
        "Use as CTA angle",
        "Promise in thumbnail",
        "Hook teaser",
        "Video topic idea",
        "Lead magnet concept"
    ],
    "questions": [
        "Next video topic",
        "FAQ content",
        "Tutorial series idea",
        "Community post topic",
        "Live stream Q&A"
    ],
    "competitor_gaps": [
        "Differentiation angle",
        "Market opportunity",
        "Content series idea",
        "Unique positioning",
        "Blue ocean content"
    ]
}


async def get_embeddings(texts: List[str]) -> Optional[np.ndarray]:
    """Get embeddings from FastEmbed server."""
    if not texts:
        return None
        
    try:
        async with httpx.AsyncClient(timeout=FASTEMBED_TIMEOUT) as client:
            response = await client.post(
                FASTEMBED_URL,
                json={"input": texts},
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            
            data = response.json()
            embeddings = data.get("embeddings", [])
            
            if not embeddings or len(embeddings) != len(texts):
                logger.warning("FastEmbed returned incorrect number of embeddings")
                return None
                
            return np.array(embeddings, dtype=np.float32)
            
    except Exception as e:
        logger.warning("FastEmbed request failed: %s", e)
        return None


def extract_objections(comments: List[Dict]) -> List[Dict]:
    """Extract objections and resistance from comments."""
    objections = []
    objection_clusters = defaultdict(list)
    
    for comment in comments:
        text = comment.get("text", "").strip()
        text_lower = text.lower()
        if len(text) < 10:
            continue
            
        # Check for objection patterns
        for pattern in OBJECTION_PATTERNS:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                objection_text = match.strip()
                if len(objection_text) > 5:  # Meaningful objection
                    objection_clusters[objection_text].append(comment)
                    
        # Also check for direct objection keywords
        objection_keywords = [
            "can't afford", "too expensive", "doesn't work", "disagree",
            "wrong", "not true", "however", "but ", "actually"
        ]
        
        for keyword in objection_keywords:
            if keyword in text_lower:
                # Extract the full objection context
                objection_text = text[:100]  # First 100 chars as context
                objection_clusters[objection_text.lower()].append(comment)
    
    # Convert clusters to Objection objects
    for objection_text, comment_list in objection_clusters.items():
        if len(comment_list) >= 1:  # At least 1 person has this objection (individual objections are valuable)
            sample_comments = [
                SampleComment(
                    comment_id=str(c.get("id", "")),
                    text=c.get("text", ""),
                    author=c.get("username", ""),
                    timestamp=c.get("timestamp"),
                    likes=c.get("likes", 0)
                )
                for c in comment_list[:3]  # Top 3 samples
            ]
            
            objections.append({
                "text": objection_text,
                "frequency": len(comment_list),
                "sample_comments": [asdict(sc) for sc in sample_comments],
                "usage_hint": np.random.choice(USAGE_HINTS["objections"])
            })
    
    return sorted(objections, key=lambda x: x["frequency"], reverse=True)[:10]


def extract_desires(comments: List[Dict]) -> List[Dict]:
    """Extract desires with exact verbatim language."""
    desires = []
    desire_clusters = defaultdict(list)
    verbatim_phrases = defaultdict(set)
    
    for comment in comments:
        text = comment.get("text", "").strip()
        text_lower = text.lower()
        if len(text) < 10:
            continue
            
        # Check for desire patterns
        for pattern in DESIRE_PATTERNS:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                desire_text = match.strip()
                if len(desire_text) > 5:
                    # Store the exact phrase used
                    desire_key = desire_text.lower()
                    desire_clusters[desire_key].append(comment)
                    verbatim_phrases[desire_key].add(desire_text)
                    
        # Also check for direct desire keywords with better context extraction
        desire_keywords = [
            "i want", "i need", "i wish", "looking for", "help me",
            "goal is", "hoping to", "trying to"
        ]
        
        for keyword in desire_keywords:
            if keyword in text_lower:
                # Extract the desire context - the part after the keyword
                start_idx = text_lower.find(keyword)
                if start_idx >= 0:
                    context_start = start_idx + len(keyword)
                    desire_context = text[context_start:].split('.')[0].split('?')[0].strip()
                    if len(desire_context) > 10:  # Meaningful desire
                        desire_key = desire_context.lower()
                        desire_clusters[desire_key].append(comment)
                        verbatim_phrases[desire_key].add(desire_context)
    
    # Convert clusters to Desire objects
    for desire_key, comment_list in desire_clusters.items():
        if len(comment_list) >= 1:  # At least 1 person wants this (individual desires are valuable)
            sample_comments = [
                SampleComment(
                    comment_id=str(c.get("id", "")),
                    text=c.get("text", ""),
                    author=c.get("username", ""),
                    timestamp=c.get("timestamp"),
                    likes=c.get("likes", 0)
                )
                for c in comment_list[:3]  # Top 3 samples
            ]
            
            desires.append({
                "text": desire_key,
                "language": list(verbatim_phrases[desire_key]),
                "frequency": len(comment_list),
                "sample_comments": [asdict(sc) for sc in sample_comments],
                "usage_hint": np.random.choice(USAGE_HINTS["desires"])
            })
    
    return sorted(desires, key=lambda x: x["frequency"], reverse=True)[:10]


def extract_questions(comments: List[Dict]) -> List[Dict]:
    """Extract unanswered questions that could become content."""
    questions = []
    question_clusters = defaultdict(list)
    
    for comment in comments:
        text = comment.get("text", "").strip()
        if not text.endswith("?") or len(text) < 10:
            continue
            
        # Check if it's a real question (starts with question words)
        text_lower = text.lower()
        if any(text_lower.startswith(keyword) for keyword in QUESTION_KEYWORDS):
            # Check if it's unanswered (no replies in the thread)
            has_reply = comment.get("replies", 0) > 0
            if not has_reply:  # Unanswered question
                question_key = text.lower()
                question_clusters[question_key].append(comment)
    
    # Convert clusters to Question objects  
    for question_text, comment_list in question_clusters.items():
        if len(comment_list) >= 1:  # Even single unanswered questions are valuable
            sample_comments = [
                SampleComment(
                    comment_id=str(c.get("id", "")),
                    text=c.get("text", ""),
                    author=c.get("username", ""),
                    timestamp=c.get("timestamp"),
                    likes=c.get("likes", 0)
                )
                for c in comment_list[:3]
            ]
            
            questions.append({
                "text": question_text,
                "frequency": len(comment_list),
                "sample_comments": [asdict(sc) for sc in sample_comments],
                "usage_hint": np.random.choice(USAGE_HINTS["questions"])
            })
    
    return sorted(questions, key=lambda x: x["frequency"], reverse=True)[:15]


def extract_emotional_triggers(comments: List[Dict]) -> List[Dict]:
    """Extract emotional triggers that drive engagement."""
    triggers = []
    
    for trigger_type, keywords in EMOTIONAL_SHARE_TRIGGERS.items():
        trigger_comments = []
        
        for comment in comments:
            text = comment.get("text", "").lower()
            if any(keyword in text for keyword in keywords):
                trigger_comments.append(comment)
        
        if trigger_comments:
            # Get sample comments
            sample_comments = [
                SampleComment(
                    comment_id=str(c.get("id", "")),
                    text=c.get("text", ""),
                    author=c.get("username", ""),
                    timestamp=c.get("timestamp"),
                    likes=c.get("likes", 0)
                )
                for c in trigger_comments[:3]
            ]
            
            triggers.append({
                "trigger": f"{trigger_type.title()} signals",
                "type": trigger_type,
                "video_timestamp": None,  # Could be extracted from comments mentioning time
                "sample_comments": [asdict(sc) for sc in sample_comments]
            })
    
    return triggers


async def extract_competitor_gaps(comments: List[Dict]) -> List[Dict]:
    """Extract gaps in competitor's content coverage."""
    gaps = []
    gap_indicators = defaultdict(list)
    
    # Look for unmet needs and missing content
    gap_patterns = [
        r"(?:i\s+)?wish\s+(?:you\s+)?(?:would\s+)?(?:make|do|show)\s+(.*?)(?:\.|$)",
        r"(?:can\s+you\s+)?(?:please\s+)?(?:make|do|cover)\s+(?:a\s+video\s+(?:on|about)\s+)?(.*?)(?:\?|$)",
        r"(?:you\s+)?should\s+(?:make|do|show)\s+(.*?)(?:\.|$)",
        r"(?:i'd\s+love\s+to\s+see)\s+(.*?)(?:\.|$)",
        r"(?:what\s+about)\s+(.*?)(?:\?|$)",
        r"(?:nobody\s+(?:talks\s+about|covers))\s+(.*?)(?:\.|$)"
    ]
    
    for comment in comments:
        text = comment.get("text", "").strip()
        if len(text) < 10:
            continue
            
        for pattern in gap_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                gap_text = match.strip()
                if len(gap_text) > 3:
                    gap_indicators[gap_text].append(comment)
    
    # Convert to CompetitorGap objects
    for gap_text, comment_list in gap_indicators.items():
        if len(comment_list) >= 1:  # At least one person requesting this
            sample_comments = [
                SampleComment(
                    comment_id=str(c.get("id", "")),
                    text=c.get("text", ""),
                    author=c.get("username", ""),
                    timestamp=c.get("timestamp"),
                    likes=c.get("likes", 0)
                )
                for c in comment_list[:3]
            ]
            
            gaps.append({
                "gap": gap_text,
                "frequency": len(comment_list),
                "sample_comments": [asdict(sc) for sc in sample_comments],
                "usage_hint": np.random.choice(USAGE_HINTS["competitor_gaps"])
            })
    
    return sorted(gaps, key=lambda x: x["frequency"], reverse=True)[:10]


async def cluster_similar_comments(comments: List[Dict], embeddings: np.ndarray) -> Dict[str, List[Dict]]:
    """Cluster similar comments using embeddings for better insight extraction."""
    if len(comments) < 10 or embeddings is None:
        return {}
    
    try:
        from sklearn.cluster import KMeans
        from sklearn.metrics.pairwise import cosine_similarity
    except ImportError:
        logger.warning("scikit-learn not available, skipping clustering")
        return {}
    
    # Optimal number of clusters (between 5 and 20)
    n_clusters = min(max(len(comments) // 10, 5), 20)
    
    # K-means clustering
    kmeans = KMeans(n_clusters=n_clusters, random_state=42)
    cluster_labels = kmeans.fit_predict(embeddings)
    
    # Group comments by cluster
    clusters = defaultdict(list)
    for i, label in enumerate(cluster_labels):
        clusters[f"cluster_{label}"].append(comments[i])
    
    return clusters


async def analyze_audience_intelligence(comments_data: List[Dict]) -> Dict[str, Any]:
    """
    Main analysis function that extracts all 5 categories of audience intelligence.
    
    Args:
        comments_data: List of comment dictionaries from competitor_posts.comments_data
        
    Returns:
        Complete audience intelligence analysis
    """
    if not comments_data or len(comments_data) < 5:
        return {
            "objections": [],
            "desires": [],
            "questions": [],
            "emotional_triggers": [],
            "competitor_gaps": [],
            "total_comments_analyzed": 0,
            "analysis_timestamp": datetime.utcnow().isoformat()
        }
    
    logger.info(f"Analyzing {len(comments_data)} comments for audience intelligence")
    
    # Get embeddings for semantic clustering
    comment_texts = [c.get("text", "") for c in comments_data if c.get("text")]
    embeddings = await get_embeddings(comment_texts)
    
    # Optional: Cluster similar comments for better extraction
    if embeddings is not None:
        clusters = await cluster_similar_comments(comments_data, embeddings)
        logger.info(f"Clustered comments into {len(clusters)} groups")
    
    # Extract all 5 categories
    objections = extract_objections(comments_data)
    desires = extract_desires(comments_data)
    questions = extract_questions(comments_data)
    emotional_triggers = extract_emotional_triggers(comments_data)
    competitor_gaps = await extract_competitor_gaps(comments_data)
    
    logger.info(
        f"Extracted: {len(objections)} objections, {len(desires)} desires, "
        f"{len(questions)} questions, {len(emotional_triggers)} emotional triggers, "
        f"{len(competitor_gaps)} competitor gaps"
    )
    
    return {
        "objections": objections,
        "desires": desires,
        "questions": questions,
        "emotional_triggers": emotional_triggers,
        "competitor_gaps": competitor_gaps,
        "total_comments_analyzed": len(comments_data),
        "analysis_timestamp": datetime.utcnow().isoformat()
    }


async def extract_audience_intelligence_for_post(
    db, 
    post_id: int,
    org_id: int
) -> Optional[Dict[str, Any]]:
    """Extract audience intelligence for a specific post."""
    from sqlalchemy import text
    
    # Get post with comments
    query = text("""
        SELECT id, comments_data, content_analysis 
        FROM crm.competitor_posts 
        WHERE id = :post_id AND org_id = :org_id
    """)
    
    result = await db.execute(query, {"post_id": post_id, "org_id": org_id})
    post = result.first()
    
    if not post or not post.comments_data:
        return None
    
    # Extract intelligence
    intelligence = await analyze_audience_intelligence(post.comments_data)
    
    # Store results back to content_analysis field
    update_query = text("""
        UPDATE crm.competitor_posts 
        SET content_analysis = COALESCE(content_analysis, '{}') || :intelligence
        WHERE id = :post_id
    """)
    
    await db.execute(update_query, {
        "post_id": post_id,
        "intelligence": json.dumps({"audience_intelligence": intelligence})
    })
    await db.commit()
    
    return intelligence


async def extract_audience_intelligence_for_competitor(
    db,
    competitor_id: int, 
    org_id: int
) -> Dict[str, Any]:
    """Extract aggregated audience intelligence across a competitor's videos."""
    from sqlalchemy import text
    
    # Get all posts with comments for this competitor
    query = text("""
        SELECT id, comments_data, content_analysis, post_url, posted_at
        FROM crm.competitor_posts 
        WHERE competitor_id = :competitor_id 
        AND org_id = :org_id 
        AND comments_data IS NOT NULL
        ORDER BY posted_at DESC
        LIMIT 20
    """)
    
    result = await db.execute(query, {"competitor_id": competitor_id, "org_id": org_id})
    posts = result.fetchall()
    
    if not posts:
        return {
            "error": "No posts with comments found for this competitor",
            "total_posts_analyzed": 0
        }
    
    # Aggregate all comments
    all_comments = []
    for post in posts:
        if post.comments_data:
            all_comments.extend(post.comments_data)
    
    # Extract aggregated intelligence
    intelligence = await analyze_audience_intelligence(all_comments)
    intelligence["total_posts_analyzed"] = len(posts)
    intelligence["posts_analyzed"] = [
        {"id": p.id, "url": p.post_url, "date": p.posted_at.isoformat() if p.posted_at else None}
        for p in posts
    ]
    
    return intelligence