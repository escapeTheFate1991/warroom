"""Social Post Generator - Create platform-optimized posts from extracted content.

Generates posts tailored for Instagram, TikTok, Twitter, LinkedIn, and Facebook with
platform-specific character limits, formatting, and best practices.
"""

import logging
import re
from typing import Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.nano_banana import _get_api_key, call_gemini_api

logger = logging.getLogger(__name__)

# Platform configurations with limits and capabilities
PLATFORM_CONFIGS = {
    'instagram': {
        'max_chars': 2200,
        'supports_carousel': True,
        'supports_video': True,
        'hashtag_limit': 30,
        'hashtag_style': 'inline',  # Mix hashtags with text
        'tone': 'visual_storytelling'
    },
    'tiktok': {
        'max_chars': 2200,
        'supports_carousel': False,
        'supports_video': True,
        'hashtag_limit': 20,
        'hashtag_style': 'inline',
        'tone': 'trendy_engaging'
    },
    'twitter': {
        'max_chars': 280,
        'supports_carousel': False,
        'supports_video': True,
        'hashtag_limit': 5,
        'hashtag_style': 'minimal',
        'tone': 'concise_witty'
    },
    'linkedin': {
        'max_chars': 3000,
        'supports_carousel': True,
        'supports_video': True,
        'hashtag_limit': 10,
        'hashtag_style': 'professional',
        'tone': 'professional_insightful'
    },
    'facebook': {
        'max_chars': 63206,
        'supports_carousel': True,
        'supports_video': True,
        'hashtag_limit': 15,
        'hashtag_style': 'moderate',
        'tone': 'conversational_engaging'
    }
}

