"""Content Extraction Service - Extract structured content from URLs.

Handles articles, blog posts, YouTube videos, GitHub repos, and other content sources.
Uses Scrapling for robust web scraping and Gemini for AI-powered summarization.
"""

import logging
import re
import os
from typing import Dict, Optional, List
from urllib.parse import urlparse, parse_qs
import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.scraping import fetch_page, fetch_stealthy, fetch_dynamic, extract_text, extract_all_text
from app.services.nano_banana import _get_api_key, call_gemini_api

logger = logging.getLogger(__name__)

class ContentExtractor:
    """Extract and process content from various URL sources."""
    
    def __init__(self, db: Optional[AsyncSession] = None):
        self.db = db
    
    async def extract_from_url(self, url: str) -> Dict:
        """Extract structured content from any URL.
        
        Args:
            url: Source URL to extract content from
            
        Returns:
            {
                title: str,
                body_text: str,
                summary: str,
                images: List[str],
                author: str,
                published_date: str,
                word_count: int,
                source_url: str,
                content_type: str  # "article", "youtube", "github", "generic"
            }
        """
        logger.info(f"Extracting content from URL: {url}")
        
        try:
            # Determine content type and route to appropriate handler
            if self._is_youtube_url(url):
                return await self.extract_from_youtube(url)
            elif self._is_github_url(url):
                return await self._extract_from_github(url)
            else:
                return await self._extract_from_webpage(url)
        except Exception as e:
            logger.error(f"Content extraction failed for {url}: {e}")
            return {
                "title": "Extraction Failed",
                "body_text": f"Failed to extract content: {str(e)}",
                "summary": "Content extraction encountered an error",
                "images": [],
                "author": "",
                "published_date": "",
                "word_count": 0,
                "source_url": url,
                "content_type": "error"
            }
    
    async def extract_from_youtube(self, url: str) -> Dict:
        """Extract YouTube video transcript and metadata."""
        logger.info(f"Extracting YouTube content from: {url}")
        
        video_id = self._extract_youtube_video_id(url)
        if not video_id:
            return self._error_result("Invalid YouTube URL", url)
        
        try:
            # Try to get transcript using youtube-transcript-api
            transcript_text = await self._get_youtube_transcript(video_id)
            
            # Get video metadata using basic web scraping
            metadata = await self._get_youtube_metadata(url)
            
            return {
                "title": metadata.get("title", "YouTube Video"),
                "body_text": transcript_text,
                "summary": await self._generate_summary(transcript_text[:3000]) if transcript_text else "",
                "images": [metadata.get("thumbnail", "")],
                "author": metadata.get("channel", ""),
                "published_date": metadata.get("published_date", ""),
                "word_count": len(transcript_text.split()) if transcript_text else 0,
                "source_url": url,
                "content_type": "youtube"
            }
        except Exception as e:
            logger.error(f"YouTube extraction failed: {e}")
            return self._error_result(f"YouTube extraction failed: {str(e)}", url)
    
    async def summarize_for_social(self, content: Dict) -> Dict:
        """Generate social media optimized summary from extracted content.
        
        Args:
            content: Content dict from extract_from_url()
            
        Returns:
            {
                hook: str,           # Attention-grabbing opener
                main_points: List[str],  # Key takeaways (3-5 points)
                cta: str,           # Call-to-action
                suggested_hashtags: List[str]  # Relevant hashtags
            }
        """
        logger.info("Generating social media summary")
        
        if not content.get("body_text"):
            return {
                "hook": "🔥 New content alert!",
                "main_points": ["Content extracted successfully"],
                "cta": "Check it out!",
                "suggested_hashtags": ["#content", "#share"]
            }
        
        try:
            # Prepare content for AI summarization
            text_sample = content["body_text"][:2000]  # Limit to avoid token limits
            content_type = content.get("content_type", "article")
            title = content.get("title", "")
            
            prompt = f"""
Create a social media summary for this {content_type}:

Title: {title}
Content: {text_sample}

Provide:
1. Hook: An attention-grabbing opener (max 120 chars, use emojis)
2. Main Points: 3-5 key takeaways as bullet points
3. CTA: A compelling call-to-action 
4. Hashtags: 5-8 relevant hashtags

Format as JSON:
{{
  "hook": "...",
  "main_points": ["...", "...", "..."],
  "cta": "...",
  "suggested_hashtags": ["#...", "#..."]
}}
"""
            
            result = await self._call_gemini_for_summarization(prompt)
            
            # Parse JSON response
            import json
            if result and "candidates" in result:
                text_response = result["candidates"][0]["content"]["parts"][0]["text"]
                # Clean up markdown code blocks if present
                text_response = re.sub(r'```json\s*|\s*```', '', text_response)
                summary_data = json.loads(text_response)
                
                return {
                    "hook": summary_data.get("hook", "🔥 New content alert!"),
                    "main_points": summary_data.get("main_points", ["Great insights shared"]),
                    "cta": summary_data.get("cta", "Check it out!"),
                    "suggested_hashtags": summary_data.get("suggested_hashtags", ["#content"])
                }
        
        except Exception as e:
            logger.error(f"Social summarization failed: {e}")
            
        # Fallback summary
        return {
            "hook": f"📖 {content.get('title', 'New content')[:80]}...",
            "main_points": [
                "Interesting insights shared",
                f"From {content.get('author', 'a great source')}",
                "Worth checking out"
            ],
            "cta": "Read the full article!",
            "suggested_hashtags": ["#content", "#insights", "#reading"]
        }
    
    # Private helper methods
    
    def _is_youtube_url(self, url: str) -> bool:
        """Check if URL is a YouTube video."""
        return "youtube.com/watch" in url or "youtu.be/" in url
    
    def _is_github_url(self, url: str) -> bool:
        """Check if URL is a GitHub repository."""
        return "github.com" in url and "/tree/" not in url and "/blob/" not in url
    
    def _extract_youtube_video_id(self, url: str) -> Optional[str]:
        """Extract video ID from YouTube URL."""
        patterns = [
            r'(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]+)',
            r'youtube\.com/embed/([a-zA-Z0-9_-]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    async def _get_youtube_transcript(self, video_id: str) -> str:
        """Get YouTube video transcript."""
        try:
            # Try to use youtube-transcript-api if available
            try:
                from youtube_transcript_api import YouTubeTranscriptApi
                transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
                return " ".join([item["text"] for item in transcript_list])
            except ImportError:
                logger.warning("youtube-transcript-api not available, using fallback method")
                return await self._get_youtube_transcript_fallback(video_id)
            except Exception as e:
                logger.warning(f"Transcript API failed: {e}, trying fallback")
                return await self._get_youtube_transcript_fallback(video_id)
        except Exception as e:
            logger.error(f"Failed to get YouTube transcript: {e}")
            return ""
    
    async def _get_youtube_transcript_fallback(self, video_id: str) -> str:
        """Fallback method for getting YouTube transcript via web scraping."""
        try:
            # This is a simplified fallback - in production, you might use
            # a more sophisticated approach or external service
            transcript_url = f"https://www.youtube.com/watch?v={video_id}"
            page = await fetch_page(transcript_url)
            
            # Look for transcript data in page (this is simplified)
            # In reality, YouTube transcript data is complex and changes frequently
            return "Transcript not available via fallback method"
        except Exception as e:
            logger.error(f"YouTube transcript fallback failed: {e}")
            return ""
    
    async def _get_youtube_metadata(self, url: str) -> Dict:
        """Get YouTube video metadata via web scraping."""
        try:
            page = await fetch_page(url)
            
            title = extract_text(page, 'meta[property="og:title"]::attr(content)') or \
                   extract_text(page, 'title') or "YouTube Video"
            
            channel = extract_text(page, 'link[itemprop="name"]::attr(content)') or \
                     extract_text(page, 'meta[name="author"]::attr(content)') or ""
            
            thumbnail = extract_text(page, 'meta[property="og:image"]::attr(content)') or ""
            
            # Try to extract publish date
            published_date = extract_text(page, 'meta[itemprop="datePublished"]::attr(content)') or ""
            
            return {
                "title": title.strip(),
                "channel": channel.strip(),
                "thumbnail": thumbnail,
                "published_date": published_date
            }
        except Exception as e:
            logger.error(f"YouTube metadata extraction failed: {e}")
            return {"title": "YouTube Video", "channel": "", "thumbnail": "", "published_date": ""}
    
    async def _extract_from_webpage(self, url: str) -> Dict:
        """Extract content from a general webpage (article, blog post, etc.)."""
        try:
            # Try different scraping methods in order of preference
            page = None
            
            # First try standard fetch
            try:
                page = await fetch_page(url)
            except Exception:
                # If that fails, try stealthy fetch for protected sites
                try:
                    page = await fetch_stealthy(url)
                except Exception:
                    # Last resort: dynamic fetch for SPAs
                    page = await fetch_dynamic(url)
            
            if not page:
                return self._error_result("Failed to fetch webpage", url)
            
            # Extract basic metadata
            title = self._extract_title(page)
            author = self._extract_author(page)
            published_date = self._extract_published_date(page)
            images = self._extract_images(page, url)
            
            # Extract main content
            body_text = self._extract_main_content(page)
            word_count = len(body_text.split()) if body_text else 0
            
            # Generate summary if content is substantial
            summary = ""
            if word_count > 50:
                summary = await self._generate_summary(body_text[:2000])
            
            return {
                "title": title,
                "body_text": body_text,
                "summary": summary,
                "images": images,
                "author": author,
                "published_date": published_date,
                "word_count": word_count,
                "source_url": url,
                "content_type": "article"
            }
            
        except Exception as e:
            logger.error(f"Webpage extraction failed: {e}")
            return self._error_result(f"Webpage extraction failed: {str(e)}", url)
    
    async def _extract_from_github(self, url: str) -> Dict:
        """Extract content from GitHub repository (README, description)."""
        try:
            # Parse GitHub URL to get repo info
            parsed = urlparse(url)
            path_parts = parsed.path.strip('/').split('/')
            
            if len(path_parts) < 2:
                return self._error_result("Invalid GitHub URL", url)
            
            owner, repo = path_parts[0], path_parts[1]
            
            # Fetch repository page
            page = await fetch_page(url)
            
            # Extract repository info
            title = f"{owner}/{repo}"
            description = extract_text(page, '[data-pjax="#repo-content-pjax-container"] p') or ""
            
            # Try to extract README content
            readme_content = self._extract_github_readme(page)
            
            # Get repository stats
            stars = extract_text(page, '#repo-stars-counter-star::text') or "0"
            language = extract_text(page, '[data-ga-click*="language"]::text') or ""
            
            body_text = f"Repository: {title}\nDescription: {description}\n\n{readme_content}"
            word_count = len(body_text.split())
            
            summary = await self._generate_summary(body_text[:2000]) if word_count > 50 else description
            
            return {
                "title": title,
                "body_text": body_text,
                "summary": summary,
                "images": [],
                "author": owner,
                "published_date": "",
                "word_count": word_count,
                "source_url": url,
                "content_type": "github",
                "metadata": {
                    "stars": stars,
                    "language": language,
                    "description": description
                }
            }
            
        except Exception as e:
            logger.error(f"GitHub extraction failed: {e}")
            return self._error_result(f"GitHub extraction failed: {str(e)}", url)
    
    def _extract_title(self, page) -> str:
        """Extract page title from various sources."""
        selectors = [
            'meta[property="og:title"]::attr(content)',
            'meta[name="twitter:title"]::attr(content)',
            'h1::text',
            'title::text'
        ]
        
        for selector in selectors:
            title = extract_text(page, selector)
            if title:
                return title.strip()
        
        return "Untitled"
    
    def _extract_author(self, page) -> str:
        """Extract author from various sources."""
        selectors = [
            'meta[name="author"]::attr(content)',
            'meta[property="article:author"]::attr(content)',
            '[rel="author"]::text',
            '.author::text',
            '.byline::text'
        ]
        
        for selector in selectors:
            author = extract_text(page, selector)
            if author:
                return author.strip()
        
        return ""
    
    def _extract_published_date(self, page) -> str:
        """Extract published date from various sources."""
        selectors = [
            'meta[property="article:published_time"]::attr(content)',
            'meta[name="publishdate"]::attr(content)',
            'time[datetime]::attr(datetime)',
            'time::text',
            '.published::text',
            '.date::text'
        ]
        
        for selector in selectors:
            date = extract_text(page, selector)
            if date:
                return date.strip()
        
        return ""
    
    def _extract_images(self, page, base_url: str) -> List[str]:
        """Extract relevant images from the page."""
        try:
            images = []
            
            # Try featured/hero image first
            featured_selectors = [
                'meta[property="og:image"]::attr(content)',
                'meta[name="twitter:image"]::attr(content)',
                '.featured-image img::attr(src)',
                '.hero-image img::attr(src)',
                'article img::attr(src)'
            ]
            
            for selector in featured_selectors:
                img_url = extract_text(page, selector)
                if img_url:
                    # Convert relative URLs to absolute
                    if img_url.startswith('/'):
                        parsed_base = urlparse(base_url)
                        img_url = f"{parsed_base.scheme}://{parsed_base.netloc}{img_url}"
                    elif not img_url.startswith(('http://', 'https://')):
                        img_url = f"{base_url.rstrip('/')}/{img_url}"
                    
                    images.append(img_url)
                    if len(images) >= 3:  # Limit to 3 images
                        break
            
            return images
        except Exception as e:
            logger.error(f"Image extraction failed: {e}")
            return []
    
    def _extract_main_content(self, page) -> str:
        """Extract main article content from page."""
        # Try various content selectors in order of preference
        content_selectors = [
            'article',
            '.post-content',
            '.entry-content',
            '.article-body',
            '.content',
            'main',
            '.post',
            '[role="main"]'
        ]
        
        for selector in content_selectors:
            content = extract_text(page, f'{selector}')
            if content and len(content.strip()) > 100:
                # Clean up the text
                content = re.sub(r'\s+', ' ', content)  # Normalize whitespace
                content = content.strip()
                return content
        
        # Fallback: try to get all paragraph text
        paragraphs = extract_all_text(page, 'p')
        if paragraphs:
            content = ' '.join(paragraphs)
            content = re.sub(r'\s+', ' ', content)
            return content.strip()
        
        return ""
    
    def _extract_github_readme(self, page) -> str:
        """Extract README content from GitHub page."""
        try:
            # GitHub README is typically in a specific container
            readme_selectors = [
                '[data-testid="readme"] .Box-body',
                '#readme .Box-body',
                '.readme .Box-body',
                'article[itemprop="text"]'
            ]
            
            for selector in readme_selectors:
                readme = extract_text(page, selector)
                if readme and len(readme.strip()) > 50:
                    return readme.strip()
            
            return ""
        except Exception as e:
            logger.error(f"GitHub README extraction failed: {e}")
            return ""
    
    async def _generate_summary(self, text: str) -> str:
        """Generate AI summary of content."""
        try:
            if not text or len(text.strip()) < 50:
                return ""
            
            prompt = f"""
Summarize this content in 2-3 concise sentences that capture the key points:

{text[:1500]}

Focus on the main insights and takeaways. Keep it under 200 words.
"""
            
            result = await self._call_gemini_for_summarization(prompt)
            
            if result and "candidates" in result:
                summary = result["candidates"][0]["content"]["parts"][0]["text"]
                return summary.strip()
        
        except Exception as e:
            logger.error(f"Summary generation failed: {e}")
        
        return ""
    
    async def _call_gemini_for_summarization(self, prompt: str) -> Optional[Dict]:
        """Call Gemini API for text summarization."""
        try:
            api_key = await _get_api_key(self.db)
            
            messages = [{
                "role": "user",
                "parts": [{"text": prompt}]
            }]
            
            generation_config = {
                "temperature": 0.7,
                "maxOutputTokens": 1000,
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
    
    def _error_result(self, error_msg: str, url: str) -> Dict:
        """Create standardized error result."""
        return {
            "title": "Extraction Failed",
            "body_text": error_msg,
            "summary": "Content could not be extracted",
            "images": [],
            "author": "",
            "published_date": "",
            "word_count": 0,
            "source_url": url,
            "content_type": "error"
        }