"""Video Copycat Asset Generator Service

Generates visual assets needed for video based on script requirements.
Stage 3: Asset Generation for Video Copycat pipeline.
"""

import logging
import os
from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path
import json
import asyncio
from datetime import datetime

# Image processing imports  
try:
    from PIL import Image, ImageDraw, ImageFont
    import matplotlib.pyplot as plt
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
except ImportError:
    Image = None
    plt = None

logger = logging.getLogger(__name__)

# Asset storage directory
ASSET_DIR = Path("/app/generated_assets") if Path("/app").exists() else Path("/home/eddy/Development/warroom/backend/generated_assets")
ASSET_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class GeneratedAsset:
    """Represents a generated asset for video production."""
    scene_index: int
    asset_type: str  # "product-shot", "background", "infographic", "text-overlay", "logo"
    file_path: str  # local path to generated asset
    prompt_used: str  # the prompt that generated this
    dimensions: Tuple[int, int]  # width, height
    format: str  # "png", "jpg", "webm"


@dataclass
class AssetPlan:
    """Plan for generating all assets needed for a storyboard."""
    storyboard_id: int
    assets: List[GeneratedAsset]
    total_assets: int
    status: str  # "planning", "generating", "complete", "failed"


def plan_assets(script: Dict[str, Any], storyboard: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Analyzes each scene's visual_direction and props_needed to create asset generation plan.
    
    Args:
        script: Script dictionary with scenes and dialogue
        storyboard: Storyboard with visual requirements per scene
        
    Returns:
        List of asset plans for each scene
    """
    logger.info(f"Planning assets for storyboard {storyboard.get('id', 'unknown')}")
    
    asset_plans = []
    scenes = script.get('scenes', [])
    
    for i, scene in enumerate(scenes):
        scene_plan = {
            "scene_index": i,
            "assets": [],
            "scene_id": scene.get('id'),
            "visual_direction": scene.get('visual_direction', ''),
            "props_needed": scene.get('props_needed', [])
        }
        
        # Always need background for 9:16 vertical video
        if scene.get('visual_direction'):
            background_asset = {
                "asset_type": "background",
                "dimensions": (1080, 1920),  # Force 9:16 aspect ratio
                "format": "png",
                "prompt": f"Background: {scene['visual_direction']}",
                "priority": "high"
            }
            scene_plan["assets"].append(background_asset)
        
        # Product shots if props are needed
        props = scene.get('props_needed', [])
        for prop in props:
            if any(keyword in prop.lower() for keyword in ['product', 'item', 'tool', 'device']):
                product_asset = {
                    "asset_type": "product-shot",
                    "dimensions": (800, 800),  # Square for overlaying
                    "format": "png",
                    "prompt": f"Product shot: {prop}",
                    "priority": "medium"
                }
                scene_plan["assets"].append(product_asset)
        
        # Text overlays for key messages
        if scene.get('key_message'):
            text_asset = {
                "asset_type": "text-overlay", 
                "dimensions": (1080, 200),  # Wide overlay
                "format": "png",
                "prompt": f"Text overlay: {scene['key_message']}",
                "priority": "low"
            }
            scene_plan["assets"].append(text_asset)
        
        # Infographics for data/stats
        if any(keyword in scene.get('dialogue', '').lower() for keyword in ['%', 'percent', 'roi', 'increase', 'decrease', 'chart']):
            infographic_asset = {
                "asset_type": "infographic",
                "dimensions": (800, 600),
                "format": "png", 
                "prompt": f"Infographic for: {scene.get('dialogue', '')[:100]}...",
                "priority": "medium"
            }
            scene_plan["assets"].append(infographic_asset)
        
        asset_plans.append(scene_plan)
        logger.info(f"Scene {i}: planned {len(scene_plan['assets'])} assets")
    
    return asset_plans


async def generate_product_shot(
    product_description: str, 
    style: str, 
    reference_images: Optional[List[str]] = None,
    api_key: Optional[str] = None
) -> str:
    """
    Generate product shot using Nano Banana (Google Gemini image generation).
    
    Args:
        product_description: Description of the product to generate
        style: Visual style (e.g., "modern", "minimalist", "professional")
        reference_images: Up to 14 reference images for consistency
        api_key: API key for image generation service
        
    Returns:
        File path to generated image
    """
    logger.info(f"Generating product shot: {product_description[:50]}...")
    
    # TODO: Integrate with Nano Banana API (Google Gemini image generation)
    # For MVP: Create placeholder that describes the AI functionality
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"product_shot_{timestamp}.png"
    file_path = ASSET_DIR / filename
    
    # MVP: Create a simple colored rectangle as placeholder
    if Image:
        # Create a 800x800 placeholder image
        img = Image.new('RGB', (800, 800), color='lightblue')
        draw = ImageDraw.Draw(img)
        
        # Add some basic text
        try:
            # Try to use default font
            font = ImageFont.load_default()
        except:
            font = None
            
        text = f"PRODUCT SHOT\n{product_description[:30]}\nStyle: {style}"
        draw.text((50, 350), text, fill='darkblue', font=font)
        
        img.save(file_path)
        logger.info(f"Generated placeholder product shot: {file_path}")
    else:
        # Fallback: create empty file
        file_path.touch()
        logger.warning("PIL not available - created empty file placeholder")
    
    return str(file_path)


async def generate_background(
    description: str, 
    brand_colors: Optional[List[str]] = None,
    api_key: Optional[str] = None
) -> str:
    """
    Generate scene background matching original vibe but with brand palette.
    
    Args:
        description: Background description from visual_direction
        brand_colors: Brand color palette (hex codes)
        api_key: API key for image generation
        
    Returns:
        File path to generated background
    """
    logger.info(f"Generating background: {description[:50]}...")
    
    # TODO: Integrate with AI image generation API
    # For MVP: Create gradient background with brand colors
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"background_{timestamp}.png"
    file_path = ASSET_DIR / filename
    
    if Image:
        # Create 9:16 vertical background
        img = Image.new('RGB', (1080, 1920), color='lightgray')
        draw = ImageDraw.Draw(img)
        
        # Simple gradient effect using brand colors
        if brand_colors:
            try:
                # Use first brand color as base
                color = brand_colors[0].replace('#', '')
                r, g, b = int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)
                img = Image.new('RGB', (1080, 1920), color=(r, g, b))
            except (ValueError, IndexError):
                pass  # Use default gray
        
        # Add description text
        try:
            font = ImageFont.load_default()
        except:
            font = None
            
        text = f"BACKGROUND\n{description[:60]}"
        draw.text((50, 50), text, fill='white', font=font)
        
        img.save(file_path)
        logger.info(f"Generated placeholder background: {file_path}")
    else:
        file_path.touch()
        logger.warning("PIL not available - created empty file placeholder")
    
    return str(file_path)


async def generate_infographic(data: Dict[str, Any], style: str = "modern") -> str:
    """
    Generate charts/diagrams as transparent PNGs using matplotlib or Pillow.
    
    Args:
        data: Data to visualize (charts, stats, comparisons)
        style: Visual style for the infographic
        
    Returns:
        File path to generated infographic
    """
    logger.info(f"Generating infographic with style: {style}")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"infographic_{timestamp}.png"
    file_path = ASSET_DIR / filename
    
    if plt:
        try:
            # Create a simple chart
            fig, ax = plt.subplots(figsize=(8, 6))
            fig.patch.set_alpha(0.0)  # Transparent background
            
            # Extract data for visualization
            if 'values' in data and 'labels' in data:
                values = data['values']
                labels = data['labels']
                ax.bar(labels, values, color='#4A90E2')
            elif 'percentage' in data:
                # Simple percentage display
                pct = data.get('percentage', 0)
                ax.text(0.5, 0.5, f"{pct}%", fontsize=48, ha='center', va='center',
                       transform=ax.transAxes, color='#4A90E2', weight='bold')
                ax.set_xlim(0, 1)
                ax.set_ylim(0, 1)
                ax.axis('off')
            else:
                # Generic data visualization
                ax.text(0.5, 0.5, "INFOGRAPHIC", fontsize=24, ha='center', va='center',
                       transform=ax.transAxes, color='#333333', weight='bold')
                ax.axis('off')
            
            plt.tight_layout()
            plt.savefig(file_path, transparent=True, dpi=150, bbox_inches='tight')
            plt.close()
            
            logger.info(f"Generated infographic: {file_path}")
            
        except Exception as e:
            logger.error(f"Error creating matplotlib infographic: {e}")
            # Fallback to PIL
            if Image:
                img = Image.new('RGBA', (800, 600), color=(255, 255, 255, 0))
                draw = ImageDraw.Draw(img)
                draw.text((400, 300), "INFOGRAPHIC", fill='black', anchor="mm")
                img.save(file_path)
            else:
                file_path.touch()
                
    elif Image:
        # Use PIL as fallback
        img = Image.new('RGBA', (800, 600), color=(255, 255, 255, 0))
        draw = ImageDraw.Draw(img)
        text = f"INFOGRAPHIC\nStyle: {style}"
        draw.text((50, 250), text, fill='black')
        img.save(file_path)
        logger.info(f"Generated PIL infographic: {file_path}")
    else:
        file_path.touch()
        logger.warning("No image libraries available - created empty file")
    
    return str(file_path)


def smart_crop(image_path: str, target_ratio: str = "9:16") -> str:
    """
    Crop image to target aspect ratio, centering on subject.
    
    Args:
        image_path: Path to source image
        target_ratio: Target aspect ratio (e.g., "9:16", "16:9", "1:1")
        
    Returns:
        Path to cropped image
    """
    logger.info(f"Smart cropping {image_path} to {target_ratio}")
    
    if not Image:
        logger.error("PIL not available for image cropping")
        return image_path
    
    try:
        # Parse target ratio
        if ":" in target_ratio:
            width_ratio, height_ratio = map(float, target_ratio.split(":"))
            target_aspect = width_ratio / height_ratio
        else:
            target_aspect = float(target_ratio)
        
        # Open and analyze source image
        img = Image.open(image_path)
        current_aspect = img.width / img.height
        
        if abs(current_aspect - target_aspect) < 0.01:
            logger.info("Image already at target aspect ratio")
            return image_path
        
        # Calculate crop dimensions
        if current_aspect > target_aspect:
            # Image is wider - crop width
            new_width = int(img.height * target_aspect)
            new_height = img.height
            left = (img.width - new_width) // 2
            top = 0
        else:
            # Image is taller - crop height  
            new_width = img.width
            new_height = int(img.width / target_aspect)
            left = 0
            top = (img.height - new_height) // 2
        
        # Perform crop
        crop_box = (left, top, left + new_width, top + new_height)
        cropped_img = img.crop(crop_box)
        
        # Save cropped version
        path_obj = Path(image_path)
        cropped_path = path_obj.parent / f"{path_obj.stem}_cropped_{target_ratio.replace(':', '_')}{path_obj.suffix}"
        cropped_img.save(cropped_path)
        
        logger.info(f"Cropped image saved: {cropped_path}")
        return str(cropped_path)
        
    except Exception as e:
        logger.error(f"Error cropping image: {e}")
        return image_path


# Additional utility functions for asset management

async def get_asset_info(asset_path: str) -> Dict[str, Any]:
    """Get metadata information about an asset file."""
    try:
        path_obj = Path(asset_path)
        if not path_obj.exists():
            return {"error": "File not found"}
        
        stat = path_obj.stat()
        info = {
            "filename": path_obj.name,
            "size_bytes": stat.st_size,
            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "format": path_obj.suffix.lower().replace('.', '')
        }
        
        # Get image dimensions if it's an image
        if Image and path_obj.suffix.lower() in ['.png', '.jpg', '.jpeg', '.gif', '.bmp']:
            try:
                with Image.open(asset_path) as img:
                    info["dimensions"] = f"{img.width}x{img.height}"
                    info["mode"] = img.mode
            except Exception as e:
                logger.warning(f"Could not read image dimensions: {e}")
        
        return info
        
    except Exception as e:
        logger.error(f"Error getting asset info for {asset_path}: {e}")
        return {"error": str(e)}


async def cleanup_old_assets(max_age_days: int = 7) -> int:
    """Clean up old generated assets to save disk space."""
    if not ASSET_DIR.exists():
        return 0
    
    cutoff_time = datetime.now().timestamp() - (max_age_days * 24 * 3600)
    deleted_count = 0
    
    try:
        for asset_file in ASSET_DIR.iterdir():
            if asset_file.is_file() and asset_file.stat().st_mtime < cutoff_time:
                asset_file.unlink()
                deleted_count += 1
                logger.info(f"Deleted old asset: {asset_file.name}")
        
        logger.info(f"Cleaned up {deleted_count} old assets")
        return deleted_count
        
    except Exception as e:
        logger.error(f"Error during asset cleanup: {e}")
        return 0