class SocialPostGenerator:
    """Generate platform-optimized social media posts."""
    
    def __init__(self, db: Optional[AsyncSession] = None):
        self.db = db
    
    async def generate_posts(
        self, 
        content: Dict, 
        platforms: List[str], 
        tone: str = "professional"
    ) -> Dict:
        """Generate platform-optimized posts from extracted content.
        
        Args:
            content: Content dict from ContentExtractor
            platforms: List of platforms to generate for
            tone: Overall tone (professional, casual, funny, inspiring)
            
        Returns:
            {
                platform: {
                    text: str,
                    hashtags: List[str],
                    suggested_media: List[str],
                    post_type: str,  # "text", "image", "video", "carousel"
                    character_count: int,
                    truncated: bool
                }
            }
        """
        logger.info(f"Generating posts for platforms: {platforms}")
        
        posts = {}
        
        # Validate platforms
        valid_platforms = [p for p in platforms if p in PLATFORM_CONFIGS]
        if not valid_platforms:
            logger.warning(f"No valid platforms in {platforms}")
            return {}
        
        # Get social summary if not already available
        social_summary = content.get('social_summary')
        if not social_summary and hasattr(content, 'get'):
            from app.services.content_extractor import ContentExtractor
            extractor = ContentExtractor(self.db)
            social_summary = await extractor.summarize_for_social(content)
        
        if not social_summary:
            social_summary = self._fallback_social_summary(content)
        
        # Generate posts for each platform
        for platform in valid_platforms:
            try:
                post = await self._generate_platform_post(
                    platform, content, social_summary, tone
                )
                posts[platform] = post
            except Exception as e:
                logger.error(f"Failed to generate {platform} post: {e}")
                posts[platform] = self._fallback_post(platform, content)
        
        return posts
    
    async def generate_variations(self, post: Dict, count: int = 3) -> List[Dict]:
        """Generate A/B test variations of a post.
        
        Args:
            post: Original post dict with text, hashtags, etc.
            count: Number of variations to generate
            
        Returns:
            List of post variations
        """
        logger.info(f"Generating {count} variations of post")
        
        variations = []
        original_text = post.get('text', '')
        
        if not original_text:
            logger.warning("No text in original post for variations")
            return [post]
        
        try:
            prompt = f"""
Create {count} different variations of this social media post. Keep the core message but vary:
- Hook/opening line
- Phrasing and word choice  
- Emoji usage
- Call-to-action

Original post:
{original_text}

Return as JSON array:
[
  {{"text": "variation 1...", "reason": "why this variation works"}},
  {{"text": "variation 2...", "reason": "why this variation works"}},
  {{"text": "variation 3...", "reason": "why this variation works"}}
]
"""
            
            result = await self._call_gemini_for_generation(prompt)
            
            if result and "candidates" in result:
                response_text = result["candidates"][0]["content"]["parts"][0]["text"]
                # Clean up markdown if present
                response_text = re.sub(r'```json\s*|\s*```', '', response_text)
                
                import json
                variations_data = json.loads(response_text)
                
                for i, var_data in enumerate(variations_data):
                    if isinstance(var_data, dict) and 'text' in var_data:
                        variation = post.copy()
                        variation['text'] = var_data['text']
                        variation['character_count'] = len(var_data['text'])
                        variation['variation_reason'] = var_data.get('reason', f'Variation {i+1}')
                        variations.append(variation)
        
        except Exception as e:
            logger.error(f"Variation generation failed: {e}")
        
        # If AI generation failed, create simple variations manually
        if not variations:
            variations = self._create_manual_variations(post, count)
        
        return variations[:count]
    
    # Private helper methods
    
    async def _generate_platform_post(
        self, 
        platform: str, 
        content: Dict, 
        social_summary: Dict, 
        tone: str
    ) -> Dict:
        """Generate a post optimized for specific platform."""
        config = PLATFORM_CONFIGS[platform]
        
        # Determine post type based on available media
        post_type = self._determine_post_type(content, config)
        
        # Create platform-specific prompt
        prompt = self._create_platform_prompt(platform, content, social_summary, tone, config)
        
        # Generate post with AI
        result = await self._call_gemini_for_generation(prompt)
        
        if result and "candidates" in result:
            response_text = result["candidates"][0]["content"]["parts"][0]["text"]
            return self._parse_ai_response(response_text, platform, content, config, post_type)
        else:
            # Fallback generation
            return self._create_manual_post(platform, content, social_summary, config, post_type)
    
    def _create_platform_prompt(
        self, 
        platform: str, 
        content: Dict, 
        social_summary: Dict, 
        tone: str, 
        config: Dict
    ) -> str:
        """Create AI prompt for platform-specific post generation."""
        
        platform_guidelines = {
            'instagram': "Visual storytelling with engaging captions. Mix hashtags naturally in text.",
            'tiktok': "Trendy, engaging, with popular hashtags. Hook viewers immediately.",
            'twitter': "Concise and impactful. Every word counts. Minimal hashtags.",
            'linkedin': "Professional insights with value for business audience. Thoughtful hashtags.",
            'facebook': "Conversational and community-focused. Encourage engagement."
        }
        
        content_preview = content.get('body_text', '')[:500]
        title = content.get('title', '')
        
        prompt = f"""
Create a {platform} post from this content:

CONTENT INFO:
Title: {title}
Source: {content.get('source_url', '')}
Type: {content.get('content_type', 'article')}
Content preview: {content_preview}

SOCIAL SUMMARY:
Hook: {social_summary.get('hook', '')}
Key points: {', '.join(social_summary.get('main_points', []))}
CTA: {social_summary.get('cta', '')}
Suggested hashtags: {', '.join(social_summary.get('suggested_hashtags', []))}

PLATFORM REQUIREMENTS:
- Platform: {platform}
- Max characters: {config['max_chars']}
- Tone: {config['tone']} with {tone} approach
- Hashtag limit: {config['hashtag_limit']}
- Guidelines: {platform_guidelines.get(platform, '')}

Generate a compelling post that:
1. Hooks the audience immediately
2. Delivers value from the content
3. Includes a strong call-to-action
4. Uses appropriate hashtags for discoverability
5. Stays within character limits

Return as JSON:
{{
  "text": "the full post text with hashtags",
  "hashtags": ["#hashtag1", "#hashtag2"],
  "key_message": "the core value proposition"
}}
"""
        return prompt
    
    def _parse_ai_response(
        self, 
        response_text: str, 
        platform: str, 
        content: Dict, 
        config: Dict, 
        post_type: str
    ) -> Dict:
        """Parse AI-generated response into structured post data."""
        try:
            # Clean up markdown code blocks if present
            response_text = re.sub(r'```json\s*|\s*```', '', response_text)
            
            import json
            data = json.loads(response_text)
            
            post_text = data.get('text', '')
            hashtags = data.get('hashtags', [])
            
            # Ensure character limits
            if len(post_text) > config['max_chars']:
                post_text = self._truncate_post(post_text, config['max_chars'])
            
            # Ensure hashtag limits  
            if len(hashtags) > config['hashtag_limit']:
                hashtags = hashtags[:config['hashtag_limit']]
            
            return {
                'text': post_text,
                'hashtags': hashtags,
                'suggested_media': content.get('images', [])[:3],
                'post_type': post_type,
                'character_count': len(post_text),
                'truncated': len(data.get('text', '')) > config['max_chars'],
                'key_message': data.get('key_message', ''),
                'platform': platform
            }
            
        except Exception as e:
            logger.error(f"Failed to parse AI response: {e}")
            return self._create_manual_post(platform, content, {}, config, post_type)
    
    def _create_manual_post(
        self, 
        platform: str, 
        content: Dict, 
        social_summary: Dict, 
        config: Dict, 
        post_type: str
    ) -> Dict:
        """Create a basic post manually when AI generation fails."""
        title = content.get('title', 'Check this out!')
        hook = social_summary.get('hook', f"📖 {title}")
        cta = social_summary.get('cta', 'Check it out!')
        hashtags = social_summary.get('suggested_hashtags', ['#content'])[:config['hashtag_limit']]
        
        if platform == 'twitter':
            # Twitter requires extreme brevity
            text = f"{hook}\n\n{cta}\n\n{' '.join(hashtags[:3])}"
        elif platform == 'linkedin':
            # LinkedIn allows more professional detail
            main_points = social_summary.get('main_points', ['Great insights shared'])
            points_text = '\n• '.join(main_points[:3])
            text = f"{hook}\n\n• {points_text}\n\n{cta}\n\n{' '.join(hashtags)}"
        else:
            # Instagram, TikTok, Facebook
            main_point = social_summary.get('main_points', ['Interesting insights'])[0] if social_summary.get('main_points') else 'Worth checking out!'
            text = f"{hook}\n\n{main_point}\n\n{cta}\n\n{' '.join(hashtags)}"
        
        # Truncate if needed
        if len(text) > config['max_chars']:
            text = self._truncate_post(text, config['max_chars'])
        
        return {
            'text': text,
            'hashtags': hashtags,
            'suggested_media': content.get('images', [])[:3],
            'post_type': post_type,
            'character_count': len(text),
            'truncated': False,
            'key_message': title,
            'platform': platform
        }
    
    def _determine_post_type(self, content: Dict, config: Dict) -> str:
        """Determine the best post type based on content and platform capabilities."""
        images = content.get('images', [])
        content_type = content.get('content_type', 'article')
        
        if content_type == 'youtube' and config['supports_video']:
            return 'video'
        elif len(images) > 1 and config['supports_carousel']:
            return 'carousel'
        elif len(images) >= 1:
            return 'image'
        else:
            return 'text'
    
    def _truncate_post(self, text: str, max_chars: int) -> str:
        """Intelligently truncate post while preserving readability."""
        if len(text) <= max_chars:
            return text
        
        # Try to cut at sentence boundaries first
        sentences = text.split('. ')
        truncated = ''
        
        for sentence in sentences:
            if len(truncated + sentence + '. ') <= max_chars - 3:  # Leave room for "..."
                truncated += sentence + '. '
            else:
                break
        
        if truncated:
            return truncated.rstrip() + '...'
        
        # If no sentence breaks work, cut at word boundaries
        words = text.split()
        truncated = ''
        
        for word in words:
            if len(truncated + word + ' ') <= max_chars - 3:
                truncated += word + ' '
            else:
                break
        
        return truncated.rstrip() + '...'
    
    def _create_manual_variations(self, post: Dict, count: int) -> List[Dict]:
        """Create simple manual variations when AI fails."""
        variations = []
        original_text = post.get('text', '')
        
        # Create variations by modifying hooks and CTAs
        hooks = ['🔥', '✨', '💡', '🚀', '👀']
        ctas = ['Check it out!', 'Thoughts?', 'What do you think?', 'Read more:', 'Link in bio!']
        
        for i in range(min(count, 3)):
            variation = post.copy()
            
            # Simple text modifications
            modified_text = original_text
            if i < len(hooks):
                # Add different emoji at the start
                modified_text = f"{hooks[i]} " + modified_text.lstrip('🔥✨💡🚀👀 ')
            
            # Rotate CTA if present
            for j, old_cta in enumerate(ctas):
                if old_cta in modified_text:
                    new_cta = ctas[(j + i + 1) % len(ctas)]
                    modified_text = modified_text.replace(old_cta, new_cta)
                    break
            
            variation['text'] = modified_text
            variation['character_count'] = len(modified_text)
            variation['variation_reason'] = f'Hook and CTA variation {i+1}'
            variations.append(variation)
        
        return variations
    
    def _fallback_social_summary(self, content: Dict) -> Dict:
        """Create basic social summary when none exists."""
        title = content.get('title', 'New content')
        return {
            'hook': f"📖 {title[:80]}{'...' if len(title) > 80 else ''}",
            'main_points': ['Interesting insights shared', 'Worth checking out'],
            'cta': 'Check it out!',
            'suggested_hashtags': ['#content', '#insights']
        }
    
    def _fallback_post(self, platform: str, content: Dict) -> Dict:
        """Create basic fallback post when generation fails."""
        config = PLATFORM_CONFIGS[platform]
        title = content.get('title', 'Check this out!')
        
        text = f"📖 {title}\n\nInteresting insights shared!\n\nCheck it out! #content #insights"
        
        if len(text) > config['max_chars']:
            text = self._truncate_post(text, config['max_chars'])
        
        return {
            'text': text,
            'hashtags': ['#content', '#insights'],
            'suggested_media': content.get('images', [])[:3],
            'post_type': 'text',
            'character_count': len(text),
            'truncated': False,
            'key_message': title,
            'platform': platform
        }
    
    async def _call_gemini_for_generation(self, prompt: str) -> Optional[Dict]:
        """Call Gemini API for post generation."""
        try:
            api_key = await _get_api_key(self.db)
            
            messages = [{
                "role": "user",
                "parts": [{"text": prompt}]
            }]
            
            generation_config = {
                "temperature": 0.8,  # More creative for social posts
                "maxOutputTokens": 1500,
            }
            
            result = await call_gemini_api(
                api_key=api_key,
                model="gemini-1.5-flash",
                messages=messages,
                generation_config=generation_config
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Gemini API call failed: {e}")
            return None