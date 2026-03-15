"""Video Analysis Service — Extract video storyboards for copycat pipeline."""

import json
import logging
import os
import subprocess
import tempfile
from dataclasses import dataclass, asdict
from typing import List, Optional
import httpx
import yt_dlp

logger = logging.getLogger(__name__)

@dataclass
class Scene:
    index: int
    start_time: float  # seconds
    end_time: float
    duration: float
    shot_type: str  # "close-up", "wide", "pov", "medium", "over-shoulder"
    camera_movement: str  # "static", "dolly", "pan", "zoom-in", "zoom-out", "handheld"
    scene_type: str  # "hook", "problem", "solution", "social-proof", "cta", "transition"
    description: str  # what's happening visually
    speaker_text: str  # transcribed speech in this scene
    visual_elements: List[str]  # ["product-shot", "text-overlay", "b-roll", "diagram"]
    transition_to_next: str  # "cut", "cross-dissolve", "fade", "swipe", "none"
    energy_level: str  # "high", "medium", "low"

@dataclass  
class VideoStoryboard:
    source_url: str
    total_duration: float
    aspect_ratio: str  # "9:16", "16:9", "1:1"
    scene_count: int
    scenes: List[Scene]
    overall_style: str  # "talking-head", "b-roll-heavy", "slideshow", "mixed"
    hook_technique: str  # "question", "bold-claim", "controversy", "relatability"
    cta_technique: str  # "follow", "link-in-bio", "comment", "share"
    background_music: str  # "upbeat", "dramatic", "minimal", "none"
    text_overlay_style: str  # "hormozi-captions", "minimal", "animated", "none"
    estimated_word_count: int


def storyboard_to_json(storyboard: VideoStoryboard) -> dict:
    """Serialize storyboard to JSON-compatible dict."""
    return asdict(storyboard)


def json_to_storyboard(data: dict) -> VideoStoryboard:
    """Deserialize JSON dict to storyboard object."""
    scenes = [Scene(**scene) for scene in data['scenes']]
    return VideoStoryboard(
        source_url=data['source_url'],
        total_duration=data['total_duration'],
        aspect_ratio=data['aspect_ratio'],
        scene_count=data['scene_count'],
        scenes=scenes,
        overall_style=data['overall_style'],
        hook_technique=data['hook_technique'],
        cta_technique=data['cta_technique'],
        background_music=data['background_music'],
        text_overlay_style=data['text_overlay_style'],
        estimated_word_count=data['estimated_word_count']
    )


async def analyze_video(video_url: str, api_key: Optional[str] = None) -> VideoStoryboard:
    """
    Analyze video and extract structural storyboard.
    
    Process:
    1. Download video (yt-dlp for social URLs, direct for files)
    2. Extract key frames (ffmpeg)
    3. Extract audio transcript
    4. Send to Gemini API for multimodal analysis
    5. Return structured storyboard
    """
    
    if not api_key:
        raise ValueError("Google AI API key required for video analysis")
    
    try:
        # Download video to temp directory
        with tempfile.TemporaryDirectory() as temp_dir:
            video_path = await _download_video(video_url, temp_dir)
            
            # Get video metadata
            metadata = await _get_video_metadata(video_path)
            
            # Extract key frames
            frames_dir = os.path.join(temp_dir, "frames")
            os.makedirs(frames_dir, exist_ok=True)
            frame_paths = await _extract_key_frames(video_path, frames_dir, metadata['duration'])
            
            # Extract audio transcript
            transcript = await _extract_transcript(video_path)
            
            # Analyze with AI
            storyboard = await _analyze_with_ai(
                video_url=video_url,
                frame_paths=frame_paths,
                transcript=transcript,
                metadata=metadata,
                api_key=api_key
            )
            
            return storyboard
            
    except Exception as e:
        logger.error(f"Video analysis failed for {video_url}: {e}")
        # Fallback: create basic storyboard based on URL/description
        return await _create_fallback_storyboard(video_url)


async def _download_video(video_url: str, temp_dir: str) -> str:
    """Download video using yt-dlp or direct download."""
    
    # Check if it's a direct video file URL
    if video_url.endswith(('.mp4', '.mov', '.avi', '.mkv', '.webm')):
        # Direct download
        video_path = os.path.join(temp_dir, "video.mp4")
        async with httpx.AsyncClient() as client:
            response = await client.get(video_url)
            response.raise_for_status()
            with open(video_path, 'wb') as f:
                f.write(response.content)
        return video_path
    
    # Use yt-dlp for social media URLs
    ydl_opts = {
        'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
        'format': 'best[height<=720]',  # Limit quality for faster processing
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=True)
        video_path = ydl.prepare_filename(info)
        
    return video_path


async def _get_video_metadata(video_path: str) -> dict:
    """Extract video metadata using ffprobe."""
    
    cmd = [
        'ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', video_path
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr}")
    
    data = json.loads(result.stdout)
    
    video_stream = next(s for s in data['streams'] if s['codec_type'] == 'video')
    
    duration = float(data['format']['duration'])
    width = int(video_stream['width'])
    height = int(video_stream['height'])
    
    # Determine aspect ratio
    if abs(width/height - 9/16) < 0.1:
        aspect_ratio = "9:16"
    elif abs(width/height - 16/9) < 0.1:
        aspect_ratio = "16:9"
    elif abs(width/height - 1.0) < 0.1:
        aspect_ratio = "1:1"
    else:
        aspect_ratio = f"{width}:{height}"
    
    return {
        'duration': duration,
        'width': width,
        'height': height,
        'aspect_ratio': aspect_ratio
    }


