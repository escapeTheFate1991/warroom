"""Editing DNA Service — Visual Format Extraction for Remotion Templates.

Extract visual layout structures from competitor videos and store them as reusable Remotion templates.
The "Visual Grammar Parser" that analyzes video layouts and converts them to standardized JSON schemas.
"""

import json
import logging
import os
import uuid
import base64
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════
# SCHEMA DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════

EDITING_DNA_SCHEMA = {
    "layout_id": "split_vertical_v1",
    "meta": {
        "composition_type": "educational_commentary",
        "aspect_ratio": "9:16",
        "source_reference_id": "competitor_clip_001"
    },
    "layers": [
        {
            "role": "visual_subject",
            "position": {"top": 0, "height": "50%", "width": "100%"},
            "source_type": "veo_generated_environment",
            "z_index": 1,
            "effects": ["subtle_zoom_in"]
        },
        {
            "role": "digital_twin_anchor",
            "position": {"bottom": 0, "height": "50%", "width": "100%"},
            "source_type": "veo_generated_character",
            "z_index": 2,
            "mask": "rounded_corners_lg"
        }
    ],
    "audio_logic": {
        "primary_track": "digital_twin_voiceover",
        "ducking": {"bg_music_volume": 0.1},
        "auto_captions": {"style": "bold_yellow_centered", "y_offset": "75%"}
    },
    "timing_dna": {
        "hook_duration_frames": 90,
        "transition_style": "hard_cut",
        "b_roll_frequency": "every_5_seconds"
    }
}

# Role mapping for visual layout analysis
ROLE_TO_SOURCE_TYPE = {
    "talking_head": "veo_generated_character",
    "talking head": "veo_generated_character", 
    "speaker": "veo_generated_character",
    "person": "veo_generated_character",
    "character": "veo_generated_character",
    "anchor": "veo_generated_character",
    "host": "veo_generated_character",
    "presenter": "veo_generated_character",
    "facecam": "veo_generated_character",
    "face": "veo_generated_character",
    
    "product": "veo_generated_environment",
    "environment": "veo_generated_environment",
    "background": "veo_generated_environment",
    "scene": "veo_generated_environment",
    "location": "veo_generated_environment",
    "setting": "veo_generated_environment",
    "content": "veo_generated_environment",
    "main_video": "veo_generated_environment",
    "footage": "veo_generated_environment",
    "b_roll": "veo_generated_environment",
    "broll": "veo_generated_environment",
    
    "text": "text_overlay",
    "caption": "text_overlay",
    "subtitle": "text_overlay",
    "overlay": "text_overlay",
    "title": "text_overlay",
    "label": "text_overlay",
}

LAYOUT_TO_REMOTION_COMPOSITION = {
    "split_vertical": "SplitScreen",
    "split_horizontal": "SplitScreen", 
    "pip": "ProductShowcase",
    "fullscreen": "UniversalTemplate",
    "floating_bubble": "ProductShowcase",
    "side_by_side": "SplitScreen",
    "picture_in_picture": "ProductShowcase",
    "reaction": "ProductShowcase",
}

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"

# DDL for editing_dna table
EDITING_DNA_DDL = """
CREATE TABLE IF NOT EXISTS crm.editing_dna (
    id SERIAL PRIMARY KEY,
    org_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    source_post_id INTEGER REFERENCES crm.competitor_posts(id),
    layout_type TEXT NOT NULL,  -- 'split_vertical', 'split_horizontal', 'pip', 'fullscreen', 'floating_bubble'
    aspect_ratio TEXT DEFAULT '9:16',
    layers JSONB NOT NULL DEFAULT '[]',
    audio_logic JSONB DEFAULT '{}',
    timing_dna JSONB DEFAULT '{}',
    remotion_composition TEXT,  -- which Remotion component to use
    zod_schema JSONB DEFAULT '{}',
    thumbnail_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
"""

