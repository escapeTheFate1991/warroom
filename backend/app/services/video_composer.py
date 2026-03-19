"""Video Composer Service — Remotion-style video composition.

Assembles generated assets into final video using Remotion configuration
format. Provides ffmpeg fallback when Remotion isn't available.
"""

import json
import logging
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union

logger = logging.getLogger(__name__)


@dataclass
class CompositionLayer:
    """Individual layer in video composition."""
    type: str  # "avatar-video", "background", "product-shot", "text-overlay", "audio"
    asset_path: str
    start_time: float  # seconds
    end_time: float
    position: Dict[str, Union[int, float]]  # {"x": 0, "y": 0, "width": 1080, "height": 1920}
    opacity: float  # 0.0 - 1.0
    transition_in: str  # "cut", "fade", "slide-left"
    transition_out: str
    z_index: int  # layer order

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "asset_path": self.asset_path,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "position": self.position,
            "opacity": self.opacity,
            "transition_in": self.transition_in,
            "transition_out": self.transition_out,
            "z_index": self.z_index,
        }


@dataclass
class Composition:
    """Complete video composition with all layers."""
    storyboard_id: int
    duration: float
    width: int  # 1080
    height: int  # 1920
    fps: int  # 30
    layers: List[CompositionLayer]
    audio_track: str  # background music path
    caption_style: str  # "hormozi", "minimal", "animated"

    def to_dict(self) -> dict:
        return {
            "storyboard_id": self.storyboard_id,
            "duration": self.duration,
            "width": self.width,
            "height": self.height,
            "fps": self.fps,
            "layers": [layer.to_dict() for layer in self.layers],
            "audio_track": self.audio_track,
            "caption_style": self.caption_style,
        }


def build_composition(storyboard: dict, script: dict, assets: List[dict]) -> Composition:
    """
    Build composition from storyboard, script, and assets.
    
    Args:
        storyboard: Storyboard data with scenes and timing
        script: Script with text overlays and timing
        assets: List of generated assets (avatar videos, backgrounds, product shots)
        
    Returns:
        Complete Composition ready for rendering
    """
    logger.info(f"Building composition for storyboard {storyboard.get('id', 'unknown')}")
    
    # Extract basic composition properties
    scenes = storyboard.get("scenes", [])
    duration = sum(scene.get("duration", 3.0) for scene in scenes)
    
    composition = Composition(
        storyboard_id=storyboard.get("id", 0),
        duration=duration,
        width=1080,
        height=1920,
        fps=30,
        layers=[],
        audio_track="",
        caption_style=storyboard.get("caption_style", "hormozi")
    )
    
    current_time = 0.0
    z_index = 1
    
    # Process each scene
    for scene_idx, scene in enumerate(scenes):
        scene_duration = scene.get("duration", 3.0)
        scene_start = current_time
        scene_end = current_time + scene_duration
        
        # Add scene image/video as background layer for this scene
        scene_asset = _find_asset(assets, "scene_image", scene_idx) or _find_asset(assets, "scene_video", scene_idx)
        if scene_asset and scene_asset["path"]:
            composition.layers.append(CompositionLayer(
                type="background",
                asset_path=scene_asset["path"],
                start_time=scene_start,
                end_time=scene_end,
                position={"x": 0, "y": 0, "width": 1080, "height": 1920},
                opacity=1.0,
                transition_in="fade" if scene_idx > 0 else "cut",
                transition_out="fade",
                z_index=z_index
            ))
            z_index += 1
        
        # Add product shot if specified in scene
        if scene.get("show_product"):
            product_asset = _find_asset(assets, "product-shot", scene_idx)
            if product_asset:
                composition.layers.append(CompositionLayer(
                    type="product-shot",
                    asset_path=product_asset["path"],
                    start_time=scene_start + 1.0,  # Delay product reveal
                    end_time=scene_end,
                    position={"x": 20, "y": 20, "width": 300, "height": 300},  # Top-left corner
                    opacity=0.9,
                    transition_in="slide-left",
                    transition_out="fade",
                    z_index=z_index
                ))
                z_index += 1
        
        # Add text overlays from script for this scene
        scene_script = script.get("scenes", {}).get(str(scene_idx), {})
        if scene_script.get("text"):
            composition.layers.append(CompositionLayer(
                type="text-overlay",
                asset_path="",  # Generated inline
                start_time=scene_start,
                end_time=scene_end,
                position={"x": 50, "y": 100, "width": 980, "height": 200},  # Top area
                opacity=1.0,
                transition_in="fade",
                transition_out="fade",
                z_index=z_index
            ))
            z_index += 1
        
        current_time += scene_duration
    
    # Add background audio track if available
    audio_asset = _find_asset(assets, "background-music", 0)
    if audio_asset:
        composition.audio_track = audio_asset["path"]
    
    logger.info(f"Built composition with {len(composition.layers)} layers, duration {duration}s")
    return composition


