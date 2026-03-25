"""Deep Behavioral Psychology Analysis for Audience Intelligence.

Transforms surface-level comment analysis into deep psychological insights about:
1. WHY people share content (relatability/utility/identity signals)
2. Comment depth analysis (substantive vs generic) 
3. Behavioral patterns behind engagement metrics
4. Pain points and motivations extraction
5. Content sharing psychology ("This is how I feel" vs "You need this")
6. Algorithm insights and authentic friction vs perfection analysis

Focus: Understanding audience mindset to create viral content strategies.
"""

import asyncio
import json
import logging
import re
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass
from enum import Enum

import httpx
import numpy as np
# from sklearn.cluster import KMeans, DBSCAN
# from sklearn.metrics.pairwise import cosine_similarity
# from sklearn.decomposition import TruncatedSVD

logger = logging.getLogger(__name__)

# FastEmbed endpoint configuration
FASTEMBED_URL = "http://10.0.0.11:11435/api/embed"
FASTEMBED_TIMEOUT = 30.0


class ShareMotivation(Enum):
    """Why people share content - psychological drivers."""
    IDENTITY_SIGNAL = "identity_signal"  # "This represents who I am"
    RELATABILITY = "relatability"        # "This is exactly how I feel" 
    UTILITY = "utility"                  # "Others need to see this"
    STATUS = "status"                    # "I want to appear knowledgeable"
    EMOTION = "emotion"                  # "This made me feel something"
    TRIBAL = "tribal"                    # "My community needs this"


class CommentDepth(Enum):
    """Comment substance levels."""
    SURFACE = "surface"        # Generic reactions, emoji-only
    SHALLOW = "shallow"        # Basic agreement/disagreement  
    ENGAGED = "engaged"        # Personal experience sharing
    ANALYTICAL = "analytical"  # Deep thoughts, questions
    EXPERT = "expert"         # Domain knowledge display


class EngagementPsychology(Enum):
    """Psychological patterns in engagement."""
    VALIDATION_SEEKING = "validation_seeking"    # Seeking approval/likes
    HELP_SEEKING = "help_seeking"               # Asking for solutions
    EXPERTISE_DISPLAY = "expertise_display"     # Showing knowledge
    COMMUNITY_BUILDING = "community_building"   # Creating connections
    CONTROVERSY_ENGAGEMENT = "controversy"      # Stirring debate
    AUTHENTIC_SHARING = "authentic_sharing"     # Genuine experience


@dataclass
class PsychologicalProfile:
    """Individual commenter psychological profile."""
    username: str
    share_motivation: ShareMotivation
    comment_depth: CommentDepth
    engagement_psychology: EngagementPsychology
    pain_points: List[str]
    identity_signals: List[str]
    expertise_domains: List[str]
    emotional_tone: str
    influence_score: float  # Based on likes, replies, follower estimates


@dataclass
class ContentPsychology:
    """Psychological analysis of content and audience reaction."""
    hook_psychology: str  # What psychological trigger the hook uses
    shareability_score: float  # Predicted virality based on psychological factors
    friction_points: List[str]  # Where audience struggles with content
    perfection_vs_authenticity: float  # -1 (too polished) to 1 (authentic)
    algorithm_optimization: Dict[str, float]  # Platform algorithm psychology insights
    viral_triggers: List[str]  # Psychological elements that drive shares


# Psychological pattern recognition
IDENTITY_SIGNAL_PATTERNS = {
    "entrepreneur": ["startup", "founder", "ceo", "business owner", "entrepreneur"],
    "creator": ["creator", "artist", "designer", "content creator", "influencer"],
    "developer": ["developer", "programmer", "coder", "engineer", "tech"],
    "parent": ["mom", "dad", "parent", "kids", "children", "family"],
    "fitness": ["gym", "workout", "fitness", "health", "athlete"],
    "traveler": ["travel", "nomad", "explore", "adventure", "journey"],
    "student": ["student", "college", "university", "learning", "studying"]
}

