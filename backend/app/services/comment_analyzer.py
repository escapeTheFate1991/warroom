"""ML-powered comment analysis service.

Replaces regex-based theme extraction with embedding-based topic clustering
using FastEmbed + scikit-learn. Provides content gap analysis and video topic suggestions.
"""

import asyncio
import logging
import re
import json
from collections import Counter
from typing import Dict, List, Optional, Tuple, Any

import httpx
import numpy as np
# from sklearn.cluster import KMeans, DBSCAN
# from sklearn.metrics import silhouette_score

logger = logging.getLogger(__name__)

# FastEmbed endpoint configuration
FASTEMBED_URL = "http://10.0.0.11:11435/api/embed"
FASTEMBED_TIMEOUT = 30.0

# Sentiment keyword sets (keep existing logic - it works fine)
POSITIVE_WORDS = {
    "love", "amazing", "great", "awesome", "perfect", "best", "beautiful", 
    "incredible", "excellent", "fantastic", "fire", "insane", "goat", 
    "🔥", "❤️", "💯", "🙌", "helpful", "useful", "inspiring", "motivating"
}

NEGATIVE_WORDS = {
    "hate", "terrible", "worst", "awful", "bad", "disappointed", "scam",
    "waste", "boring", "fake", "cringe", "mid", "👎", "useless", "misleading"
}

# Comment classification patterns
QUESTION_STARTERS = {"how", "what", "where", "when", "why", "which", "can", "do", "does", "is", "are", "will", "would"}
PAIN_POINT_KEYWORDS = {"struggle", "can't", "cant", "wish", "need help", "frustrated", "confused", "stuck", "don't know", "have trouble"}
PRAISE_KEYWORDS = {"love", "amazing", "great", "awesome", "thank", "thanks", "appreciate", "helpful", "inspiring"}
REQUEST_KEYWORDS = {"please", "can you", "would you", "make a video about", "tutorial on", "explain how"}

# Stop words for theme extraction
THEME_STOP_WORDS = {
    "the", "and", "for", "this", "that", "you", "your", "with", "from", "have", "are",
    "but", "not", "was", "were", "been", "being", "its", "just", "really", "very",
    "would", "could", "should", "will", "can", "more", "about", "like", "what",
    "how", "all", "they", "them", "their", "there", "here", "also", "than", "then",
    "too", "out", "get", "got", "has", "had", "did", "does", "don", "one", "who",
    "want", "know", "think", "make", "need", "some", "look", "going", "thing",
    "comment", "comments", "video", "post", "instagram", "follow", "following"
}


async def get_embeddings(texts: List[str]) -> Optional[np.ndarray]:
    """Get embeddings from FastEmbed server for a batch of texts.
    
    Returns None if FastEmbed is unreachable (for fallback handling).
    """
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


def classify_comment_type(text: str) -> str:
    """Classify a comment into: question, pain_point, praise, request, discussion, spam."""
    text_lower = text.lower().strip()
    
    # Skip very short or emoji-only comments as spam
    if len(text_lower) < 5:
        return "spam"
    
    # Check if it's mostly emojis/symbols
    alpha_chars = sum(1 for c in text if c.isalpha())
    if alpha_chars < len(text) * 0.3:  # Less than 30% alphabetic
        return "spam"
    
    words = set(re.findall(r'\w+', text_lower))
    first_word = text_lower.split()[0] if text_lower.split() else ""
    
    # Questions: explicit question mark or question starters
    if "?" in text or first_word in QUESTION_STARTERS:
        return "question"
    
    # Pain points: struggling/confusion indicators
    if any(keyword in text_lower for keyword in PAIN_POINT_KEYWORDS):
        return "pain_point"
    
    # Requests: asking for content
    if any(keyword in text_lower for keyword in REQUEST_KEYWORDS):
        return "request"
    
    # Praise: positive feedback
    if any(keyword in text_lower for keyword in PRAISE_KEYWORDS):
        return "praise"
    
    # Default to discussion
    return "discussion"


def extract_meaningful_words(text: str, min_length: int = 3) -> List[str]:
    """Extract meaningful words from text, excluding stop words."""
    words = re.findall(r'\b[a-z]{' + str(min_length) + ',}\b', text.lower())
    return [w for w in words if w not in THEME_STOP_WORDS]