# ═══════════════════════════════════════════════════════════════════════
# INITIALIZATION
# ═══════════════════════════════════════════════════════════════════════

async def _get_api_key(db: Optional[AsyncSession] = None) -> str:
    """Get Google AI Studio API key from environment or database"""
    # Try environment variable first
    key = os.environ.get('GOOGLE_AI_STUDIO_API_KEY')
    if key:
        return key
    
    # Fall back to database setting
    if db:
        try:
            result = await db.execute(text("SELECT value FROM public.settings WHERE key = 'google_ai_studio_api_key'"))
            row = result.first()
            if row and row[0]:
                return row[0]
        except Exception as e:
            logger.error(f"Failed to get Google API key from database: {e}")
    
    raise ValueError("Google AI Studio API key not configured. Add it in Settings.")


async def init_editing_dna_table(db: AsyncSession):
    """Initialize the editing_dna table if it doesn't exist."""
    try:
        await db.execute(text(EDITING_DNA_DDL))
        await db.commit()
        logger.info("Editing DNA table initialized")
    except Exception as e:
        logger.warning(f"Error initializing editing DNA table: {e}")
        await db.rollback()

# ═══════════════════════════════════════════════════════════════════════
# CORE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════

async def extract_visual_layout(video_url: str, api_key: str) -> Dict[str, Any]:
    """
    Use Gemini 3 Flash to analyze video/thumbnail for visual layout.
    
    Args:
        video_url: URL to video or image (thumbnail)
        api_key: Google AI Studio API key
    
    Returns:
        Raw layout data from Gemini analysis
    """
    
    # Determine if this is an image or video
    is_image = any(video_url.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.webp'])
    media_type = "image" if is_image else "video"
    
    # Build the analysis prompt
    prompt = f"""Analyze this {media_type} for its visual layout structure. 

Identify every distinct visual panel, layer, or region. For each element:

1. **Role**: What is this element? (talking_head, product, environment, text_overlay, etc.)
2. **Coordinates**: Position as percentages (top, bottom, left, right, width, height)
3. **Z-Index**: Layering order (1=background, higher=foreground)
4. **Motion**: Type of movement or animation (zoom_in, static, pan, etc.)

Special focus on:
- Split-screen layouts (vertical/horizontal divisions)
- Picture-in-picture (small floating elements)
- Text overlays and captions
- Background vs foreground elements

Return as JSON with this structure:
{{
    "layout_type": "split_vertical|split_horizontal|pip|fullscreen|floating_bubble",
    "aspect_ratio": "9:16|16:9|1:1",
    "elements": [
        {{
            "role": "talking_head",
            "coordinates": {{"top": 0, "left": 0, "width": "100%", "height": "50%"}},
            "z_index": 2,
            "motion_type": "subtle_zoom_in",
            "description": "Person speaking directly to camera"
        }}
    ]
}}

Be precise with coordinates and identify the primary layout pattern."""

    try:
        # Prepare the request based on media type
        if is_image:
            # For images, we can send them directly
            mime_type = "image/jpeg"
            if video_url.lower().endswith('.png'):
                mime_type = "image/png"
            elif video_url.lower().endswith('.webp'):
                mime_type = "image/webp"
            
            # Download the image
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(video_url)
                if resp.status_code != 200:
                    raise Exception(f"Failed to download image: {resp.status_code}")
                
                image_data = base64.b64encode(resp.content).decode()
                
                # Prepare Gemini request
                payload = {
                    "contents": [
                        {
                            "parts": [
                                {"text": prompt},
                                {
                                    "inline_data": {
                                        "mime_type": mime_type,
                                        "data": image_data
                                    }
                                }
                            ]
                        }
                    ],
                    "generationConfig": {
                        "temperature": 0.2,
                        "maxOutputTokens": 2048
                    }
                }
                
                # Use Gemini 2.0 Flash for image analysis
                gen_url = f"{GEMINI_API_BASE}/models/gemini-2.0-flash:generateContent"
                
                resp = await client.post(gen_url, params={"key": api_key}, json=payload)
                
        else:
            # For videos, we'll analyze the first frame as an image for now
            # In a full implementation, you'd use Gemini's video analysis
            # For this MVP, we'll extract a frame and analyze that
            raise Exception("Video analysis not yet implemented - please provide thumbnail URL")
        
        # Handle rate limiting
        if resp.status_code == 429:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=429,
                detail="Google AI rate limit reached. Please wait a moment and try again."
            )
        
        # Handle quota exhaustion
        response_text = resp.text.lower()
        if "quota" in response_text or "exceeded" in response_text:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=402,
                detail="Google AI billing quota exceeded. Check your billing at https://ai.google.dev"
            )
            
        if resp.status_code != 200:
            logger.error(f"Gemini API error: {resp.status_code} {resp.text}")
            from fastapi import HTTPException
            raise HTTPException(
                status_code=502,
                detail=f"Gemini analysis failed: {resp.text[:200]}"
            )
        
        # Parse response
        data = resp.json()
        content = data.get("candidates", [{}])[0].get("content", {})
        text_response = ""
        
        for part in content.get("parts", []):
            if "text" in part:
                text_response += part["text"]
        
        if not text_response:
            raise Exception("Empty response from Gemini")
        
        # Clean up the response and parse JSON
        cleaned_response = text_response.strip()
        if cleaned_response.startswith("```json"):
            cleaned_response = cleaned_response[7:]
        if cleaned_response.endswith("```"):
            cleaned_response = cleaned_response[:-3]
        cleaned_response = cleaned_response.strip()
        
        try:
            layout_data = json.loads(cleaned_response)
            logger.info(f"Successfully analyzed {media_type} layout: {layout_data.get('layout_type', 'unknown')}")
            return layout_data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini JSON response: {e}")
            logger.error(f"Raw response: {text_response[:500]}")
            # Return a fallback structure
            return {
                "layout_type": "fullscreen",
                "aspect_ratio": "9:16",
                "elements": [
                    {
                        "role": "talking_head",
                        "coordinates": {"top": 0, "left": 0, "width": "100%", "height": "100%"},
                        "z_index": 1,
                        "motion_type": "static",
                        "description": "Full screen content"
                    }
                ],
                "raw_response": text_response
            }
            
    except Exception as e:
        logger.error(f"Error in extract_visual_layout: {e}")
        raise


