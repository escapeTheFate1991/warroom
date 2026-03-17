"""Nano Banana 2 Image Generation Service

Wraps Google's Gemini image generation (Nano Banana 2 = Gemini's image generation capability).
Provides character reference sheet generation and scene rendering for Digital Copies.
"""

import os
import json
import base64
import logging
import httpx
from typing import List, Dict, Any, Optional, Union
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"


async def get_google_api_key(db: Optional[AsyncSession] = None) -> str:
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
            if row:
                return row[0]
        except Exception as e:
            logger.error(f"Failed to get Google API key from database: {e}")
    
    raise ValueError("Google AI Studio API key not configured")


async def download_image_bytes(url: str) -> bytes:
    """Download image from URL and return bytes"""
    async with httpx.AsyncClient() as client:
        response = await client.get(url, timeout=30.0)
        response.raise_for_status()
        return response.content


def encode_image_for_gemini(image_bytes: bytes, mime_type: str = "image/jpeg") -> Dict[str, Any]:
    """Encode image bytes to base64 for Gemini API"""
    encoded = base64.b64encode(image_bytes).decode('utf-8')
    return {
        "inline_data": {
            "mime_type": mime_type,
            "data": encoded
        }
    }


async def call_gemini_api(
    api_key: str,
    model: str,
    messages: List[Dict[str, Any]],
    generation_config: Dict[str, Any]
) -> Dict[str, Any]:
    """Make API call to Gemini"""
    url = f"{GEMINI_API_BASE}/models/{model}:generateContent"
    
    payload = {
        "contents": messages,
        "generationConfig": generation_config
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{url}?key={api_key}",
            headers=headers,
            json=payload,
            timeout=120.0  # Image generation can be slow
        )
        response.raise_for_status()
        return response.json()


async def generate_reference_sheet(
    reference_images: List[bytes], 
    character_name: str, 
    character_dna: Dict[str, Any],
    db: Optional[AsyncSession] = None
) -> bytes:
    """
    Generate a Master Reference Sheet from uploaded photos
    
    Args:
        reference_images: List of image bytes from uploaded photos
        character_name: Character name for context
        character_dna: Character DNA dict with biological anchors
        db: Database session for API key lookup
    
    Returns:
        Generated reference sheet image bytes
    """
    if not reference_images:
        raise ValueError("No reference images provided")
    
    api_key = await get_google_api_key(db)
    
    # Build the prompt with character DNA context
    biological_anchors = character_dna.get("biological_anchors", {})
    dna_context = ""
    
    if biological_anchors:
        facial_structure = biological_anchors.get("facial_structure", "")
        eyes = biological_anchors.get("eyes", {})
        hair = biological_anchors.get("hair", {})
        skin = biological_anchors.get("skin", {})
        
        dna_parts = []
        if facial_structure:
            dna_parts.append(f"facial structure: {facial_structure}")
        if eyes:
            eye_desc = f"{eyes.get('color', '')} {eyes.get('shape', '')} eyes".strip()
            if eye_desc != " eyes":
                dna_parts.append(eye_desc)
        if hair:
            hair_desc = f"{hair.get('color', '')} {hair.get('style', '')} {hair.get('texture', '')} hair".strip()
            if hair_desc != "  hair":
                dna_parts.append(hair_desc)
        if skin:
            skin_desc = f"{skin.get('tone', '')} skin tone".strip()
            if skin_desc != " skin tone":
                dna_parts.append(skin_desc)
        
        if dna_parts:
            dna_context = f"Key features to maintain: {', '.join(dna_parts)}. "
    
    prompt = f"""Create a comprehensive character reference sheet for "{character_name}" based on these photos. {dna_context}

Generate a master reference sheet showing this person in 4 different views:
1. Front view - looking directly at camera, neutral expression
2. Three-quarter view - slight turn to show profile angle
3. Left profile - complete side view from left side
4. Right profile - complete side view from right side

Requirements:
- MAINTAIN EXACT FACIAL FEATURES across all views
- Same lighting and art style for all poses
- Clean white background
- Professional character sheet layout
- Consistent identity and proportions
- High detail on facial features, hair, and distinctive characteristics
- Label each view clearly

Style: Clean reference sheet, consistent lighting, photorealistic"""

    # Prepare image parts for the API call
    image_parts = []
    for i, img_bytes in enumerate(reference_images[:8]):  # Limit to 8 images max
        image_parts.append(encode_image_for_gemini(img_bytes))
    
    # Build the message
    content_parts = image_parts + [{"text": prompt}]
    
    messages = [{
        "role": "user",
        "parts": content_parts
    }]
    
    generation_config = {
        "responseModalities": ["TEXT", "IMAGE"],
        "temperature": 0.2,  # Lower for consistency
        "topK": 32,
        "topP": 0.8
    }
    
    try:
        # Try with the experimental model first
        model = "gemini-2.0-flash-exp"
        result = await call_gemini_api(api_key, model, messages, generation_config)
    except Exception as e:
        logger.warning(f"Failed with {model}, trying fallback: {e}")
        # Fallback to stable model
        model = "gemini-2.0-flash"
        result = await call_gemini_api(api_key, model, messages, generation_config)
    
    # Extract image from response
    candidates = result.get("candidates", [])
    if not candidates:
        raise ValueError("No candidates returned from Gemini")
    
    content = candidates[0].get("content", {})
    parts = content.get("parts", [])
    
    # Find the image part
    for part in parts:
        if "inlineData" in part:
            image_data = part["inlineData"]["data"]
            return base64.b64decode(image_data)
    
    raise ValueError("No image found in Gemini response")


