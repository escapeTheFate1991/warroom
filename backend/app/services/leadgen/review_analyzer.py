"""Keyword-based review sentiment analysis and pain point extraction.

No external API calls — purely pattern matching. Fast and free.
"""

import re
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Positive and negative keyword lists for sentiment scoring
POSITIVE_KEYWORDS = [
    "great", "excellent", "amazing", "wonderful", "fantastic", "awesome",
    "love", "loved", "best", "perfect", "outstanding", "superb",
    "friendly", "professional", "recommend", "highly recommend",
    "impressed", "happy", "satisfied", "pleasant", "helpful",
    "quick", "fast", "efficient", "reliable", "trustworthy",
    "clean", "beautiful", "quality", "top notch", "five star",
    "above and beyond", "exceeded expectations",
]

NEGATIVE_KEYWORDS = [
    "terrible", "horrible", "awful", "worst", "bad", "poor",
    "rude", "unprofessional", "waste", "disappointed", "disappointing",
    "never again", "avoid", "scam", "overpriced", "expensive",
    "slow", "waited", "waiting", "forever", "hours",
    "dirty", "broken", "damaged", "cheap", "shoddy",
    "unresponsive", "ignored", "didn't care", "don't bother",
    "complaint", "refund", "ripoff", "rip off", "nightmare",
]

# Opportunity flag patterns — maps regex patterns to flag names
# Each entry: (flag_name, list_of_patterns, scoring_rule_name)
OPPORTUNITY_PATTERNS: list[tuple[str, list[str], str]] = [
    (
        "needs_website_help",
        [
            r"website\s*(is|looks|seems)?\s*(bad|terrible|awful|broken|down|slow|outdated|ugly|horrible|confusing|hard to navigate)",
            r"(bad|terrible|awful|broken|no|need[s]? a|need[s]? new|update)\s*website",
            r"website\s*(doesn.?t|does not|didn.?t)\s*work",
            r"can.?t\s*(find|use|navigate)\s*(the|their)?\s*website",
            r"website.*crash",
            r"website.*error",
            r"(no|don.?t have a?)\s*website",
        ],
        "website_complaints",
    ),
    (
        "poor_communication",
        [
            r"can.?t\s*(reach|contact|get\s*(a )?hold)",
            r"never\s*(answer|pick up|respond|call back|return)",
            r"hard\s*to\s*(reach|contact|get\s*(a )?hold)",
            r"(no|didn.?t|doesn.?t|don.?t)\s*(respond|reply|answer|call back|return)",
            r"(ignored|ghosted)\s*(my|our|the)?\s*(call|email|message)",
            r"(phone|call)\s*(goes?\s*to)?\s*voicemail",
            r"left\s*(multiple\s*)?messages?\s*(and)?\s*(no|never)",
        ],
        "communication_issues",
    ),
    (
        "needs_modernization",
        [
            r"outdated",
            r"old\s*(fashioned|school|looking|style)",
            r"stuck\s*in\s*(the\s*)?past",
            r"need[s]?\s*(to\s*)?(update|upgrade|modernize|renovate)",
            r"(looks|feels|seems)\s*(really\s*)?(dated|old|ancient|archaic)",
            r"hasn.?t\s*(changed|updated|upgraded)\s*in\s*(years|decades|forever)",
        ],
        "needs_modernization",
    ),
    (
        "needs_online_booking",
        [
            r"(no|can.?t|cannot|couldn.?t)\s*(online\s*)?(book|schedule|appointment|reservation)\s*(online)?",
            r"(wish|should|need)\s*(they\s*)?(had\s*)?(online\s*)?(booking|scheduling|appointments?)",
            r"have\s*to\s*call\s*(to\s*)?(book|schedule|make)",
            r"no\s*online\s*(booking|scheduling|reservation|appointment)",
        ],
        "needs_online_booking",
    ),
    (
        "needs_social_presence",
        [
            r"(no|not\s*on|don.?t have)\s*(social\s*media|instagram|facebook|tiktok)",
            r"(can.?t|couldn.?t)\s*find\s*(them\s*)?(on\s*)?(social|instagram|facebook)",
            r"(wish|should)\s*(they\s*)?(were\s*on|had)\s*(social|instagram|facebook)",
            r"no\s*(online|social|web)\s*presence",
        ],
        "needs_social_presence",
    ),
    (
        "process_inefficiency",
        [
            r"(slow|took|waited|waiting)\s*(so\s*)?(long|forever|hours|ages)",
            r"(very|extremely|incredibly|ridiculously)\s*slow",
            r"(inefficient|disorganized|chaotic|mess)",
            r"took\s*(them\s*)?\d+\s*(hours?|days?|weeks?)",
            r"still\s*waiting",
        ],
        "process_inefficiency",
    ),
    (
        "price_sensitive",
        [
            r"(too\s*)?expensive",
            r"overpriced",
            r"(rip\s*off|ripoff)",
            r"(not\s*worth|wasn.?t\s*worth)\s*(the\s*)?(price|money|cost)",
            r"(way|much)\s*(too\s*)?(much|pricey|costly)",
            r"(cheaper|better\s*price|more\s*affordable)\s*(elsewhere|somewhere|options?)",
        ],
        "price_sensitive",
    ),
]


