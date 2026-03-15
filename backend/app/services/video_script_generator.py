"""Video Script Generator — Generate new scripts from storyboard templates."""

import logging
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
import httpx

from app.services.video_analyzer import VideoStoryboard

logger = logging.getLogger(__name__)

@dataclass
class ScriptScene:
    index: int
    duration: float  # match original timing
    speaker_text: str  # new script for this scene
    visual_direction: str  # what should be on screen
    emotion: str  # "skeptical", "excited", "authoritative", "casual"
    props_needed: List[str]  # ["product-shot-angle-1", "diagram-roi"]
    
@dataclass
class VideoScript:
    title: str
    target_duration: float
    scenes: List[ScriptScene]
    brand_name: str
    product_name: str
    target_audience: str
    key_message: str
    total_word_count: int
    words_per_minute: float  # should match original cadence


def script_to_json(script: VideoScript) -> dict:
    """Serialize script to JSON-compatible dict."""
    return asdict(script)


def json_to_script(data: dict) -> VideoScript:
    """Deserialize JSON dict to script object."""
    scenes = [ScriptScene(**scene) for scene in data['scenes']]
    return VideoScript(
        title=data['title'],
        target_duration=data['target_duration'],
        scenes=scenes,
        brand_name=data['brand_name'],
        product_name=data['product_name'],
        target_audience=data['target_audience'],
        key_message=data['key_message'],
        total_word_count=data['total_word_count'],
        words_per_minute=data['words_per_minute']
    )


async def generate_script(
    storyboard: VideoStoryboard, 
    brand_context: dict, 
    product_url: Optional[str] = None,
    api_key: Optional[str] = None
) -> VideoScript:
    """
    Generate new script that keeps storyboard structure but swaps content.
    
    Args:
        storyboard: Original video structure to mimic
        brand_context: Brand info, voice, messaging
        product_url: Optional product page for context
        api_key: LLM API key for script generation
    """
    
    if not api_key:
        raise ValueError("API key required for script generation")
    
    # Extract brand details with defaults
    brand_name = brand_context.get('brand_name', 'Your Brand')
    product_name = brand_context.get('product_name', 'Your Product')
    target_audience = brand_context.get('target_audience', 'potential customers')
    key_message = brand_context.get('key_message', 'This product will change your life')
    brand_voice = brand_context.get('brand_voice', 'conversational and authentic')
    
    # Calculate target WPM from original storyboard
    original_wpm = storyboard.estimated_word_count / (storyboard.total_duration / 60)
    
    # Generate script for each scene
    script_scenes = []
    total_word_count = 0
    
    for scene in storyboard.scenes:
        # Calculate target words for this scene
        scene_duration_minutes = scene.duration / 60
        target_words = int(original_wpm * scene_duration_minutes)
        
        # Generate script for this scene
        scene_script = await _generate_scene_script(
            scene=scene,
            brand_context=brand_context,
            target_words=target_words,
            api_key=api_key
        )
        
        script_scenes.append(scene_script)
        total_word_count += len(scene_script.speaker_text.split())
    
    # Adjust for cadence if needed
    script = VideoScript(
        title=f"{brand_name} Video - {storyboard.overall_style.title()} Style",
        target_duration=storyboard.total_duration,
        scenes=script_scenes,
        brand_name=brand_name,
        product_name=product_name,
        target_audience=target_audience,
        key_message=key_message,
        total_word_count=total_word_count,
        words_per_minute=original_wpm
    )
    
    # Adjust cadence if word count is off
    if abs(total_word_count - storyboard.estimated_word_count) > 20:
        script = await adjust_for_cadence(script, original_wpm)
    
    return script


