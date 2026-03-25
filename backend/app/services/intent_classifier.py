"""Intent Classifier + Weighted Scorer for War Room CDR System.

Classifies comment intents into 6 buckets for audience intelligence:
- UTILITY_SAVE: Saving/bookmarking behavior
- IDENTITY_SHARE: Personal resonance/sharing 
- CURIOSITY_GAP: Questions/knowledge gaps
- FRICTION_POINT: Confusion/technical issues
- SOCIAL_PROOF: Validation/agreement
- TOPIC_RELEVANCE: Contextual alignment

Uses local pattern matching with FastEmbed fallback for semantic understanding.
Calculates weighted Power Score for CDR generation priority.
"""

import asyncio
import json
import logging
import re
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum

import httpx
import numpy as np
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# FastEmbed endpoint configuration
FASTEMBED_URL = "http://10.0.0.11:11435/api/embed"
FASTEMBED_TIMEOUT = 30.0

class IntentType(Enum):
    """Comment intent categories for audience intelligence."""
    UTILITY_SAVE = "UTILITY_SAVE"
    IDENTITY_SHARE = "IDENTITY_SHARE" 
    CURIOSITY_GAP = "CURIOSITY_GAP"
    FRICTION_POINT = "FRICTION_POINT"
    SOCIAL_PROOF = "SOCIAL_PROOF"
    TOPIC_RELEVANCE = "TOPIC_RELEVANCE"

# Intent classification patterns (zero-cost local matching)
INTENT_PATTERNS = {
    IntentType.UTILITY_SAVE: {
        "keywords": [
            "saving this", "save this", "saved", "bookmark", "bookmarked", 
            "screenshot", "screenshotting", "need this", "keeping this",
            "where can i find", "how do i get", "link please", "source",
            "download", "remember this"
        ],
        "phrases": [
            "saving for later", "definitely saving", "saved to camera roll",
            "screenshotted this", "need to remember", "bookmarking this"
        ]
    },
    
    IntentType.IDENTITY_SHARE: {
        "keywords": [
            "literally me", "that's me", "so me", "relatable", "same energy",
            "send this to", "sending this", "tagging", "tag your", "mood",
            "sending to my", "showing this to", "@", "you need to see"
        ],
        "phrases": [
            "this is so me", "literally my life", "why is this me",
            "calling me out", "describing my life", "too relatable",
            "sending to everyone", "sharing with friends"
        ]
    },
    
    IntentType.CURIOSITY_GAP: {
        "keywords": [
            "wait how", "how did", "what was that", "explain", "what app",
            "how do you", "part 2", "more info", "tutorial", "teach me",
            "i need to know", "tell me more", "what's the", "which tool"
        ],
        "phrases": [
            "need to know more", "want to learn", "how does this work",
            "can you explain", "make a tutorial", "show me how",
            "what's the secret", "spill the tea"
        ]
    },
    
    IntentType.FRICTION_POINT: {
        "keywords": [
            "too fast", "slow down", "confused", "lost", "don't understand",
            "what app", "which app", "didn't catch", "missed that",
            "can't follow", "unclear", "help me understand"
        ],
        "phrases": [
            "going too fast", "slow it down", "didn't understand",
            "what did you use", "can't keep up", "lost me there",
            "too confusing", "need more details"
        ]
    },
    
    IntentType.SOCIAL_PROOF: {
        "keywords": [
            "finally someone", "exactly", "facts", "truth", "so true",
            "verified", "confirmed", "preach", "speak truth", "real talk",
            "couldn't agree more", "absolutely right", "this is it"
        ],
        "phrases": [
            "finally someone said it", "this is so true", "speaking facts",
            "needed to hear this", "absolutely right", "couldn't agree more",
            "this is the truth", "facts only"
        ]
    }
}

# Topic relevance comparison weights
TOPIC_WEIGHT_MULTIPLIERS = {
    "exact_match": 1.0,
    "high_relevance": 0.8,
    "medium_relevance": 0.6,
    "low_relevance": 0.3,
    "no_relevance": 0.1
}


async def get_embedding(text: str) -> Optional[List[float]]:
    """Get embedding from FastEmbed service."""
    try:
        async with httpx.AsyncClient(timeout=FASTEMBED_TIMEOUT) as client:
            response = await client.post(
                FASTEMBED_URL,
                json={"text": text}
            )
            response.raise_for_status()
            data = response.json()
            return data.get("embedding")
    except Exception as e:
        logger.error(f"FastEmbed error: {e}")
        return None