PAIN_POINT_INDICATORS = {
    "time_management": ["no time", "busy", "overwhelmed", "rushing", "deadline"],
    "skill_gap": ["don't know how", "learn", "tutorial", "help", "confused"],
    "resource_constraints": ["expensive", "budget", "cheap", "affordable", "free"],
    "social_anxiety": ["nervous", "scared", "intimidated", "confidence", "imposter"],
    "decision_paralysis": ["which one", "so many options", "overwhelmed", "choose"],
    "perfectionism": ["perfect", "not good enough", "compare", "standards"],
    "technical_barriers": ["complicated", "complex", "technical", "difficult"]
}

SHARING_TRIGGERS = {
    "utility": ["helpful", "useful", "need this", "save", "bookmark", "everyone should"],
    "relatability": ["exactly", "me too", "same here", "relate", "feel this", "story of my life"],
    "identity": ["as a", "being a", "proud", "represent", "community", "tribe"],
    "emotional": ["made me cry", "laughing", "angry", "inspired", "motivated", "touched"],
    "validation": ["agree", "finally", "someone said it", "truth", "facts", "preach"],
    "controversy": ["disagree", "wrong", "actually", "but", "however", "unpopular opinion"]
}

ENGAGEMENT_DEPTH_SIGNALS = {
    "surface": ["❤️", "🔥", "💯", "nice", "cool", "good", "great"],  # Low effort
    "shallow": ["love this", "so true", "exactly", "agree", "yes"],
    "engaged": ["i", "my", "when i", "i used to", "this reminds me", "similar experience"],
    "analytical": ["what about", "how does", "why", "because", "the reason", "analysis"],
    "expert": ["actually", "in my experience", "i've found", "pro tip", "having done this"]
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


def analyze_share_motivation(comment: str) -> ShareMotivation:
    """Determine why someone would share this content."""
    comment_lower = comment.lower()
    
    # Check for sharing trigger patterns
    for motivation, patterns in SHARING_TRIGGERS.items():
        if any(pattern in comment_lower for pattern in patterns):
            if motivation == "utility":
                return ShareMotivation.UTILITY
            elif motivation == "relatability":
                return ShareMotivation.RELATABILITY
            elif motivation == "identity":
                return ShareMotivation.IDENTITY_SIGNAL
            elif motivation == "emotional":
                return ShareMotivation.EMOTION
            elif motivation == "validation":
                return ShareMotivation.STATUS
            elif motivation == "controversy":
                return ShareMotivation.TRIBAL
    
    # Default based on comment characteristics
    if any(word in comment_lower for word in ["save", "bookmark", "helpful"]):
        return ShareMotivation.UTILITY
    elif any(word in comment_lower for word in ["me", "i", "my"]):
        return ShareMotivation.RELATABILITY
    else:
        return ShareMotivation.EMOTION


def analyze_comment_depth(comment: str, likes: int = 0) -> CommentDepth:
    """Determine the substantive depth of a comment."""
    comment_lower = comment.lower()
    
    # Check for depth signals
    for depth, signals in ENGAGEMENT_DEPTH_SIGNALS.items():
        if any(signal in comment_lower for signal in signals):
            if depth == "surface":
                return CommentDepth.SURFACE
            elif depth == "shallow":
                return CommentDepth.SHALLOW
            elif depth == "engaged":
                return CommentDepth.ENGAGED
            elif depth == "analytical":
                return CommentDepth.ANALYTICAL
            elif depth == "expert":
                return CommentDepth.EXPERT
    
    # Length-based classification
    word_count = len(comment.split())
    if word_count < 5:
        return CommentDepth.SURFACE
    elif word_count < 15:
        return CommentDepth.SHALLOW
    elif word_count < 30:
        return CommentDepth.ENGAGED
    else:
        return CommentDepth.ANALYTICAL


def extract_identity_signals(comment: str, username: str = "") -> List[str]:
    """Extract identity signals from comment and username."""
    signals = []
    comment_lower = f"{comment} {username}".lower()
    
    for identity, keywords in IDENTITY_SIGNAL_PATTERNS.items():
        if any(keyword in comment_lower for keyword in keywords):
            signals.append(identity)
    
    # Extract explicit identity declarations
    identity_patterns = [
        r"as a (\w+)",
        r"being a (\w+)",
        r"i'm a (\w+)",
        r"(\w+) here",
        r"(\w+) perspective"
    ]
    
    for pattern in identity_patterns:
        matches = re.findall(pattern, comment_lower)
        signals.extend(matches)
    
    return list(set(signals))


def extract_pain_points(comment: str) -> List[str]:
    """Extract psychological pain points from comment."""
    pain_points = []
    comment_lower = comment.lower()
    
    for pain_type, indicators in PAIN_POINT_INDICATORS.items():
        if any(indicator in comment_lower for indicator in indicators):
            pain_points.append(pain_type)
    
    # Extract explicit pain expressions
    pain_patterns = [
        r"i (?:struggle|can't|wish|need help) with (.{5,50})",
        r"(?:frustrated|confused|stuck|lost) (?:with|about|by) (.{5,50})",
        r"why (?:is|does|don't) (.{5,50})"
    ]
    
    for pattern in pain_patterns:
        matches = re.findall(pattern, comment_lower)
        pain_points.extend([match.strip() for match in matches])
    
    return pain_points


def analyze_engagement_psychology(comment: str, likes: int, is_reply: bool) -> EngagementPsychology:
    """Determine the psychological driver behind the engagement."""
    comment_lower = comment.lower()
    
    # Question asking = help seeking
    if "?" in comment and any(word in comment_lower for word in ["how", "what", "why", "help"]):
        return EngagementPsychology.HELP_SEEKING
    
    # Expertise display patterns
    if any(phrase in comment_lower for phrase in ["actually", "in my experience", "pro tip", "having done"]):
        return EngagementPsychology.EXPERTISE_DISPLAY
    
    # Validation seeking (fishing for likes/replies)
    if any(phrase in comment_lower for phrase in ["agree?", "thoughts?", "am i right", "anyone else"]):
        return EngagementPsychology.VALIDATION_SEEKING
    
    # Community building
    if any(phrase in comment_lower for phrase in ["connect", "let's", "dm me", "follow for", "community"]):
        return EngagementPsychology.COMMUNITY_BUILDING
    
    # Controversy/debate
    if any(phrase in comment_lower for phrase in ["wrong", "disagree", "actually", "but", "unpopular opinion"]):
        return EngagementPsychology.CONTROVERSY_ENGAGEMENT
    
    # Default to authentic sharing
    return EngagementPsychology.AUTHENTIC_SHARING


def calculate_influence_score(likes: int, replies_to_comment: int, username: str) -> float:
    """Estimate commenter influence based on engagement metrics."""
    base_score = likes * 1.0 + replies_to_comment * 2.0
    
    # Username signals (verified, business, etc.)
    if any(signal in username.lower() for signal in ["verified", "official", "ceo", "founder"]):
        base_score *= 1.5
    
    # Normalize to 0-1 scale
    return min(base_score / 100.0, 1.0)


def remove_audience_overlap(profiles: List[PsychologicalProfile]) -> List[PsychologicalProfile]:
    """Remove shared audience members and top engagers to focus on unique insights."""
    unique_profiles = []
    seen_usernames = set()
    
    # Sort by influence score descending
    sorted_profiles = sorted(profiles, key=lambda p: p.influence_score, reverse=True)
    
    # Remove top 20% (likely shared engagers across posts)
    cutoff = int(len(sorted_profiles) * 0.2)
    filtered_profiles = sorted_profiles[cutoff:]
    
    # Remove duplicates
    for profile in filtered_profiles:
        if profile.username not in seen_usernames:
            seen_usernames.add(profile.username)
            unique_profiles.append(profile)
    
    return unique_profiles


async def analyze_content_psychology(
    comments: List[Dict], 
    post_caption: str = "",
    post_metrics: Dict = None
) -> ContentPsychology:
    """Analyze the psychological appeal and viral potential of content."""
    if not post_metrics:
        post_metrics = {}
    
    # Analyze hook psychology
    hook_psychology = analyze_hook_psychology(post_caption)
    
    # Calculate shareability score based on comment psychology
    shareability_score = calculate_shareability_score(comments)
    
    # Identify friction points
    friction_points = identify_friction_points(comments)
    
    # Analyze authenticity vs perfection
    authenticity_score = analyze_authenticity_spectrum(comments, post_caption)
    
    # Algorithm insights
    algorithm_insights = analyze_algorithm_psychology(comments, post_metrics)
    
    # Viral triggers
    viral_triggers = identify_viral_triggers(comments, post_caption)
    
    return ContentPsychology(
        hook_psychology=hook_psychology,
        shareability_score=shareability_score,
        friction_points=friction_points,
        perfection_vs_authenticity=authenticity_score,
        algorithm_optimization=algorithm_insights,
        viral_triggers=viral_triggers
    )


def analyze_hook_psychology(caption: str) -> str:
    """Analyze what psychological trigger the hook uses."""
    caption_lower = caption.lower()
    
    # Pattern matching for hook psychology
    if any(phrase in caption_lower for phrase in ["secret", "nobody tells you", "they don't want"]):
        return "forbidden_knowledge"
    elif any(phrase in caption_lower for phrase in ["mistake", "wrong", "stop doing"]):
        return "loss_aversion"
    elif any(phrase in caption_lower for phrase in ["story", "journey", "when i"]):
        return "narrative_transportation"
    elif any(phrase in caption_lower for phrase in ["free", "template", "resource"]):
        return "reciprocity_trigger"
    elif "?" in caption:
        return "curiosity_gap"
    elif any(phrase in caption_lower for phrase in ["unpopular", "controversial", "hot take"]):
        return "controversy_magnetism"
    else:
        return "generic_attention"


def calculate_shareability_score(comments: List[Dict]) -> float:
    """Calculate viral potential based on comment psychology patterns."""
    if not comments:
        return 0.0
    
    share_signals = 0
    total_analyzed = 0
    
    for comment in comments:
        text = comment.get("text", "")
        text_lower = text.lower()
        
        # Count sharing signals
        if any(phrase in text_lower for phrase in ["save", "bookmark", "sharing", "everyone needs"]):
            share_signals += 3
        elif any(phrase in text_lower for phrase in ["relate", "exactly", "me too", "same"]):
            share_signals += 2
        elif any(phrase in text_lower for phrase in ["love", "amazing", "incredible"]):
            share_signals += 1
        
        total_analyzed += 1
    
    return min(share_signals / max(total_analyzed, 1), 1.0)


def identify_friction_points(comments: List[Dict]) -> List[str]:
    """Identify where audience struggles with the content."""
    friction_points = []
    
    for comment in comments:
        text = comment.get("text", "").lower()
        
        if any(phrase in text for phrase in ["confused", "don't understand", "unclear", "lost"]):
            friction_points.append("comprehension_difficulty")
        elif any(phrase in text for phrase in ["too fast", "slow down", "missed"]):
            friction_points.append("pacing_issues")
        elif any(phrase in text for phrase in ["can't see", "small", "quality"]):
            friction_points.append("technical_quality")
        elif any(phrase in text for phrase in ["skip", "part", "boring"]):
            friction_points.append("attention_loss")
        elif any(phrase in text for phrase in ["expensive", "can't afford", "budget"]):
            friction_points.append("financial_barriers")
    
    return list(set(friction_points))


def analyze_authenticity_spectrum(comments: List[Dict], caption: str) -> float:
    """Analyze position on authentic friction vs perfection spectrum."""
    authenticity_signals = 0
    perfection_signals = 0
    
    # Analyze comments for authenticity perception
    for comment in comments:
        text = comment.get("text", "").lower()
        
        if any(phrase in text for phrase in ["real", "authentic", "honest", "genuine", "relatable"]):
            authenticity_signals += 1
        elif any(phrase in text for phrase in ["perfect", "polished", "fake", "staged", "try hard"]):
            perfection_signals += 1
    
    # Analyze caption for authenticity markers
    caption_lower = caption.lower()
    if any(phrase in caption_lower for phrase in ["struggle", "fail", "mistake", "journey"]):
        authenticity_signals += 2
    elif any(phrase in caption_lower for phrase in ["perfect", "flawless", "expert", "master"]):
        perfection_signals += 2
    
    total_signals = authenticity_signals + perfection_signals
    if total_signals == 0:
        return 0.0
    
    # Scale: -1 (too polished) to +1 (authentic)
    return (authenticity_signals - perfection_signals) / total_signals


def analyze_algorithm_psychology(comments: List[Dict], metrics: Dict) -> Dict[str, float]:
    """Analyze how content performs with platform algorithm psychology."""
    insights = {
        "engagement_velocity": 0.0,
        "comment_depth_ratio": 0.0,
        "save_signal_strength": 0.0,
        "watch_time_proxies": 0.0
    }
    
    if not comments:
        return insights
    
    # Calculate comment depth ratio (deep vs surface comments)
    deep_comments = sum(1 for c in comments if len(c.get("text", "").split()) > 10)
    insights["comment_depth_ratio"] = deep_comments / len(comments)
    
    # Save signal strength
    save_signals = sum(1 for c in comments 
                      if any(word in c.get("text", "").lower() for word in ["save", "bookmark"]))
    insights["save_signal_strength"] = save_signals / len(comments)
    
    # Watch time proxies (comments about specific parts)
    watch_time_signals = sum(1 for c in comments 
                           if any(phrase in c.get("text", "").lower() 
                                 for phrase in ["at", "minute", "second", "part where"]))
    insights["watch_time_proxies"] = watch_time_signals / len(comments)
    
    return insights


def identify_viral_triggers(comments: List[Dict], caption: str) -> List[str]:
    """Identify psychological elements that drive viral sharing."""
    triggers = []
    
    # Analyze comment patterns for viral indicators
    comment_text = " ".join(c.get("text", "") for c in comments).lower()
    
    if "tag" in comment_text and "friend" in comment_text:
        triggers.append("social_tagging")
    
    if any(phrase in comment_text for phrase in ["everyone needs", "share this", "spread"]):
        triggers.append("utility_compulsion")
    
    if any(phrase in comment_text for phrase in ["exactly", "relate", "same"]):
        triggers.append("relatability_trigger")
    
    if any(phrase in comment_text for phrase in ["controversy", "disagree", "debate"]):
        triggers.append("controversy_engagement")
    
    if any(phrase in comment_text for phrase in ["story", "experience", "happened to me"]):
        triggers.append("narrative_resonance")
    
    # Analyze caption for viral elements
    caption_lower = caption.lower()
    if "?" in caption:
        triggers.append("curiosity_gap")
    
    if any(phrase in caption_lower for phrase in ["unpopular", "hot take", "controversial"]):
        triggers.append("opinion_polarization")
    
    return list(set(triggers))


async def analyze_audience_psychology(
    comments: List[Dict], 
    post_caption: str = "",
    creator_username: str = "",
    post_metrics: Dict = None
) -> Dict[str, Any]:
    """
    Comprehensive behavioral psychology analysis of audience.
    
    Returns deep insights about audience mindset, sharing psychology,
    and content optimization opportunities.
    """
    if not comments:
        return {
            "psychological_profiles": [],
            "content_psychology": None,
            "behavioral_insights": {},
            "sharing_psychology": {},
            "optimization_recommendations": []
        }
    
    # Step 1: Create psychological profiles for each commenter
    profiles = []
    for comment in comments:
        text = comment.get("text", "")
        username = comment.get("username", "")
        likes = comment.get("likes", 0)
        is_reply = comment.get("is_reply", False)
        
        if len(text.strip()) < 5:  # Skip empty/spam
            continue
        
        profile = PsychologicalProfile(
            username=username,
            share_motivation=analyze_share_motivation(text),
            comment_depth=analyze_comment_depth(text, likes),
            engagement_psychology=analyze_engagement_psychology(text, likes, is_reply),
            pain_points=extract_pain_points(text),
            identity_signals=extract_identity_signals(text, username),
            expertise_domains=[],  # TODO: Extract from comment content
            emotional_tone=analyze_emotional_tone(text),
            influence_score=calculate_influence_score(likes, 0, username)
        )
        profiles.append(profile)
    
    # Step 2: Remove audience overlap (shared top engagers)
    unique_profiles = remove_audience_overlap(profiles)
    
    # Step 3: Analyze content psychology
    content_psychology = await analyze_content_psychology(comments, post_caption, post_metrics)
    
    # Step 4: Generate behavioral insights
    behavioral_insights = generate_behavioral_insights(unique_profiles)
    
    # Step 5: Analyze sharing psychology patterns
    sharing_psychology = analyze_sharing_psychology_patterns(unique_profiles)
    
    # Step 6: Algorithm psychology analysis
    try:
        from app.services.algorithm_psychology import algorithm_analyzer
        algorithm_insights = algorithm_analyzer.generate_algorithm_insights(comments, post_metrics)
        algorithm_score = algorithm_analyzer.calculate_algorithm_score(algorithm_insights)
    except Exception as e:
        logger.warning("Algorithm analysis failed: %s", e)
        algorithm_insights = []
        algorithm_score = {}
    
    # Step 7: Generate optimization recommendations
    optimization_recommendations = generate_optimization_recommendations(
        unique_profiles, content_psychology, behavioral_insights, algorithm_insights
    )
    
    return {
        "psychological_profiles": [
            {
                "username": p.username,
                "share_motivation": p.share_motivation.value,
                "comment_depth": p.comment_depth.value,
                "engagement_psychology": p.engagement_psychology.value,
                "pain_points": p.pain_points,
                "identity_signals": p.identity_signals,
                "emotional_tone": p.emotional_tone,
                "influence_score": p.influence_score
            }
            for p in unique_profiles[:50]  # Top 50 most insightful profiles
        ],
        "content_psychology": {
            "hook_psychology": content_psychology.hook_psychology,
            "shareability_score": content_psychology.shareability_score,
            "friction_points": content_psychology.friction_points,
            "authenticity_score": content_psychology.perfection_vs_authenticity,
            "algorithm_insights": content_psychology.algorithm_optimization,
            "viral_triggers": content_psychology.viral_triggers
        },
        "behavioral_insights": behavioral_insights,
        "sharing_psychology": sharing_psychology,
        "algorithm_insights": {
            "signals": [
                {
                    "signal_type": insight.signal_type.value,
                    "strength": insight.strength,
                    "evidence": insight.evidence,
                    "optimization_tip": insight.optimization_tip
                }
                for insight in algorithm_insights
            ],
            "overall_score": algorithm_score
        },
        "optimization_recommendations": optimization_recommendations
    }


def analyze_emotional_tone(text: str) -> str:
    """Analyze the emotional tone of a comment."""
    text_lower = text.lower()
    
    # Emotional indicators
    if any(word in text_lower for word in ["love", "amazing", "incredible", "awesome"]):
        return "enthusiastic"
    elif any(word in text_lower for word in ["frustrated", "angry", "disappointed"]):
        return "frustrated"
    elif any(word in text_lower for word in ["confused", "lost", "help"]):
        return "confused"
    elif any(word in text_lower for word in ["thanks", "grateful", "appreciate"]):
        return "grateful"
    elif any(word in text_lower for word in ["inspired", "motivated", "encouraging"]):
        return "inspired"
    else:
        return "neutral"


def generate_behavioral_insights(profiles: List[PsychologicalProfile]) -> Dict[str, Any]:
    """Generate insights about audience behavioral patterns."""
    if not profiles:
        return {}
    
    # Motivation distribution
    motivations = [p.share_motivation.value for p in profiles]
    motivation_dist = dict(Counter(motivations))
    
    # Depth distribution  
    depths = [p.comment_depth.value for p in profiles]
    depth_dist = dict(Counter(depths))
    
    # Psychology distribution
    psychologies = [p.engagement_psychology.value for p in profiles]
    psychology_dist = dict(Counter(psychologies))
    
    # Common pain points
    all_pain_points = [pain for p in profiles for pain in p.pain_points]
    top_pain_points = dict(Counter(all_pain_points).most_common(10))
    
    # Identity signals
    all_identities = [identity for p in profiles for identity in p.identity_signals]
    top_identities = dict(Counter(all_identities).most_common(10))
    
    return {
        "motivation_distribution": motivation_dist,
        "engagement_depth_distribution": depth_dist,
        "psychology_distribution": psychology_dist,
        "top_pain_points": top_pain_points,
        "dominant_identities": top_identities,
        "average_influence_score": sum(p.influence_score for p in profiles) / len(profiles),
        "high_influence_percentage": sum(1 for p in profiles if p.influence_score > 0.5) / len(profiles)
    }


def analyze_sharing_psychology_patterns(profiles: List[PsychologicalProfile]) -> Dict[str, Any]:
    """Analyze WHY and HOW audience shares content."""
    utility_sharers = [p for p in profiles if p.share_motivation == ShareMotivation.UTILITY]
    identity_sharers = [p for p in profiles if p.share_motivation == ShareMotivation.IDENTITY_SIGNAL]
    relatability_sharers = [p for p in profiles if p.share_motivation == ShareMotivation.RELATABILITY]
    
    return {
        "primary_sharing_driver": max(
            [
                (ShareMotivation.UTILITY.value, len(utility_sharers)),
                (ShareMotivation.IDENTITY_SIGNAL.value, len(identity_sharers)),
                (ShareMotivation.RELATABILITY.value, len(relatability_sharers))
            ],
            key=lambda x: x[1]
        )[0],
        "utility_share_signals": len(utility_sharers) / len(profiles) if profiles else 0,
        "identity_share_signals": len(identity_sharers) / len(profiles) if profiles else 0,
        "relatability_share_signals": len(relatability_sharers) / len(profiles) if profiles else 0,
        "sharing_psychology_breakdown": {
            "this_is_how_i_feel": len(relatability_sharers),
            "you_need_this": len(utility_sharers),
            "this_represents_me": len(identity_sharers)
        }
    }


def generate_optimization_recommendations(
    profiles: List[PsychologicalProfile],
    content_psychology: ContentPsychology,
    behavioral_insights: Dict,
    algorithm_insights: List = None
) -> List[Dict[str, str]]:
    """Generate actionable recommendations for viral content creation."""
    recommendations = []
    
    # Based on sharing psychology
    primary_driver = behavioral_insights.get("motivation_distribution", {})
    if primary_driver:
        top_motivation = max(primary_driver.items(), key=lambda x: x[1])[0]
        
        if top_motivation == "utility":
            recommendations.append({
                "category": "Content Strategy",
                "recommendation": "Focus on actionable, save-worthy content",
                "reasoning": "Audience primarily shares for utility value"
            })
        elif top_motivation == "relatability":
            recommendations.append({
                "category": "Content Strategy", 
                "recommendation": "Increase personal story sharing and 'me too' moments",
                "reasoning": "Audience connects through shared experiences"
            })
        elif top_motivation == "identity_signal":
            recommendations.append({
                "category": "Content Strategy",
                "recommendation": "Create content that helps audience signal their identity",
                "reasoning": "Audience shares to represent who they are"
            })
    
    # Based on friction points
    if content_psychology.friction_points:
        for friction in content_psychology.friction_points:
            if friction == "comprehension_difficulty":
                recommendations.append({
                    "category": "Content Optimization",
                    "recommendation": "Simplify explanations and add visual aids",
                    "reasoning": "Audience struggling with comprehension"
                })
            elif friction == "pacing_issues":
                recommendations.append({
                    "category": "Content Optimization",
                    "recommendation": "Adjust content pacing based on audience feedback",
                    "reasoning": "Audience indicates pacing problems"
                })
    
    # Based on authenticity score
    if content_psychology.perfection_vs_authenticity < -0.3:
        recommendations.append({
            "category": "Authenticity",
            "recommendation": "Show more struggle, failure, and behind-the-scenes",
            "reasoning": "Content perceived as too polished/perfect"
        })
    elif content_psychology.perfection_vs_authenticity > 0.7:
        recommendations.append({
            "category": "Quality",
            "recommendation": "Improve production quality while maintaining authenticity",
            "reasoning": "High authenticity but may benefit from better quality"
        })
    
    # Based on engagement depth
    depth_dist = behavioral_insights.get("engagement_depth_distribution", {})
    if depth_dist.get("surface", 0) > depth_dist.get("engaged", 0):
        recommendations.append({
            "category": "Engagement Strategy",
            "recommendation": "Ask deeper questions to encourage substantive comments",
            "reasoning": "Most engagement is surface-level"
        })
    
    # Algorithm-based recommendations
    if algorithm_insights:
        for insight in algorithm_insights:
            if insight.strength < 0.4:  # Low performing signals
                recommendations.append({
                    "category": "Algorithm Optimization",
                    "recommendation": insight.optimization_tip,
                    "reasoning": f"Low {insight.signal_type.value.replace('_', ' ')} signals detected"
                })
    
    return recommendations