def _find_asset(assets: List[dict], asset_type: str, scene_idx: int) -> Optional[dict]:
    """Find asset by type and scene index."""
    for asset in assets:
        # Check metadata for index if scene_index not at top level
        asset_index = asset.get("scene_index") or asset.get("metadata", {}).get("index")
        if (asset.get("type") == asset_type and asset_index == scene_idx):
            return {"path": asset.get("url", "")}
    
    # Fallback: find first asset of this type
    for asset in assets:
        if asset.get("type") == asset_type:
            return {"path": asset.get("url", "")}
    
    return None


def generate_remotion_config(composition: Composition) -> dict:
    """
    Convert Composition to Remotion-compatible JSON props.
    
    Args:
        composition: Video composition
        
    Returns:
        JSON config that can be sent to Remotion renderer
    """
    logger.info(f"Generating Remotion config for composition {composition.storyboard_id}")
    
    # Convert layers to Remotion format
    remotion_layers = []
    for layer in composition.layers:
        remotion_layer = {
            "id": f"layer_{layer.z_index}",
            "type": layer.type,
            "src": layer.asset_path if layer.asset_path else None,
            "from": int(layer.start_time * composition.fps),
            "durationInFrames": int((layer.end_time - layer.start_time) * composition.fps),
            "style": {
                "left": layer.position.get("x", 0),
                "top": layer.position.get("y", 0),
                "width": layer.position.get("width", composition.width),
                "height": layer.position.get("height", composition.height),
                "opacity": layer.opacity,
                "zIndex": layer.z_index
            },
            "transitions": {
                "in": layer.transition_in,
                "out": layer.transition_out
            }
        }
        
        # Add text-specific properties
        if layer.type == "text-overlay":
            remotion_layer["textContent"] = "{{scene_text}}"  # Placeholder for dynamic text
            remotion_layer["fontSize"] = 72 if composition.caption_style == "hormozi" else 48
            remotion_layer["fontWeight"] = "bold" if composition.caption_style == "hormozi" else "normal"
            remotion_layer["textAlign"] = "center"
            remotion_layer["color"] = "#FFFFFF"
            remotion_layer["strokeWidth"] = 4 if composition.caption_style == "hormozi" else 2
            remotion_layer["strokeColor"] = "#000000"
        
        remotion_layers.append(remotion_layer)
    
    config = {
        "id": f"video_copycat_{composition.storyboard_id}",
        "width": composition.width,
        "height": composition.height,
        "fps": composition.fps,
        "durationInFrames": int(composition.duration * composition.fps),
        "props": {
            "layers": remotion_layers,
            "audioTrack": composition.audio_track,
            "captionStyle": composition.caption_style
        }
    }
    
    logger.info(f"Generated Remotion config with {len(remotion_layers)} layers")
    return config