def calculate_cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    if not vec1 or not vec2:
        return 0.0
    
    np1, np2 = np.array(vec1), np.array(vec2)
    return float(np.dot(np1, np2) / (np.linalg.norm(np1) * np.linalg.norm(np2)))


def classify_comment_intent_local(comment_text: str, theme: str = "") -> List[Tuple[IntentType, float]]:
    """Classify comment intent using local pattern matching.
    
    Returns list of (intent, confidence) tuples.
    """
    if not comment_text:
        return []
    
    text_lower = comment_text.lower().strip()
    results = []
    
    for intent_type, patterns in INTENT_PATTERNS.items():
        confidence = 0.0
        
        # Check keyword matches
        for keyword in patterns["keywords"]:
            if keyword.lower() in text_lower:
                confidence = max(confidence, 0.9)
                break
        
        # Check phrase matches
        for phrase in patterns["phrases"]:
            if phrase.lower() in text_lower:
                confidence = max(confidence, 0.95)
                break
        
        if confidence > 0:
            results.append((intent_type, confidence))
    
    return results


async def classify_comment_intent_semantic(comment_text: str, context_text: str = "") -> List[Tuple[IntentType, float]]:
    """Classify comment intent using semantic embeddings when patterns fail."""
    
    # Intent reference texts for embedding comparison
    intent_references = {
        IntentType.UTILITY_SAVE: "I want to save this for later use",
        IntentType.IDENTITY_SHARE: "This represents me and I want to share it with others",
        IntentType.CURIOSITY_GAP: "I have questions and want to learn more about this",
        IntentType.FRICTION_POINT: "I am confused and need help understanding",
        IntentType.SOCIAL_PROOF: "I completely agree with this statement",
        IntentType.TOPIC_RELEVANCE: context_text if context_text else "This is relevant to the topic"
    }
    
    # Get embedding for the comment
    comment_embedding = await get_embedding(comment_text)
    if not comment_embedding:
        return []
    
    results = []
    for intent_type, reference_text in intent_references.items():
        reference_embedding = await get_embedding(reference_text)
        if reference_embedding:
            similarity = calculate_cosine_similarity(comment_embedding, reference_embedding)
            if similarity > 0.7:  # High confidence threshold
                results.append((intent_type, similarity))
    
    return results


def calculate_topic_relevance(comment_themes: List[str], post_content: str) -> float:
    """Calculate topic relevance between comment themes and post content."""
    if not comment_themes or not post_content:
        return 0.1
    
    post_lower = post_content.lower()
    post_words = set(re.findall(r'\b\w+\b', post_lower))
    
    max_relevance = 0.0
    for theme in comment_themes:
        theme_words = set(re.findall(r'\b\w+\b', theme.lower()))
        
        # Calculate word overlap
        overlap = len(theme_words.intersection(post_words))
        total_words = len(theme_words.union(post_words))
        
        if total_words > 0:
            relevance = overlap / total_words
            max_relevance = max(max_relevance, relevance)
    
    # Map relevance score to multiplier categories
    if max_relevance > 0.8:
        return TOPIC_WEIGHT_MULTIPLIERS["exact_match"]
    elif max_relevance > 0.6:
        return TOPIC_WEIGHT_MULTIPLIERS["high_relevance"]
    elif max_relevance > 0.4:
        return TOPIC_WEIGHT_MULTIPLIERS["medium_relevance"]
    elif max_relevance > 0.2:
        return TOPIC_WEIGHT_MULTIPLIERS["low_relevance"]
    else:
        return TOPIC_WEIGHT_MULTIPLIERS["no_relevance"]