@dataclass
class AnalysisResult:
    sentiment_score: float = 0.0  # -1.0 to 1.0
    pain_points: list[str] = field(default_factory=list)
    opportunity_flags: list[str] = field(default_factory=list)
    highlight_quotes: list[str] = field(default_factory=list)


def analyze_reviews(review_texts: list[str]) -> AnalysisResult:
    """Analyze a list of review texts for sentiment and opportunity flags.

    Returns sentiment score (-1.0 to 1.0), pain points, opportunity flags,
    and highlight quotes (top 5 most relevant snippets).
    """
    if not review_texts:
        return AnalysisResult()

    result = AnalysisResult()
    total_sentiment = 0.0
    scored_reviews = 0
    all_pain_points: set[str] = set()
    all_flags: set[str] = set()
    # (relevance_score, quote) tuples for ranking highlights
    candidate_highlights: list[tuple[float, str]] = []

    for text in review_texts:
        if not text or not text.strip():
            continue

        text_lower = text.lower()

        # --- Sentiment scoring ---
        pos_count = sum(1 for kw in POSITIVE_KEYWORDS if kw in text_lower)
        neg_count = sum(1 for kw in NEGATIVE_KEYWORDS if kw in text_lower)
        total = pos_count + neg_count
        if total > 0:
            review_sentiment = (pos_count - neg_count) / total
        else:
            review_sentiment = 0.0
        total_sentiment += review_sentiment
        scored_reviews += 1

        # --- Opportunity flag matching ---
        review_relevance = 0.0
        matched_patterns: list[str] = []

        for flag_name, patterns, _rule_name in OPPORTUNITY_PATTERNS:
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    all_flags.add(flag_name)
                    pain_desc = _flag_to_pain_point(flag_name, text_lower)
                    if pain_desc:
                        all_pain_points.add(pain_desc)
                    review_relevance += 1.0
                    matched_patterns.append(flag_name)
                    break  # One match per flag per review is enough

        # Negative sentiment also contributes to relevance
        if neg_count > pos_count:
            review_relevance += 0.5

        if review_relevance > 0:
            # Truncate to a reasonable quote length
            quote = text.strip()[:300]
            if len(text) > 300:
                quote += "..."
            candidate_highlights.append((review_relevance, quote))

    # Compute final sentiment
    if scored_reviews > 0:
        raw_sentiment = total_sentiment / scored_reviews
        # Clamp to [-1.0, 1.0]
        result.sentiment_score = round(max(-1.0, min(1.0, raw_sentiment)), 2)

    result.pain_points = sorted(all_pain_points)
    result.opportunity_flags = sorted(all_flags)

    # Top 5 most relevant highlights
    candidate_highlights.sort(key=lambda x: x[0], reverse=True)
    result.highlight_quotes = [q for _, q in candidate_highlights[:5]]

    return result


def _flag_to_pain_point(flag: str, text_lower: str) -> str:
    """Convert an opportunity flag to a human-readable pain point description."""
    mapping = {
        "needs_website_help": "bad website",
        "poor_communication": "hard to reach",
        "needs_modernization": "outdated/needs modernization",
        "needs_online_booking": "no online booking",
        "needs_social_presence": "no social media presence",
        "process_inefficiency": "slow service",
        "price_sensitive": "overpriced",
    }
    return mapping.get(flag, "")
