"""Video Copycat Avatar Service

Manages digital doubles — user avatars and voice clones.
Stage 4: Avatar Swap for Video Copycat pipeline.
"""

import logging
import os
import asyncio
import tempfile
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from pathlib import Path
import json
from datetime import datetime
import subprocess

# Audio processing
try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False
    edge_tts = None

# Image/video processing
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = None

logger = logging.getLogger(__name__)

# Asset storage
_BASE = Path("/app/generated_assets") if Path("/app").exists() else Path("/home/eddy/Development/warroom/backend/generated_assets")
AVATAR_DIR = _BASE / "avatars"
AVATAR_DIR.mkdir(parents=True, exist_ok=True)
VOICE_DIR = _BASE / "voice" 
VOICE_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class DigitalCopy:
    """Represents a user's digital double configuration."""
    user_id: int
    org_id: int
    avatar_images: List[str]  # reference photos
    voice_clone_id: str  # voice clone identifier
    voice_provider: str  # "elevenlabs", "google-tts", "edge-tts"
    default_style: str  # "professional", "casual", "energetic"


async def get_digital_copy(db, org_id: int, user_id: int) -> Optional[Dict[str, Any]]:
    """
    Retrieve user's digital copy info from database.
    
    Args:
        db: Database session
        org_id: Organization ID
        user_id: User ID
        
    Returns:
        Digital copy data or None if not found
    """
    try:
        from sqlalchemy import text
        
        query = text("""
            SELECT id, org_id, user_id, avatar_images, voice_clone_id, 
                   voice_provider, default_style, created_at, updated_at
            FROM crm.digital_copies 
            WHERE org_id = :org_id AND user_id = :user_id
        """)
        
        result = await db.execute(query, {"org_id": org_id, "user_id": user_id})
        row = result.fetchone()
        
        if not row:
            logger.info(f"No digital copy found for org {org_id}, user {user_id}")
            return None
        
        return {
            "id": row.id,
            "org_id": row.org_id,
            "user_id": row.user_id,
            "avatar_images": row.avatar_images,
            "voice_clone_id": row.voice_clone_id,
            "voice_provider": row.voice_provider,
            "default_style": row.default_style,
            "created_at": row.created_at,
            "updated_at": row.updated_at
        }
        
    except Exception as e:
        logger.error(f"Error retrieving digital copy: {e}")
        return None


