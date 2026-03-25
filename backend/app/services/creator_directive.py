"""Creator Directive Report (CDR) Generator Service

Generates 5-section Creator Directive Reports that turn raw engagement data into
actionable video creation instructions for Veo and Nano Banana.

Flow: Raw Data → Intent Classification → Strategy Engine → CDR → Video Prompts

CDR Sections:
1. Hook Directive: Visual/audio/script instructions for the opener
2. Retention Blueprint: Pacing rules, pattern interrupts, boredom triggers
3. Share Catalyst: Vulnerability frames, identity moments, visual shifts  
4. Conversion Close: CTA type, script line, open loops, automation triggers
5. Technical Specs: Lighting, aspect ratio, captions, music, length
"""

import json
import logging
import httpx
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from pydantic import BaseModel, Field

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Strategy Map: Intent buckets to specific directives
STRATEGY_MAP = {
    "UTILITY_SAVE": "Create a cheat sheet frame. End with 2-second static list impossible to read without saving.",
    "IDENTITY_SHARE": "Script a POV hook. Use hyper-specific internal thought that makes people feel seen.", 
    "CURIOSITY_GAP": "Open-Loop strategy. Start with result, hide the how until final 3 seconds.",
    "FRICTION_POINT": "Visual Anchor. Insert permanent lower-third text overlay during complex parts.",
    "SOCIAL_PROOF": "The Look-to-Camera moment. Break 4th wall at climax to build human trust."
}

# Power Score thresholds
MIN_POWER_SCORE = 2000

# LLM endpoints (local first, then fallback)
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama3.1:8b-cpu"

class HookDirective(BaseModel):
    """Hook instruction set for video opener (0-3s)"""
    visual: str = ""
    audio: str = ""
    script_line: str = ""
    overlay: str = ""
    reasoning: str = ""

class RetentionBlueprint(BaseModel):
    """Retention optimization instruction set"""
    pacing_rules: List[str] = Field(default_factory=list)
    pattern_interrupts: List[str] = Field(default_factory=list) 
    anti_boredom_triggers: List[str] = Field(default_factory=list)
    j_cut_points: List[str] = Field(default_factory=list)

class ShareCatalyst(BaseModel):
    """Viral sharing catalyst instruction set"""
    vulnerability_frame: str = ""
    identity_moment: str = ""
    visual_style_shift: str = ""
    timestamp: str = ""

class ConversionClose(BaseModel):
    """Conversion optimization instruction set"""
    cta_type: str = ""
    script_line: str = ""
    open_loop_topic: str = ""
    automation_trigger: str = ""

class TechnicalSpecs(BaseModel):
    """Technical production specifications"""
    lighting: str = ""
    aspect_ratio: str = "9:16"
    center_zone_safety: str = "Top 1/3 for mobile"
    caption_style: str = ""
    color_palette: str = ""
    music_bpm: str = ""
    video_length: str = ""

class GeneratorPrompts(BaseModel):
    """Copy-paste ready prompts for video generation"""
    veo_prompt: str = ""
    nano_banana_prompt: str = ""

class CreatorDirectiveReport(BaseModel):
    """Complete Creator Directive Report"""
    hook_directive: HookDirective
    retention_blueprint: RetentionBlueprint
    share_catalyst: ShareCatalyst
    conversion_close: ConversionClose
    technical_specs: TechnicalSpecs
    generator_prompts: GeneratorPrompts
    power_score: float
    dominant_intent: str
    post_id: int
    generated_at: datetime = Field(default_factory=datetime.utcnow)

@dataclass
class PostData:
    """Post data structure for CDR generation"""
    post_id: int
    shortcode: str
    competitor_handle: str
    hook: str
    full_script: str
    likes: int
    comments: int
    shares: int
    engagement_score: float
    content_analysis: Dict
    video_analysis: Dict
    frame_chunks: List[Dict]
    posted_at: datetime

