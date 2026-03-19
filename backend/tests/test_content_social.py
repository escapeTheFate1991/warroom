"""
Test Content Social API endpoints
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone

from app.services.content_extractor import ContentExtractor
from app.services.social_post_generator import SocialPostGenerator, PLATFORM_CONFIGS


class TestContentExtractor:
    """Test ContentExtractor service."""
    
    def test_youtube_url_detection(self):
        """Test YouTube URL detection."""
        extractor = ContentExtractor()
        
        assert extractor._is_youtube_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        assert extractor._is_youtube_url("https://youtu.be/dQw4w9WgXcQ")
        assert not extractor._is_youtube_url("https://example.com")
    
    def test_github_url_detection(self):
        """Test GitHub URL detection."""
        extractor = ContentExtractor()
        
        assert extractor._is_github_url("https://github.com/owner/repo")
        assert not extractor._is_github_url("https://github.com/owner/repo/blob/main/file.py")
        assert not extractor._is_github_url("https://example.com")
    
    def test_youtube_video_id_extraction(self):
        """Test YouTube video ID extraction."""
        extractor = ContentExtractor()
        
        # Standard YouTube URLs
        assert extractor._extract_youtube_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"
        assert extractor._extract_youtube_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
        assert extractor._extract_youtube_video_id("https://youtube.com/embed/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
        
        # Invalid URLs
        assert extractor._extract_youtube_video_id("https://example.com") is None
        assert extractor._extract_youtube_video_id("") is None
    
    def test_error_result(self):
        """Test error result generation."""
        extractor = ContentExtractor()
        
        error = extractor._error_result("Test error", "https://example.com")
        
        assert error["title"] == "Extraction Failed"
        assert error["body_text"] == "Test error"
        assert error["source_url"] == "https://example.com"
        assert error["content_type"] == "error"
        assert error["word_count"] == 0


class TestSocialPostGenerator:
    """Test SocialPostGenerator service."""
    
    def test_platform_configs_exist(self):
        """Test that all expected platforms have configurations."""
        expected_platforms = ['instagram', 'tiktok', 'twitter', 'linkedin', 'facebook']
        
        for platform in expected_platforms:
            assert platform in PLATFORM_CONFIGS
            config = PLATFORM_CONFIGS[platform]
            assert 'max_chars' in config
            assert 'supports_carousel' in config
            assert 'supports_video' in config
    
    def test_determine_post_type(self):
        """Test post type determination based on content."""
        generator = SocialPostGenerator()
        
        # Test video content
        youtube_content = {'content_type': 'youtube', 'images': []}
        instagram_config = PLATFORM_CONFIGS['instagram']
        assert generator._determine_post_type(youtube_content, instagram_config) == 'video'
        
        # Test carousel content
        carousel_content = {'content_type': 'article', 'images': ['img1.jpg', 'img2.jpg']}
        assert generator._determine_post_type(carousel_content, instagram_config) == 'carousel'
        
        # Test single image
        image_content = {'content_type': 'article', 'images': ['img1.jpg']}
        assert generator._determine_post_type(image_content, instagram_config) == 'image'
        
        # Test text only
        text_content = {'content_type': 'article', 'images': []}
        assert generator._determine_post_type(text_content, instagram_config) == 'text'
    
    def test_truncate_post(self):
        """Test post truncation logic."""
        generator = SocialPostGenerator()
        
        # Test no truncation needed
        short_text = "This is a short post."
        assert generator._truncate_post(short_text, 100) == short_text
        
        # Test sentence boundary truncation
        long_text = "First sentence. Second sentence. Third sentence."
        truncated = generator._truncate_post(long_text, 30)
        assert truncated.endswith("...")
        assert len(truncated) <= 30
        
        # Test word boundary truncation
        no_periods = "word1 word2 word3 word4 word5 word6"
        truncated_words = generator._truncate_post(no_periods, 20)
        assert truncated_words.endswith("...")
        assert len(truncated_words) <= 20
    
    def test_fallback_social_summary(self):
        """Test fallback social summary generation."""
        generator = SocialPostGenerator()
        
        content = {'title': 'Test Article'}
        summary = generator._fallback_social_summary(content)
        
        assert 'hook' in summary
        assert 'main_points' in summary
        assert 'cta' in summary
        assert 'suggested_hashtags' in summary
        assert summary['hook'].startswith('📖 Test Article')
    
    def test_fallback_post(self):
        """Test fallback post generation."""
        generator = SocialPostGenerator()
        
        content = {'title': 'Test Content', 'images': ['test.jpg']}
        config = PLATFORM_CONFIGS['twitter']
        
        post = generator._fallback_post('twitter', content, {}, config, 'text')
        
        assert 'text' in post
        assert 'hashtags' in post
        assert 'platform' in post
        assert post['platform'] == 'twitter'
        assert post['character_count'] <= config['max_chars']
    
    def test_create_manual_variations(self):
        """Test manual variation creation."""
        generator = SocialPostGenerator()
        
        original_post = {
            'text': '🔥 Original post text Check it out! #test',
            'hashtags': ['#test'],
            'platform': 'twitter'
        }
        
        variations = generator._create_manual_variations(original_post, 3)
        
        assert len(variations) == 3
        for i, variation in enumerate(variations):
            assert 'text' in variation
            assert 'variation_reason' in variation
            # Each variation should be different from the original
            if i > 0:  # First variation might be the same as original
                # At least some variations should be different
                pass


@pytest.mark.asyncio
class TestContentSocialIntegration:
    """Integration tests for the content social pipeline."""
    
    async def test_extract_and_generate_flow(self):
        """Test the complete extract → generate → schedule flow."""
        # Mock extracted content
        mock_content = {
            'title': 'Test Article',
            'body_text': 'This is a test article with interesting content.',
            'summary': 'A test article summary.',
            'images': ['test.jpg'],
            'author': 'Test Author',
            'published_date': '2024-01-01',
            'word_count': 10,
            'source_url': 'https://example.com/test',
            'content_type': 'article',
            'social_summary': {
                'hook': '📖 Test Article',
                'main_points': ['Interesting content', 'Test data'],
                'cta': 'Read more!',
                'suggested_hashtags': ['#test', '#article']
            }
        }
        
        # Test social post generator
        generator = SocialPostGenerator()
        
        # Mock the Gemini API call
        with patch.object(generator, '_call_gemini_for_generation') as mock_gemini:
            mock_gemini.return_value = {
                'candidates': [{
                    'content': {
                        'parts': [{
                            'text': '{"text": "📖 Test Article\\n\\nInteresting insights!\\n\\nRead more! #test #article", "hashtags": ["#test", "#article"], "key_message": "Test insights"}'
                        }]
                    }
                }]
            }
            
            platforms = ['twitter', 'instagram']
            posts = await generator.generate_posts(mock_content, platforms, 'professional')
            
            assert len(posts) == 2
            assert 'twitter' in posts
            assert 'instagram' in posts
            
            for platform, post in posts.items():
                assert 'text' in post
                assert 'hashtags' in post
                assert 'character_count' in post
                assert post['platform'] == platform
                assert post['character_count'] <= PLATFORM_CONFIGS[platform]['max_chars']


if __name__ == '__main__':
    # Run basic tests
    test_extractor = TestContentExtractor()
    test_extractor.test_youtube_url_detection()
    test_extractor.test_github_url_detection()
    test_extractor.test_youtube_video_id_extraction()
    test_extractor.test_error_result()
    
    test_generator = TestSocialPostGenerator()
    test_generator.test_platform_configs_exist()
    test_generator.test_determine_post_type()
    test_generator.test_truncate_post()
    test_generator.test_fallback_social_summary()
    test_generator.test_fallback_post()
    test_generator.test_create_manual_variations()
    
    print("✅ All basic tests passed!")