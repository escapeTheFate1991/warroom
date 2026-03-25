"""
Unified Video Data Model for Competitor Intelligence Platform

This model normalizes video data from competitor_posts into a structured
format for the CDR (Creator Directive Report) platform.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field
import json
import re


class VideoMetrics(BaseModel):
    """Real engagement metrics from social platforms"""
    likes: int = 0
    comments: int = 0
    views: Optional[int] = None
    saves: Optional[int] = None
    shares: Optional[int] = None


class VideoRuntime(BaseModel):
    """Video duration with proper formatting"""
    seconds: int = Field(description="Total duration in seconds")
    display: str = Field(description="Human readable M:SS format")
    
    @classmethod
    def from_seconds(cls, seconds: Union[int, float, str]) -> 'VideoRuntime':
        """Create runtime from various second formats"""
        try:
            # Handle broken formats like "1:9.09999999999994" or "0:47.4"
            if isinstance(seconds, str):
                if ':' in seconds:
                    # Parse MM:SS format and extract seconds
                    parts = seconds.split(':')
                    if len(parts) == 2:
                        minutes = float(parts[0])
                        secs = float(parts[1])
                        total_seconds = int(minutes * 60 + secs)
                    else:
                        total_seconds = 0
                else:
                    total_seconds = int(float(seconds))
            else:
                total_seconds = int(float(seconds or 0))
        except (ValueError, TypeError):
            total_seconds = 0
        
        # Format as M:SS
        if total_seconds <= 0:
            display = "0:00"
        else:
            minutes = total_seconds // 60
            secs = total_seconds % 60
            display = f"{minutes}:{secs:02d}"
        
        return cls(seconds=total_seconds, display=display)


class VideoPacing(BaseModel):
    """Video pacing and structure analysis"""
    pace: str = "unknown"  # fast | medium | slow | unknown
    pattern: str = "unknown"  # hook_value_cta | rapid_fire | storytelling | unknown
    hook_type: Optional[str] = None  # curiosity | controversy | social_proof | etc
    value_stack_type: Optional[str] = None  # educational | entertainment | inspirational
    cta_type: Optional[str] = None  # soft | direct | none


class TranscriptSegment(BaseModel):
    """Timed segment of video transcript"""
    type: str  # hook | value_beat | cta | transition
    label: str  # Human readable description
    start_time: float = 0.0  # Seconds from start
    end_time: float = 0.0  # Seconds from start
    text: str = ""
    psych_mechanism: Optional[str] = None  # Psychological trigger used


class VideoTranscript(BaseModel):
    """Complete video transcript with segments"""
    full: str = ""
    segments: List[TranscriptSegment] = Field(default_factory=list)


class CreatorDirective(BaseModel):
    """Actionable directive extracted from video analysis"""
    directive: str  # What to do
    category: str  # replicate | avoid | test
    reasoning: str  # Why this directive matters


class VideoAnalytics(BaseModel):
    """Optional advanced analytics"""
    view_velocity: Optional[float] = None  # Views per hour in first 24h
    engagement_curve: Optional[Dict[str, float]] = None  # Time -> engagement rate
    comment_sentiment: Optional[str] = None  # positive | negative | neutral


class VideoRecord(BaseModel):
    """
    Unified Video Record Model
    
    This model represents a single video/post from competitor analysis,
    structured for the CDR platform frontend.
    """
    
    # Basic identifiers
    id: Optional[int] = None
    competitor_id: Optional[int] = None
    competitor_handle: str = "unknown"  # Handle/username of competitor
    platform: str
    title: str  # Derived from post_text or hook
    url: str
    posted_at: Optional[datetime] = None
    scraped_at: Optional[datetime] = None
    
    # Real metrics only - no calculated scores
    metrics: VideoMetrics
    
    # Runtime with proper format handling
    runtime: VideoRuntime
    
    # Content format classification
    format: str  # short_form | mid_form | long_form
    
    # Video pacing and structure
    pacing: VideoPacing
    
    # Transcript with timed segments
    transcript: VideoTranscript
    
    # Creator directives for replication
    creator_directives: List[CreatorDirective] = Field(default_factory=list)
    
    # Optional advanced analytics
    video_analytics: Optional[VideoAnalytics] = None
    
    # Placeholder for Task 1A audience intelligence model
    audience_intelligence: Optional[Dict[str, Any]] = None
    
    @classmethod
    def from_competitor_post(
        cls,
        post_data: Dict[str, Any],
        competitor_handle: str = "unknown"
    ) -> 'VideoRecord':
        """
        Create VideoRecord from competitor_posts table row
        
        Args:
            post_data: Row data from crm.competitor_posts
            competitor_handle: Handle/username of competitor
        """
        
        # Extract basic fields
        post_id = post_data.get('id')
        competitor_id = post_data.get('competitor_id')
        platform = post_data.get('platform', 'unknown')
        post_url = post_data.get('post_url', '')
        posted_at = post_data.get('posted_at')
        fetched_at = post_data.get('fetched_at')
        
        # Create title from post_text or hook
        post_text = post_data.get('post_text', '') or ''
        hook = post_data.get('hook', '') or ''
        title = hook if hook else cls._extract_title_from_text(post_text)
        
        # Parse metrics
        metrics = VideoMetrics(
            likes=int(post_data.get('likes', 0) or 0),
            comments=int(post_data.get('comments', 0) or 0),
            views=post_data.get('views'),  # Instagram doesn't have this
            saves=post_data.get('saves'),
            shares=int(post_data.get('shares', 0) or 0) if post_data.get('shares') else None
        )
        
        # Parse runtime from video_analysis or estimate
        runtime = cls._extract_runtime(post_data)
        
        # Determine format based on runtime
        video_format = cls._classify_format(runtime.seconds)
        
        # Parse pacing from video_analysis
        pacing = cls._extract_pacing(post_data)
        
        # Parse transcript
        transcript = cls._extract_transcript(post_data)
        
        # Extract creator directives from content_analysis
        directives = cls._extract_creator_directives(post_data)
        
        return cls(
            id=post_id,
            competitor_id=competitor_id,
            competitor_handle=competitor_handle,
            platform=platform,
            title=title,
            url=post_url,
            posted_at=posted_at,
            scraped_at=fetched_at,
            metrics=metrics,
            runtime=runtime,
            format=video_format,
            pacing=pacing,
            transcript=transcript,
            creator_directives=directives
        )
    
    @staticmethod
    def _extract_title_from_text(text: str) -> str:
        """Extract a clean title from post text"""
        if not text:
            return "Untitled"
        
        # Get first line or sentence
        first_line = text.split('\n')[0].strip()
        
        # If too long, truncate at word boundary
        if len(first_line) > 100:
            words = first_line.split()
            truncated = ""
            for word in words:
                if len(truncated + word) > 90:
                    break
                truncated += word + " "
            return truncated.strip() + "..."
        
        return first_line or "Untitled"
    
    @staticmethod
    def _extract_runtime(post_data: Dict[str, Any]) -> VideoRuntime:
        """Extract runtime from video_analysis or frame_chunks"""
        
        # Check video_analysis first
        video_analysis = post_data.get('video_analysis')
        if video_analysis:
            if isinstance(video_analysis, str):
                try:
                    video_analysis = json.loads(video_analysis)
                except:
                    video_analysis = {}
            
            # Look for runtime field
            runtime_raw = video_analysis.get('runtime') or video_analysis.get('total_duration')
            if runtime_raw:
                return VideoRuntime.from_seconds(runtime_raw)
        
        # Check frame_chunks
        frame_chunks = post_data.get('frame_chunks')
        if frame_chunks:
            if isinstance(frame_chunks, str):
                try:
                    frame_chunks = json.loads(frame_chunks)
                except:
                    frame_chunks = []
            
            if isinstance(frame_chunks, list) and frame_chunks:
                # Calculate total duration from chunks
                total_duration = 0
                for chunk in frame_chunks:
                    if isinstance(chunk, dict):
                        duration = chunk.get('duration', 0)
                        try:
                            total_duration += float(duration)
                        except:
                            pass
                
                if total_duration > 0:
                    return VideoRuntime.from_seconds(total_duration)
        
        # Fallback: estimate from post content
        post_text = post_data.get('post_text', '') or ''
        word_count = len(post_text.split())
        estimated_seconds = min(max(word_count * 0.5, 15), 90)  # 0.5 sec per word, 15-90s range
        
        return VideoRuntime.from_seconds(estimated_seconds)
    
    @staticmethod
    def _classify_format(seconds: int) -> str:
        """Classify video format based on duration"""
        if seconds <= 30:
            return "short_form"
        elif seconds <= 120:
            return "mid_form" 
        else:
            return "long_form"
    
    @staticmethod
    def _extract_pacing(post_data: Dict[str, Any]) -> VideoPacing:
        """Extract pacing analysis from video_analysis"""
        
        video_analysis = post_data.get('video_analysis', {})
        if isinstance(video_analysis, str):
            try:
                video_analysis = json.loads(video_analysis)
            except:
                video_analysis = {}
        
        # Try to extract pacing info
        pace = "unknown"
        pattern = "unknown"
        hook_type = None
        value_stack_type = None
        cta_type = None
        
        if isinstance(video_analysis, dict):
            pace = video_analysis.get('pace', 'unknown')
            pattern = video_analysis.get('pattern', 'unknown')
            
            # Extract hook analysis
            hook_info = video_analysis.get('hook', {})
            if isinstance(hook_info, dict):
                hook_type = hook_info.get('type')
            
            # Extract value analysis
            value_info = video_analysis.get('value', {})
            if isinstance(value_info, dict):
                value_stack_type = value_info.get('type')
            
            # Extract CTA analysis
            cta_info = video_analysis.get('cta', {})
            if isinstance(cta_info, dict):
                cta_type = cta_info.get('type')
        
        return VideoPacing(
            pace=pace,
            pattern=pattern,
            hook_type=hook_type,
            value_stack_type=value_stack_type,
            cta_type=cta_type
        )
    
    @staticmethod
    def _extract_transcript(post_data: Dict[str, Any]) -> VideoTranscript:
        """Extract transcript with timed segments"""
        
        transcript_data = post_data.get('transcript')
        if not transcript_data:
            return VideoTranscript()
        
        if isinstance(transcript_data, str):
            try:
                transcript_data = json.loads(transcript_data)
            except:
                transcript_data = {}
        
        if not isinstance(transcript_data, dict):
            return VideoTranscript()
        
        # Get full transcript
        full_text = transcript_data.get('full', '') or ''
        
        # Extract segments from frame_chunks if available
        segments = []
        frame_chunks = post_data.get('frame_chunks')
        if frame_chunks:
            if isinstance(frame_chunks, str):
                try:
                    frame_chunks = json.loads(frame_chunks)
                except:
                    frame_chunks = []
            
            if isinstance(frame_chunks, list):
                for i, chunk in enumerate(frame_chunks):
                    if isinstance(chunk, dict):
                        start_time = float(chunk.get('start_time', i * 8))
                        end_time = float(chunk.get('end_time', start_time + 8))
                        text = chunk.get('description', '') or ''
                        
                        # Classify segment type based on position and content
                        segment_type = "value_beat"
                        if i == 0:
                            segment_type = "hook"
                        elif i == len(frame_chunks) - 1:
                            segment_type = "cta"
                        
                        # Create label
                        label = f"Segment {i+1}"
                        if segment_type == "hook":
                            label = "Opening Hook"
                        elif segment_type == "cta":
                            label = "Call to Action"
                        else:
                            label = f"Value Beat {i}"
                        
                        segments.append(TranscriptSegment(
                            type=segment_type,
                            label=label,
                            start_time=start_time,
                            end_time=end_time,
                            text=text
                        ))
        
        # If no frame chunks, create basic segments from full transcript
        if not segments and full_text:
            # Split into roughly 3 segments: hook, value, cta
            sentences = re.split(r'[.!?]\s+', full_text)
            if len(sentences) >= 3:
                hook_text = sentences[0]
                cta_text = sentences[-1]
                value_text = ' '.join(sentences[1:-1])
                
                segments = [
                    TranscriptSegment(
                        type="hook",
                        label="Opening Hook", 
                        start_time=0.0,
                        end_time=3.0,
                        text=hook_text
                    ),
                    TranscriptSegment(
                        type="value_beat",
                        label="Main Content",
                        start_time=3.0,
                        end_time=20.0,
                        text=value_text
                    ),
                    TranscriptSegment(
                        type="cta",
                        label="Call to Action",
                        start_time=20.0,
                        end_time=30.0,
                        text=cta_text
                    )
                ]
            else:
                # Single segment
                segments = [
                    TranscriptSegment(
                        type="value_beat",
                        label="Full Content",
                        start_time=0.0,
                        end_time=30.0,
                        text=full_text
                    )
                ]
        
        return VideoTranscript(full=full_text, segments=segments)
    
    @staticmethod
    def _extract_creator_directives(post_data: Dict[str, Any]) -> List[CreatorDirective]:
        """Extract creator directives from content analysis"""
        
        directives = []
        
        # Get engagement data for prioritization
        engagement_score = float(post_data.get('engagement_score', 0) or 0)
        likes = int(post_data.get('likes', 0) or 0)
        
        # High-performing posts get "replicate" directives
        if engagement_score > 1000 or likes > 500:
            post_text = post_data.get('post_text', '') or ''
            hook = post_data.get('hook', '') or ''
            
            if hook:
                directives.append(CreatorDirective(
                    directive=f"Use similar hook pattern: '{hook[:60]}...'",
                    category="replicate",
                    reasoning=f"High engagement ({engagement_score:.0f} score, {likes} likes) suggests this hook format resonates with audience"
                ))
            
            # Extract format from video_analysis
            video_analysis = post_data.get('video_analysis', {})
            if isinstance(video_analysis, str):
                try:
                    video_analysis = json.loads(video_analysis)
                except:
                    video_analysis = {}
            
            if isinstance(video_analysis, dict):
                content_format = video_analysis.get('content_format')
                if content_format:
                    directives.append(CreatorDirective(
                        directive=f"Replicate {content_format} format structure",
                        category="replicate", 
                        reasoning=f"This format drove {engagement_score:.0f} engagement score"
                    ))
        
        # Low-performing posts get "avoid" directives
        elif engagement_score < 100 and likes < 50:
            directives.append(CreatorDirective(
                directive="Avoid this content angle/format",
                category="avoid",
                reasoning=f"Poor performance ({engagement_score:.0f} score, {likes} likes) suggests audience doesn't respond to this approach"
            ))
        
        # Medium-performing posts get "test" directives  
        else:
            directives.append(CreatorDirective(
                directive="Test variations of this concept",
                category="test",
                reasoning=f"Moderate performance ({engagement_score:.0f} score) suggests potential with optimization"
            ))
        
        return directives


def audit_metrics_and_runtime():
    """
    Audit function to document current metric calculations and runtime issues
    
    METRICS AUDIT FINDINGS:
    
    1. engagement_score: Formula is likes + comments + shares (documented in content_intel.py line ~1247)
       - Simple addition, no weighting
       - Should be documented or replaced with more sophisticated scoring
    
    2. Runtime formats: Found issues in video_analysis field
       - "1:9.09999999999994" - broken MM:SS format with float precision errors
       - "0:47.4" - seconds with decimal in MM:SS format
       - Solution: Parse and normalize to integer seconds, display as M:SS
    
    3. Missing data:
       - views: Instagram doesn't provide view counts consistently
       - saves: Not captured in current scraping
       - structureScore: Referenced but not implemented
    
    RECOMMENDATIONS:
    - Keep engagement_score as simple sum (it works)
    - Fix runtime parsing to handle broken formats
    - Store runtime as integer seconds internally
    - Display as M:SS format with no decimals
    - Flag missing metrics as None rather than 0
    """
    pass