class CreatorDirectiveService:
    """CDR Generation Service"""
    
    def __init__(self):
        self.ollama_client = httpx.AsyncClient(base_url=OLLAMA_BASE_URL, timeout=30.0)

    async def generate_cdr(
        self, 
        post_data: PostData, 
        intent_scores: Dict[str, float]
    ) -> Optional[CreatorDirectiveReport]:
        """Generate a Creator Directive Report for a high-performing post
        
        Args:
            post_data: Post performance and content data
            intent_scores: Intent classification scores from intent_classifier
            
        Returns:
            Complete CDR or None if insufficient data
        """
        try:
            # Calculate power score
            power_score = self._calculate_power_score(post_data, intent_scores)
            
            if power_score < MIN_POWER_SCORE:
                logger.info("Post %s below power score threshold: %.0f < %d", 
                           post_data.shortcode, power_score, MIN_POWER_SCORE)
                return None
            
            # Determine dominant intent
            dominant_intent = max(intent_scores.items(), key=lambda x: x[1])[0]
            
            # Generate each CDR section
            hook_directive = await self._generate_hook_directive(post_data, intent_scores, dominant_intent)
            retention_blueprint = await self._generate_retention_blueprint(post_data, intent_scores)
            share_catalyst = await self._generate_share_catalyst(post_data, intent_scores)
            conversion_close = await self._generate_conversion_close(post_data, intent_scores)
            technical_specs = await self._generate_technical_specs(post_data, intent_scores)
            generator_prompts = await self._generate_video_prompts(post_data, intent_scores, dominant_intent)
            
            cdr = CreatorDirectiveReport(
                hook_directive=hook_directive,
                retention_blueprint=retention_blueprint,
                share_catalyst=share_catalyst,
                conversion_close=conversion_close,
                technical_specs=technical_specs,
                generator_prompts=generator_prompts,
                power_score=power_score,
                dominant_intent=dominant_intent,
                post_id=post_data.post_id
            )
            
            logger.info("✅ Generated CDR for %s: Power=%.0f, Intent=%s", 
                       post_data.shortcode, power_score, dominant_intent)
            
            return cdr
            
        except Exception as e:
            logger.error("CDR generation failed for post %s: %s", post_data.post_id, e)
            return None

    def _calculate_power_score(self, post_data: PostData, intent_scores: Dict[str, float]) -> float:
        """Calculate Power Score: engagement weighted by intent strength and viral indicators"""
        base_engagement = post_data.engagement_score
        
        # Intent amplification factor (1.0 - 2.5x)
        max_intent_score = max(intent_scores.values()) if intent_scores else 0
        intent_multiplier = 1.0 + (max_intent_score * 1.5)
        
        # Viral indicators boost
        viral_boost = 1.0
        if post_data.shares > 100:
            viral_boost += 0.3
        if post_data.comments > post_data.likes * 0.1:  # High comment ratio
            viral_boost += 0.2
        if post_data.likes > 10000:
            viral_boost += 0.2
            
        # Hook quality boost
        content_analysis = post_data.content_analysis or {}
        hook_data = content_analysis.get('hook', {})
        hook_strength = hook_data.get('strength', 0)
        hook_boost = 1.0 + (hook_strength * 0.3)
        
        power_score = base_engagement * intent_multiplier * viral_boost * hook_boost
        
        return round(power_score, 1)

    async def _generate_hook_directive(
        self, 
        post_data: PostData, 
        intent_scores: Dict[str, float],
        dominant_intent: str
    ) -> HookDirective:
        """Generate hook directive based on dominant intent and performance data"""
        
        strategy_directive = STRATEGY_MAP.get(dominant_intent, "Create an attention-grabbing opener")
        
        # Extract actual hook and performance context
        hook_text = post_data.hook[:200] if post_data.hook else ""
        content_analysis = post_data.content_analysis or {}
        hook_data = content_analysis.get('hook', {})
        hook_type = hook_data.get('type', 'unknown')
        hook_strength = hook_data.get('strength', 0)
        
        prompt = f"""
        Generate specific hook directive for video creation. Use this high-performing example as reference:
        
        Original Hook: "{hook_text}"
        Hook Type: {hook_type}
        Hook Strength: {hook_strength:.2f}
        Strategy: {strategy_directive}
        Engagement: {post_data.likes:,} likes, {post_data.comments:,} comments
        
        Provide specific instructions for:
        1. VISUAL: What should be on screen in first 3 seconds
        2. AUDIO: Sound/music requirements  
        3. SCRIPT_LINE: Exact opener text to say
        4. OVERLAY: Text overlay strategy
        5. REASONING: Why this hook works for {dominant_intent}
        
        Make it copy-paste actionable for video creators.
        """
        
        response = await self._call_llm(prompt)
        
        # Parse response into structured format
        visual, audio, script_line, overlay, reasoning = self._parse_hook_response(response)
        
        return HookDirective(
            visual=visual,
            audio=audio,
            script_line=script_line,
            overlay=overlay,
            reasoning=reasoning
        )

    async def _generate_retention_blueprint(
        self, 
        post_data: PostData, 
        intent_scores: Dict[str, float]
    ) -> RetentionBlueprint:
        """Generate retention optimization blueprint"""
        
        content_analysis = post_data.content_analysis or {}
        video_analysis = post_data.video_analysis or {}
        
        prompt = f"""
        Generate retention blueprint for high-engagement video recreation:
        
        Original Performance: {post_data.likes:,} likes, {post_data.comments:,} comments
        Content Analysis: {json.dumps(content_analysis, indent=2)[:500]}
        
        Provide specific instructions for:
        1. PACING_RULES: Timing and rhythm guidelines (3-4 rules)
        2. PATTERN_INTERRUPTS: Visual/audio breaks to reset attention (3-4 items)
        3. ANTI_BOREDOM_TRIGGERS: Engagement maintainers throughout video (3-4 items) 
        4. J_CUT_POINTS: Strategic audio-over-video moments (2-3 timestamp suggestions)
        
        Make each instruction actionable for video editors.
        """
        
        response = await self._call_llm(prompt)
        
        # Parse response into lists
        pacing_rules, pattern_interrupts, anti_boredom_triggers, j_cut_points = self._parse_retention_response(response)
        
        return RetentionBlueprint(
            pacing_rules=pacing_rules,
            pattern_interrupts=pattern_interrupts,
            anti_boredom_triggers=anti_boredom_triggers,
            j_cut_points=j_cut_points
        )

    async def _generate_share_catalyst(
        self, 
        post_data: PostData, 
        intent_scores: Dict[str, float]
    ) -> ShareCatalyst:
        """Generate viral sharing catalyst instructions"""
        
        share_ratio = post_data.shares / max(post_data.likes, 1)
        
        prompt = f"""
        Generate share catalyst strategy for viral moment creation:
        
        Original Shares: {post_data.shares} ({share_ratio:.3f} share-to-like ratio)
        Script: "{post_data.full_script[:300]}..."
        
        Identify the moment that made this shareable and provide:
        1. VULNERABILITY_FRAME: Personal revelation moment that creates connection
        2. IDENTITY_MOMENT: When viewer sees themselves in the content  
        3. VISUAL_STYLE_SHIFT: Camera/editing change that amplifies impact
        4. TIMESTAMP: When in video this moment should occur (e.g. "15-20s")
        
        Focus on the psychological triggers that make people hit share.
        """
        
        response = await self._call_llm(prompt)
        
        vulnerability_frame, identity_moment, visual_style_shift, timestamp = self._parse_share_response(response)
        
        return ShareCatalyst(
            vulnerability_frame=vulnerability_frame,
            identity_moment=identity_moment,
            visual_style_shift=visual_style_shift,
            timestamp=timestamp
        )

    async def _generate_conversion_close(
        self, 
        post_data: PostData, 
        intent_scores: Dict[str, float]
    ) -> ConversionClose:
        """Generate conversion optimization close strategy"""
        
        content_analysis = post_data.content_analysis or {}
        cta_data = content_analysis.get('cta', {})
        cta_type = cta_data.get('type', 'none')
        
        comment_ratio = post_data.comments / max(post_data.likes, 1)
        
        prompt = f"""
        Generate conversion close strategy based on high-engagement CTA:
        
        Original CTA Type: {cta_type}
        Comments: {post_data.comments:,} ({comment_ratio:.3f} comment-to-like ratio)
        Script ending: "{post_data.full_script[-200:]}"
        
        Design close strategy with:
        1. CTA_TYPE: Specific call-to-action category (engagement/conversion/growth)
        2. SCRIPT_LINE: Exact closing words that drive action
        3. OPEN_LOOP_TOPIC: Unresolved question to drive follow engagement  
        4. AUTOMATION_TRIGGER: What automated response/sequence this should trigger
        
        Optimize for maximum audience response and follow-through.
        """
        
        response = await self._call_llm(prompt)
        
        cta_type_result, script_line, open_loop_topic, automation_trigger = self._parse_conversion_response(response)
        
        return ConversionClose(
            cta_type=cta_type_result,
            script_line=script_line,
            open_loop_topic=open_loop_topic,
            automation_trigger=automation_trigger
        )

    async def _generate_technical_specs(
        self, 
        post_data: PostData, 
        intent_scores: Dict[str, float]
    ) -> TechnicalSpecs:
        """Generate technical production specifications"""
        
        video_analysis = post_data.video_analysis or {}
        frame_chunks = post_data.frame_chunks or []
        
        prompt = f"""
        Generate technical specs for recreating this high-performing video:
        
        Engagement: {post_data.likes:,} likes, {post_data.comments:,} comments
        Video Analysis: {json.dumps(video_analysis, indent=2)[:300]}
        
        Specify exact requirements for:
        1. LIGHTING: Indoor/outdoor, time of day, mood lighting requirements
        2. CAPTION_STYLE: Font, placement, color, animation timing
        3. COLOR_PALETTE: Primary and accent colors for optimal engagement
        4. MUSIC_BPM: Beats per minute range that matches energy level
        5. VIDEO_LENGTH: Optimal duration for this content type
        
        Make specs copy-paste ready for video producers.
        """
        
        response = await self._call_llm(prompt)
        
        lighting, caption_style, color_palette, music_bpm, video_length = self._parse_technical_response(response)
        
        return TechnicalSpecs(
            lighting=lighting,
            aspect_ratio="9:16",  # Standard for short-form
            center_zone_safety="Top 1/3 for mobile", 
            caption_style=caption_style,
            color_palette=color_palette,
            music_bpm=music_bpm,
            video_length=video_length
        )

    async def _generate_video_prompts(
        self, 
        post_data: PostData, 
        intent_scores: Dict[str, float],
        dominant_intent: str
    ) -> GeneratorPrompts:
        """Generate copy-paste ready prompts for Veo and Nano Banana"""
        
        strategy_directive = STRATEGY_MAP.get(dominant_intent, "Create engaging short-form content")
        
        prompt = f"""
        Generate video creation prompts based on this high-performing content:
        
        Original Hook: "{post_data.hook}"
        Strategy: {strategy_directive}
        Performance: {post_data.likes:,} likes, {post_data.comments:,} comments
        Dominant Intent: {dominant_intent}
        
        Create two ready-to-use prompts:
        
        1. VEO_PROMPT: Detailed video generation prompt for Google's Veo
        2. NANO_BANANA_PROMPT: Quick social media video prompt for Nano Banana
        
        Include specific visual style, pacing, and content direction. 
        Make them immediately actionable for content creators.
        """
        
        response = await self._call_llm(prompt)
        
        veo_prompt, nano_banana_prompt = self._parse_prompt_response(response)
        
        return GeneratorPrompts(
            veo_prompt=veo_prompt,
            nano_banana_prompt=nano_banana_prompt
        )

    async def _call_llm(self, prompt: str) -> str:
        """Call LLM with local Ollama first, fallback to any available"""
        try:
            # Try local Ollama first
            response = await self.ollama_client.post(
                "/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("response", "")
                
        except Exception as e:
            logger.warning("Ollama unavailable, using fallback: %s", e)
        
        # Fallback to simple template-based response if LLM unavailable
        return self._generate_fallback_response(prompt)

    def _generate_fallback_response(self, prompt: str) -> str:
        """Generate a basic template response when LLM is unavailable"""
        if "hook directive" in prompt.lower():
            return """
            VISUAL: Dynamic opener with text overlay
            AUDIO: Upbeat background music, clear narration
            SCRIPT_LINE: Start with a hook that grabs attention immediately
            OVERLAY: Bold text highlighting key point
            REASONING: Creates immediate engagement and scroll-stopping moment
            """
        elif "retention blueprint" in prompt.lower():
            return """
            PACING_RULES: 
            - Cut every 2-3 seconds to maintain attention
            - Vary shot sizes from close-up to medium
            - Use quick transitions between segments
            
            PATTERN_INTERRUPTS:
            - Text pop-ups at 5s and 15s marks
            - Sound effect at major points
            - Visual zoom/pan changes
            
            ANTI_BOREDOM_TRIGGERS:
            - Tease upcoming content early
            - Use countdown timers
            - Include before/after reveals
            
            J_CUT_POINTS:
            - 8-10s: Audio continues over new visual
            - 25-30s: Narration over supporting footage
            """
        else:
            return "Template response generated due to LLM unavailability"

    # Response parsing methods
    def _parse_hook_response(self, response: str) -> Tuple[str, str, str, str, str]:
        """Parse hook directive response into components"""
        lines = [line.strip() for line in response.split('\n') if line.strip()]
        
        visual = ""
        audio = ""
        script_line = ""
        overlay = ""
        reasoning = ""
        
        current_section = ""
        for line in lines:
            if line.upper().startswith(("VISUAL:", "1. VISUAL")):
                current_section = "visual"
                visual = line.split(':', 1)[1].strip() if ':' in line else ""
            elif line.upper().startswith(("AUDIO:", "2. AUDIO")):
                current_section = "audio"  
                audio = line.split(':', 1)[1].strip() if ':' in line else ""
            elif line.upper().startswith(("SCRIPT_LINE:", "3. SCRIPT", "SCRIPT:")):
                current_section = "script"
                script_line = line.split(':', 1)[1].strip() if ':' in line else ""
            elif line.upper().startswith(("OVERLAY:", "4. OVERLAY")):
                current_section = "overlay"
                overlay = line.split(':', 1)[1].strip() if ':' in line else ""
            elif line.upper().startswith(("REASONING:", "5. REASONING")):
                current_section = "reasoning"
                reasoning = line.split(':', 1)[1].strip() if ':' in line else ""
            elif current_section and not line.startswith(('1.', '2.', '3.', '4.', '5.')):
                # Continue previous section
                if current_section == "visual":
                    visual += " " + line
                elif current_section == "audio":
                    audio += " " + line
                elif current_section == "script":
                    script_line += " " + line
                elif current_section == "overlay":
                    overlay += " " + line
                elif current_section == "reasoning":
                    reasoning += " " + line
        
        return (
            visual[:300] or "Dynamic visual opener",
            audio[:200] or "Clear audio with background music", 
            script_line[:200] or "Attention-grabbing opening line",
            overlay[:200] or "Bold text overlay",
            reasoning[:300] or "Creates immediate engagement"
        )

    def _parse_retention_response(self, response: str) -> Tuple[List[str], List[str], List[str], List[str]]:
        """Parse retention blueprint response"""
        lines = [line.strip() for line in response.split('\n') if line.strip()]
        
        pacing_rules = []
        pattern_interrupts = []
        anti_boredom_triggers = []
        j_cut_points = []
        
        current_section = ""
        
        for line in lines:
            upper_line = line.upper()
            if "PACING_RULES" in upper_line or "PACING RULES" in upper_line:
                current_section = "pacing"
                continue
            elif "PATTERN_INTERRUPTS" in upper_line or "PATTERN INTERRUPTS" in upper_line:
                current_section = "interrupts"
                continue
            elif "ANTI_BOREDOM" in upper_line or "BOREDOM TRIGGERS" in upper_line:
                current_section = "boredom"
                continue
            elif "J_CUT" in upper_line or "J CUT" in upper_line:
                current_section = "jcuts"
                continue
            
            if line.startswith(('-', '•', '*')) or line[0:2].isdigit():
                cleaned_line = line.lstrip('-•*0123456789. ').strip()
                if current_section == "pacing":
                    pacing_rules.append(cleaned_line)
                elif current_section == "interrupts":
                    pattern_interrupts.append(cleaned_line)
                elif current_section == "boredom":
                    anti_boredom_triggers.append(cleaned_line)
                elif current_section == "jcuts":
                    j_cut_points.append(cleaned_line)
        
        # Fallbacks if parsing failed
        return (
            pacing_rules or ["Cut every 2-3 seconds", "Vary shot sizes", "Quick transitions"],
            pattern_interrupts or ["Text pop-ups", "Sound effects", "Visual changes"],
            anti_boredom_triggers or ["Tease upcoming content", "Use timers", "Before/after reveals"],
            j_cut_points or ["8-10s: Audio over new visual", "25-30s: Narration over footage"]
        )

    def _parse_share_response(self, response: str) -> Tuple[str, str, str, str]:
        """Parse share catalyst response"""
        lines = [line.strip() for line in response.split('\n') if line.strip()]
        
        vulnerability_frame = ""
        identity_moment = ""
        visual_style_shift = ""
        timestamp = ""
        
        for line in lines:
            upper_line = line.upper()
            if "VULNERABILITY" in upper_line and ':' in line:
                vulnerability_frame = line.split(':', 1)[1].strip()
            elif "IDENTITY" in upper_line and ':' in line:
                identity_moment = line.split(':', 1)[1].strip()
            elif "VISUAL" in upper_line and "SHIFT" in upper_line and ':' in line:
                visual_style_shift = line.split(':', 1)[1].strip()
            elif "TIMESTAMP" in upper_line and ':' in line:
                timestamp = line.split(':', 1)[1].strip()
        
        return (
            vulnerability_frame[:300] or "Personal revelation moment",
            identity_moment[:300] or "Viewer sees themselves in content", 
            visual_style_shift[:200] or "Camera angle change for impact",
            timestamp or "15-20s"
        )

    def _parse_conversion_response(self, response: str) -> Tuple[str, str, str, str]:
        """Parse conversion close response"""
        lines = [line.strip() for line in response.split('\n') if line.strip()]
        
        cta_type = ""
        script_line = ""
        open_loop_topic = ""
        automation_trigger = ""
        
        for line in lines:
            upper_line = line.upper()
            if "CTA_TYPE" in upper_line and ':' in line:
                cta_type = line.split(':', 1)[1].strip()
            elif "SCRIPT_LINE" in upper_line and ':' in line:
                script_line = line.split(':', 1)[1].strip()
            elif "OPEN_LOOP" in upper_line and ':' in line:
                open_loop_topic = line.split(':', 1)[1].strip()
            elif "AUTOMATION" in upper_line and "TRIGGER" in upper_line and ':' in line:
                automation_trigger = line.split(':', 1)[1].strip()
        
        return (
            cta_type or "engagement",
            script_line[:200] or "What do you think about this?",
            open_loop_topic[:200] or "Next week I'll reveal the secret technique", 
            automation_trigger[:200] or "Auto-reply to comments"
        )

    def _parse_technical_response(self, response: str) -> Tuple[str, str, str, str, str]:
        """Parse technical specs response"""
        lines = [line.strip() for line in response.split('\n') if line.strip()]
        
        lighting = ""
        caption_style = ""
        color_palette = ""
        music_bpm = ""
        video_length = ""
        
        for line in lines:
            upper_line = line.upper()
            if "LIGHTING" in upper_line and ':' in line:
                lighting = line.split(':', 1)[1].strip()
            elif "CAPTION" in upper_line and ':' in line:
                caption_style = line.split(':', 1)[1].strip()
            elif "COLOR" in upper_line and ':' in line:
                color_palette = line.split(':', 1)[1].strip()
            elif "BPM" in upper_line and ':' in line:
                music_bpm = line.split(':', 1)[1].strip()
            elif "LENGTH" in upper_line and ':' in line:
                video_length = line.split(':', 1)[1].strip()
        
        return (
            lighting[:200] or "Natural daylight, soft shadows",
            caption_style[:200] or "Bold sans-serif, yellow on black",
            color_palette[:200] or "High contrast, vibrant accents",
            music_bpm or "120-140 BPM",
            video_length or "30-45 seconds"
        )

    def _parse_prompt_response(self, response: str) -> Tuple[str, str]:
        """Parse video generation prompts"""
        lines = [line.strip() for line in response.split('\n') if line.strip()]
        
        veo_prompt = ""
        nano_banana_prompt = ""
        
        current_section = ""
        
        for line in lines:
            upper_line = line.upper()
            if "VEO_PROMPT" in upper_line or ("VEO" in upper_line and "PROMPT" in upper_line):
                current_section = "veo"
                if ':' in line:
                    veo_prompt = line.split(':', 1)[1].strip()
                continue
            elif "NANO_BANANA" in upper_line or ("NANO" in upper_line and "BANANA" in upper_line):
                current_section = "nano"
                if ':' in line:
                    nano_banana_prompt = line.split(':', 1)[1].strip()
                continue
            
            # Continue building current prompt
            if current_section == "veo" and line:
                veo_prompt += " " + line if veo_prompt else line
            elif current_section == "nano" and line:
                nano_banana_prompt += " " + line if nano_banana_prompt else line
        
        return (
            veo_prompt[:500] or "Create high-engagement short-form video with clear hook and strong retention",
            nano_banana_prompt[:300] or "Quick viral video with trending format and clear CTA"
        )

    async def close(self):
        """Clean up HTTP clients"""
        await self.ollama_client.aclose()


# Database functions
async def get_post_data(db: AsyncSession, post_id: int) -> Optional[PostData]:
    """Retrieve post data for CDR generation"""
    result = await db.execute(
        text("""
            SELECT 
                cp.id,
                cp.shortcode,
                c.handle,
                cp.hook,
                cp.full_script,
                cp.likes,
                cp.comments, 
                cp.shares,
                cp.engagement_score,
                cp.content_analysis,
                cp.video_analysis,
                cp.frame_chunks,
                cp.posted_at
            FROM crm.competitor_posts cp
            JOIN crm.competitors c ON cp.competitor_id = c.id
            WHERE cp.id = :post_id
        """),
        {"post_id": post_id}
    )
    
    row = result.fetchone()
    if not row:
        return None
    
    return PostData(
        post_id=row[0],
        shortcode=row[1] or "",
        competitor_handle=row[2] or "",
        hook=row[3] or "",
        full_script=row[4] or "",
        likes=row[5] or 0,
        comments=row[6] or 0,
        shares=row[7] or 0,
        engagement_score=row[8] or 0,
        content_analysis=json.loads(row[9]) if row[9] else {},
        video_analysis=json.loads(row[10]) if row[10] else {},
        frame_chunks=json.loads(row[11]) if row[11] else [],
        posted_at=row[12]
    )

async def get_high_power_posts(db: AsyncSession, org_id: int, limit: int = 10) -> List[int]:
    """Get post IDs with highest power scores for CDR generation"""
    result = await db.execute(
        text("""
            SELECT cp.id
            FROM crm.competitor_posts cp
            JOIN crm.competitors c ON cp.competitor_id = c.id  
            WHERE cp.org_id = :org_id
              AND cp.engagement_score > 100
              AND cp.content_analysis IS NOT NULL
              AND cp.likes > 1000
            ORDER BY cp.engagement_score DESC
            LIMIT :limit
        """),
        {"org_id": org_id, "limit": limit}
    )
    
    return [row[0] for row in result.fetchall()]

async def store_cdr(db: AsyncSession, cdr: CreatorDirectiveReport) -> None:
    """Store CDR in database"""
    await db.execute(
        text("""
            UPDATE crm.competitor_posts 
            SET creator_directive_report = :cdr
            WHERE id = :post_id
        """),
        {
            "cdr": json.dumps(cdr.model_dump()),
            "post_id": cdr.post_id
        }
    )
    await db.commit()

# Mock intent classifier for testing (replace with actual service when available)
def mock_intent_classifier(content_analysis: Dict) -> Dict[str, float]:
    """Mock intent classification - replace with actual intent_classifier.py output"""
    hook = content_analysis.get('hook', {})
    value = content_analysis.get('value', {})
    cta = content_analysis.get('cta', {})
    
    scores = {
        "UTILITY_SAVE": 0.0,
        "IDENTITY_SHARE": 0.0,
        "CURIOSITY_GAP": 0.0,
        "FRICTION_POINT": 0.0,
        "SOCIAL_PROOF": 0.0
    }
    
    # Simple rule-based classification for testing
    hook_text = hook.get('text', '').lower()
    hook_type = hook.get('type', '')
    
    if any(word in hook_text for word in ['tip', 'hack', 'cheat sheet', 'save this']):
        scores["UTILITY_SAVE"] = 0.8
    elif hook_type == 'question' or any(word in hook_text for word in ['you', 'your', 'relate']):
        scores["IDENTITY_SHARE"] = 0.7
    elif any(word in hook_text for word in ['secret', 'never', 'reveal', 'finally']):
        scores["CURIOSITY_GAP"] = 0.9
    elif any(word in hook_text for word in ['mistake', 'wrong', 'avoid']):
        scores["FRICTION_POINT"] = 0.6
    else:
        scores["SOCIAL_PROOF"] = 0.5
    
    return scores