async def generate_scene(
    reference_sheet_url: str, 
    scene_prompt: str, 
    character_dna: Dict[str, Any], 
    style_dna: str = None,
    db: Optional[AsyncSession] = None
) -> bytes:
    """
    Generate a scene image using the reference sheet and character DNA
    
    Args:
        reference_sheet_url: URL to the master reference sheet
        scene_prompt: Description of the scene to generate
        character_dna: Character DNA dict for consistency
        style_dna: Optional style override
        db: Database session for API key lookup
    
    Returns:
        Generated scene image bytes
    """
    api_key = await get_google_api_key(db)
    
    # Download the reference sheet
    reference_bytes = await download_image_bytes(reference_sheet_url)
    
    # Get style DNA from character or use override
    if style_dna is None:
        visual_consistency = character_dna.get("visual_consistency_assets", {})
        style_dna = visual_consistency.get("style_dna", "cinematic 35mm film, soft Rembrandt lighting, f/2.8 depth of field")
    
    # Build relationship instruction prompt
    prompt = f"""Using this reference sheet as a guide, generate an image of the EXACT SAME PERSON in the following scene:

Scene: {scene_prompt}

CRITICAL REQUIREMENTS:
- The person MUST match the reference sheet EXACTLY (100% fidelity)
- Same facial features, hair, skin tone, and proportions
- Maintain the character's identity completely
- Use this visual style: {style_dna}

The generated image should show this character naturally integrated into the scene while preserving their exact appearance from the reference sheet."""

    # Prepare the message with reference sheet
    content_parts = [
        encode_image_for_gemini(reference_bytes),
        {"text": prompt}
    ]
    
    messages = [{
        "role": "user", 
        "parts": content_parts
    }]
    
    generation_config = {
        "responseModalities": ["TEXT", "IMAGE"],
        "temperature": 0.3,  # Slightly higher for scene creativity
        "topK": 40,
        "topP": 0.9
    }
    
    try:
        # Try with the experimental model first
        model = "gemini-2.0-flash-exp"
        result = await call_gemini_api(api_key, model, messages, generation_config)
    except Exception as e:
        logger.warning(f"Failed with {model}, trying fallback: {e}")
        # Fallback to stable model
        model = "gemini-2.0-flash"
        result = await call_gemini_api(api_key, model, messages, generation_config)
    
    # Extract image from response
    candidates = result.get("candidates", [])
    if not candidates:
        raise ValueError("No candidates returned from Gemini")
    
    content = candidates[0].get("content", {})
    parts = content.get("parts", [])
    
    # Find the image part
    for part in parts:
        if "inlineData" in part:
            image_data = part["inlineData"]["data"]
            return base64.b64decode(image_data)
    
    raise ValueError("No image found in Gemini response")


async def enrich_character_dna(
    reference_images: List[bytes], 
    current_dna: Dict[str, Any],
    db: Optional[AsyncSession] = None
) -> Dict[str, Any]:
    """
    Analyze reference images to enrich character DNA with biological anchors
    
    Args:
        reference_images: List of image bytes from uploaded photos
        current_dna: Current character DNA dict
        db: Database session for API key lookup
    
    Returns:
        Enriched character DNA dict with biological_anchors filled in
    """
    if not reference_images:
        return current_dna
    
    api_key = await get_google_api_key(db)
    
    # Use the first few images for analysis
    analysis_images = reference_images[:3]
    
    prompt = """Analyze these photos of a person and describe their biological features in detail for AI character generation.

Provide a JSON response with this exact structure:
{
  "biological_anchors": {
    "facial_structure": "describe face shape, jawline, cheekbones, overall structure",
    "eyes": {
      "color": "specific eye color",
      "shape": "eye shape description", 
      "distinction": "unique characteristics"
    },
    "hair": {
      "style": "current hairstyle",
      "color": "hair color",
      "texture": "hair texture description"
    },
    "skin": {
      "tone": "skin tone description",
      "texture": "skin texture notes",
      "pore_detail": "skin detail level"
    }
  }
}

Be specific and detailed - this will be used to maintain character consistency across AI generations. Focus on distinctive features that make this person recognizable."""

    # Prepare image parts for analysis
    image_parts = []
    for img_bytes in analysis_images:
        image_parts.append(encode_image_for_gemini(img_bytes))
    
    content_parts = image_parts + [{"text": prompt}]
    
    messages = [{
        "role": "user",
        "parts": content_parts
    }]
    
    generation_config = {
        "responseModalities": ["TEXT"],
        "temperature": 0.1,  # Very low for analytical accuracy
        "topK": 32,
        "topP": 0.7
    }
    
    # Use stable model for text analysis
    model = "gemini-2.0-flash"
    result = await call_gemini_api(api_key, model, messages, generation_config)
    
    # Extract text response
    candidates = result.get("candidates", [])
    if not candidates:
        raise ValueError("No candidates returned from Gemini")
    
    content = candidates[0].get("content", {})
    parts = content.get("parts", [])
    
    response_text = ""
    for part in parts:
        if "text" in part:
            response_text += part["text"]
    
    if not response_text:
        logger.warning("No text response from Gemini analysis")
        return current_dna
    
    try:
        # Parse JSON response
        analysis_data = json.loads(response_text.strip())
        
        # Merge with current DNA
        enriched_dna = current_dna.copy()
        enriched_dna.update(analysis_data)
        
        return enriched_dna
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Gemini analysis response: {e}")
        logger.error(f"Response was: {response_text}")
        return current_dna