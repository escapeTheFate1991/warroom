"""Competitor Script Engine — Generate scripts from competitor intel data.

Uses the 551 competitor posts with hooks, CTAs, transcripts, and content analysis
to generate scripts that leverage proven viral patterns.
"""

import logging
import json
import os
from datetime import datetime
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.settings import Setting
from sqlalchemy import select

logger = logging.getLogger(__name__)


@dataclass
class ScriptStructure:
    """Structured competitor post script data."""
    hook: str  # The opening hook text
    body: List[str]  # Body segments  
    cta: str  # Call to action
    total_duration: float
    format_type: str  # detected_format from competitor post
    engagement_score: float
    source_post_id: int


@dataclass
class GeneratedScript:
    """AI-generated script based on competitor structure."""
    hook: str
    body: List[str]
    cta: str
    visual_directions: List[str]  # What should be on screen for each segment
    total_duration: float
    source_structure_id: int  # Which competitor post structure was used


async def get_top_scripts(db: AsyncSession, org_id: int, format_filter: Optional[str] = None, limit: int = 20) -> List[ScriptStructure]:
    """Query competitor_posts sorted by engagement_score DESC.
    
    Args:
        db: Database session
        org_id: Organization ID  
        format_filter: Optional format to filter by (e.g. 'transformation', 'myth_buster')
        limit: Maximum number of scripts to return
        
    Returns:
        List of structured scripts from top competitor posts
    """
    try:
        # Build query
        query = """
            SELECT cp.id, cp.post_text, cp.hook, cp.engagement_score, cp.detected_format,
                   cp.content_analysis, cp.transcript, cp.post_url, c.handle
            FROM crm.competitor_posts cp
            JOIN crm.competitors c ON cp.competitor_id = c.id
            WHERE c.org_id = :org_id
              AND cp.hook IS NOT NULL
              AND LENGTH(cp.hook) >= 10
        """
        
        params = {"org_id": org_id}
        
        if format_filter:
            query += " AND cp.detected_format = :format_filter"
            params["format_filter"] = format_filter
            
        query += " ORDER BY cp.engagement_score DESC LIMIT :limit"
        params["limit"] = limit
        
        result = await db.execute(text(query), params)
        rows = result.fetchall()
        
        scripts = []
        for row in rows:
            script_structure = await extract_hook_body_cta(dict(row._mapping))
            if script_structure:
                scripts.append(script_structure)
                
        return scripts
        
    except Exception as e:
        logger.error(f"Failed to get top scripts: {e}")
        return []


async def extract_hook_body_cta(post_data: Dict[str, Any]) -> Optional[ScriptStructure]:
    """Parse content_analysis JSON to extract the three parts.
    
    Args:
        post_data: Dictionary containing post data from database
        
    Returns:
        ScriptStructure with hook/body/cta extracted, or None if extraction fails
    """
    try:
        post_id = post_data.get("id")
        engagement_score = float(post_data.get("engagement_score", 0))
        format_type = post_data.get("detected_format") or "unclassified"
        
        # Extract hook (prioritize existing hook field)
        hook = post_data.get("hook", "").strip()
        
        # Extract content_analysis for more detailed structure
        content_analysis = post_data.get("content_analysis")
        if isinstance(content_analysis, str):
            try:
                content_analysis = json.loads(content_analysis)
            except json.JSONDecodeError:
                content_analysis = {}
        elif not isinstance(content_analysis, dict):
            content_analysis = {}
            
        # Try to get full_script from content_analysis first
        full_script = content_analysis.get("full_script", "")
        if full_script:
            # Split full_script into hook (first sentence), body (middle), cta (last sentence)
            sentences = full_script.replace('\n', ' ').split('. ')
            sentences = [s.strip() + '.' for s in sentences if s.strip()]
            
            if not hook and sentences:
                hook = sentences[0]
            
            body_segments = sentences[1:-1] if len(sentences) > 2 else sentences[1:] if len(sentences) > 1 else []
            cta = sentences[-1] if len(sentences) > 1 and sentences[-1] != hook else ""
            
        else:
            # Fallback: use post_text and extract manually
            post_text = post_data.get("post_text", "")
            
            if not hook:
                # Extract first sentence as hook
                first_sentence_end = min([
                    i for i in [post_text.find('. '), post_text.find('! '), post_text.find('? ')]
                    if i > 0
                ] or [len(post_text)])
                hook = post_text[:first_sentence_end].strip()
                if first_sentence_end < len(post_text):
                    hook += post_text[first_sentence_end]  # Add the punctuation
            
            # Extract body (everything after hook)
            remaining_text = post_text[len(hook):].strip()
            body_segments = [segment.strip() for segment in remaining_text.split('. ') if segment.strip()]
            
            # Extract CTA from content_analysis if available
            cta_data = content_analysis.get("cta", {})
            if isinstance(cta_data, dict):
                cta = cta_data.get("text", "")
            else:
                cta = str(cta_data) if cta_data else ""
                
            # Fallback: last segment as CTA if no explicit CTA
            if not cta and body_segments:
                cta = body_segments[-1]
                body_segments = body_segments[:-1]
        
        # Estimate duration based on content length
        total_words = len(hook.split()) + sum(len(seg.split()) for seg in body_segments) + len(cta.split())
        total_duration = max(15.0, min(90.0, total_words * 0.4))  # ~150 words per minute
        
        # Use explicit duration from content_analysis if available
        if content_analysis.get("total_duration"):
            total_duration = float(content_analysis["total_duration"])
            
        return ScriptStructure(
            hook=hook,
            body=body_segments,
            cta=cta,
            total_duration=total_duration,
            format_type=format_type,
            engagement_score=engagement_score,
            source_post_id=post_id
        )
        
    except Exception as e:
        logger.error(f"Failed to extract hook/body/cta from post {post_data.get('id', 'unknown')}: {e}")
        return None