def render_with_ffmpeg(composition: Composition) -> str:
    """
    MVP fallback: Use ffmpeg to composite layers when Remotion isn't available.
    
    Args:
        composition: Video composition
        
    Returns:
        Path to rendered video file
    """
    logger.info(f"Rendering composition {composition.storyboard_id} with ffmpeg")
    
    # Check if ffmpeg is available
    if not _check_ffmpeg():
        logger.warning("ffmpeg not available for video rendering, skipping composition")
        raise RuntimeError("ffmpeg not available for video rendering")
    
    # Create temporary directory for processing
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        output_path = temp_path / f"video_{composition.storyboard_id}.mp4"
        
        # Sort layers by z-index for proper layering
        sorted_layers = sorted(composition.layers, key=lambda x: x.z_index)
        
        # Build ffmpeg filter chain
        filter_complex = _build_ffmpeg_filter(composition, sorted_layers, temp_path)
        
        # Prepare input files
        input_files = []
        downloaded_files = []  # Track downloaded files for cleanup
        
        for layer in sorted_layers:
            if not layer.asset_path:
                continue
                
            asset_path = layer.asset_path
            
            # Check if asset is a URL that needs downloading
            if asset_path.startswith(("http://", "https://")):
                try:
                    import httpx
                    import asyncio
                    
                    # Download to temp file
                    temp_file = temp_path / f"asset_{len(downloaded_files)}.{asset_path.split('.')[-1]}"
                    
                    async def download_asset():
                        async with httpx.AsyncClient() as client:
                            resp = await client.get(asset_path)
                            resp.raise_for_status()
                            with open(temp_file, "wb") as f:
                                f.write(resp.content)
                    
                    # Run download in sync context
                    asyncio.run(download_asset())
                    downloaded_files.append(temp_file)
                    asset_path = str(temp_file)
                    
                except Exception as download_err:
                    logger.warning(f"Failed to download asset {layer.asset_path}: {download_err}")
                    continue
            
            # Check if local file exists
            if Path(asset_path).exists():
                input_files.extend(["-i", asset_path])
        
        # Add background audio if available
        if composition.audio_track and Path(composition.audio_track).exists():
            input_files.extend(["-i", composition.audio_track])
        
        # Build complete ffmpeg command
        cmd = [
            "ffmpeg", "-y",  # Overwrite output
            *input_files,
            "-filter_complex", filter_complex,
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "128k",
            "-t", str(composition.duration),
            str(output_path)
        ]
        
        logger.info(f"Running ffmpeg command: {' '.join(cmd[:10])}...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            logger.error(f"ffmpeg failed: {result.stderr}")
            raise RuntimeError(f"Video rendering failed: {result.stderr}")
        
        # Move rendered video to permanent location
        final_path = f"/tmp/rendered_video_{composition.storyboard_id}_{int(datetime.now().timestamp())}.mp4"
        shutil.move(str(output_path), final_path)
        
        logger.info(f"Video rendered successfully to {final_path}")
        return final_path


def _check_ffmpeg() -> bool:
    """Check if ffmpeg is available."""
    try:
        result = subprocess.run(["ffmpeg", "-version"], 
                              capture_output=True, timeout=5)
        return result.returncode == 0
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


def _build_ffmpeg_filter(composition: Composition, layers: List[CompositionLayer], temp_path: Path) -> str:
    """Build ffmpeg filter_complex string for layering."""
    filters = []
    current_output = ""
    
    # Start with base canvas
    filters.append(f"color=black:{composition.width}x{composition.height}:d={composition.duration}[base]")
    current_output = "[base]"
    
    input_idx = 0
    for layer in layers:
        if not layer.asset_path or not Path(layer.asset_path).exists():
            continue
            
        layer_output = f"[layer{layer.z_index}]"
        
        # Scale and position this layer
        pos_x = layer.position.get("x", 0)
        pos_y = layer.position.get("y", 0)
        width = layer.position.get("width", composition.width)
        height = layer.position.get("height", composition.height)
        
        if layer.type in ["avatar-video", "background", "product-shot"]:
            # Video/image layer
            filters.append(f"[{input_idx}]scale={width}:{height}[scaled{input_idx}]")
            filters.append(f"{current_output}[scaled{input_idx}]overlay={pos_x}:{pos_y}:enable='between(t,{layer.start_time},{layer.end_time})'[out{layer.z_index}]")
            current_output = f"[out{layer.z_index}]"
            input_idx += 1
    
    return ";".join(filters)


def add_captions(video_path: str, script: dict, style: str = "hormozi") -> str:
    """
    Add captions to rendered video using ffmpeg drawtext filter.
    
    Args:
        video_path: Path to input video
        script: Script with text and timing
        style: Caption style ("hormozi", "minimal", "animated")
        
    Returns:
        Path to captioned video
    """
    logger.info(f"Adding {style} captions to video {video_path}")
    
    if not _check_ffmpeg():
        raise RuntimeError("ffmpeg not available for caption burning")
    
    if not Path(video_path).exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")
    
    # Generate output path
    input_path = Path(video_path)
    output_path = input_path.with_suffix(f".captioned{input_path.suffix}")
    
    # Build drawtext filters for each scene
    drawtext_filters = []
    current_time = 0.0
    
    scenes = script.get("scenes", {})
    for scene_idx, scene_data in scenes.items():
        scene_text = scene_data.get("text", "")
        scene_duration = scene_data.get("duration", 3.0)
        
        if not scene_text:
            current_time += scene_duration
            continue
        
        # Style-specific formatting
        if style == "hormozi":
            font_size = 72
            font_color = "white"
            border_width = 4
            border_color = "black"
            font_weight = "bold"
        elif style == "minimal":
            font_size = 48
            font_color = "white"
            border_width = 2
            border_color = "black"
            font_weight = "normal"
        else:  # animated
            font_size = 56
            font_color = "yellow"
            border_width = 3
            border_color = "black"
            font_weight = "bold"
        
        # Escape text for ffmpeg
        escaped_text = scene_text.replace(":", r"\:")
        
        drawtext_filter = (
            f"drawtext=text='{escaped_text}':"
            f"x=(w-text_w)/2:y=h/8:"  # Centered horizontally, top area
            f"fontsize={font_size}:"
            f"fontcolor={font_color}:"
            f"borderw={border_width}:"
            f"bordercolor={border_color}:"
            f"enable='between(t,{current_time},{current_time + scene_duration})'"
        )
        
        drawtext_filters.append(drawtext_filter)
        current_time += scene_duration
    
    if not drawtext_filters:
        logger.warning("No captions to add, returning original video")
        return video_path
    
    # Combine all drawtext filters
    filter_complex = ",".join(drawtext_filters)
    
    # Run ffmpeg command
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vf", filter_complex,
        "-c:a", "copy",  # Copy audio without re-encoding
        str(output_path)
    ]
    
    logger.info(f"Adding captions with ffmpeg...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    
    if result.returncode != 0:
        logger.error(f"Caption burning failed: {result.stderr}")
        raise RuntimeError(f"Caption burning failed: {result.stderr}")
    
    logger.info(f"Captions added successfully to {output_path}")
    return str(output_path)


def auto_level_audio(avatar_path: str, background_path: str, output_path: str) -> None:
    """
    Auto-level avatar speech vs background music using ffmpeg.
    
    Args:
        avatar_path: Path to avatar video/audio
        background_path: Path to background music
        output_path: Path for output audio
    """
    if not _check_ffmpeg():
        raise RuntimeError("ffmpeg not available for audio leveling")
    
    # Extract audio from avatar video and normalize levels
    cmd = [
        "ffmpeg", "-y",
        "-i", avatar_path,
        "-i", background_path,
        "-filter_complex",
        "[0:a]volume=1.0[speech];[1:a]volume=0.3[music];[speech][music]amix=inputs=2:duration=shortest",
        "-c:a", "aac",
        "-b:a", "192k",
        output_path
    ]
    
    logger.info("Auto-leveling audio tracks...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    
    if result.returncode != 0:
        logger.error(f"Audio leveling failed: {result.stderr}")
        raise RuntimeError(f"Audio leveling failed: {result.stderr}")
    
    logger.info(f"Audio leveled successfully: {output_path}")