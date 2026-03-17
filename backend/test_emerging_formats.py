#!/usr/bin/env python3
"""
Test script for emerging format detection functionality
"""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.api.content_intel import classify_post_format_v2, _generate_format_name, _generate_format_description

def test_classify_post_format_v2():
    """Test the enhanced format classification with confidence scores"""
    
    # Test myth buster
    result = classify_post_format_v2(
        "Everyone thinks this is true but actually it's wrong. Here's what really happens.",
        "The biggest lie they tell you"
    )
    print(f"Myth buster test: {result}")
    assert result[0] == "myth_buster"
    assert result[1] > 0.5
    
    # Test transformation
    result = classify_post_format_v2(
        "I went from zero to 100k followers in 6 months. Here's my journey.",
        "My transformation story"
    )
    print(f"Transformation test: {result}")
    assert result[0] == "transformation"
    assert result[1] > 0.5
    
    # Test unclassified (should have low confidence)
    result = classify_post_format_v2(
        "Just some random text that doesn't match any pattern",
        "Generic opener"
    )
    print(f"Unclassified test: {result}")
    assert result[0] == "unclassified"
    assert result[1] < 0.5
    
    print("✅ classify_post_format_v2 tests passed!")

def test_format_name_generation():
    """Test format name generation"""
    
    # Test question pattern
    hooks = ["What if I told you this secret?", "What would you do in this situation?", "What's the real truth?"]
    patterns = ["Question-based opening"]
    name = _generate_format_name(hooks, patterns)
    print(f"Question format name: {name}")
    assert "question" in name.lower() or "curiosity" in name.lower()
    
    # Test personal pattern
    hooks = ["I made this mistake", "I learned this the hard way", "I discovered something"]
    patterns = ["Personal narrative starter"]
    name = _generate_format_name(hooks, patterns)
    print(f"Personal format name: {name}")
    assert "personal" in name.lower() or "confession" in name.lower() or "revelation" in name.lower()
    
    print("✅ Format name generation tests passed!")

def test_format_description_generation():
    """Test format description generation"""
    
    posts = [
        {"hook": "What if I told you this?", "engagement_score": 50000},
        {"hook": "What would you do?", "engagement_score": 45000},
        {"hook": "What's the truth?", "engagement_score": 55000}
    ]
    patterns = ["Question-based opening", "Ultra-short hooks"]
    
    description = _generate_format_description(posts, patterns)
    print(f"Format description: {description}")
    assert len(description) > 20  # Should generate meaningful description
    assert "question" in description.lower() or "engagement" in description.lower()
    
    print("✅ Format description generation tests passed!")

if __name__ == "__main__":
    test_classify_post_format_v2()
    test_format_name_generation() 
    test_format_description_generation()
    print("\n🎉 All tests passed! Emerging format detection is working correctly.")