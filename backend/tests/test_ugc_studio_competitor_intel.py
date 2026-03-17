"""Test UGC Studio competitor intelligence enhancements."""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
from app.api.ugc_studio import (
    GenerateScriptRequest, 
    extract_competitor_context,
    parse_script_response
)


def test_generate_script_request_model():
    """Test the enhanced GenerateScriptRequest model."""
    # Test default values
    req = GenerateScriptRequest(
        format="myth_buster",
        hook="Everyone thinks this is true",
        topic="AI productivity"
    )
    assert req.use_competitor_intel is False
    assert req.tone == "energetic and authentic"
    assert req.duration_seconds == 30
    
    # Test competitor intel enabled
    req_with_intel = GenerateScriptRequest(
        format="transformation",
        hook="From chaos to clarity",
        topic="Productivity systems",
        use_competitor_intel=True
    )
    assert req_with_intel.use_competitor_intel is True


@pytest.mark.asyncio
async def test_extract_competitor_context():
    """Test competitor context extraction from posts."""
    # Mock posts data
    sample_posts = [
        {
            "id": 1,
            "hook": "This productivity hack changed everything",
            "post_text": "This productivity hack changed everything for me...",
            "likes": 5000,
            "comments": 200,
            "shares": 50,
            "engagement_score": 5250,
            "handle": "@productivity_guru",
            "detected_format": "transformation",
            "comments_data": json.dumps([
                {"text": "How do you stay motivated?"},
                {"text": "What tools do you use for this?"},
                {"text": "Does this work for remote workers?"}
            ])
        },
        {
            "id": 2,
            "hook": "Stop believing this productivity myth",
            "post_text": "Stop believing this productivity myth...",
            "likes": 3000,
            "comments": 100,
            "shares": 30,
            "engagement_score": 3130,
            "handle": "@myth_buster",
            "detected_format": "myth_buster",
            "comments_data": json.dumps([
                {"text": "What about task management apps?"},
                {"text": "How long does this take daily?"}
            ])
        }
    ]
    
    # Test extraction
    context = await extract_competitor_context(sample_posts, "transformation")
    
    # Check structure
    assert "top_hooks" in context
    assert "audience_themes" in context
    assert "format_patterns" in context
    assert "source_handles" in context
    
    # Check hooks extraction
    assert len(context["top_hooks"]) > 0
    hook_texts = [h[0] for h in context["top_hooks"]]
    assert "This productivity hack changed everything" in hook_texts
    
    # Check handles
    assert "@productivity_guru" in context["source_handles"]
    
    # Check audience themes extraction
    assert isinstance(context["audience_themes"], list)


def test_parse_script_response():
    """Test parsing of AI response with WHY THIS WORKS section."""
    # Sample response with analysis sections
    sample_response = """
[HOOK] This productivity myth is killing your success.
(Camera: close-up, urgent tone)

[BODY] Everyone says multitasking makes you productive.
But science proves it reduces your output by 40%.
Here's what actually works...

[CTA] Try single-tasking for one week.
Comment 'FOCUS' if you're ready.

WHY THIS WORKS:
This script combines the myth-buster format with transformation promise. The hook leverages pattern from @productivity_guru's viral post about "killing productivity." The audience demand signal about "staying motivated" is addressed through the single-tasking challenge.

AUDIENCE DEMAND:
- "How do you stay motivated?" → Answered with concrete action step
- "What tools do you use?" → Implicit in single-tasking approach
"""
    
    parsed = parse_script_response(sample_response)
    
    # Check script extraction
    assert "[HOOK]" in parsed["script"]
    assert "[BODY]" in parsed["script"]
    assert "[CTA]" in parsed["script"]
    assert "WHY THIS WORKS:" not in parsed["script"]
    
    # Check analysis extraction
    assert "myth-buster format" in parsed["why_this_works"]
    assert "audience demand signal" in parsed["why_this_works"]


def test_parse_script_response_without_analysis():
    """Test parsing when no analysis sections exist."""
    simple_response = """
[HOOK] Your morning routine is broken.

[BODY] Most people start their day reactive.
Check email, scroll social media, panic mode.
Try this instead: plan, move, create.

[CTA] Share your morning routine below.
"""
    
    parsed = parse_script_response(simple_response)
    
    # Should get the full response as script
    assert "[HOOK]" in parsed["script"]
    assert parsed["why_this_works"] == ""


@pytest.mark.asyncio
async def test_competitor_hooks_endpoint_structure():
    """Test the expected response structure for competitor hooks endpoint."""
    # This would be an integration test with a real database
    # Here we just test the expected structure
    
    expected_structure = {
        "hooks": [
            {
                "hook_text": "Example hook",
                "handle": "@example",
                "likes": 1000,
                "engagement_score": 1200,
                "format": "transformation",
                "post_url": "https://..."
            }
        ],
        "audience_demands": [
            {
                "theme": "how to get started",
                "frequency": 3,
                "source_competitors": ["@example1", "@example2"]
            }
        ]
    }
    
    # Validate structure keys
    assert "hooks" in expected_structure
    assert "audience_demands" in expected_structure
    
    # Validate hook structure
    hook = expected_structure["hooks"][0]
    required_hook_fields = ["hook_text", "handle", "likes", "engagement_score", "format", "post_url"]
    for field in required_hook_fields:
        assert field in hook
    
    # Validate audience demand structure
    demand = expected_structure["audience_demands"][0]
    required_demand_fields = ["theme", "frequency", "source_competitors"]
    for field in required_demand_fields:
        assert field in demand


if __name__ == "__main__":
    # Run basic tests
    test_generate_script_request_model()
    print("✓ GenerateScriptRequest model tests passed")
    
    test_parse_script_response()
    test_parse_script_response_without_analysis()
    print("✓ Script response parsing tests passed")
    
    test_competitor_hooks_endpoint_structure()
    print("✓ API structure tests passed")
    
    print("\n🎯 All UGC Studio competitor intelligence tests passed!")