async def _generate_scene_script(
    scene,
    brand_context: dict,
    target_words: int,
    api_key: str
) -> ScriptScene:
    """Generate script for a single scene."""
    
    brand_name = brand_context.get('brand_name', 'Your Brand')
    product_name = brand_context.get('product_name', 'Your Product')
    brand_voice = brand_context.get('brand_voice', 'conversational and authentic')
    
    # Map scene types to script purposes
    scene_purpose_map = {
        'hook': 'grab attention and create curiosity',
        'problem': 'identify the pain point or challenge',
        'solution': 'present the product as the solution',
        'social-proof': 'provide credibility and testimonials',
        'cta': 'encourage specific action',
        'transition': 'bridge to the next section'
    }
    
    # Map emotions based on scene type
    emotion_map = {
        'hook': 'excited',
        'problem': 'empathetic',
        'solution': 'confident',
        'social-proof': 'authoritative',
        'cta': 'enthusiastic',
        'transition': 'casual'
    }
    
    purpose = scene_purpose_map.get(scene.scene_type, 'deliver engaging content')
    emotion = emotion_map.get(scene.scene_type, 'casual')
    
    # Create prompts for AI generation
    prompt = f"""
    Write a {target_words}-word script for a video scene with these requirements:
    
    Scene Purpose: {purpose}
    Duration: {scene.duration} seconds
    Original Scene: {scene.description}
    Energy Level: {scene.energy_level}
    
    Brand Context:
    - Brand: {brand_name}
    - Product: {product_name}
    - Voice: {brand_voice}
    - Key Message: {brand_context.get('key_message', '')}
    
    Requirements:
    - Match the energy level ({scene.energy_level})
    - Speak in {brand_voice} tone
    - Target exactly {target_words} words
    - Scene type: {scene.scene_type}
    
    Write ONLY the spoken text, no stage directions.
    """
    
    # For MVP, generate based on templates
    # In production, would call LLM API
    speaker_text = _generate_template_script(scene, brand_context, target_words)
    
    # Generate visual direction
    visual_direction = _generate_visual_direction(scene, brand_context)
    
    # Determine props needed
    props_needed = _determine_props(scene, brand_context)
    
    return ScriptScene(
        index=scene.index,
        duration=scene.duration,
        speaker_text=speaker_text,
        visual_direction=visual_direction,
        emotion=emotion,
        props_needed=props_needed
    )


def _generate_template_script(scene, brand_context: dict, target_words: int) -> str:
    """Generate script using templates (MVP fallback)."""
    
    brand_name = brand_context.get('brand_name', 'Your Brand')
    product_name = brand_context.get('product_name', 'Your Product')
    
    templates = {
        'hook': [
            f"You know what's crazy about {product_name}? I've been using it for weeks and honestly didn't expect this...",
            f"Okay, real talk - I was skeptical about {product_name} at first. But after trying it myself...",
            f"If you're struggling with [pain point], you need to see this. {product_name} literally changed everything for me.",
        ],
        'problem': [
            f"So here's the thing - before {product_name}, I was dealing with the same frustration you probably are.",
            f"You know that feeling when [describe problem]? I was there too, constantly searching for something that actually worked.",
            f"I used to think this problem was just part of life. That there wasn't really a good solution out there.",
        ],
        'solution': [
            f"That's exactly why {product_name} is such a game-changer. It literally solves [specific problem] in a way I've never seen before.",
            f"What makes {product_name} different is [key benefit]. It's not just another [category] - it's designed specifically for people like us.",
            f"Here's what happened when I started using {product_name}. Within [timeframe], I noticed [specific result].",
        ],
        'social-proof': [
            f"And I'm not the only one saying this. Thousands of people are getting similar results with {product_name}.",
            f"The reviews on this thing are insane. People are calling it life-changing, and honestly? I get it now.",
            f"My friend Sarah told me about this first, and now I understand why she wouldn't stop talking about it.",
        ],
        'cta': [
            f"So if you want to try {product_name} for yourself, I'll put the link in my bio. You can thank me later.",
            f"I highly recommend checking out {product_name}. Link in bio if you're interested. Trust me on this one.",
            f"Definitely worth trying if you're dealing with [problem]. Link's in my bio - go check it out.",
        ],
        'transition': [
            f"But here's what really surprised me about {product_name}...",
            f"Now, the part that really sold me was...",
            f"And this is where it gets really interesting...",
        ]
    }
    
    scene_templates = templates.get(scene.scene_type, templates['solution'])
    base_script = scene_templates[scene.index % len(scene_templates)]
    
    # Adjust length to target words
    words = base_script.split()
    if len(words) < target_words:
        # Extend with relevant details
        extensions = [
            f"The quality is incredible and the {brand_name} team really knows what they're doing.",
            f"I've tried so many alternatives but nothing comes close to this.",
            f"The difference in my daily routine has been absolutely noticeable.",
            f"It's one of those products that just makes sense once you try it.",
        ]
        while len(words) < target_words and extensions:
            words.extend(extensions.pop(0).split())
    
    # Trim if too long
    if len(words) > target_words:
        words = words[:target_words]
    
    return ' '.join(words)