async def classify_post_intents(
    comments_analysis: Dict,
    post_content: str = "",
    hook_text: str = ""
) -> Dict[str, Any]:
    """Classify intents from post comment analysis data.
    
    Args:
        comments_analysis: The comments_data JSONB from competitor_posts
        post_content: Post text/caption for topic relevance
        hook_text: Hook text for additional context
        
    Returns:
        Dict with classified intents, confidence scores, and intent distribution
    """
    if not comments_analysis:
        return {"error": "No comment analysis data"}
    
    # Extract analyzable data from comments_analysis
    themes = comments_analysis.get("themes", [])
    questions = comments_analysis.get("questions", [])
    pain_points = comments_analysis.get("pain_points", [])
    sentiment = comments_analysis.get("sentiment", "neutral")
    
    # Initialize intent counters
    intent_scores = defaultdict(float)
    intent_evidence = defaultdict(list)
    
    # Classify themes
    for theme_data in themes:
        if isinstance(theme_data, dict) and "theme" in theme_data:
            theme = theme_data["theme"]
            count = theme_data.get("count", 1)
            
            # Local pattern classification
            local_results = classify_comment_intent_local(theme)
            for intent_type, confidence in local_results:
                weight = count * confidence
                intent_scores[intent_type.value] += weight
                intent_evidence[intent_type.value].append({
                    "text": theme,
                    "type": "theme",
                    "confidence": confidence,
                    "count": count
                })
            
            # If no local match, try semantic
            if not local_results and len(theme.split()) > 2:
                context = f"{post_content} {hook_text}".strip()
                semantic_results = await classify_comment_intent_semantic(theme, context)
                for intent_type, confidence in semantic_results:
                    weight = count * confidence * 0.8  # Slightly lower weight for semantic
                    intent_scores[intent_type.value] += weight
                    intent_evidence[intent_type.value].append({
                        "text": theme,
                        "type": "semantic_theme", 
                        "confidence": confidence,
                        "count": count
                    })
    
    # Classify questions (strong indicator of CURIOSITY_GAP)
    for question_data in questions:
        if isinstance(question_data, dict) and "question" in question_data:
            question = question_data["question"]
            likes = question_data.get("likes", 0)
            
            # Questions are primarily curiosity gaps
            weight = (likes + 1) * 0.9  # +1 to avoid zero weight
            intent_scores[IntentType.CURIOSITY_GAP.value] += weight
            intent_evidence[IntentType.CURIOSITY_GAP.value].append({
                "text": question,
                "type": "question",
                "confidence": 0.9,
                "likes": likes
            })
            
            # Check for other intents in questions
            local_results = classify_comment_intent_local(question)
            for intent_type, confidence in local_results:
                if intent_type != IntentType.CURIOSITY_GAP:  # Avoid double-counting
                    intent_scores[intent_type.value] += (likes + 1) * confidence * 0.5
                    intent_evidence[intent_type.value].append({
                        "text": question,
                        "type": "question_secondary",
                        "confidence": confidence,
                        "likes": likes
                    })
    
    # Classify pain points (indicators of FRICTION_POINT)
    for pain_point in pain_points:
        pain_text = pain_point if isinstance(pain_point, str) else str(pain_point)
        intent_scores[IntentType.FRICTION_POINT.value] += 2.0  # Fixed weight for pain points
        intent_evidence[IntentType.FRICTION_POINT.value].append({
            "text": pain_text,
            "type": "pain_point",
            "confidence": 0.85
        })
    
    # Calculate topic relevance
    all_theme_texts = [t.get("theme", "") for t in themes if isinstance(t, dict)]
    topic_relevance = calculate_topic_relevance(all_theme_texts, f"{post_content} {hook_text}")
    intent_scores[IntentType.TOPIC_RELEVANCE.value] = topic_relevance * 10  # Scale to comparable range
    intent_evidence[IntentType.TOPIC_RELEVANCE.value].append({
        "text": "Topic alignment analysis",
        "type": "topic_relevance",
        "confidence": topic_relevance,
        "post_themes": len(all_theme_texts)
    })
    
    return {
        "intent_scores": dict(intent_scores),
        "intent_evidence": dict(intent_evidence),
        "total_themes": len(themes),
        "total_questions": len(questions),
        "total_pain_points": len(pain_points),
        "sentiment": sentiment,
        "topic_relevance": topic_relevance
    }