async def generate_voice_audio(
    text: str, 
    voice_clone_id: str, 
    emotion: str = "neutral"
) -> str:
    """
    Generate speech audio from text using voice clone.
    
    Args:
        text: Text to convert to speech
        voice_clone_id: Voice clone identifier (or voice name for TTS)
        emotion: Emotion/style for the voice ("neutral", "excited", "calm")
        
    Returns:
        File path to generated audio file
    """
    logger.info(f"Generating voice audio for text: {text[:50]}...")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"voice_{timestamp}.mp3"
    file_path = VOICE_DIR / filename
    
    # For MVP: Use edge-tts as free fallback
    if EDGE_TTS_AVAILABLE:
        try:
            # Map emotion to edge-tts voice style
            voice_map = {
                "neutral": "en-US-AvaNeural",
                "excited": "en-US-JennyNeural", 
                "calm": "en-US-AriaNeural",
                "professional": "en-US-AvaNeural"
            }
            
            voice = voice_map.get(emotion, "en-US-AvaNeural")
            if voice_clone_id and voice_clone_id in voice_map:
                voice = voice_clone_id
            
            # Generate audio using edge-tts
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(str(file_path))
            
            logger.info(f"Generated voice audio using edge-tts: {file_path}")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"Edge-TTS generation failed: {e}")
    
    # Fallback: Create silent audio file placeholder
    try:
        # Create 3-second silent MP3 using ffmpeg if available
        silence_path = file_path.with_suffix('.wav')
        cmd = [
            'ffmpeg', '-f', 'lavfi', '-i', 'anullsrc=r=22050:cl=mono', 
            '-t', '3', '-y', str(silence_path)
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        
        # Convert to MP3
        cmd = ['ffmpeg', '-i', str(silence_path), '-y', str(file_path)]
        subprocess.run(cmd, check=True, capture_output=True)
        
        # Clean up WAV
        silence_path.unlink()
        
        logger.info(f"Generated silent audio placeholder: {file_path}")
        return str(file_path)
        
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Ultimate fallback: empty file
        file_path.touch()
        logger.warning("Created empty audio file placeholder")
        return str(file_path)


async def generate_avatar_video(
    script_scene: Dict[str, Any],
    avatar_images: List[str],
    audio_path: str,
    api_key: Optional[str] = None
) -> str:
    """
    Generate avatar video with lip-sync using reference images and audio.
    
    Args:
        script_scene: Scene data with dialogue and visual direction
        avatar_images: Reference images of the user's face
        audio_path: Path to audio file for lip-sync
        api_key: API key for video generation service
        
    Returns:
        File path to generated video or generation job ID
    """
    logger.info(f"Generating avatar video for scene: {script_scene.get('id', 'unknown')}")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"avatar_video_{timestamp}.mp4"
    file_path = AVATAR_DIR / filename
    
    # TODO: Integration with Veo 3.1 for neural avatar rendering with lip-sync
    # For MVP: This is a placeholder describing the AI functionality
    
    """
    In production, this function would:
    1. Upload avatar reference images to Veo 3.1 API
    2. Upload audio file for lip-sync analysis
    3. Send generation request with scene context:
       - Character description from script_scene
       - Emotion/style from scene
       - Background requirements
       - Camera angles/framing
    4. Poll for generation completion
    5. Download and return video file path
    
    Veo 3.1 capabilities:
    - Neural lip-sync from audio
    - Consistent character generation from reference photos
    - 9:16 vertical video format
    - High-quality realistic rendering
    - Emotion and style control
    """
    
    # MVP: Create placeholder video description
    placeholder_info = {
        "scene_id": script_scene.get('id'),
        "dialogue": script_scene.get('dialogue', ''),
        "visual_direction": script_scene.get('visual_direction', ''),
        "emotion": script_scene.get('emotion', 'neutral'),
        "avatar_references": len(avatar_images),
        "audio_duration": "unknown",  # Would analyze audio file
        "target_format": "9:16 vertical video",
        "ai_features": [
            "Neural lip-sync from audio",
            "Photorealistic avatar from reference images", 
            "Scene-appropriate emotions and gestures",
            "Consistent character across scenes"
        ]
    }
    
    # Save placeholder metadata
    metadata_path = file_path.with_suffix('.json')
    with open(metadata_path, 'w') as f:
        json.dump(placeholder_info, f, indent=2)
    
    # Create basic video file placeholder using ffmpeg if available
    try:
        if Path(audio_path).exists():
            # Create static image video with audio
            duration_cmd = ['ffprobe', '-v', 'quiet', '-show_entries', 
                          'format=duration', '-of', 'csv=p=0', audio_path]
            result = subprocess.run(duration_cmd, capture_output=True, text=True)
            duration = float(result.stdout.strip()) if result.stdout.strip() else 3.0
        else:
            duration = 3.0
        
        # Create placeholder image
        if PIL_AVAILABLE:
            img = Image.new('RGB', (1080, 1920), color='lightblue')
            placeholder_img = file_path.with_suffix('.png')
            img.save(placeholder_img)
        else:
            placeholder_img = None
        
        # Generate video
        if placeholder_img and placeholder_img.exists():
            cmd = [
                'ffmpeg', '-loop', '1', '-i', str(placeholder_img),
                '-i', audio_path, '-t', str(duration),
                '-c:v', 'libx264', '-c:a', 'aac', '-y', str(file_path)
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            placeholder_img.unlink()  # Clean up temp image
            
            logger.info(f"Generated placeholder avatar video: {file_path}")
        else:
            # Just copy audio as fallback
            import shutil
            shutil.copy2(audio_path, file_path.with_suffix('.mp3'))
            logger.info(f"Created audio placeholder: {file_path}")
            
    except (subprocess.CalledProcessError, FileNotFoundError, Exception) as e:
        logger.error(f"Video generation failed: {e}")
        # Ultimate fallback: empty file
        file_path.touch()
        
    return str(file_path)


async def compose_scene(
    avatar_video: str,
    background: str,
    text_overlay: Optional[str] = None,
    product_shot: Optional[str] = None
) -> str:
    """
    Layer avatar on background with optional overlays using basic compositing.
    
    Args:
        avatar_video: Path to avatar video file
        background: Path to background image
        text_overlay: Optional text overlay image
        product_shot: Optional product shot overlay
        
    Returns:
        File path to composed final video
    """
    logger.info(f"Composing scene with avatar: {Path(avatar_video).name}")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = AVATAR_DIR / f"composed_scene_{timestamp}.mp4"
    
    # For MVP: Use Pillow/ffmpeg for basic compositing
    try:
        # Build ffmpeg command for video composition
        cmd = ['ffmpeg']
        
        # Input files
        cmd.extend(['-i', avatar_video])  # Avatar video (input 0)
        cmd.extend(['-i', background])    # Background (input 1)
        
        input_index = 2
        filter_complex = []
        
        # Scale background to 1080x1920 (9:16)
        filter_complex.append(f"[1:v]scale=1080:1920[bg]")
        
        # Overlay avatar on background
        filter_complex.append(f"[bg][0:v]overlay=0:0[comp]")
        current_output = "comp"
        
        # Add product shot overlay if provided
        if product_shot and Path(product_shot).exists():
            cmd.extend(['-i', product_shot])
            filter_complex.append(f"[{input_index}:v]scale=400:400[prod]")
            filter_complex.append(f"[{current_output}][prod]overlay=W-w-50:50[comp2]")
            current_output = "comp2"
            input_index += 1
        
        # Add text overlay if provided
        if text_overlay and Path(text_overlay).exists():
            cmd.extend(['-i', text_overlay])
            filter_complex.append(f"[{current_output}][{input_index}:v]overlay=0:H-h-100[final]")
            current_output = "final"
        
        # Apply filter complex
        cmd.extend(['-filter_complex', ';'.join(filter_complex)])
        cmd.extend(['-map', f'[{current_output}]'])
        
        # Include audio from avatar video
        cmd.extend(['-map', '0:a?'])  # Optional audio from avatar
        
        # Output settings
        cmd.extend(['-c:v', 'libx264', '-c:a', 'aac', '-y', str(output_path)])
        
        # Execute composition
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info(f"Scene composed successfully: {output_path}")
            return str(output_path)
        else:
            logger.error(f"FFmpeg composition failed: {result.stderr}")
            
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        logger.error(f"Scene composition failed: {e}")
    
    # Fallback: Just copy avatar video
    try:
        import shutil
        shutil.copy2(avatar_video, output_path)
        logger.info(f"Fallback: copied avatar video as composed scene")
        return str(output_path)
    except Exception as e:
        logger.error(f"Fallback composition failed: {e}")
        output_path.touch()
        return str(output_path)


# Additional utility functions

async def validate_avatar_images(image_paths: List[str]) -> Dict[str, Any]:
    """Validate avatar reference images for quality and format."""
    validation_results = {
        "valid_images": [],
        "invalid_images": [],
        "total_count": len(image_paths),
        "issues": []
    }
    
    if not PIL_AVAILABLE:
        validation_results["issues"].append("PIL not available for image validation")
        return validation_results
    
    for img_path in image_paths:
        try:
            path_obj = Path(img_path)
            if not path_obj.exists():
                validation_results["invalid_images"].append(img_path)
                validation_results["issues"].append(f"File not found: {img_path}")
                continue
            
            with Image.open(img_path) as img:
                # Check format
                if img.format.lower() not in ['jpeg', 'jpg', 'png']:
                    validation_results["invalid_images"].append(img_path)
                    validation_results["issues"].append(f"Unsupported format: {img.format}")
                    continue
                
                # Check dimensions (should be reasonable size)
                if img.width < 200 or img.height < 200:
                    validation_results["invalid_images"].append(img_path)
                    validation_results["issues"].append(f"Image too small: {img.width}x{img.height}")
                    continue
                
                # Check if image is too large (>5MB)
                file_size = path_obj.stat().st_size
                if file_size > 5 * 1024 * 1024:
                    validation_results["invalid_images"].append(img_path)
                    validation_results["issues"].append(f"Image too large: {file_size / 1024 / 1024:.1f}MB")
                    continue
                
                validation_results["valid_images"].append(img_path)
                
        except Exception as e:
            validation_results["invalid_images"].append(img_path)
            validation_results["issues"].append(f"Error processing {img_path}: {str(e)}")
    
    logger.info(f"Avatar validation: {len(validation_results['valid_images'])}/{len(image_paths)} images valid")
    return validation_results


async def get_available_voices(provider: str = "edge-tts") -> List[Dict[str, str]]:
    """Get list of available voices for the specified provider."""
    voices = []
    
    if provider == "edge-tts" and EDGE_TTS_AVAILABLE:
        try:
            voice_list = await edge_tts.list_voices()
            for voice in voice_list:
                if voice["Locale"].startswith("en-"):  # English voices only
                    voices.append({
                        "id": voice["ShortName"],
                        "name": voice["FriendlyName"],
                        "locale": voice["Locale"],
                        "gender": voice["Gender"]
                    })
        except Exception as e:
            logger.error(f"Error fetching edge-tts voices: {e}")
    
    # Fallback default voices
    if not voices:
        voices = [
            {"id": "en-US-AvaNeural", "name": "Ava (Professional)", "locale": "en-US", "gender": "Female"},
            {"id": "en-US-JennyNeural", "name": "Jenny (Excited)", "locale": "en-US", "gender": "Female"},
            {"id": "en-US-AriaNeural", "name": "Aria (Calm)", "locale": "en-US", "gender": "Female"}
        ]
    
    return voices


async def estimate_generation_cost(
    scenes_count: int,
    avg_duration_seconds: int = 30,
    provider: str = "veo"
) -> Dict[str, Any]:
    """Estimate cost for generating avatar videos."""
    # MVP: Return placeholder cost estimates
    costs = {
        "provider": provider,
        "scenes_count": scenes_count,
        "avg_duration_seconds": avg_duration_seconds,
        "total_duration_minutes": (scenes_count * avg_duration_seconds) / 60,
        "estimated_cost_usd": 0.0,  # MVP: Free
        "currency": "USD",
        "breakdown": {
            "voice_generation": 0.0,
            "avatar_rendering": 0.0,
            "scene_composition": 0.0
        },
        "note": "MVP uses free tools (edge-tts, ffmpeg). Production would use paid AI services."
    }
    
    # TODO: Add real cost calculation for production services
    # - ElevenLabs voice cloning: ~$0.30/1K characters
    # - Veo video generation: ~$0.05/second
    # - Additional processing costs
    
    return costs