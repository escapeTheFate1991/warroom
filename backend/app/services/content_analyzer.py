"""Content structure analyzer — Hook/Value/CTA framework.

Analyzes transcribed video content to identify:
- Hook (0-3s): The scroll-stopping opener
- Value/Message (3-40s): The main content/tip/story
- CTA/Chat (last 5-10s): The call-to-action

This is the industry-standard short-form video structure:
Hook → Value → CTA (also known as Hook → Message → Chat)

Requires transcript with timestamps (segments with start/end/text).
"""

import json
import logging
import re
from typing import Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Hook detection: first 0-3 seconds
HOOK_END_SEC = 3.0

# CTA detection: last N seconds of video
CTA_WINDOW_SEC = 10.0

# CTA signal phrases
CTA_PHRASES = [
    r"comment\b.*\bbelow",
    r"drop\b.*\bcomment",
    r"let me know",
    r"link in (?:bio|description)",
    r"click the link",
    r"follow (?:me|for more|if)",
    r"subscribe",
    r"share (?:this|with)",
    r"save (?:this|for later)",
    r"dm me",
    r"check (?:out|the link)",
    r"grab (?:my|the|your)",
    r"sign up",
    r"book (?:a|your) (?:call|session|spot)",
    r"tag (?:a friend|someone)",
    r"what do you think",
    r"do you agree",
    r"tell me (?:in|your)",
    r"leave a comment",
    r"hit (?:the|that) (?:like|follow|subscribe)",
    r"share your (?:thoughts|experience)",
    r"type\s+['\"]?\w+['\"]?\s+(?:below|in the comments)",
]

# Hook pattern categories
HOOK_PATTERNS = {
    "question": r"^(?:do you|have you|are you|did you|what if|how (?:do|can|to)|why (?:do|don't|are)|when (?:did|was|will)|who (?:else|here)|is it|can you|would you|ever wonder)",
    "shock_stat": r"(?:\d+%|\d+ (?:out of|in|people|percent))",
    "curiosity_gap": r"(?:secret|nobody (?:tells|knows|talks)|most people (?:don't|won't)|here's (?:what|why|how)|the (?:truth|real reason|one thing))",
    "bold_claim": r"(?:stop (?:doing|making)|you're (?:doing it|wrong)|this (?:changed|will change)|i (?:made|earned|lost|quit|doubled))",
    "story": r"(?:so (?:i|this|my|one)|story time|let me tell|i was|when i|yesterday|last (?:week|month|year))",
    "direct_address": r"(?:listen|guys|okay so|alright|here's the thing|pay attention|watch this)",
    "controversy": r"(?:unpopular opinion|hot take|i don't care what|controversial|fight me on this)",
}


