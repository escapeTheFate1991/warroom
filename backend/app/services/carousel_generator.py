"""Carousel Generator Service

Converts long-form text content into carousel slides optimized for Instagram.
Integrates with Nano Banana for branded image generation.
"""

import logging
import re
from typing import List, Dict, Any, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .nano_banana import call_gemini_api, _get_api_key

logger = logging.getLogger(__name__)

# Character limits per format
FORMAT_LIMITS = {
    "portrait": 320,  # 4:5 aspect ratio
    "square": 280,    # 1:1 aspect ratio  
    "story": 400      # 9:16 aspect ratio
}

class CarouselGenerator:
    """Generates carousel slides from text content."""
    
    async def split_text_to_slides(self, text: str, format: str = "portrait") -> List[Dict[str, Any]]:
        """Split text into carousel slides.
        
        Args:
            text: Long-form content to split
            format: Format type - portrait (4:5, ~320 chars), square (1:1, ~280 chars), story (9:16, ~400 chars)
            
        Returns:
            List of slide dicts: [{"slide_num": 1, "text": "...", "is_hook": True}, ...]
            
        Rules:
            - Slide 1 is always the hook (short, punchy)
            - Last slide is CTA
            - Respect paragraph breaks
            - Smart word-boundary splitting
        """
        if not text or not text.strip():
            raise ValueError("Text content is required")
            
        char_limit = FORMAT_LIMITS.get(format, 320)
        
        # Clean and normalize text
        clean_text = re.sub(r'\s+', ' ', text.strip())
        
        # Split by paragraphs first
        paragraphs = [p.strip() for p in clean_text.split('\n') if p.strip()]
        
        slides = []
        current_slide_text = ""
        slide_num = 1
        
        # Generate hook slide (first slide)
        hook = await self._generate_hook(clean_text[:500])  # Use first 500 chars for context
        slides.append({
            "slide_num": slide_num,
            "text": hook,
            "is_hook": True,
            "image_url": None
        })
        slide_num += 1
        
        # Process paragraphs into content slides
        for paragraph in paragraphs:
            # If adding this paragraph would exceed limit, create new slide
            if current_slide_text and len(current_slide_text) + len(paragraph) + 2 > char_limit:
                slides.append({
                    "slide_num": slide_num,
                    "text": current_slide_text.strip(),
                    "is_hook": False,
                    "image_url": None
                })
                slide_num += 1
                current_slide_text = ""
            
            # If paragraph itself is too long, split it
            if len(paragraph) > char_limit:
                # Split the current accumulated text first if any
                if current_slide_text:
                    slides.append({
                        "slide_num": slide_num,
                        "text": current_slide_text.strip(),
                        "is_hook": False,
                        "image_url": None
                    })
                    slide_num += 1
                    current_slide_text = ""
                
                # Split the long paragraph
                chunks = self._split_long_text(paragraph, char_limit)
                for chunk in chunks:
                    slides.append({
                        "slide_num": slide_num,
                        "text": chunk.strip(),
                        "is_hook": False,
                        "image_url": None
                    })
                    slide_num += 1
            else:
                # Add paragraph to current slide
                if current_slide_text:
                    current_slide_text += "\n\n" + paragraph
                else:
                    current_slide_text = paragraph
        
        # Handle any remaining text
        if current_slide_text.strip():
            slides.append({
                "slide_num": slide_num,
                "text": current_slide_text.strip(),
                "is_hook": False,
                "image_url": None
            })
            slide_num += 1
        
        # Generate CTA slide (last slide)
        cta = await self._generate_cta(clean_text)
        slides.append({
            "slide_num": slide_num,
            "text": cta,
            "is_hook": False,
            "is_cta": True,
            "image_url": None
        })
        
        # Limit to max 10 slides for Instagram
        if len(slides) > 10:
            # Keep hook and CTA, compress middle slides
            hook_slide = slides[0]
            cta_slide = slides[-1]
            middle_slides = slides[1:-1]
            
            # Compress middle content into 8 slides max
            compressed_middle = await self._compress_slides(middle_slides, 8, char_limit)
            
            slides = [hook_slide] + compressed_middle + [cta_slide]
        
        return slides
    
    async def _generate_hook(self, text_preview: str, db: Optional[AsyncSession] = None) -> str:
        """Generate a compelling hook for the first slide."""
        api_key = await _get_api_key(db)
        
        prompt = f"""Create a compelling hook for a social media carousel based on this content:

"{text_preview}"

Requirements:
- Maximum 50 words
- Attention-grabbing and curiosity-driven
- Use power words and emotional triggers
- End with intrigue (e.g., "Here's what changed everything...")
- Don't reveal the main point yet
- Make people want to swipe to learn more

Generate just the hook text, no quotes or extra formatting."""

        messages = [{
            "role": "user",
            "parts": [{"text": prompt}]
        }]
        
        generation_config = {
            "responseModalities": ["TEXT"],
            "temperature": 0.8,
            "topK": 40,
            "topP": 0.9
        }
        
        result = await call_gemini_api(api_key, "gemini-2.0-flash", messages, generation_config)
        
        # Extract text response
        candidates = result.get("candidates", [])
        if not candidates:
            return "This will change how you think about everything. Swipe to see why →"
        
        content = candidates[0].get("content", {})
        parts = content.get("parts", [])
        
        hook_text = ""
        for part in parts:
            if "text" in part:
                hook_text += part["text"]
        
        return hook_text.strip() or "This will change how you think about everything. Swipe to see why →"
    
    async def _generate_cta(self, full_text: str, db: Optional[AsyncSession] = None) -> str:
        """Generate a call-to-action for the final slide."""
        api_key = await _get_api_key(db)
        
        prompt = f"""Create a compelling call-to-action for the final slide of a social media carousel based on this content:

"{full_text[:500]}..."

Requirements:
- Maximum 80 words
- Encourage engagement (like, comment, follow, share)
- Ask a question or prompt discussion
- Include relevant emoji
- Make it actionable and specific
- End with engagement prompts like "What's your take?" or "Try this and let me know!"

Generate just the CTA text, no quotes or extra formatting."""

        messages = [{
            "role": "user", 
            "parts": [{"text": prompt}]
        }]
        
        generation_config = {
            "responseModalities": ["TEXT"],
            "temperature": 0.8,
            "topK": 40,
            "topP": 0.9
        }
        
        result = await call_gemini_api(api_key, "gemini-2.0-flash", messages, generation_config)
        
        # Extract text response
        candidates = result.get("candidates", [])
        if not candidates:
            return "💭 What's your take on this? Let me know in the comments!\n\n🔄 Share if this helped you\n👤 Follow for more insights like this"
        
        content = candidates[0].get("content", {})
        parts = content.get("parts", [])
        
        cta_text = ""
        for part in parts:
            if "text" in part:
                cta_text += part["text"]
        
        return cta_text.strip() or "💭 What's your take on this? Let me know in the comments!\n\n🔄 Share if this helped you\n👤 Follow for more insights like this"
    
    def _split_long_text(self, text: str, char_limit: int) -> List[str]:
        """Split long text at word boundaries."""
        if len(text) <= char_limit:
            return [text]
        
        chunks = []
        words = text.split()
        current_chunk = ""
        
        for word in words:
            # If adding this word would exceed limit, start new chunk
            if current_chunk and len(current_chunk) + len(word) + 1 > char_limit:
                chunks.append(current_chunk.strip())
                current_chunk = word
            else:
                if current_chunk:
                    current_chunk += " " + word
                else:
                    current_chunk = word
        
        # Add remaining chunk
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    async def _compress_slides(self, slides: List[Dict[str, Any]], max_slides: int, char_limit: int) -> List[Dict[str, Any]]:
        """Compress slides to fit within max_slides limit while respecting char_limit."""
        if len(slides) <= max_slides:
            return slides
        
        # Combine slides intelligently
        compressed = []
        slides_per_group = len(slides) // max_slides
        remainder = len(slides) % max_slides
        
        current_index = 0
        for i in range(max_slides):
            group_size = slides_per_group + (1 if i < remainder else 0)
            group_slides = slides[current_index:current_index + group_size]
            
            # Combine text from group slides
            combined_text = ""
            for slide in group_slides:
                if combined_text:
                    combined_text += "\n\n" + slide["text"]
                else:
                    combined_text = slide["text"]
            
            # Truncate if too long
            if len(combined_text) > char_limit:
                # Find the last complete sentence that fits
                sentences = combined_text.split('. ')
                fit_text = ""
                for sentence in sentences:
                    if len(fit_text) + len(sentence) + 2 <= char_limit:
                        if fit_text:
                            fit_text += ". " + sentence
                        else:
                            fit_text = sentence
                    else:
                        break
                combined_text = fit_text + ("." if not fit_text.endswith('.') else "")
            
            compressed.append({
                "slide_num": i + 2,  # +2 because hook is slide 1
                "text": combined_text,
                "is_hook": False,
                "image_url": None
            })
            
            current_index += group_size
        
        return compressed
    
    async def generate_carousel_images(
        self, 
        slides: List[Dict[str, Any]], 
        brand_colors: Dict[str, str], 
        org_id: int,
        db: Optional[AsyncSession] = None
    ) -> List[str]:
        """Generate branded images for each slide using Nano Banana.
        
        Args:
            slides: List of slide dicts with text content
            brand_colors: Dict with brand color scheme (primary, secondary, background, text)
            org_id: Organization ID for branding context
            db: Database session for API key lookup
            
        Returns:
            List of image URLs/paths for each slide
        """
        from .nano_banana import call_gemini_api, encode_image_for_gemini
        import base64
        import os
        
        api_key = await _get_api_key(db)
        image_urls = []
        
        # Default brand colors if not provided
        default_colors = {
            "primary": "#007bff",
            "secondary": "#6c757d", 
            "background": "#ffffff",
            "text": "#212529"
        }
        colors = {**default_colors, **brand_colors}
        
        for slide in slides:
            try:
                # Create image generation prompt
                prompt = f"""Create a professional Instagram carousel slide image with the following text content:

Text: "{slide['text']}"

Design Requirements:
- Clean, modern layout suitable for Instagram
- Background color: {colors['background']}
- Primary text color: {colors['text']}
- Accent color: {colors['primary']}
- Typography: Bold, readable sans-serif font
- Include subtle brand elements or geometric shapes
- Text should be prominently displayed and easy to read on mobile
- Slide {slide['slide_num']} of carousel
- Maintain consistent style with professional business aesthetic
- Image dimensions suitable for Instagram carousel (1080x1350 px portrait)

Style: Professional social media graphic, clean typography, modern design"""

                messages = [{
                    "role": "user",
                    "parts": [{"text": prompt}]
                }]
                
                generation_config = {
                    "responseModalities": ["TEXT", "IMAGE"],
                    "temperature": 0.3,
                    "topK": 32,
                    "topP": 0.8
                }
                
                result = await call_gemini_api(api_key, "gemini-2.0-flash-exp", messages, generation_config)
                
                # Extract image from response
                candidates = result.get("candidates", [])
                if candidates:
                    content = candidates[0].get("content", {})
                    parts = content.get("parts", [])
                    
                    for part in parts:
                        if "inlineData" in part:
                            image_data = part["inlineData"]["data"]
                            image_bytes = base64.b64decode(image_data)
                            
                            # Save image to uploads directory
                            upload_dir = f"app/uploads/carousel/{org_id}"
                            os.makedirs(upload_dir, exist_ok=True)
                            
                            filename = f"slide_{slide['slide_num']}_{slide.get('id', 'temp')}.png"
                            filepath = os.path.join(upload_dir, filename)
                            
                            with open(filepath, 'wb') as f:
                                f.write(image_bytes)
                            
                            # Return relative path for API access
                            image_url = f"/uploads/carousel/{org_id}/{filename}"
                            image_urls.append(image_url)
                            break
                    else:
                        # No image found, use placeholder
                        image_urls.append(None)
                else:
                    image_urls.append(None)
                    
            except Exception as e:
                logger.error(f"Failed to generate image for slide {slide['slide_num']}: {e}")
                image_urls.append(None)
        
        return image_urls