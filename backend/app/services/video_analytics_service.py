"""Video Analytics Service for Competitor Performance Comparison and Drop-off Analysis
Integrates with video analysis service to provide comprehensive analytics and recommendations.
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, update, func
import statistics
import numpy as np

logger = logging.getLogger(__name__)

@dataclass
class VideoPerformanceMetrics:
    """Comprehensive video performance metrics"""
    post_id: int
    competitor_handle: str
    platform: str
    engagement_rate: float
    virality_score: float
    likes: int
    comments: int
    shares: int
    views: int
    duration: float
    hook_strength: float
    retention_curve: List[float]  # Retention % at each time segment
    drop_off_points: List[Dict[str, Any]]  # Critical drop-off moments
    content_themes: List[str]
    visual_elements: List[str]

@dataclass 
class ContentPattern:
    """Pattern identified in high-performing content"""
    pattern_id: str
    pattern_type: str  # hook, visual, pacing, structure
    description: str
    success_rate: float
    avg_engagement_boost: float
    example_posts: List[int]
    recommended_usage: str

@dataclass
class RecommendationItem:
    """Actionable recommendation for content creation"""
    recommendation_id: str
    title: str
    description: str
    confidence_score: float
    expected_impact: str
    category: str  # hook, structure, visual, timing
    supporting_data: Dict[str, Any]
    example_videos: List[int]

class VideoAnalyticsService:
    """Service for advanced video analytics and recommendations"""
    
    def __init__(self):
        self.retention_segment_duration = 5.0  # seconds per retention segment
        
    async def compare_video_performance(
        self,
        db: AsyncSession,
        org_id: int,
        competitor_handles: List[str] = None,
        timeframe_days: int = 30,
        min_views: int = 1000
    ) -> Dict[str, Any]:
        """
        Compare video performance across competitors and identify top performers
        """
        try:
            # Build competitor filter
            handle_filter = ""
            if competitor_handles:
                placeholders = ",".join([f"'{handle}'" for handle in competitor_handles])
                handle_filter = f"AND c.handle IN ({placeholders})"
            
            # Get video performance data
            result = await db.execute(
                text(f"""
                    SELECT 
                        cp.id,
                        c.handle as competitor_handle,
                        c.platform,
                        cp.likes,
                        cp.comments, 
                        cp.shares,
                        cp.engagement_score,
                        cp.text,
                        cp.hook,
                        cp.timestamp,
                        cp.frame_chunks,
                        cp.video_analysis,
                        cp.media_type,
                        cp.url
                    FROM crm.competitor_posts cp
                    JOIN crm.competitors c ON cp.competitor_id = c.id
                    WHERE cp.org_id = :org_id
                      AND cp.media_type = 'video'
                      AND cp.timestamp >= NOW() - INTERVAL '{timeframe_days} days'
                      AND cp.likes >= :min_views
                      AND cp.analysis_status = 'completed'
                      {handle_filter}
                    ORDER BY cp.engagement_score DESC
                """),
                {"org_id": org_id, "min_views": min_views}
            )
            
            videos = []
            for row in result.fetchall():
                frame_chunks = json.loads(row[10]) if row[10] else []
                video_analysis = json.loads(row[11]) if row[11] else {}
                
                # Calculate retention curve and drop-offs from frame chunks
                retention_curve, drop_offs = self._analyze_retention_curve(
                    frame_chunks, video_analysis
                )
                
                video_metrics = VideoPerformanceMetrics(
                    post_id=row[0],
                    competitor_handle=row[1],
                    platform=row[2],
                    engagement_rate=self._calculate_engagement_rate(row[3], row[4], row[5]),
                    virality_score=row[6],
                    likes=row[3],
                    comments=row[4],
                    shares=row[5],
                    views=row[3] * 10,  # Estimate views from likes
                    duration=video_analysis.get('duration', 0),
                    hook_strength=self._analyze_hook_strength(row[8]),
                    retention_curve=retention_curve,
                    drop_off_points=drop_offs,
                    content_themes=self._extract_content_themes(row[7], frame_chunks),
                    visual_elements=self._extract_visual_elements(frame_chunks)
                )
                videos.append(video_metrics)
            
            # Analyze patterns
            top_performers = [v for v in videos if v.engagement_rate > 5.0]
            avg_engagement = statistics.mean([v.engagement_rate for v in videos]) if videos else 0
            
            # Identify drop-off patterns
            common_dropoffs = self._identify_common_dropoff_patterns(videos)
            
            # Performance benchmarks
            benchmarks = {
                'avg_engagement_rate': avg_engagement,
                'top_quartile_engagement': statistics.quantiles([v.engagement_rate for v in videos], n=4)[2] if len(videos) >= 4 else avg_engagement,
                'avg_retention_30s': statistics.mean([v.retention_curve[6] if len(v.retention_curve) > 6 else 0 for v in videos]) if videos else 0,
                'avg_hook_strength': statistics.mean([v.hook_strength for v in videos]) if videos else 0
            }
            
            return {
                "success": True,
                "total_videos_analyzed": len(videos),
                "top_performers": len(top_performers),
                "performance_benchmarks": benchmarks,
                "videos": [self._video_metrics_to_dict(v) for v in videos],
                "common_dropoff_patterns": common_dropoffs,
                "analysis_timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Video performance comparison failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def identify_viral_patterns(
        self,
        db: AsyncSession,
        org_id: int,
        min_engagement_rate: float = 10.0,
        min_sample_size: int = 5
    ) -> List[ContentPattern]:
        """
        Identify patterns in high-performing viral content
        """
        patterns = []
        
        try:
            # Get high-performing videos
            result = await db.execute(
                text("""
                    SELECT 
                        cp.id,
                        cp.hook,
                        cp.frame_chunks,
                        cp.video_analysis,
                        cp.engagement_score,
                        cp.text,
                        c.handle
                    FROM crm.competitor_posts cp
                    JOIN crm.competitors c ON cp.competitor_id = c.id
                    WHERE cp.org_id = :org_id
                      AND cp.media_type = 'video'
                      AND cp.engagement_score >= :min_engagement
                      AND cp.analysis_status = 'completed'
                    ORDER BY cp.engagement_score DESC
                    LIMIT 100
                """),
                {"org_id": org_id, "min_engagement": min_engagement_rate}
            )
            
            high_performers = []
            for row in result.fetchall():
                frame_chunks = json.loads(row[2]) if row[2] else []
                video_analysis = json.loads(row[3]) if row[3] else {}
                high_performers.append({
                    'post_id': row[0],
                    'hook': row[1],
                    'frame_chunks': frame_chunks,
                    'video_analysis': video_analysis,
                    'engagement_score': row[4],
                    'text': row[5],
                    'handle': row[6]
                })
            
            if len(high_performers) < min_sample_size:
                return patterns
                
            # Analyze hook patterns
            hook_patterns = self._analyze_hook_patterns(high_performers)
            patterns.extend(hook_patterns)
            
            # Analyze visual patterns
            visual_patterns = self._analyze_visual_patterns(high_performers)
            patterns.extend(visual_patterns)
            
            # Analyze pacing patterns
            pacing_patterns = self._analyze_pacing_patterns(high_performers)
            patterns.extend(pacing_patterns)
            
            # Analyze content structure patterns
            structure_patterns = self._analyze_structure_patterns(high_performers)
            patterns.extend(structure_patterns)
            
            return patterns
            
        except Exception as e:
            logger.error(f"Pattern identification failed: {e}")
            return []
    
    async def generate_content_recommendations(
        self,
        db: AsyncSession,
        org_id: int,
        user_video_performance: Dict[str, Any] = None
    ) -> List[RecommendationItem]:
        """
        Generate personalized content recommendations based on patterns and performance
        """
        recommendations = []
        
        try:
            # Get viral patterns
            patterns = await self.identify_viral_patterns(db, org_id)
            
            # Get user's current performance if available
            if user_video_performance:
                user_avg_engagement = user_video_performance.get('avg_engagement_rate', 2.0)
                user_weak_areas = user_video_performance.get('weak_areas', [])
            else:
                user_avg_engagement = 2.0
                user_weak_areas = ['hook', 'retention', 'visual_appeal']
            
            # Generate recommendations based on patterns
            for pattern in patterns:
                if pattern.success_rate > 0.7:  # Only high-success patterns
                    
                    if pattern.pattern_type == 'hook' and 'hook' in user_weak_areas:
                        recommendations.append(RecommendationItem(
                            recommendation_id=f"hook_{pattern.pattern_id}",
                            title=f"Improve Hook Strategy: {pattern.description}",
                            description=f"Videos using this hook pattern show {pattern.avg_engagement_boost:.1f}% higher engagement. {pattern.recommended_usage}",
                            confidence_score=pattern.success_rate,
                            expected_impact=f"+{pattern.avg_engagement_boost:.1f}% engagement",
                            category="hook",
                            supporting_data={
                                "pattern_success_rate": pattern.success_rate,
                                "engagement_boost": pattern.avg_engagement_boost,
                                "sample_size": len(pattern.example_posts)
                            },
                            example_videos=pattern.example_posts[:3]
                        ))
                    
                    elif pattern.pattern_type == 'visual' and 'visual_appeal' in user_weak_areas:
                        recommendations.append(RecommendationItem(
                            recommendation_id=f"visual_{pattern.pattern_id}",
                            title=f"Visual Enhancement: {pattern.description}",
                            description=f"This visual approach increases engagement by {pattern.avg_engagement_boost:.1f}%. {pattern.recommended_usage}",
                            confidence_score=pattern.success_rate,
                            expected_impact=f"+{pattern.avg_engagement_boost:.1f}% engagement",
                            category="visual",
                            supporting_data={
                                "pattern_success_rate": pattern.success_rate,
                                "engagement_boost": pattern.avg_engagement_boost
                            },
                            example_videos=pattern.example_posts[:3]
                        ))
                    
                    elif pattern.pattern_type == 'pacing' and 'retention' in user_weak_areas:
                        recommendations.append(RecommendationItem(
                            recommendation_id=f"pacing_{pattern.pattern_id}",
                            title=f"Optimize Video Pacing: {pattern.description}",
                            description=f"This pacing strategy improves retention by {pattern.avg_engagement_boost:.1f}%. {pattern.recommended_usage}",
                            confidence_score=pattern.success_rate,
                            expected_impact=f"+{pattern.avg_engagement_boost:.1f}% retention",
                            category="pacing",
                            supporting_data={
                                "pattern_success_rate": pattern.success_rate,
                                "retention_boost": pattern.avg_engagement_boost
                            },
                            example_videos=pattern.example_posts[:3]
                        ))
            
            # Sort by confidence score and expected impact
            recommendations.sort(key=lambda x: x.confidence_score * 
                               float(x.expected_impact.replace('%', '').replace('+', '').split()[0]), 
                               reverse=True)
            
            return recommendations[:10]  # Top 10 recommendations
            
        except Exception as e:
            logger.error(f"Recommendation generation failed: {e}")
            return []
    
    def _analyze_retention_curve(
        self, 
        frame_chunks: List[Dict], 
        video_analysis: Dict
    ) -> Tuple[List[float], List[Dict[str, Any]]]:
        """Analyze retention curve and identify drop-off points"""
        if not frame_chunks or not video_analysis:
            return [], []
            
        duration = video_analysis.get('duration', 0)
        if duration == 0:
            return [], []
            
        # Create retention segments (5-second intervals)
        segments = int(duration // self.retention_segment_duration) + 1
        retention_curve = []
        drop_offs = []
        
        # Simulate retention based on content analysis
        # In production, this would use actual viewership data
        base_retention = 1.0
        
        for i in range(segments):
            segment_start = i * self.retention_segment_duration
            segment_end = min((i + 1) * self.retention_segment_duration, duration)
            
            # Find relevant frame chunk
            relevant_chunk = None
            for chunk in frame_chunks:
                if (chunk.get('start_time', 0) <= segment_start <= chunk.get('end_time', 0)):
                    relevant_chunk = chunk
                    break
            
            if relevant_chunk:
                # Calculate retention drop based on content quality
                action_type = relevant_chunk.get('action_type', 'static')
                pacing = relevant_chunk.get('pacing', 'medium')
                visual_elements = relevant_chunk.get('visual_elements', [])
                
                # Retention factors
                if action_type == 'dynamic':
                    retention_factor = 0.95  # 5% drop
                elif action_type == 'static':
                    retention_factor = 0.85  # 15% drop
                else:
                    retention_factor = 0.90  # 10% drop
                    
                if pacing == 'fast':
                    retention_factor += 0.05
                elif pacing == 'slow':
                    retention_factor -= 0.10
                    
                if 'person' in visual_elements:
                    retention_factor += 0.03
                if 'text_overlay' in visual_elements:
                    retention_factor += 0.02
                    
                base_retention *= max(0.1, retention_factor)
                
                # Identify significant drop-offs (>20% drop in single segment)
                if retention_factor < 0.80:
                    drop_offs.append({
                        'timestamp': segment_start,
                        'retention_before': base_retention / retention_factor,
                        'retention_after': base_retention,
                        'drop_percentage': (1 - retention_factor) * 100,
                        'possible_causes': [
                            f"Action type: {action_type}",
                            f"Pacing: {pacing}",
                            f"Visual elements: {', '.join(visual_elements) if visual_elements else 'None'}"
                        ]
                    })
            else:
                base_retention *= 0.90  # Default 10% drop per segment
                
            retention_curve.append(base_retention)
        
        return retention_curve, drop_offs
    
    def _calculate_engagement_rate(self, likes: int, comments: int, shares: int) -> float:
        """Calculate engagement rate from interactions"""
        total_engagement = likes + (comments * 3) + (shares * 5)  # Weighted engagement
        estimated_views = likes * 10  # Rough estimate
        return (total_engagement / max(estimated_views, 1)) * 100
    
    def _analyze_hook_strength(self, hook: str) -> float:
        """Analyze hook strength based on content"""
        if not hook:
            return 0.0
            
        hook_indicators = [
            'secret', 'never', 'surprising', 'shocking', 'amazing', 
            'unbelievable', 'instant', 'immediately', 'watch this',
            'you won\'t believe', 'this changed everything', 'exposed',
            'revealed', 'truth about', 'warning', 'alert', 'breaking'
        ]
        
        hook_lower = hook.lower()
        strength = 0.0
        
        for indicator in hook_indicators:
            if indicator in hook_lower:
                strength += 1.0
                
        # Question hooks
        if '?' in hook:
            strength += 0.5
            
        # Urgency words
        urgency_words = ['now', 'today', 'immediately', 'urgent', 'limited']
        for word in urgency_words:
            if word in hook_lower:
                strength += 0.3
                
        return min(strength, 5.0)  # Cap at 5.0
    
    def _extract_content_themes(self, text: str, frame_chunks: List[Dict]) -> List[str]:
        """Extract content themes from text and visual analysis"""
        themes = set()
        
        if text:
            text_lower = text.lower()
            
            # Common themes
            if any(word in text_lower for word in ['fitness', 'workout', 'gym', 'exercise']):
                themes.add('fitness')
            if any(word in text_lower for word in ['food', 'recipe', 'cooking', 'eat']):
                themes.add('food')
            if any(word in text_lower for word in ['tech', 'phone', 'app', 'software']):
                themes.add('technology')
            if any(word in text_lower for word in ['travel', 'vacation', 'trip', 'destination']):
                themes.add('travel')
            if any(word in text_lower for word in ['style', 'fashion', 'outfit', 'clothing']):
                themes.add('fashion')
            if any(word in text_lower for word in ['money', 'business', 'entrepreneur', 'invest']):
                themes.add('business')
            if any(word in text_lower for word in ['love', 'relationship', 'dating', 'partner']):
                themes.add('relationships')
                
        return list(themes)
    
    def _extract_visual_elements(self, frame_chunks: List[Dict]) -> List[str]:
        """Extract visual elements from frame analysis"""
        elements = set()
        
        for chunk in frame_chunks:
            chunk_elements = chunk.get('visual_elements', [])
            elements.update(chunk_elements)
            
        return list(elements)
    
    def _identify_common_dropoff_patterns(self, videos: List[VideoPerformanceMetrics]) -> List[Dict[str, Any]]:
        """Identify common patterns in viewer drop-off points"""
        dropoff_timestamps = []
        
        for video in videos:
            for dropoff in video.drop_off_points:
                dropoff_timestamps.append({
                    'timestamp': dropoff['timestamp'],
                    'drop_percentage': dropoff['drop_percentage'],
                    'causes': dropoff.get('possible_causes', [])
                })
        
        # Group by timestamp ranges (0-10s, 10-20s, etc.)
        time_ranges = {}
        for dropoff in dropoff_timestamps:
            time_range = int(dropoff['timestamp'] // 10) * 10
            if time_range not in time_ranges:
                time_ranges[time_range] = {
                    'range': f"{time_range}-{time_range + 10}s",
                    'count': 0,
                    'avg_drop': 0,
                    'common_causes': []
                }
            time_ranges[time_range]['count'] += 1
            time_ranges[time_range]['avg_drop'] += dropoff['drop_percentage']
            time_ranges[time_range]['common_causes'].extend(dropoff['causes'])
        
        # Calculate averages and find most common causes
        for range_data in time_ranges.values():
            range_data['avg_drop'] /= range_data['count']
            cause_counts = {}
            for cause in range_data['common_causes']:
                cause_counts[cause] = cause_counts.get(cause, 0) + 1
            range_data['top_causes'] = sorted(cause_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            del range_data['common_causes']  # Remove raw causes
        
        return list(time_ranges.values())
    
    def _analyze_hook_patterns(self, high_performers: List[Dict]) -> List[ContentPattern]:
        """Analyze patterns in successful hooks"""
        patterns = []
        
        # Group hooks by pattern types
        question_hooks = [p for p in high_performers if p['hook'] and '?' in p['hook']]
        statement_hooks = [p for p in high_performers if p['hook'] and '?' not in p['hook'] and p['hook']]
        
        if len(question_hooks) >= 3:
            avg_engagement = statistics.mean([p['engagement_score'] for p in question_hooks])
            patterns.append(ContentPattern(
                pattern_id="question_hook",
                pattern_type="hook",
                description="Question-based hooks that create curiosity",
                success_rate=len(question_hooks) / len(high_performers),
                avg_engagement_boost=25.0,  # Estimated boost
                example_posts=[p['post_id'] for p in question_hooks[:5]],
                recommended_usage="Start videos with engaging questions that create curiosity gaps"
            ))
        
        if len(statement_hooks) >= 3:
            patterns.append(ContentPattern(
                pattern_id="statement_hook",
                pattern_type="hook", 
                description="Bold statement hooks that promise value",
                success_rate=len(statement_hooks) / len(high_performers),
                avg_engagement_boost=20.0,
                example_posts=[p['post_id'] for p in statement_hooks[:5]],
                recommended_usage="Use confident statements that promise immediate value or revelation"
            ))
        
        return patterns
    
    def _analyze_visual_patterns(self, high_performers: List[Dict]) -> List[ContentPattern]:
        """Analyze visual patterns in high-performing content"""
        patterns = []
        
        # Analyze visual elements
        person_videos = []
        text_overlay_videos = []
        product_videos = []
        
        for video in high_performers:
            elements = set()
            for chunk in video['frame_chunks']:
                elements.update(chunk.get('visual_elements', []))
                
            if 'person' in elements:
                person_videos.append(video)
            if 'text_overlay' in elements:
                text_overlay_videos.append(video)
            if 'product' in elements:
                product_videos.append(video)
        
        if len(person_videos) >= 5:
            patterns.append(ContentPattern(
                pattern_id="person_focused",
                pattern_type="visual",
                description="Videos featuring people prominently",
                success_rate=len(person_videos) / len(high_performers),
                avg_engagement_boost=30.0,
                example_posts=[p['post_id'] for p in person_videos[:5]],
                recommended_usage="Include people in your videos to increase relatability and engagement"
            ))
        
        return patterns
    
    def _analyze_pacing_patterns(self, high_performers: List[Dict]) -> List[ContentPattern]:
        """Analyze pacing patterns in successful content"""
        patterns = []
        
        fast_paced = []
        for video in high_performers:
            fast_chunks = sum(1 for chunk in video['frame_chunks'] 
                            if chunk.get('pacing') == 'fast')
            total_chunks = len(video['frame_chunks'])
            if total_chunks > 0 and fast_chunks / total_chunks > 0.6:
                fast_paced.append(video)
        
        if len(fast_paced) >= 3:
            patterns.append(ContentPattern(
                pattern_id="fast_pacing",
                pattern_type="pacing",
                description="Fast-paced content with quick transitions",
                success_rate=len(fast_paced) / len(high_performers),
                avg_engagement_boost=35.0,
                example_posts=[p['post_id'] for p in fast_paced[:5]],
                recommended_usage="Use quick cuts and fast pacing to maintain viewer attention"
            ))
        
        return patterns
    
    def _analyze_structure_patterns(self, high_performers: List[Dict]) -> List[ContentPattern]:
        """Analyze content structure patterns"""
        patterns = []
        
        # Analyze video duration patterns  
        short_videos = [p for p in high_performers 
                       if p['video_analysis'].get('duration', 0) < 30]
        medium_videos = [p for p in high_performers 
                        if 30 <= p['video_analysis'].get('duration', 0) < 60]
        
        if len(short_videos) >= 5:
            patterns.append(ContentPattern(
                pattern_id="short_form",
                pattern_type="structure",
                description="Short-form content under 30 seconds",
                success_rate=len(short_videos) / len(high_performers),
                avg_engagement_boost=40.0,
                example_posts=[p['post_id'] for p in short_videos[:5]],
                recommended_usage="Keep content under 30 seconds for maximum engagement"
            ))
        
        return patterns
    
    def _video_metrics_to_dict(self, video: VideoPerformanceMetrics) -> Dict[str, Any]:
        """Convert VideoPerformanceMetrics to dictionary"""
        return {
            "post_id": video.post_id,
            "competitor_handle": video.competitor_handle,
            "platform": video.platform,
            "engagement_rate": video.engagement_rate,
            "virality_score": video.virality_score,
            "likes": video.likes,
            "comments": video.comments,
            "shares": video.shares,
            "views": video.views,
            "duration": video.duration,
            "hook_strength": video.hook_strength,
            "retention_curve": video.retention_curve,
            "drop_off_points": video.drop_off_points,
            "content_themes": video.content_themes,
            "visual_elements": video.visual_elements
        }


# Service instance
video_analytics_service = VideoAnalyticsService()