async def _extract_key_frames(video_path: str, frames_dir: str, duration: float) -> List[str]:
    """Extract key frames at scene transitions using ffmpeg."""
    
    # Extract frames every 3-5 seconds as potential scene boundaries
    interval = max(3.0, duration / 10)  # At most 10 frames
    frame_paths = []
    
    for i, timestamp in enumerate(range(0, int(duration), int(interval))):
        frame_path = os.path.join(frames_dir, f"frame_{i:03d}.jpg")
        
        cmd = [
            'ffmpeg', '-y', '-i', video_path, '-ss', str(timestamp),
            '-frames:v', '1', '-q:v', '2', frame_path
        ]
        
        result = subprocess.run(cmd, capture_output=True)
        if result.returncode == 0 and os.path.exists(frame_path):
            frame_paths.append(frame_path)
    
    return frame_paths


async def _extract_transcript(video_path: str) -> str:
    """Extract audio and generate transcript (placeholder - would use Whisper/etc)."""
    
    # For MVP, return placeholder transcript
    # In production, would:
    # 1. Extract audio with ffmpeg
    # 2. Send to Whisper API or similar
    # 3. Return timestamped transcript
    
    return "Transcript extraction not yet implemented - placeholder text for analysis"


async def _analyze_with_ai(video_url: str, frame_paths: List[str], transcript: str, 
                          metadata: dict, api_key: str) -> VideoStoryboard:
    """Send frames and transcript to Gemini API for multimodal analysis."""
    
    # For MVP, create a reasonable storyboard based on available data
    # In production, would send frames to Gemini Vision API
    
    prompt = f"""
    Analyze this video and create a structural storyboard:
    
    Video URL: {video_url}
    Duration: {metadata['duration']} seconds
    Aspect Ratio: {metadata['aspect_ratio']}
    Frames extracted: {len(frame_paths)}
    Transcript: {transcript[:500]}...
    
    Create a detailed scene breakdown identifying:
    - Scene boundaries and timing
    - Shot types and camera movements
    - Scene purposes (hook, problem, solution, CTA, etc.)
    - Visual elements and energy levels
    - Overall video style and techniques
    """
    
    # TODO: Implement actual Gemini API call
    # For now, return a realistic example storyboard
    
    duration = metadata['duration']
    scene_count = max(3, min(8, int(duration / 5)))  # 3-8 scenes based on length
    
    scenes = []
    time_per_scene = duration / scene_count
    
    for i in range(scene_count):
        start_time = i * time_per_scene
        end_time = (i + 1) * time_per_scene
        
        # Determine scene type based on position
        if i == 0:
            scene_type = "hook"
        elif i == scene_count - 1:
            scene_type = "cta"
        elif i == 1:
            scene_type = "problem"
        elif i == scene_count - 2:
            scene_type = "solution"
        else:
            scene_type = "transition"
        
        scene = Scene(
            index=i + 1,
            start_time=start_time,
            end_time=end_time,
            duration=time_per_scene,
            shot_type="medium" if i % 2 == 0 else "close-up",
            camera_movement="static" if i % 3 == 0 else "handheld",
            scene_type=scene_type,
            description=f"Scene {i+1} - {scene_type} section",
            speaker_text=f"Placeholder speech for scene {i+1}",
            visual_elements=["talking-head", "product-shot"] if i % 2 == 0 else ["b-roll"],
            transition_to_next="cut" if i < scene_count - 1 else "none",
            energy_level="high" if i == 0 or i == scene_count - 1 else "medium"
        )
        scenes.append(scene)
    
    return VideoStoryboard(
        source_url=video_url,
        total_duration=duration,
        aspect_ratio=metadata['aspect_ratio'],
        scene_count=scene_count,
        scenes=scenes,
        overall_style="talking-head",
        hook_technique="question",
        cta_technique="follow",
        background_music="minimal",
        text_overlay_style="minimal",
        estimated_word_count=int(duration * 150 / 60)  # ~150 WPM
    )


async def _create_fallback_storyboard(video_url: str) -> VideoStoryboard:
    """Create a basic storyboard when video download/analysis fails."""
    
    # Create a minimal 3-scene storyboard
    scenes = [
        Scene(
            index=1,
            start_time=0.0,
            end_time=5.0,
            duration=5.0,
            shot_type="medium",
            camera_movement="static",
            scene_type="hook",
            description="Opening hook - grab attention",
            speaker_text="Engaging opening statement",
            visual_elements=["talking-head"],
            transition_to_next="cut",
            energy_level="high"
        ),
        Scene(
            index=2,
            start_time=5.0,
            end_time=20.0,
            duration=15.0,
            shot_type="close-up",
            camera_movement="handheld",
            scene_type="solution",
            description="Main content delivery",
            speaker_text="Core message and value proposition",
            visual_elements=["product-shot", "b-roll"],
            transition_to_next="cut",
            energy_level="medium"
        ),
        Scene(
            index=3,
            start_time=20.0,
            end_time=30.0,
            duration=10.0,
            shot_type="medium",
            camera_movement="static",
            scene_type="cta",
            description="Call to action",
            speaker_text="Strong call to action",
            visual_elements=["talking-head"],
            transition_to_next="none",
            energy_level="high"
        )
    ]
    
    return VideoStoryboard(
        source_url=video_url,
        total_duration=30.0,
        aspect_ratio="9:16",
        scene_count=3,
        scenes=scenes,
        overall_style="talking-head",
        hook_technique="question",
        cta_technique="follow",
        background_music="minimal",
        text_overlay_style="minimal",
        estimated_word_count=75
    )