def analyze_content_structure(segments: List[Dict]) -> Dict:
    """Analyze transcript segments into Hook/Value/CTA structure.
    
    Args:
        segments: List of {start: float, end: float, text: str}
    
    Returns:
        {
            hook: {text, start, end, type, strength},
            value: {text, start, end, key_points: []},
            cta: {text, start, end, type, phrase},
            total_duration: float,
            structure_score: float,  # 0-1 how well it follows the framework
            full_script: str,
        }
    """
    if not segments:
        return _empty_result()
    
    # Sort by start time
    segments = sorted(segments, key=lambda s: s.get("start", 0))
    
    total_duration = max(s.get("end", 0) for s in segments)
    if total_duration == 0:
        # Single segment without timestamps — estimate from text length
        total_duration = len(" ".join(s.get("text", "") for s in segments).split()) * 0.4  # ~0.4s per word
    
    full_script = " ".join(s.get("text", "") for s in segments).strip()
    
    # Detect if this is a clip (< 15s) — likely Instagram preview, not full reel
    is_clip = total_duration < 15 and len(segments) <= 2
    
    # Detect text-overlay/meme reels — short audio (trending sound) with real content in caption
    # These are "Tip" format videos: text on screen, music/sound underneath
    word_count = len(full_script.split())
    is_text_overlay = (
        total_duration < 15
        and word_count < 20
        and len(segments) <= 2
    )
    
    # === HOOK (0 - 3s) ===
    hook_segments = [s for s in segments if s.get("start", 0) < HOOK_END_SEC]
    if not hook_segments:
        hook_segments = segments[:1]  # At least first segment
    
    hook_text = " ".join(s.get("text", "") for s in hook_segments).strip()
    hook_end = max(s.get("end", HOOK_END_SEC) for s in hook_segments)
    hook_type = _classify_hook(hook_text)
    hook_strength = _score_hook(hook_text, hook_type)
    
    # === CTA (last 5-10s) ===
    cta_start_threshold = max(total_duration - CTA_WINDOW_SEC, total_duration * 0.75)
    cta_segments = [s for s in segments if s.get("start", 0) >= cta_start_threshold]
    
    cta_text = " ".join(s.get("text", "") for s in cta_segments).strip()
    cta_start = min(s.get("start", 0) for s in cta_segments) if cta_segments else total_duration
    cta_type, cta_phrase = _classify_cta(cta_text)
    
    # === VALUE/MESSAGE (everything between hook and CTA) ===
    value_segments = [
        s for s in segments
        if s.get("start", 0) >= hook_end and s.get("start", 0) < cta_start_threshold
    ]
    if not value_segments:
        # If no clear separation, middle portion is value
        mid_start = len(segments) // 4
        mid_end = max(len(segments) * 3 // 4, mid_start + 1)
        value_segments = segments[mid_start:mid_end]
    
    value_text = " ".join(s.get("text", "") for s in value_segments).strip()
    value_start = min(s.get("start", 0) for s in value_segments) if value_segments else hook_end
    value_end = max(s.get("end", 0) for s in value_segments) if value_segments else cta_start_threshold
    key_points = _extract_key_points(value_text)
    
    # === STRUCTURE SCORE ===
    structure_score = _score_structure(
        hook_text=hook_text,
        hook_type=hook_type,
        value_text=value_text,
        cta_text=cta_text,
        cta_type=cta_type,
        total_duration=total_duration,
    )
    
    # Determine content format
    if is_text_overlay:
        content_format = "text_overlay"  # Tip/meme reel — text on screen, trending sound
    elif total_duration <= 60:
        content_format = "short_form"    # Standard short-form (Hook/Value/CTA applies)
    elif total_duration <= 180:
        content_format = "mid_form"      # Longer reel/video
    else:
        content_format = "long_form"     # Full video/interview
    
    # Determine if there's a verbal hook
    has_verbal_hook = bool(hook_text and len(hook_text.strip()) > 5 and not is_text_overlay)
    
    # If no verbal hook, adjust hook type and text
    if not has_verbal_hook:
        if is_text_overlay:
            hook_type = "text_overlay"
            if not hook_text:
                hook_text = "No verbal hook detected - check visual"
        else:
            hook_type = "none"
            hook_text = hook_text or "No verbal hook detected"
    
    return {
        "is_clip": is_clip,
        "content_format": content_format,
        "has_verbal_hook": has_verbal_hook,
        "hook": {
            "text": hook_text,
            "start": 0.0,
            "end": round(hook_end, 1),
            "type": hook_type,
            "strength": round(hook_strength, 2),
        },
        "value": {
            "text": value_text,
            "start": round(value_start, 1),
            "end": round(value_end, 1),
            "key_points": key_points,
        },
        "cta": {
            "text": cta_text,
            "start": round(cta_start, 1),
            "end": round(total_duration, 1),
            "type": cta_type,
            "phrase": cta_phrase,
        },
        "total_duration": round(total_duration, 1),
        "structure_score": round(structure_score, 2),
        "full_script": full_script,
    }


def _classify_hook(text: str) -> str:
    """Classify the hook type based on patterns."""
    text_lower = text.lower().strip()
    for hook_type, pattern in HOOK_PATTERNS.items():
        if re.search(pattern, text_lower):
            return hook_type
    return "statement"


def _score_hook(text: str, hook_type: str) -> float:
    """Score hook strength 0-1."""
    score = 0.3  # Base score for having any hook
    
    # Length: hooks should be punchy (5-20 words ideal)
    words = text.split()
    word_count = len(words)
    if 3 <= word_count <= 12:
        score += 0.2  # Ideal length
    elif word_count <= 20:
        score += 0.1  # Acceptable
    
    # Hook type bonus
    strong_types = {"question", "curiosity_gap", "bold_claim", "shock_stat", "controversy"}
    if hook_type in strong_types:
        score += 0.25
    elif hook_type in {"story", "direct_address"}:
        score += 0.15
    
    # Emotional/power words
    power_words = {"secret", "never", "always", "stop", "mistake", "truth", "actually",
                   "exactly", "finally", "free", "proven", "guaranteed", "mind-blowing",
                   "insane", "changed", "everything", "nobody"}
    if any(w in text.lower() for w in power_words):
        score += 0.15
    
    # Numbers/specifics
    if re.search(r'\d+', text):
        score += 0.1
    
    return min(score, 1.0)


def _classify_cta(text: str) -> tuple:
    """Classify CTA type and extract the phrase. Returns (type, phrase)."""
    text_lower = text.lower()
    
    for pattern in CTA_PHRASES:
        match = re.search(pattern, text_lower)
        if match:
            # Determine CTA type
            phrase = match.group(0)
            if any(w in phrase for w in ["comment", "let me know", "tell me", "what do you think", "do you agree", "type"]):
                return "engagement", phrase
            elif any(w in phrase for w in ["link", "click", "grab", "sign up", "book", "check out"]):
                return "conversion", phrase
            elif any(w in phrase for w in ["follow", "subscribe", "hit"]):
                return "growth", phrase
            elif any(w in phrase for w in ["share", "tag", "save"]):
                return "amplification", phrase
            return "engagement", phrase
    
    return "none", ""


def _extract_key_points(text: str) -> List[str]:
    """Extract key points/tips from the value section."""
    if not text:
        return []
    
    points = []
    sentences = re.split(r'[.!?]+', text)
    
    for sent in sentences:
        sent = sent.strip()
        if not sent or len(sent) < 15:
            continue
        
        # Look for tip/insight indicators
        tip_patterns = [
            r"(?:the (?:key|trick|secret|first|second|third|best|most important))",
            r"(?:you (?:need to|should|have to|want to|can))",
            r"(?:make sure|don't forget|remember to|always|never)",
            r"(?:step (?:one|two|three|\d))",
            r"(?:number (?:one|two|three|\d))",
            r"(?:tip|strategy|technique|method|approach|framework)",
            r"(?:instead of|rather than|the difference)",
            r"(?:so what (?:i|we|you) did)",
        ]
        
        for pattern in tip_patterns:
            if re.search(pattern, sent.lower()):
                points.append(sent[:200])
                break
    
    # If no structured points found, take the longest sentences as key ideas
    if not points:
        sorted_sents = sorted(
            [s.strip() for s in sentences if len(s.strip()) > 20],
            key=len,
            reverse=True,
        )
        points = [s[:200] for s in sorted_sents[:3]]
    
    return points[:5]


def _score_structure(
    hook_text: str,
    hook_type: str,
    value_text: str,
    cta_text: str,
    cta_type: str,
    total_duration: float,
) -> float:
    """Score how well the video follows Hook/Value/CTA framework. 0-1."""
    score = 0.0
    
    # Has a clear hook (not just rambling)
    if hook_text and len(hook_text.split()) >= 3:
        score += 0.25
        if hook_type != "statement":
            score += 0.1  # Bonus for using a recognized hook pattern
    
    # Has substantial value section
    if value_text and len(value_text.split()) >= 15:
        score += 0.25
    
    # Has a CTA
    if cta_type != "none":
        score += 0.25
    elif cta_text and len(cta_text.split()) >= 5:
        score += 0.1  # Has closing words but no clear CTA
    
    # Duration is in sweet spot (15-60s)
    if 15 <= total_duration <= 60:
        score += 0.15
    elif 10 <= total_duration <= 90:
        score += 0.08
    
    return min(score, 1.0)


def _empty_result() -> Dict:
    return {
        "is_clip": False,
        "content_format": "unknown",
        "has_verbal_hook": False,
        "hook": {"text": "", "start": 0, "end": 0, "type": "none", "strength": 0},
        "value": {"text": "", "start": 0, "end": 0, "key_points": []},
        "cta": {"text": "", "start": 0, "end": 0, "type": "none", "phrase": ""},
        "total_duration": 0,
        "structure_score": 0,
        "full_script": "",
    }


async def analyze_post_content(
    db: AsyncSession,
    post_id: int,
) -> Optional[Dict]:
    """Analyze a single post's transcript into Hook/Value/CTA structure.
    
    Updates the post's hook field and stores full analysis in content_analysis JSONB.
    """
    result = await db.execute(
        text("SELECT transcript, shortcode, music_info FROM crm.competitor_posts WHERE id = :id"),
        {"id": post_id},
    )
    row = result.fetchone()
    if not row or not row[0]:
        return None
    
    transcript = json.loads(row[0]) if isinstance(row[0], str) else row[0]
    shortcode = row[1]
    music_info = row[2] if len(row) > 2 else None
    
    analysis = analyze_content_structure(transcript)
    
    # Add music info to analysis if available
    if music_info:
        analysis["music_info"] = music_info
    
    # Update hook from transcript (first 3s) instead of caption
    hook_text = analysis["hook"]["text"]
    
    await db.execute(
        text("""
            UPDATE crm.competitor_posts 
            SET hook = :hook,
                content_analysis = :analysis
            WHERE id = :id
        """),
        {
            "hook": hook_text[:200] if hook_text else "",
            "analysis": json.dumps(analysis),
            "id": post_id,
        },
    )
    await db.commit()
    
    logger.info("✅ %s: Hook[%s] %.0f%% | Value: %d words | CTA[%s]: %s",
                shortcode, analysis["hook"]["type"], analysis["hook"]["strength"] * 100,
                len(analysis["value"]["text"].split()),
                analysis["cta"]["type"], analysis["cta"]["phrase"][:40] or "none")
    
    return analysis


async def analyze_competitor_content_batch(
    db: AsyncSession,
    competitor_ids: List[int],
) -> Dict:
    """Batch analyze all transcribed posts for Hook/Value/CTA structure.
    
    Returns: {analyzed: int, skipped: int}
    """
    result = await db.execute(
        text("""
            SELECT id FROM crm.competitor_posts
            WHERE competitor_id = ANY(:ids)
              AND transcript IS NOT NULL
              AND content_analysis IS NULL
        """),
        {"ids": competitor_ids},
    )
    post_ids = [r[0] for r in result.fetchall()]
    
    stats = {"analyzed": 0, "skipped": 0}
    
    for pid in post_ids:
        try:
            analysis = await analyze_post_content(db, pid)
            if analysis:
                stats["analyzed"] += 1
            else:
                stats["skipped"] += 1
        except Exception as e:
            logger.warning("Content analysis failed for post %s: %s", pid, e)
            stats["skipped"] += 1
    
    return stats