def generate_cluster_label(comments: List[str]) -> str:
    """Generate a 2-4 word topic label from a cluster of comments."""
    # Combine all comment texts in the cluster
    combined_text = " ".join(comments)
    meaningful_words = extract_meaningful_words(combined_text)
    
    if not meaningful_words:
        return "general discussion"
    
    # Count word frequency and pick top meaningful words
    word_counts = Counter(meaningful_words)
    top_words = [word for word, _ in word_counts.most_common(4)]
    
    # Create a readable label from top words
    if len(top_words) >= 2:
        return " ".join(top_words[:3])  # 2-3 words max
    else:
        return top_words[0] if top_words else "general"


def detect_unanswered_questions(comments: List[Dict], creator_username: str = "") -> List[Dict]:
    """Detect questions that haven't been answered by the post creator.
    
    Returns questions where is_reply=False and no creator reply exists.
    """
    unanswered = []
    creator_replies = set()
    
    # First pass: identify all creator replies
    for comment in comments:
        if (comment.get("username", "").lower() == creator_username.lower() and 
            comment.get("is_reply", False)):
            creator_replies.add(comment.get("reply_to", ""))
    
    # Second pass: find unanswered top-level questions
    for comment in comments:
        if (classify_comment_type(comment.get("text", "")) == "question" and
            not comment.get("is_reply", False) and  # Top-level comment
            comment.get("username", "") not in creator_replies):
            unanswered.append(comment)
    
    return unanswered


def generate_video_topic_suggestions(content_gaps: List[Dict], post_caption: str = "") -> List[Dict]:
    """Generate actionable video topic suggestions from content gaps."""
    suggestions = []
    
    for gap in content_gaps:
        topic = gap.get("topic", "")
        questions = gap.get("unanswered_questions", [])
        
        if not questions:
            continue
        
        # Analyze the questions to understand what people want to learn
        common_themes = []
        for question in questions[:3]:  # Focus on top 3 questions
            words = extract_meaningful_words(question, min_length=4)
            common_themes.extend(words)
        
        theme_counts = Counter(common_themes)
        main_theme = theme_counts.most_common(1)[0][0] if theme_counts else topic
        
        # Generate suggestion based on the gap
        reasoning = f"Audience asking about {topic} but getting no answers. "
        reasoning += f"{len(questions)} unanswered questions with {gap.get('opportunity_score', 0):.1f} engagement score."
        
        # Create actionable video topic
        video_topic = f"How to {main_theme}" if main_theme else f"Complete guide to {topic}"
        if "tutorial" in post_caption.lower():
            video_topic = f"Advanced {main_theme} techniques"
        elif "beginner" in post_caption.lower():
            video_topic = f"{main_theme.title()} for beginners"
        
        suggestions.append({
            "topic": video_topic,
            "reasoning": reasoning,
            "source_questions": questions[:3]  # Include top questions as evidence
        })
    
    return suggestions


async def analyze_comments_ml(comments: List[Dict], post_caption: str = "", creator_username: str = "") -> Dict:
    """Enhanced ML-powered comment analysis with behavioral psychology insights.
    
    Falls back to regex analysis if ML services are unreachable.
    """
    if not comments:
        return {
            "analyzed": 0,
            "sentiment": "neutral",
            "sentiment_breakdown": {"positive": 0, "negative": 0, "neutral": 0},
            "avg_comment_likes": 0.0,
            "reply_rate": 0.0,
            "questions": [],
            "pain_points": [],
            "product_mentions": [],
            "themes": [],
            "top_commenters": [],
            "engagement_quality": "low",
            "content_gaps": [],
            "video_topic_suggestions": [],
            "psychology_analysis": {}
        }
    
    try:
        # Get base ML analysis
        base_result = await _analyze_comments_with_ml(comments, post_caption, creator_username)
        
        # Psychology analysis removed - replaced with audience intelligence
        base_result["psychology_analysis"] = {}
        
        return base_result
        
    except Exception as e:
        logger.warning("ML analysis failed, falling back to regex: %s", e)
        # Import the original function for fallback
        from app.services.comment_scraper import _analyze_comments as _analyze_comments_regex
        
        # Add empty new fields to maintain API compatibility
        result = _analyze_comments_regex(comments, post_caption)
        result["content_gaps"] = []
        result["video_topic_suggestions"] = []
        result["psychology_analysis"] = {}
        return result