async def generate_script_from_reference(
    db: AsyncSession, 
    reference_post_id: int, 
    brand_context: Dict[str, Any], 
    api_key: str
) -> Optional[GeneratedScript]:
    """Generate script from reference post using Gemini.
    
    Args:
        db: Database session
        reference_post_id: ID of competitor post to use as reference
        brand_context: Dict with brand_name, product_name, target_audience, key_message
        api_key: Google AI Studio API key
        
    Returns:
        GeneratedScript with new content based on reference structure
    """
    try:
        # Load the reference competitor post
        query = """
            SELECT cp.*, c.handle, c.platform
            FROM crm.competitor_posts cp
            JOIN crm.competitors c ON cp.competitor_id = c.id
            WHERE cp.id = :post_id
        """
        result = await db.execute(text(query), {"post_id": reference_post_id})
        post_row = result.mappings().first()
        
        if not post_row:
            logger.error(f"Reference post {reference_post_id} not found")
            return None
            
        post_data = dict(post_row)
        
        # Extract structure from reference post
        reference_structure = await extract_hook_body_cta(post_data)
        if not reference_structure:
            logger.error(f"Could not extract structure from post {reference_post_id}")
            return None
            
        # Build prompt for Gemini
        brand_name = brand_context.get("brand_name", "Your Brand")
        product_name = brand_context.get("product_name", "Your Product") 
        target_audience = brand_context.get("target_audience", "your target audience")
        key_message = brand_context.get("key_message", "your key message")
        
        # Get original transcript for context if available
        transcript = post_data.get("transcript")
        if isinstance(transcript, str):
            try:
                transcript = json.loads(transcript)
            except json.JSONDecodeError:
                transcript = {}
        transcript_text = ""
        if isinstance(transcript, dict):
            transcript_text = transcript.get("text", "")
        
        prompt = f"""Here is a successful video structure from @{post_data.get('handle')} that got {int(reference_structure.engagement_score)} engagement:

ORIGINAL STRUCTURE:
Hook: "{reference_structure.hook}"
Body: {json.dumps(reference_structure.body)}
CTA: "{reference_structure.cta}"
Format: {reference_structure.format_type}
Duration: {reference_structure.total_duration}s

{f'Original transcript context: {transcript_text[:500]}...' if transcript_text else ''}

REWRITE THIS FOR:
Brand: {brand_name}
Product: {product_name}  
Target Audience: {target_audience}
Key Message: {key_message}

Keep the same pacing, hook style, and CTA approach but with entirely new messaging about the brand and product. Match the energy and structure but make it 100% original content.

Return JSON in this exact format:
{{
  "hook": "New hook that matches the style and energy",
  "body": ["New body segment 1", "New body segment 2", ...],
  "cta": "New call to action matching the style",
  "visual_directions": ["Visual direction for hook", "Visual direction for body", "Visual direction for CTA"],
  "total_duration": {reference_structure.total_duration}
}}"""

        # Call Gemini API
        import httpx
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}",
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.8,
                        "maxOutputTokens": 1024,
                        "responseMimeType": "application/json"
                    }
                }
            )
            
            if response.status_code != 200:
                logger.error(f"Gemini API error: {response.status_code} {response.text}")
                return None
                
            response_data = response.json()
            content = response_data.get("candidates", [{}])[0].get("content", {})
            generated_text = content.get("parts", [{}])[0].get("text", "")
            
            if not generated_text:
                logger.error("Empty response from Gemini")
                return None
                
            # Parse JSON response
            try:
                generated_data = json.loads(generated_text)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse Gemini JSON response: {generated_text}")
                return None
                
            # Create GeneratedScript
            return GeneratedScript(
                hook=generated_data.get("hook", reference_structure.hook),
                body=generated_data.get("body", reference_structure.body),
                cta=generated_data.get("cta", reference_structure.cta),
                visual_directions=generated_data.get("visual_directions", [
                    "Close-up of speaker delivering hook",
                    "Medium shot with product/demo visible", 
                    "Direct to camera for call to action"
                ]),
                total_duration=generated_data.get("total_duration", reference_structure.total_duration),
                source_structure_id=reference_post_id
            )
            
    except Exception as e:
        logger.error(f"Failed to generate script from reference {reference_post_id}: {e}")
        return None


async def _get_google_api_key(db: AsyncSession) -> Optional[str]:
    """Get Google AI Studio API key from settings or environment."""
    try:
        # Try database first
        result = await db.execute(
            select(Setting.value).where(Setting.key == "google_ai_studio_api_key")
        )
        api_key = result.scalar_one_or_none()
        
        if api_key:
            return api_key
            
        # Fallback to environment variable
        return os.getenv("GOOGLE_AI_STUDIO_API_KEY")
        
    except Exception as e:
        logger.error(f"Failed to get Google API key: {e}")
        return os.getenv("GOOGLE_AI_STUDIO_API_KEY")