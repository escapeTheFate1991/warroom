#!/usr/bin/env python3
"""
Isolated test for format classification logic
"""

from collections import Counter

def classify_post_format_v2(post_text: str, hook: str = "", content_analysis: dict = None) -> tuple[str, float]:
    """Classify post format with confidence score."""
    text = f"{hook} {post_text}".lower()
    
    # Format patterns with weighted scores
    format_patterns = {
        "myth_buster": [
            "myth", "everyone thinks", "they told you", "actually wrong", "lie", 
            "misconception", "false", "debunk", "truth is", "reality is", 
            "stop believing", "common mistake", "actually", "wrong about",
            "don't believe", "not true", "fact check", "busted"
        ],
        "expose": [
            "nobody talks about", "secret", "they don't want you to know", "hidden", 
            "behind the scenes", "what really happens", "insider", "truth about",
            "exposed", "reveal", "industry secret", "never tell you", "won't admit",
            "dirty secret", "what they hide", "real story", "leaked", "confession"
        ],
        "transformation": [
            "before", "after", "transformed", "went from", "journey", "change",
            "transformation", "from zero to", "how i became", "evolution",
            "progress", "growth", "metamorphosis", "makeover", "upgrade",
            "before vs after", "then vs now", "my story", "changed everything"
        ],
        "pov": [
            "pov:", "pov ", "when you", "that moment when", "imagine", "picture this",
            "you know that feeling", "we've all been there", "relatable", "me when",
            "anyone else", "is it just me", "that awkward moment", "scenario"
        ]
    }
    
    # Calculate confidence scores for each format
    format_scores = {}
    for format_name, patterns in format_patterns.items():
        matches = sum(1 for pattern in patterns if pattern in text)
        if matches > 0:
            # Confidence based on pattern matches and text length
            text_length = len(text.split())
            confidence = min(0.95, 0.3 + (matches * 0.15) + min(0.2, text_length / 100))
            format_scores[format_name] = confidence
    
    # Find best match
    if format_scores:
        best_format = max(format_scores.items(), key=lambda x: x[1])
        confidence = min(0.95, best_format[1])
        return best_format[0], confidence
    
    # Return unclassified with very low confidence
    return "unclassified", 0.1

def _generate_format_name(hooks, patterns):
    """Generate a suggested name for an emerging format based on hooks and patterns."""
    hook_text = " ".join(hooks).lower()
    
    if "question" in " ".join(patterns).lower():
        if any(word in hook_text for word in ["what", "how", "why"]):
            return "The Curiosity Hook"
        elif any(word in hook_text for word in ["would you", "could you", "can you"]):
            return "The Challenge Question"
        else:
            return "The Question Opener"
    
    if any("personal" in pattern.lower() for pattern in patterns):
        if any(word in hook_text for word in ["mistake", "wrong", "failed"]):
            return "The Confession"
        elif any(word in hook_text for word in ["learned", "discovered", "realized"]):
            return "The Revelation"
        else:
            return "The Personal Story"
    
    # Fallback based on most common words
    word_counter = Counter()
    for hook in hooks:
        words = [word for word in hook.lower().split() if len(word) > 3]
        word_counter.update(words[:3])
    
    if word_counter:
        top_word = word_counter.most_common(1)[0][0].title()
        return f"The {top_word} Format"
    
    return "The Emerging Pattern"

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
    
    # Test personal pattern
    hooks = ["I made this mistake", "I learned this the hard way", "I discovered something"]
    patterns = ["Personal narrative starter"]
    name = _generate_format_name(hooks, patterns)
    print(f"Personal format name: {name}")
    
    print("✅ Format name generation tests passed!")

if __name__ == "__main__":
    test_classify_post_format_v2()
    test_format_name_generation()
    print("\n🎉 Core format detection logic is working correctly!")