async def _analyze_comments_with_ml(comments: List[Dict], post_caption: str = "", creator_username: str = "") -> Dict:
    """Core ML analysis implementation."""
    total = len(comments)
    total_likes = sum(c.get("likes", 0) for c in comments)
    
    # Step 1: Filter and classify comments
    filtered_comments = []
    questions = []
    pain_points = []
    product_mentions = []
    top_commenters = Counter()
    
    pos_count = 0
    neg_count = 0
    reply_count = 0
    
    for comment in comments:
        text = comment.get("text", "").strip()
        username = comment.get("username", "")
        likes = comment.get("likes", 0)
        is_reply = comment.get("is_reply", False)
        
        if not text or len(text) < 5:
            continue
            
        comment_type = classify_comment_type(text)
        if comment_type == "spam":
            continue
        
        # Count replies for engagement stats
        if is_reply:
            reply_count += 1
        
        # Sentiment analysis (keep existing keyword approach)
        text_lower = text.lower()
        words = set(re.findall(r'\w+', text_lower)) | set(re.findall(r'[🔥❤️💯🙌👎😂💀🤔💡👀✅]', text))
        
        if words & POSITIVE_WORDS:
            pos_count += 1
        if words & NEGATIVE_WORDS:
            neg_count += 1
        
        # Extract questions and pain points
        if comment_type == "question":
            q_match = re.search(r'([^.!]*\?)', text)
            question_text = q_match.group(1).strip()[:150] if q_match else text[:150]
            questions.append({"question": question_text, "likes": likes})
        
        elif comment_type == "pain_point":
            pain_points.append({"pain": text[:150], "likes": likes})
        
        # Product mentions (keep existing logic)
        original_text = text
        product_trigger = re.search(
            r"(?:use|using|try|tried|recommend|check out|switched to|built with|powered by|running|works with)\s+"
            r"([A-Z][\w]*(?:\s+[A-Z][\w]*){0,3})",
            original_text,
        )
        if product_trigger:
            product_name = product_trigger.group(1).strip()
            if len(product_name) > 2 and product_name.lower() not in {"the", "this", "that", "it", "they", "you", "my"}:
                product_mentions.append(product_name[:50])
        
        # @mentions as products
        at_mentions = re.findall(r"@(\w{2,30})", text_lower)
        for mention in at_mentions:
            if mention not in top_commenters and len(mention) > 2:
                product_mentions.append(mention)
        
        # Track commenters
        if username:
            top_commenters[username] += 1
        
        # Add to filtered list for embedding
        filtered_comments.append({
            "text": text,
            "username": username,
            "likes": likes,
            "is_reply": is_reply,
            "type": comment_type
        })
    
    # Step 2: Generate embeddings and cluster
    themes = []
    content_gaps = []
    
    if len(filtered_comments) >= 2:
        comment_texts = [c["text"] for c in filtered_comments]
        embeddings = await get_embeddings(comment_texts)
        
        if embeddings is not None and len(embeddings) >= 2:
            # Step 3: Cluster comments
            num_clusters = min(max(len(filtered_comments) // 3, 2), 8)
            
            try:
                if len(filtered_comments) >= 3:
                    # Try KMeans first
                    kmeans = KMeans(n_clusters=num_clusters, random_state=42, n_init=10)
                    cluster_labels = kmeans.fit_predict(embeddings)
                    cluster_centers = kmeans.cluster_centers_
                else:
                    # Fallback for very small datasets
                    cluster_labels = np.zeros(len(filtered_comments))
                    cluster_centers = np.array([embeddings.mean(axis=0)])
                
                # Step 4: Generate cluster labels and themes
                clusters = {}
                for i, label in enumerate(cluster_labels):
                    if label not in clusters:
                        clusters[label] = []
                    clusters[label].append(i)
                
                for cluster_id, comment_indices in clusters.items():
                    cluster_comments = [filtered_comments[i]["text"] for i in comment_indices]
                    cluster_label = generate_cluster_label(cluster_comments)
                    
                    themes.append({
                        "theme": cluster_label,
                        "count": len(comment_indices)
                    })
                
                # Step 5: Content gap analysis
                unanswered_questions = detect_unanswered_questions(
                    [filtered_comments[i] for i in range(len(filtered_comments)) 
                     if filtered_comments[i]["type"] == "question"],
                    creator_username
                )
                
                # Group unanswered questions by cluster
                question_clusters = {}
                for question in unanswered_questions:
                    # Find which cluster this question belongs to
                    question_text = question.get("text", "")
                    best_cluster = 0
                    
                    for i, comment in enumerate(filtered_comments):
                        if comment["text"] == question_text:
                            best_cluster = cluster_labels[i]
                            break
                    
                    if best_cluster not in question_clusters:
                        question_clusters[best_cluster] = []
                    question_clusters[best_cluster].append(question_text)
                
                # Generate content gaps
                for cluster_id, questions_in_cluster in question_clusters.items():
                    if not questions_in_cluster:
                        continue
                    
                    # Find the theme for this cluster
                    cluster_theme = "general discussion"
                    for theme in themes:
                        if any(comment_idx for comment_idx, label in enumerate(cluster_labels) 
                              if label == cluster_id):
                            cluster_theme = theme["theme"]
                            break
                    
                    # Calculate opportunity score based on question engagement
                    avg_engagement = sum(
                        q.get("likes", 0) for q in unanswered_questions
                        if q.get("text", "") in questions_in_cluster
                    ) / len(questions_in_cluster)
                    
                    content_gaps.append({
                        "topic": cluster_theme,
                        "unanswered_questions": questions_in_cluster[:5],  # Top 5
                        "opportunity_score": min(avg_engagement * len(questions_in_cluster), 100.0)
                    })
                
            except Exception as e:
                logger.warning("Clustering failed: %s", e)
                # Fallback to simple word-based themes
                all_text = " ".join(c["text"] for c in filtered_comments)
                meaningful_words = extract_meaningful_words(all_text)
                word_counts = Counter(meaningful_words)
                themes = [{"theme": word, "count": count} 
                         for word, count in word_counts.most_common(10)]
        else:
            # Fallback when embeddings fail
            logger.warning("Embeddings failed, using word-based themes")
            all_text = " ".join(c["text"] for c in filtered_comments)
            meaningful_words = extract_meaningful_words(all_text)
            word_counts = Counter(meaningful_words)
            themes = [{"theme": word, "count": count} 
                     for word, count in word_counts.most_common(10)]
    
    # Step 6: Generate video topic suggestions
    video_suggestions = generate_video_topic_suggestions(content_gaps, post_caption)
    
    # Step 7: Calculate final metrics
    sentiment = "neutral"
    if pos_count > neg_count * 2:
        sentiment = "very_positive"
    elif pos_count > neg_count:
        sentiment = "positive"
    elif neg_count > pos_count * 2:
        sentiment = "very_negative"
    elif neg_count > pos_count:
        sentiment = "negative"
    
    # Sort by engagement
    questions.sort(key=lambda x: x.get("likes", 0), reverse=True)
    pain_points.sort(key=lambda x: x.get("likes", 0), reverse=True)
    content_gaps.sort(key=lambda x: x.get("opportunity_score", 0), reverse=True)
    
    # Deduplicate product mentions
    product_counter = Counter(product_mentions)
    
    reply_rate = reply_count / max(total, 1) if total > 0 else 0.0
    avg_likes = total_likes / max(total, 1) if total > 0 else 0.0
    
    engagement_quality = (
        "high" if avg_likes > 5 else 
        "moderate" if avg_likes > 1 else 
        "low"
    )
    
    return {
        "analyzed": len(filtered_comments),
        "sentiment": sentiment,
        "sentiment_breakdown": {
            "positive": pos_count,
            "negative": neg_count,
            "neutral": len(filtered_comments) - pos_count - neg_count,
        },
        "avg_comment_likes": round(avg_likes, 1),
        "reply_rate": round(reply_rate * 100, 1),
        "questions": questions[:10],  # Top 10 by likes
        "pain_points": pain_points[:10],  # Top 10 by likes
        "product_mentions": [
            {"product": p, "count": c} 
            for p, c in product_counter.most_common(10)
        ],
        "themes": themes[:15],  # Top 15 cluster-based themes
        "top_commenters": [
            {"username": u, "count": c} 
            for u, c in top_commenters.most_common(10)
        ],
        "engagement_quality": engagement_quality,
        # New ML-powered fields
        "content_gaps": content_gaps[:10],  # Top 10 opportunities
        "video_topic_suggestions": video_suggestions[:5]  # Top 5 suggestions
    }