def _generate_visual_direction(scene, brand_context: dict) -> str:
    """Generate visual direction for the scene."""
    
    directions = {
        'hook': f"Close-up shot, direct eye contact, {scene.energy_level} energy. Quick cuts if multiple products shown.",
        'problem': f"Medium shot, slightly concerned expression, {scene.energy_level} energy. Maybe B-roll of problem scenario.",
        'solution': f"Product showcase shot, confident presentation, {scene.energy_level} energy. Show product in action.",
        'social-proof': f"Cut to testimonial graphics or user-generated content, {scene.energy_level} energy.",
        'cta': f"Direct to camera, clear hand gestures, {scene.energy_level} energy. End with product visible.",
        'transition': f"{scene.shot_type} shot, {scene.camera_movement} movement, building {scene.energy_level} energy."
    }
    
    return directions.get(scene.scene_type, f"{scene.shot_type} shot with {scene.energy_level} energy")


def _determine_props(scene, brand_context: dict) -> List[str]:
    """Determine what props/visuals are needed for the scene."""
    
    props_map = {
        'hook': ['product-hero-shot'],
        'problem': ['problem-demonstration', 'before-scenario'],
        'solution': ['product-in-action', 'key-benefits-visual'],
        'social-proof': ['testimonial-graphics', 'user-photos'],
        'cta': ['product-packaging', 'call-to-action-text'],
        'transition': ['b-roll-footage']
    }
    
    base_props = props_map.get(scene.scene_type, ['general-b-roll'])
    
    # Add brand-specific props
    if brand_context.get('product_name'):
        base_props.append(f"{brand_context['product_name'].lower().replace(' ', '-')}-shot")
    
    return base_props


async def adjust_for_cadence(script: VideoScript, target_wpm: float) -> VideoScript:
    """Adjust script to match target words per minute."""
    
    # Calculate current WPM
    current_wpm = script.total_word_count / (script.target_duration / 60)
    
    if abs(current_wpm - target_wpm) < 10:  # Close enough
        return script
    
    # Need to adjust word count
    target_total_words = int(target_wpm * (script.target_duration / 60))
    adjustment_ratio = target_total_words / script.total_word_count
    
    # Adjust each scene proportionally
    adjusted_scenes = []
    new_total_words = 0
    
    for scene in script.scenes:
        current_words = len(scene.speaker_text.split())
        target_scene_words = int(current_words * adjustment_ratio)
        
        if adjustment_ratio < 1:  # Need to trim
            words = scene.speaker_text.split()[:target_scene_words]
            adjusted_text = ' '.join(words)
        else:  # Need to expand
            # For expansion, just ensure we hit the word count (simple approach)
            # In production, would use AI to naturally extend
            words = scene.speaker_text.split()
            while len(words) < target_scene_words:
                words.append("exactly")  # Simple padding
            adjusted_text = ' '.join(words[:target_scene_words])
        
        adjusted_scene = ScriptScene(
            index=scene.index,
            duration=scene.duration,
            speaker_text=adjusted_text,
            visual_direction=scene.visual_direction,
            emotion=scene.emotion,
            props_needed=scene.props_needed
        )
        
        adjusted_scenes.append(adjusted_scene)
        new_total_words += len(adjusted_text.split())
    
    # Return adjusted script
    return VideoScript(
        title=script.title,
        target_duration=script.target_duration,
        scenes=adjusted_scenes,
        brand_name=script.brand_name,
        product_name=script.product_name,
        target_audience=script.target_audience,
        key_message=script.key_message,
        total_word_count=new_total_words,
        words_per_minute=target_wpm
    )