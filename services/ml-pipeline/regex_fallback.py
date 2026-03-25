"""Regex-based comment analysis fallback.

Used when FastEmbed is unreachable. Extracted from comment_scraper.py.
"""

import re
from collections import Counter
from typing import Dict, List


def _analyze_comments_regex(comments: List[Dict], post_caption: str = "") -> Dict:
    """Analyze raw comments into audience intelligence — no raw text stored.
    
    Extracts: sentiment, themes, questions, pain points, product mentions,
    engagement patterns. Raw comment text is discarded after analysis.
    """
    if not comments:
        return {"analyzed": 0, "sentiment": "neutral", "themes": [], "questions": [], "pain_points": []}
    
    total = len(comments)
    total_likes = sum(c.get("likes", 0) for c in comments)
    
    # Sentiment: simple keyword-based (fast, no API needed)
    positive_words = {"love", "amazing", "great", "awesome", "perfect", "best", "beautiful", 
                      "incredible", "excellent", "fantastic", "fire", "insane", "goat", "🔥", "❤️", "💯", "🙌"}
    negative_words = {"hate", "terrible", "worst", "awful", "bad", "disappointed", "scam",
                      "waste", "boring", "fake", "cringe", "mid", "👎"}
    question_words = {"how", "what", "where", "when", "why", "which", "can", "do", "does", "is", "are"}
    
    pos_count = 0
    neg_count = 0
    questions = []
    pain_points = []
    product_mentions = []
    themes = Counter()
    top_commenters = Counter()
    reply_rate = sum(1 for c in comments if c.get("is_reply")) / max(total, 1)
    
    for c in comments:
        text = (c.get("text") or "").lower()
        username = c.get("username", "")
        likes = c.get("likes", 0)
        
        # Sentiment
        words = set(re.findall(r'\w+', text)) | set(re.findall(r'[🔥❤️💯🙌👎😂💀🤔💡👀✅]', text))
        if words & positive_words:
            pos_count += 1
        if words & negative_words:
            neg_count += 1
        
        # Questions (audience wants to know)
        first_word = text.split()[0] if text.split() else ""
        if "?" in text or first_word in question_words:
            # Extract the question (first sentence with ?)
            q_match = re.search(r'([^.!]*\?)', text)
            if q_match and len(q_match.group(1)) > 10:
                questions.append({"question": q_match.group(1).strip()[:150], "likes": likes})
        
        # Pain points ("I struggle with", "I wish", "I need", "how do I")
        pain_patterns = [
            r"i (?:struggle|can't|cant|don't know|wish|need help|have trouble)\b.{5,80}",
            r"how do (?:i|you|we)\b.{5,80}",
            r"(?:frustrat|confus|stuck|lost|overwhelm)\w*.{5,60}",
        ]
        for pattern in pain_patterns:
            match = re.search(pattern, text)
            if match:
                pain_points.append({"pain": match.group(0).strip()[:150], "likes": likes})
                break
        
        # Product/tool mentions — look for capitalized names or @mentions
        # Only match words that look like proper nouns (capitalized) after trigger verbs
        original_text = (c.get("text") or "")
        product_trigger = re.search(
            r"(?:use|using|try|tried|recommend|check out|switched to|built with|powered by|running|works with)\s+"
            r"([A-Z][\w]*(?:\s+[A-Z][\w]*){0,3})",
            original_text,
        )
        if product_trigger:
            product_name = product_trigger.group(1).strip()
            if len(product_name) > 2 and product_name.lower() not in {"the", "this", "that", "it", "they", "you", "my"}:
                product_mentions.append(product_name[:50])
        # Also catch @mentions as products/tools
        at_mentions = re.findall(r"@(\w{2,30})", text)
        for mention in at_mentions:
            if mention not in top_commenters and len(mention) > 2:
                product_mentions.append(mention)

        # Theme extraction — extract meaningful 2-4 word phrases, not single words
        # Use noun-phrase-like patterns from the comment text
        theme_stop = {"the", "and", "for", "this", "that", "you", "your", "with", "from", "have", "are",
                      "but", "not", "was", "were", "been", "being", "its", "just", "really", "very",
                      "would", "could", "should", "will", "can", "more", "about", "like", "what",
                      "how", "all", "they", "them", "their", "there", "here", "also", "than", "then",
                      "too", "out", "get", "got", "has", "had", "did", "does", "don", "one", "who",
                      "want", "know", "think", "make", "need", "some", "look", "going", "thing"}
        # Extract 2-3 word phrases (bigrams/trigrams) as topic candidates
        clean_words = re.findall(r'\b[a-z]{3,}\b', text)
        clean_words = [w for w in clean_words if w not in theme_stop]
        for i in range(len(clean_words) - 1):
            bigram = f"{clean_words[i]} {clean_words[i+1]}"
            themes[bigram] += 1
            if i + 2 < len(clean_words):
                trigram = f"{clean_words[i]} {clean_words[i+1]} {clean_words[i+2]}"
                themes[trigram] += 1
        
        if username:
            top_commenters[username] += 1
    
    # Determine overall sentiment
    if pos_count > neg_count * 2:
        sentiment = "very_positive"
    elif pos_count > neg_count:
        sentiment = "positive"
    elif neg_count > pos_count * 2:
        sentiment = "very_negative"
    elif neg_count > pos_count:
        sentiment = "negative"
    else:
        sentiment = "neutral"
    
    # Sort questions and pain points by likes (most-liked = most resonant)
    questions.sort(key=lambda x: x.get("likes", 0), reverse=True)
    pain_points.sort(key=lambda x: x.get("likes", 0), reverse=True)
    
    # Deduplicate product mentions
    product_counter = Counter(product_mentions)
    
    return {
        "analyzed": total,
        "sentiment": sentiment,
        "sentiment_breakdown": {
            "positive": pos_count,
            "negative": neg_count,
            "neutral": total - pos_count - neg_count,
        },
        "avg_comment_likes": round(total_likes / max(total, 1), 1),
        "reply_rate": round(reply_rate * 100, 1),
        "questions": questions[:10],  # Top 10 questions by likes
        "pain_points": pain_points[:10],
        "product_mentions": [{"product": p, "count": c} for p, c in product_counter.most_common(10)],
        "themes": [{"theme": t, "count": c} for t, c in themes.most_common(15)],
        "top_commenters": [{"username": u, "count": c} for u, c in top_commenters.most_common(10)],
        "engagement_quality": "high" if total_likes / max(total, 1) > 5 else "moderate" if total_likes / max(total, 1) > 1 else "low",
    }