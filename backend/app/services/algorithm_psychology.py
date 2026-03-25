"""Algorithm Psychology Analysis

Analyzes how audience behavior signals to platform algorithms and identifies
optimization opportunities for viral content distribution.
"""

import logging
import re
from collections import Counter, defaultdict
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class AlgorithmSignal(Enum):
    """Types of signals that influence algorithm distribution."""
    ENGAGEMENT_VELOCITY = "engagement_velocity"      # Fast initial engagement
    WATCH_TIME_PROXIES = "watch_time_proxies"        # Comments about specific parts
    SAVE_SIGNALS = "save_signals"                    # Bookmarking behavior
    SHARE_SIGNALS = "share_signals"                  # Explicit sharing mentions
    COMMENT_DEPTH = "comment_depth"                  # Substantive vs surface comments
    REPLAY_SIGNALS = "replay_signals"                # Multiple viewing indicators
    COMPLETION_SIGNALS = "completion_signals"        # Watched to end indicators
    EMOTIONAL_ENGAGEMENT = "emotional_engagement"    # Strong emotional reactions


@dataclass
class AlgorithmInsight:
    """Individual algorithm optimization insight."""
    signal_type: AlgorithmSignal
    strength: float  # 0-1 score for signal strength
    evidence: List[str]  # Supporting comments/data
    optimization_tip: str