def calculate_intent_scores(metrics: Dict, classified_comments: Dict) -> Dict[str, Any]:
    """Calculate weighted Power Score and determine dominant intent.
    
    Args:
        metrics: {likes, comments, shares} from competitor_posts
        classified_comments: Result from classify_post_intents()
        
    Returns:
        {power_score, dominant_intent, action_priority, breakdown}
    """
    # Extract metrics
    likes = metrics.get("likes", 0)
    comments = metrics.get("comments", 0) 
    shares = metrics.get("shares", 0)
    saves = metrics.get("saves", 0)  # Instagram saves if available
    
    # Comment quality analysis
    total_questions = classified_comments.get("total_questions", 0)
    total_themes = classified_comments.get("total_themes", 0)
    avg_theme_length = 0
    
    if total_themes > 0:
        themes = classified_comments.get("intent_evidence", {}).get("TOPIC_RELEVANCE", [])
        if themes:
            theme_lengths = [len(evidence.get("text", "").split()) for evidence in themes]
            avg_theme_length = sum(theme_lengths) / len(theme_lengths) if theme_lengths else 0
    
    # Weighted Power Score calculation
    deep_comments = total_questions + max(0, total_themes - 5)  # Questions + substantial themes
    surface_comments = max(0, comments - deep_comments)  # Remaining comments
    
    power_score = (
        shares * 10 +           # Shares (highest intent signal)
        saves * 8 +            # Saves (high utility signal)  
        deep_comments * 5 +    # Deep engagement comments
        surface_comments * 1 + # Surface-level comments
        likes * 0.5            # Likes (lowest signal)
    )
    
    # Determine dominant intent
    intent_scores = classified_comments.get("intent_scores", {})
    
    # Dominant intent logic
    dominant_intent = "UNKNOWN"
    if shares > saves * 1.5:
        dominant_intent = "IDENTITY_SHARE"
    elif saves > shares:
        dominant_intent = "UTILITY_SAVE"
    elif total_questions > comments * 0.3:  # >30% questions
        dominant_intent = "CURIOSITY_GAP"
    elif intent_scores.get("FRICTION_POINT", 0) > 5:
        dominant_intent = "FRICTION_POINT"
    elif intent_scores.get("SOCIAL_PROOF", 0) > intent_scores.get("CURIOSITY_GAP", 0):
        dominant_intent = "SOCIAL_PROOF"
    else:
        # Find highest scoring intent
        if intent_scores:
            dominant_intent = max(intent_scores.items(), key=lambda x: x[1])[0]
    
    # Action priority determination
    action_priority = "LOW"
    if power_score > 10000:
        action_priority = "CRITICAL"
    elif power_score > 5000:
        action_priority = "HIGH"
    elif power_score > 2000:
        action_priority = "MEDIUM"
    
    # CDR generation flag (only if power score > 2000)
    should_generate_cdr = power_score > 2000
    
    return {
        "power_score": round(power_score, 1),
        "dominant_intent": dominant_intent,
        "action_priority": action_priority,
        "should_generate_cdr": should_generate_cdr,
        "breakdown": {
            "shares_points": shares * 10,
            "saves_points": saves * 8,
            "deep_comments_points": deep_comments * 5,
            "surface_comments_points": surface_comments * 1,
            "likes_points": likes * 0.5,
            "deep_comments": deep_comments,
            "surface_comments": surface_comments
        },
        "intent_distribution": intent_scores,
        "engagement_quality": {
            "total_comments": comments,
            "questions_ratio": total_questions / max(1, comments),
            "avg_theme_depth": avg_theme_length
        }
    }


async def process_post_intent_classification(
    db: AsyncSession,
    post_id: int
) -> Optional[Dict[str, Any]]:
    """Process intent classification for a single post and update database.
    
    Returns the classification results.
    """
    try:
        # Fetch post data
        query = text("""
            SELECT id, likes, comments, shares, comments_data, content_analysis,
                   hook, post_text, platform
            FROM crm.competitor_posts 
            WHERE id = :post_id
        """)
        
        result = await db.execute(query, {"post_id": post_id})
        row = result.fetchone()
        
        if not row:
            return {"error": f"Post {post_id} not found"}
        
        post_data = row._asdict()
        
        # Extract metrics
        metrics = {
            "likes": post_data["likes"] or 0,
            "comments": post_data["comments"] or 0, 
            "shares": post_data["shares"] or 0
        }
        
        # Get comment analysis
        comments_analysis = post_data["comments_data"] or {}
        post_content = f"{post_data.get('hook', '')} {post_data.get('post_text', '')}".strip()
        
        # Classify intents
        classified_comments = await classify_post_intents(
            comments_analysis,
            post_content,
            post_data.get("hook", "")
        )
        
        if "error" in classified_comments:
            return classified_comments
        
        # Calculate scores
        scores = calculate_intent_scores(metrics, classified_comments)
        
        # Prepare content analysis update
        current_analysis = post_data.get("content_analysis") or {}
        current_analysis["intent_classification"] = {
            "classified_at": "2026-03-25T12:00:00Z",  # Current timestamp
            "intent_scores": classified_comments["intent_scores"],
            "power_score": scores["power_score"],
            "dominant_intent": scores["dominant_intent"],
            "action_priority": scores["action_priority"],
            "should_generate_cdr": scores["should_generate_cdr"],
            "breakdown": scores["breakdown"],
            "engagement_quality": scores["engagement_quality"]
        }
        
        # Update database
        update_query = text("""
            UPDATE crm.competitor_posts 
            SET content_analysis = :analysis
            WHERE id = :post_id
        """)
        
        await db.execute(update_query, {
            "post_id": post_id,
            "analysis": json.dumps(current_analysis)
        })
        
        await db.commit()
        
        return {
            "post_id": post_id,
            "platform": post_data["platform"],
            "metrics": metrics,
            "classification": classified_comments,
            "scores": scores,
            "updated": True
        }
        
    except Exception as e:
        logger.error(f"Error processing post {post_id}: {e}")
        await db.rollback()
        return {"error": f"Processing failed: {str(e)}"}