async def synthesize_editing_dna(raw_layout: Dict[str, Any], source_post_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Convert Gemini's raw layout analysis to standardized Editing DNA schema.
    
    Args:
        raw_layout: Raw output from Gemini analysis
        source_post_id: ID of the competitor post this came from
        
    Returns:
        Complete Editing DNA JSON structure
    """
    
    layout_type = raw_layout.get("layout_type", "fullscreen")
    aspect_ratio = raw_layout.get("aspect_ratio", "9:16")
    elements = raw_layout.get("elements", [])
    
    # Generate unique layout ID
    layout_id = f"{layout_type}_{uuid.uuid4().hex[:8]}"
    
    # Build layers from elements
    layers = []
    for idx, element in enumerate(elements):
        role = element.get("role", "unknown").lower()
        coordinates = element.get("coordinates", {})
        
        # Map role to source_type
        source_type = ROLE_TO_SOURCE_TYPE.get(role, "veo_generated_environment")
        
        # Convert coordinates to our format
        position = {}
        if "top" in coordinates:
            if isinstance(coordinates["top"], str) and coordinates["top"].endswith("%"):
                position["top"] = coordinates["top"]
            else:
                position["top"] = f"{coordinates['top']}%"
                
        if "left" in coordinates:
            if isinstance(coordinates["left"], str) and coordinates["left"].endswith("%"):
                position["left"] = coordinates["left"]
            else:
                position["left"] = f"{coordinates['left']}%"
                
        if "width" in coordinates:
            position["width"] = coordinates["width"]
        else:
            position["width"] = "100%"
            
        if "height" in coordinates:
            position["height"] = coordinates["height"]
        else:
            position["height"] = "100%"
            
        # Handle bottom positioning
        if "bottom" in coordinates:
            if isinstance(coordinates["bottom"], str) and coordinates["bottom"].endswith("%"):
                position["bottom"] = coordinates["bottom"]
            else:
                position["bottom"] = f"{coordinates['bottom']}%"
        
        # Extract effects from motion_type
        motion = element.get("motion_type", "static")
        effects = []
        if motion and motion != "static":
            effects = [motion]
            
        layer = {
            "role": role,
            "position": position,
            "source_type": source_type,
            "z_index": element.get("z_index", idx + 1),
            "effects": effects
        }
        
        # Add mask for floating elements
        if "pip" in layout_type or "floating" in layout_type or source_type == "veo_generated_character":
            layer["mask"] = "rounded_corners_lg"
            
        layers.append(layer)
    
    # Determine composition type
    composition_type = "educational_commentary"
    if any(layer["role"] == "product" for layer in layers):
        composition_type = "product_showcase"
    elif layout_type in ["side_by_side", "split_horizontal"]:
        composition_type = "before_after"
    
    # Build the complete Editing DNA
    dna = {
        "layout_id": layout_id,
        "meta": {
            "composition_type": composition_type,
            "aspect_ratio": aspect_ratio,
            "source_reference_id": f"competitor_clip_{source_post_id}" if source_post_id else f"manual_{uuid.uuid4().hex[:8]}"
        },
        "layers": layers,
        "audio_logic": {
            "primary_track": "digital_twin_voiceover",
            "ducking": {"bg_music_volume": 0.1},
            "auto_captions": {"style": "bold_yellow_centered", "y_offset": "75%"}
        },
        "timing_dna": {
            "hook_duration_frames": 90,
            "transition_style": "hard_cut",
            "b_roll_frequency": "every_5_seconds"
        }
    }
    
    logger.info(f"Synthesized DNA for layout_type: {layout_type}, {len(layers)} layers")
    return dna


async def process_competitor_for_dna(
    db: AsyncSession, 
    post_id: int, 
    org_id: int, 
    api_key: str
) -> Dict[str, Any]:
    """
    Full pipeline: load competitor post → extract layout → synthesize DNA → save to DB.
    
    Args:
        db: Database session
        post_id: Competitor post ID
        org_id: Organization ID
        api_key: Google AI Studio API key
        
    Returns:
        Saved DNA record with ID
    """
    
    # Load the competitor post
    result = await db.execute(text("""
        SELECT id, media_url, thumbnail_url, post_text, handle, platform
        FROM crm.competitor_posts 
        WHERE id = :post_id
    """), {"post_id": post_id})
    
    post = result.mappings().first()
    if not post:
        raise Exception(f"Competitor post {post_id} not found")
    
    # Determine which URL to analyze (prefer thumbnail for consistency)
    analyze_url = post["thumbnail_url"] or post["media_url"]
    if not analyze_url:
        raise Exception(f"No media URL found for post {post_id}")
    
    # Extract visual layout
    raw_layout = await extract_visual_layout(analyze_url, api_key)
    
    # Synthesize to Editing DNA
    dna = await synthesize_editing_dna(raw_layout, post_id)
    
    # Generate name and description
    name = f"{post['handle']} - {dna['meta']['composition_type']}"
    description = f"Extracted from {post['platform']} post"
    if post["post_text"]:
        description += f": {post['post_text'][:100]}..."
    
    # Determine Remotion composition
    layout_type = dna["layout_id"].split("_")[0] if "_" in dna["layout_id"] else raw_layout.get("layout_type", "fullscreen")
    remotion_composition = LAYOUT_TO_REMOTION_COMPOSITION.get(layout_type, "UniversalTemplate")
    
    # Save to database
    result = await db.execute(text("""
        INSERT INTO crm.editing_dna (
            org_id, name, description, source_post_id, layout_type, aspect_ratio,
            layers, audio_logic, timing_dna, remotion_composition, thumbnail_url
        ) VALUES (
            :org_id, :name, :description, :source_post_id, :layout_type, :aspect_ratio,
            :layers::jsonb, :audio_logic::jsonb, :timing_dna::jsonb, :remotion_composition, :thumbnail_url
        ) RETURNING id
    """), {
        "org_id": org_id,
        "name": name,
        "description": description,
        "source_post_id": post_id,
        "layout_type": layout_type,
        "aspect_ratio": dna["meta"]["aspect_ratio"],
        "layers": json.dumps(dna["layers"]),
        "audio_logic": json.dumps(dna["audio_logic"]),
        "timing_dna": json.dumps(dna["timing_dna"]),
        "remotion_composition": remotion_composition,
        "thumbnail_url": post["thumbnail_url"]
    })
    
    dna_id = result.scalar()
    await db.commit()
    
    logger.info(f"Saved Editing DNA {dna_id} from competitor post {post_id}")
    
    return {
        "id": dna_id,
        "name": name,
        "layout_type": layout_type,
        "dna": dna
    }


def map_dna_to_remotion_config(dna: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert Editing DNA to Remotion-compatible props.
    
    Args:
        dna: Complete Editing DNA structure
        
    Returns:
        Config that can be passed to Remotion UniversalTemplate
    """
    
    layers = dna.get("layers", [])
    audio_logic = dna.get("audio_logic", {})
    timing_dna = dna.get("timing_dna", {})
    meta = dna.get("meta", {})
    
    # Build Remotion layers
    remotion_layers = []
    
    for layer in layers:
        position = layer.get("position", {})
        
        # Convert percentages to pixel values for 1080x1920 (9:16)
        width = 1080
        height = 1920
        
        # Parse position values
        def parse_position_value(value, dimension_size):
            if isinstance(value, str):
                if value.endswith('%'):
                    return int(float(value[:-1]) / 100 * dimension_size)
                else:
                    return int(value)
            return int(value)
        
        layer_config = {
            "id": f"layer_{layer.get('z_index', 1)}",
            "type": layer.get("source_type", "veo_generated_environment"),
            "z_index": layer.get("z_index", 1),
            "position": {
                "x": parse_position_value(position.get("left", "0%"), width),
                "y": parse_position_value(position.get("top", "0%"), height),
                "width": parse_position_value(position.get("width", "100%"), width),
                "height": parse_position_value(position.get("height", "100%"), height)
            },
            "effects": layer.get("effects", []),
            "role": layer.get("role", "content")
        }
        
        # Add mask if specified
        if layer.get("mask"):
            layer_config["mask"] = layer["mask"]
            
        remotion_layers.append(layer_config)
    
    # Build timing configuration
    timing_config = {
        "total_duration_frames": 900,  # 30 seconds at 30fps
        "hook_duration_frames": timing_dna.get("hook_duration_frames", 90),
        "transition_style": timing_dna.get("transition_style", "hard_cut")
    }
    
    # Build audio configuration
    audio_config = {
        "primary_track": audio_logic.get("primary_track", "digital_twin_voiceover"),
        "ducking": audio_logic.get("ducking", {"bg_music_volume": 0.1})
    }
    
    # Add captions config
    if "auto_captions" in audio_logic:
        audio_config["captions"] = audio_logic["auto_captions"]
    
    return {
        "composition_type": meta.get("composition_type", "educational_commentary"),
        "aspect_ratio": meta.get("aspect_ratio", "9:16"),
        "layers": remotion_layers,
        "timing": timing_config,
        "audio": audio_config,
        "layout_id": dna.get("layout_id", "unknown")
    }


# ═══════════════════════════════════════════════════════════════════════
# PREDEFINED DNA TEMPLATES
# ═══════════════════════════════════════════════════════════════════════

DEFAULT_DNA_TEMPLATES = [
    {
        "name": "Fullscreen Talking Head",
        "description": "Single layer, full screen digital character",
        "layout_type": "fullscreen",
        "dna": {
            "layout_id": "fullscreen_talking_head",
            "meta": {
                "composition_type": "direct_address",
                "aspect_ratio": "9:16",
                "source_reference_id": "template_default"
            },
            "layers": [
                {
                    "role": "digital_twin_anchor",
                    "position": {"top": "0%", "left": "0%", "width": "100%", "height": "100%"},
                    "source_type": "veo_generated_character",
                    "z_index": 1,
                    "effects": ["subtle_breathing"]
                }
            ],
            "audio_logic": {
                "primary_track": "digital_twin_voiceover",
                "ducking": {"bg_music_volume": 0.05},
                "auto_captions": {"style": "bold_yellow_centered", "y_offset": "80%"}
            },
            "timing_dna": {
                "hook_duration_frames": 60,
                "transition_style": "fade",
                "b_roll_frequency": "never"
            }
        }
    },
    {
        "name": "Split Vertical",
        "description": "Top: environment, Bottom: talking head",
        "layout_type": "split_vertical",
        "dna": {
            "layout_id": "split_vertical",
            "meta": {
                "composition_type": "educational_commentary",
                "aspect_ratio": "9:16",
                "source_reference_id": "template_default"
            },
            "layers": [
                {
                    "role": "visual_subject",
                    "position": {"top": "0%", "left": "0%", "width": "100%", "height": "50%"},
                    "source_type": "veo_generated_environment",
                    "z_index": 1,
                    "effects": ["subtle_zoom_in"]
                },
                {
                    "role": "digital_twin_anchor",
                    "position": {"top": "50%", "left": "0%", "width": "100%", "height": "50%"},
                    "source_type": "veo_generated_character",
                    "z_index": 2,
                    "effects": ["subtle_breathing"],
                    "mask": "rounded_corners_lg"
                }
            ],
            "audio_logic": {
                "primary_track": "digital_twin_voiceover",
                "ducking": {"bg_music_volume": 0.1},
                "auto_captions": {"style": "bold_yellow_centered", "y_offset": "75%"}
            },
            "timing_dna": {
                "hook_duration_frames": 90,
                "transition_style": "hard_cut",
                "b_roll_frequency": "every_5_seconds"
            }
        }
    },
    {
        "name": "PiP Bottom Right",
        "description": "Full screen content + small floating face cam",
        "layout_type": "pip",
        "dna": {
            "layout_id": "pip_bottom_right",
            "meta": {
                "composition_type": "reaction_overlay",
                "aspect_ratio": "9:16",
                "source_reference_id": "template_default"
            },
            "layers": [
                {
                    "role": "main_content",
                    "position": {"top": "0%", "left": "0%", "width": "100%", "height": "100%"},
                    "source_type": "veo_generated_environment",
                    "z_index": 1,
                    "effects": []
                },
                {
                    "role": "reaction_cam",
                    "position": {"top": "70%", "left": "70%", "width": "25%", "height": "25%"},
                    "source_type": "veo_generated_character",
                    "z_index": 2,
                    "effects": ["subtle_breathing"],
                    "mask": "rounded_corners_xl"
                }
            ],
            "audio_logic": {
                "primary_track": "digital_twin_voiceover",
                "ducking": {"bg_music_volume": 0.2},
                "auto_captions": {"style": "bold_white_bottom", "y_offset": "85%"}
            },
            "timing_dna": {
                "hook_duration_frames": 60,
                "transition_style": "cut",
                "b_roll_frequency": "every_3_seconds"
            }
        }
    },
    {
        "name": "Side by Side",
        "description": "Left: before, Right: after",
        "layout_type": "side_by_side",
        "dna": {
            "layout_id": "side_by_side",
            "meta": {
                "composition_type": "before_after",
                "aspect_ratio": "9:16",
                "source_reference_id": "template_default"
            },
            "layers": [
                {
                    "role": "before_state",
                    "position": {"top": "0%", "left": "0%", "width": "50%", "height": "100%"},
                    "source_type": "veo_generated_environment",
                    "z_index": 1,
                    "effects": []
                },
                {
                    "role": "after_state",
                    "position": {"top": "0%", "left": "50%", "width": "50%", "height": "100%"},
                    "source_type": "veo_generated_environment",
                    "z_index": 1,
                    "effects": ["subtle_glow"]
                }
            ],
            "audio_logic": {
                "primary_track": "digital_twin_voiceover",
                "ducking": {"bg_music_volume": 0.15},
                "auto_captions": {"style": "bold_yellow_centered", "y_offset": "90%"}
            },
            "timing_dna": {
                "hook_duration_frames": 75,
                "transition_style": "wipe_left_to_right",
                "b_roll_frequency": "never"
            }
        }
    },
    {
        "name": "Reaction Overlay",
        "description": "Full screen reference video + small reaction cam",
        "layout_type": "floating_bubble",
        "dna": {
            "layout_id": "reaction_overlay",
            "meta": {
                "composition_type": "reaction_commentary",
                "aspect_ratio": "9:16",
                "source_reference_id": "template_default"
            },
            "layers": [
                {
                    "role": "reference_video",
                    "position": {"top": "0%", "left": "0%", "width": "100%", "height": "100%"},
                    "source_type": "veo_generated_environment",
                    "z_index": 1,
                    "effects": []
                },
                {
                    "role": "reaction_host",
                    "position": {"top": "5%", "left": "75%", "width": "20%", "height": "20%"},
                    "source_type": "veo_generated_character",
                    "z_index": 3,
                    "effects": ["subtle_breathing"],
                    "mask": "circle"
                }
            ],
            "audio_logic": {
                "primary_track": "digital_twin_voiceover",
                "ducking": {"bg_music_volume": 0.05, "reference_audio_volume": 0.3},
                "auto_captions": {"style": "bold_white_stroke", "y_offset": "85%"}
            },
            "timing_dna": {
                "hook_duration_frames": 45,
                "transition_style": "fade",
                "b_roll_frequency": "never"
            }
        }
    }
]


async def seed_default_dna_templates(db: AsyncSession, org_id: int):
    """Seed predefined DNA templates for the organization."""
    
    for template_data in DEFAULT_DNA_TEMPLATES:
        dna = template_data["dna"]
        
        # Check if template already exists
        result = await db.execute(text("""
            SELECT id FROM crm.editing_dna 
            WHERE org_id = :org_id AND name = :name
        """), {"org_id": org_id, "name": template_data["name"]})
        
        if result.scalar():
            continue  # Template already exists
        
        # Insert the template
        await db.execute(text("""
            INSERT INTO crm.editing_dna (
                org_id, name, description, layout_type, aspect_ratio,
                layers, audio_logic, timing_dna, remotion_composition
            ) VALUES (
                :org_id, :name, :description, :layout_type, :aspect_ratio,
                :layers::jsonb, :audio_logic::jsonb, :timing_dna::jsonb, :remotion_composition
            )
        """), {
            "org_id": org_id,
            "name": template_data["name"],
            "description": template_data["description"],
            "layout_type": template_data["layout_type"],
            "aspect_ratio": dna["meta"]["aspect_ratio"],
            "layers": json.dumps(dna["layers"]),
            "audio_logic": json.dumps(dna["audio_logic"]),
            "timing_dna": json.dumps(dna["timing_dna"]),
            "remotion_composition": LAYOUT_TO_REMOTION_COMPOSITION.get(template_data["layout_type"], "UniversalTemplate")
        })
    
    await db.commit()
    logger.info(f"Seeded {len(DEFAULT_DNA_TEMPLATES)} default DNA templates for org {org_id}")


# ═══════════════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════

async def get_dna_by_id(db: AsyncSession, dna_id: int, org_id: int) -> Optional[Dict[str, Any]]:
    """Get a complete DNA template by ID."""
    
    result = await db.execute(text("""
        SELECT * FROM crm.editing_dna 
        WHERE id = :dna_id AND org_id = :org_id
    """), {"dna_id": dna_id, "org_id": org_id})
    
    row = result.mappings().first()
    if not row:
        return None
    
    # Reconstruct the full DNA structure
    dna = {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"],
        "layout_type": row["layout_type"],
        "source_post_id": row["source_post_id"],
        "thumbnail_url": row["thumbnail_url"],
        "remotion_composition": row["remotion_composition"],
        "created_at": str(row["created_at"]),
        "dna": {
            "layout_id": f"{row['layout_type']}_{row['id']}",
            "meta": {
                "composition_type": "extracted",
                "aspect_ratio": row["aspect_ratio"],
                "source_reference_id": f"dna_{row['id']}"
            },
            "layers": row["layers"] if isinstance(row["layers"], list) else json.loads(row["layers"] or "[]"),
            "audio_logic": row["audio_logic"] if isinstance(row["audio_logic"], dict) else json.loads(row["audio_logic"] or "{}"),
            "timing_dna": row["timing_dna"] if isinstance(row["timing_dna"], dict) else json.loads(row["timing_dna"] or "{}")
        }
    }
    
    return dna


async def list_dna_templates(db: AsyncSession, org_id: int) -> List[Dict[str, Any]]:
    """List all DNA templates for an organization."""
    
    result = await db.execute(text("""
        SELECT id, name, layout_type, aspect_ratio, thumbnail_url, source_post_id, created_at
        FROM crm.editing_dna 
        WHERE org_id = :org_id
        ORDER BY created_at DESC
    """), {"org_id": org_id})
    
    templates = []
    for row in result.mappings():
        templates.append({
            "id": row["id"],
            "name": row["name"],
            "layout_type": row["layout_type"],
            "aspect_ratio": row["aspect_ratio"],
            "thumbnail_url": row["thumbnail_url"],
            "source_post_id": row["source_post_id"],
            "created_at": str(row["created_at"])
        })
    
    return templates


def validate_dna_structure(dna: Dict[str, Any]) -> List[str]:
    """Validate DNA structure and return list of issues."""
    
    issues = []
    
    # Check required top-level keys
    required_keys = ["layout_id", "meta", "layers"]
    for key in required_keys:
        if key not in dna:
            issues.append(f"Missing required key: {key}")
    
    # Validate meta
    if "meta" in dna:
        meta = dna["meta"]
        if "aspect_ratio" not in meta:
            issues.append("Missing meta.aspect_ratio")
        elif meta["aspect_ratio"] not in ["9:16", "16:9", "1:1"]:
            issues.append(f"Invalid aspect_ratio: {meta['aspect_ratio']}")
    
    # Validate layers
    if "layers" in dna:
        layers = dna["layers"]
        if not isinstance(layers, list):
            issues.append("layers must be an array")
        else:
            for i, layer in enumerate(layers):
                if not isinstance(layer, dict):
                    issues.append(f"Layer {i} must be an object")
                    continue
                    
                if "role" not in layer:
                    issues.append(f"Layer {i} missing role")
                if "position" not in layer:
                    issues.append(f"Layer {i} missing position")
                if "source_type" not in layer:
                    issues.append(f"Layer {i} missing source_type")
                elif layer["source_type"] not in ["veo_generated_character", "veo_generated_environment", "text_overlay"]:
                    issues.append(f"Layer {i} invalid source_type: {layer['source_type']}")
    
    return issues