class AlgorithmPsychologyAnalyzer:
    """Analyzes audience behavior for algorithm optimization insights."""
    
    def __init__(self):
        # Patterns that indicate algorithm-favorable behavior
        self.watch_time_patterns = [
            r"at (\d+):(\d+)",  # "at 2:30"
            r"(\d+) (?:minutes?|mins?) in",  # "5 minutes in"
            r"around (\d+):(\d+)",  # "around 1:15"
            r"the part where",
            r"when (?:he|she|they) said",
            r"that moment when",
            r"skip to (\d+):(\d+)",
            r"pause at"
        ]
        
        self.save_patterns = [
            "save", "saved", "saving", "bookmark", "bookmarked",
            "screenshot", "screenshotted", "keeping this",
            "writing this down", "taking notes", "need to remember"
        ]
        
        self.share_patterns = [
            "sharing", "shared", "sending this to", "tag", "tagged",
            "everyone needs", "must watch", "share this with",
            "my friends need", "posting this", "repost"
        ]
        
        self.replay_patterns = [
            "watching again", "rewatching", "watched (\d+) times",
            "back here", "came back", "replay", "replaying",
            "had to watch twice", "seen this (\d+) times"
        ]
        
        self.completion_patterns = [
            "watched (?:the )?(?:whole|entire) (?:thing|video)",
            "stayed (?:till|until) the end",
            "watched all of it", "finished watching",
            "made it to the end", "worth watching (?:the )?(?:whole|entire)"
        ]
        
        self.emotional_intensity_patterns = {
            "high": ["amazing", "incredible", "mind-blown", "speechless", "wow", "holy"],
            "medium": ["great", "good", "nice", "cool", "interesting"],
            "low": ["ok", "fine", "decent", "alright"]
        }
    
    def analyze_watch_time_signals(self, comments: List[Dict]) -> Tuple[float, List[str]]:
        """Analyze comments for watch time / retention signals."""
        signals = []
        evidence = []
        
        for comment in comments:
            text = comment.get("text", "").lower()
            
            # Check for timestamp references
            for pattern in self.watch_time_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    signals.append(1.0)  # Strong signal
                    evidence.append(f"Timestamp reference: '{text[:100]}...'")
                    break
            
            # Check for part references
            if any(phrase in text for phrase in ["this part", "that part", "the ending", "beginning"]):
                signals.append(0.7)
                evidence.append(f"Part reference: '{text[:80]}...'")
        
        strength = min(sum(signals) / max(len(comments), 1), 1.0)
        return strength, evidence[:5]  # Top 5 examples
    
    def analyze_save_signals(self, comments: List[Dict]) -> Tuple[float, List[str]]:
        """Analyze comments for save/bookmark behavior."""
        save_count = 0
        evidence = []
        
        for comment in comments:
            text = comment.get("text", "").lower()
            
            if any(pattern in text for pattern in self.save_patterns):
                save_count += 1
                evidence.append(f"Save signal: '{text[:80]}...'")
        
        # Normalize by total comments
        strength = min(save_count / max(len(comments), 1) * 10, 1.0)  # Scale up since saves are rare
        return strength, evidence[:5]
    
    def analyze_share_signals(self, comments: List[Dict]) -> Tuple[float, List[str]]:
        """Analyze comments for sharing behavior."""
        share_count = 0
        evidence = []
        
        for comment in comments:
            text = comment.get("text", "").lower()
            
            if any(pattern in text for pattern in self.share_patterns):
                share_count += 1
                evidence.append(f"Share signal: '{text[:80]}...'")
            
            # Tag patterns (@ mentions of friends)
            if re.search(r'@\w+.*(?:watch|see|check)', text):
                share_count += 0.5  # Tagging friends
                evidence.append(f"Friend tag: '{text[:80]}...'")
        
        strength = min(share_count / max(len(comments), 1) * 8, 1.0)  # Scale up
        return strength, evidence[:5]
    
    def analyze_replay_signals(self, comments: List[Dict]) -> Tuple[float, List[str]]:
        """Analyze comments for replay/rewatch behavior."""
        replay_count = 0
        evidence = []
        
        for comment in comments:
            text = comment.get("text", "").lower()
            
            if any(pattern in text for pattern in self.replay_patterns):
                replay_count += 1
                evidence.append(f"Replay signal: '{text[:80]}...'")
        
        strength = min(replay_count / max(len(comments), 1) * 15, 1.0)  # Very rare but valuable
        return strength, evidence[:5]
    
    def analyze_completion_signals(self, comments: List[Dict]) -> Tuple[float, List[str]]:
        """Analyze comments for completion/retention signals."""
        completion_count = 0
        evidence = []
        
        for comment in comments:
            text = comment.get("text", "").lower()
            
            for pattern in self.completion_patterns:
                if re.search(pattern, text):
                    completion_count += 1
                    evidence.append(f"Completion signal: '{text[:80]}...'")
                    break
        
        strength = min(completion_count / max(len(comments), 1) * 12, 1.0)
        return strength, evidence[:5]
    
    def analyze_emotional_engagement(self, comments: List[Dict]) -> Tuple[float, List[str]]:
        """Analyze emotional intensity of engagement."""
        emotional_scores = []
        evidence = []
        
        for comment in comments:
            text = comment.get("text", "").lower()
            likes = comment.get("likes", 0)
            
            # Score emotional intensity
            score = 0
            if any(word in text for word in self.emotional_intensity_patterns["high"]):
                score = 1.0
                evidence.append(f"High emotion: '{text[:80]}...'")
            elif any(word in text for word in self.emotional_intensity_patterns["medium"]):
                score = 0.6
            elif any(word in text for word in self.emotional_intensity_patterns["low"]):
                score = 0.3
            
            # Boost score based on likes (viral emotional comments)
            if likes > 10:
                score = min(score * 1.5, 1.0)
            
            if score > 0:
                emotional_scores.append(score)
        
        if not emotional_scores:
            return 0.0, []
        
        strength = sum(emotional_scores) / len(emotional_scores)
        return strength, evidence[:5]
    
    def analyze_engagement_velocity(self, comments: List[Dict], post_metrics: Dict = None) -> Tuple[float, List[str]]:
        """Analyze speed and intensity of initial engagement."""
        if not post_metrics:
            post_metrics = {}
        
        total_comments = len(comments)
        total_likes = sum(comment.get("likes", 0) for comment in comments)
        
        # Simple velocity proxy - comments with high engagement
        high_engagement_comments = [c for c in comments if c.get("likes", 0) > 5]
        
        # Calculate engagement density
        if total_comments > 0:
            engagement_density = total_likes / total_comments
            velocity_score = min(engagement_density / 10.0, 1.0)  # Normalize
        else:
            velocity_score = 0.0
        
        evidence = [
            f"Total comments: {total_comments}",
            f"Total comment likes: {total_likes}",
            f"High-engagement comments: {len(high_engagement_comments)}",
            f"Average likes per comment: {total_likes / max(total_comments, 1):.1f}"
        ]
        
        return velocity_score, evidence
    
    def analyze_comment_depth_distribution(self, comments: List[Dict]) -> Tuple[float, List[str]]:
        """Analyze distribution of comment depths for algorithm signals."""
        depths = {"surface": 0, "shallow": 0, "engaged": 0, "analytical": 0}
        
        for comment in comments:
            text = comment.get("text", "").strip()
            word_count = len(text.split())
            
            if word_count < 5:
                depths["surface"] += 1
            elif word_count < 15:
                depths["shallow"] += 1
            elif word_count < 30:
                depths["engaged"] += 1
            else:
                depths["analytical"] += 1
        
        total = sum(depths.values())
        if total == 0:
            return 0.0, []
        
        # Algorithm favors deeper engagement
        depth_score = (depths["engaged"] + depths["analytical"] * 1.5) / total
        
        evidence = [
            f"Surface comments: {depths['surface']} ({depths['surface']/total*100:.1f}%)",
            f"Engaged comments: {depths['engaged']} ({depths['engaged']/total*100:.1f}%)",
            f"Analytical comments: {depths['analytical']} ({depths['analytical']/total*100:.1f}%)"
        ]
        
        return depth_score, evidence
    
    def generate_algorithm_insights(self, comments: List[Dict], post_metrics: Dict = None) -> List[AlgorithmInsight]:
        """Generate comprehensive algorithm optimization insights."""
        insights = []
        
        # Analyze each signal type
        watch_time_strength, watch_time_evidence = self.analyze_watch_time_signals(comments)
        insights.append(AlgorithmInsight(
            signal_type=AlgorithmSignal.WATCH_TIME_PROXIES,
            strength=watch_time_strength,
            evidence=watch_time_evidence,
            optimization_tip=self._get_optimization_tip(AlgorithmSignal.WATCH_TIME_PROXIES, watch_time_strength)
        ))
        
        save_strength, save_evidence = self.analyze_save_signals(comments)
        insights.append(AlgorithmInsight(
            signal_type=AlgorithmSignal.SAVE_SIGNALS,
            strength=save_strength,
            evidence=save_evidence,
            optimization_tip=self._get_optimization_tip(AlgorithmSignal.SAVE_SIGNALS, save_strength)
        ))
        
        share_strength, share_evidence = self.analyze_share_signals(comments)
        insights.append(AlgorithmInsight(
            signal_type=AlgorithmSignal.SHARE_SIGNALS,
            strength=share_strength,
            evidence=share_evidence,
            optimization_tip=self._get_optimization_tip(AlgorithmSignal.SHARE_SIGNALS, share_strength)
        ))
        
        replay_strength, replay_evidence = self.analyze_replay_signals(comments)
        insights.append(AlgorithmInsight(
            signal_type=AlgorithmSignal.REPLAY_SIGNALS,
            strength=replay_strength,
            evidence=replay_evidence,
            optimization_tip=self._get_optimization_tip(AlgorithmSignal.REPLAY_SIGNALS, replay_strength)
        ))
        
        completion_strength, completion_evidence = self.analyze_completion_signals(comments)
        insights.append(AlgorithmInsight(
            signal_type=AlgorithmSignal.COMPLETION_SIGNALS,
            strength=completion_strength,
            evidence=completion_evidence,
            optimization_tip=self._get_optimization_tip(AlgorithmSignal.COMPLETION_SIGNALS, completion_strength)
        ))
        
        emotional_strength, emotional_evidence = self.analyze_emotional_engagement(comments)
        insights.append(AlgorithmInsight(
            signal_type=AlgorithmSignal.EMOTIONAL_ENGAGEMENT,
            strength=emotional_strength,
            evidence=emotional_evidence,
            optimization_tip=self._get_optimization_tip(AlgorithmSignal.EMOTIONAL_ENGAGEMENT, emotional_strength)
        ))
        
        velocity_strength, velocity_evidence = self.analyze_engagement_velocity(comments, post_metrics)
        insights.append(AlgorithmInsight(
            signal_type=AlgorithmSignal.ENGAGEMENT_VELOCITY,
            strength=velocity_strength,
            evidence=velocity_evidence,
            optimization_tip=self._get_optimization_tip(AlgorithmSignal.ENGAGEMENT_VELOCITY, velocity_strength)
        ))
        
        depth_strength, depth_evidence = self.analyze_comment_depth_distribution(comments)
        insights.append(AlgorithmInsight(
            signal_type=AlgorithmSignal.COMMENT_DEPTH,
            strength=depth_strength,
            evidence=depth_evidence,
            optimization_tip=self._get_optimization_tip(AlgorithmSignal.COMMENT_DEPTH, depth_strength)
        ))
        
        return insights
    
    def _get_optimization_tip(self, signal_type: AlgorithmSignal, strength: float) -> str:
        """Get specific optimization recommendations based on signal strength."""
        tips = {
            AlgorithmSignal.WATCH_TIME_PROXIES: {
                "low": "Add timestamps or teaser moments to encourage full viewing",
                "medium": "Include more specific calls-to-action at key moments", 
                "high": "Strong retention signals - maintain current pacing strategy"
            },
            AlgorithmSignal.SAVE_SIGNALS: {
                "low": "Create more actionable, save-worthy content with clear value",
                "medium": "Add explicit save prompts for valuable information",
                "high": "Excellent save behavior - content has strong utility value"
            },
            AlgorithmSignal.SHARE_SIGNALS: {
                "low": "Increase shareability with relatable or controversial content",
                "medium": "Add share calls-to-action and create 'tag a friend' moments",
                "high": "Strong viral potential - content resonates with audience"
            },
            AlgorithmSignal.REPLAY_SIGNALS: {
                "low": "Add layers of content that reward multiple viewings",
                "medium": "Include easter eggs or details that encourage rewatching",
                "high": "Excellent rewatch value - maintain content density"
            },
            AlgorithmSignal.COMPLETION_SIGNALS: {
                "low": "Improve content structure and pacing for better retention",
                "medium": "Add stronger hooks and payoffs throughout content",
                "high": "Excellent completion rate - strong content structure"
            },
            AlgorithmSignal.EMOTIONAL_ENGAGEMENT: {
                "low": "Increase emotional stakes and personal connection",
                "medium": "Amplify emotional moments and authentic reactions",
                "high": "Strong emotional resonance - maintain authentic voice"
            },
            AlgorithmSignal.ENGAGEMENT_VELOCITY: {
                "low": "Improve hooks and early engagement to boost initial velocity",
                "medium": "Optimize posting times and initial audience targeting",
                "high": "Excellent engagement velocity - content hits algorithm sweet spot"
            },
            AlgorithmSignal.COMMENT_DEPTH: {
                "low": "Ask deeper questions to encourage substantive discussion",
                "medium": "Balance accessibility with depth to maintain engagement",
                "high": "Great discussion quality - audience highly engaged"
            }
        }
        
        if strength < 0.3:
            level = "low"
        elif strength < 0.7:
            level = "medium"
        else:
            level = "high"
        
        return tips.get(signal_type, {}).get(level, "Monitor this signal for optimization opportunities")
    
    def calculate_algorithm_score(self, insights: List[AlgorithmInsight]) -> Dict[str, Any]:
        """Calculate overall algorithm optimization score."""
        if not insights:
            return {"score": 0.0, "grade": "F", "top_signals": [], "improvement_areas": []}
        
        # Weighted scoring (some signals more important than others)
        weights = {
            AlgorithmSignal.ENGAGEMENT_VELOCITY: 0.20,
            AlgorithmSignal.WATCH_TIME_PROXIES: 0.18,
            AlgorithmSignal.SAVE_SIGNALS: 0.15,
            AlgorithmSignal.EMOTIONAL_ENGAGEMENT: 0.15,
            AlgorithmSignal.COMMENT_DEPTH: 0.12,
            AlgorithmSignal.SHARE_SIGNALS: 0.10,
            AlgorithmSignal.COMPLETION_SIGNALS: 0.08,
            AlgorithmSignal.REPLAY_SIGNALS: 0.02
        }
        
        weighted_score = sum(
            insight.strength * weights.get(insight.signal_type, 0.1)
            for insight in insights
        )
        
        # Convert to grade
        if weighted_score >= 0.8:
            grade = "A"
        elif weighted_score >= 0.7:
            grade = "B"
        elif weighted_score >= 0.6:
            grade = "C"
        elif weighted_score >= 0.4:
            grade = "D"
        else:
            grade = "F"
        
        # Top performing signals
        top_signals = sorted(insights, key=lambda x: x.strength, reverse=True)[:3]
        
        # Areas needing improvement
        improvement_areas = [
            insight for insight in insights 
            if insight.strength < 0.4
        ]
        
        return {
            "score": round(weighted_score, 3),
            "grade": grade,
            "top_signals": [
                {
                    "signal": signal.signal_type.value,
                    "strength": signal.strength,
                    "optimization_tip": signal.optimization_tip
                }
                for signal in top_signals
            ],
            "improvement_areas": [
                {
                    "signal": signal.signal_type.value,
                    "strength": signal.strength,
                    "optimization_tip": signal.optimization_tip
                }
                for signal in improvement_areas
            ]
        }


# Singleton instance
algorithm_analyzer = AlgorithmPsychologyAnalyzer()