async def batch_classify_intents(
    db: AsyncSession,
    competitor_id: Optional[int] = None,
    limit: Optional[int] = None
) -> Dict[str, Any]:
    """Batch process intent classification for posts.
    
    Args:
        competitor_id: If specified, only process posts for this competitor
        limit: Maximum number of posts to process
        
    Returns:
        Summary of batch processing results
    """
    try:
        # Build query
        where_clause = "WHERE comments_data IS NOT NULL"
        params = {}
        
        if competitor_id:
            where_clause += " AND competitor_id = :competitor_id"
            params["competitor_id"] = competitor_id
        
        limit_clause = ""
        if limit:
            limit_clause = f" LIMIT {limit}"
        
        query = text(f"""
            SELECT id FROM crm.competitor_posts 
            {where_clause}
            ORDER BY (likes + comments*5 + shares*10) DESC
            {limit_clause}
        """)
        
        result = await db.execute(query, params)
        post_ids = [row[0] for row in result.fetchall()]
        
        logger.info(f"Starting batch classification for {len(post_ids)} posts")
        
        # Process posts
        results = {
            "processed": 0,
            "errors": 0,
            "high_priority": 0,
            "cdr_candidates": 0,
            "dominant_intents": Counter(),
            "avg_power_score": 0,
            "post_details": []
        }
        
        total_power_score = 0
        
        for post_id in post_ids:
            try:
                classification_result = await process_post_intent_classification(db, post_id)
                
                if "error" in classification_result:
                    results["errors"] += 1
                    logger.error(f"Post {post_id}: {classification_result['error']}")
                    continue
                
                results["processed"] += 1
                
                # Update statistics
                scores = classification_result["scores"]
                power_score = scores["power_score"]
                dominant_intent = scores["dominant_intent"]
                action_priority = scores["action_priority"]
                
                total_power_score += power_score
                results["dominant_intents"][dominant_intent] += 1
                
                if action_priority in ["HIGH", "CRITICAL"]:
                    results["high_priority"] += 1
                
                if scores["should_generate_cdr"]:
                    results["cdr_candidates"] += 1
                
                # Store summary for top posts
                if len(results["post_details"]) < 10:
                    results["post_details"].append({
                        "post_id": post_id,
                        "power_score": power_score,
                        "dominant_intent": dominant_intent,
                        "action_priority": action_priority,
                        "metrics": classification_result["metrics"]
                    })
                
                # Log progress every 50 posts
                if results["processed"] % 50 == 0:
                    logger.info(f"Processed {results['processed']}/{len(post_ids)} posts")
                    
            except Exception as e:
                results["errors"] += 1
                logger.error(f"Error processing post {post_id}: {e}")
                continue
        
        # Calculate averages
        if results["processed"] > 0:
            results["avg_power_score"] = round(total_power_score / results["processed"], 1)
        
        logger.info(f"Batch classification completed: {results['processed']} processed, {results['errors']} errors")
        
        return results
        
    except Exception as e:
        logger.error(f"Batch classification failed: {e}")
        return {"error": f"Batch processing failed: {str(e)}"}