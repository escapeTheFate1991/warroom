"""Lead scoring engine — ranks leads by yieldlabs conversion potential."""

from app.models.lead import Lead

# Weights for lead scoring (0-100 scale)
SCORING_RULES = {
    "no_website": 25,           # No website = easy sell
    "bad_website_score": 20,    # Audit score < 60 = strong pitch
    "mediocre_website": 10,     # Audit score 60-75 = moderate pitch
    "has_email": 10,            # Direct contact available
    "has_phone": 5,             # Phone available
    "high_google_rating": 5,    # Cares about reputation (4.0+)
    "many_reviews": 5,          # Active business (50+ reviews)
    "has_socials": 5,           # Active online presence
    "old_platform": 15,         # On Wix/Weebly/GoDaddy = upgrade opportunity
    # Review intelligence scoring
    "negative_reviews": 15,     # Yelp/Google rating < 3.5 = unhappy customers
    "website_complaints": 20,   # Reviews mention website problems = HOT lead
    "communication_issues": 10, # Reviews mention can't reach them
    "needs_modernization": 15,  # Reviews say outdated/old
    "low_review_count": 5,      # < 10 reviews = low visibility
    "needs_online_booking": 10, # Reviews mention no online booking
}

# Maps opportunity flags to scoring rule names
FLAG_SCORE_MAP = {
    "needs_website_help": "website_complaints",
    "poor_communication": "communication_issues",
    "needs_modernization": "needs_modernization",
    "needs_online_booking": "needs_online_booking",
    "needs_social_presence": None,       # No dedicated score, captured by has_socials
    "process_inefficiency": None,        # Informational, not scored separately
    "price_sensitive": None,             # Informational for competitors
}

UPGRADE_PLATFORMS = {"wix", "weebly", "godaddy", "squarespace"}


def score_lead(lead: Lead) -> tuple[int, str]:
    """Calculate lead score and tier. Returns (score, tier)."""
    score = 0

    # No website = biggest opportunity
    if not lead.has_website or not lead.website:
        score += SCORING_RULES["no_website"]
    elif lead.website_audit_score is not None:
        if lead.website_audit_score < 60:
            score += SCORING_RULES["bad_website_score"]
        elif lead.website_audit_score < 75:
            score += SCORING_RULES["mediocre_website"]

    # Contact availability
    if lead.emails:
        score += SCORING_RULES["has_email"]
    if lead.phone:
        score += SCORING_RULES["has_phone"]

    # Business signals
    if lead.google_rating and float(lead.google_rating) >= 4.0:
        score += SCORING_RULES["high_google_rating"]
    if lead.google_reviews_count and lead.google_reviews_count >= 50:
        score += SCORING_RULES["many_reviews"]

    # Social presence
    social_count = sum(1 for url in [
        lead.facebook_url, lead.instagram_url, lead.linkedin_url, lead.twitter_url
    ] if url)
    if social_count >= 2:
        score += SCORING_RULES["has_socials"]

    # Platform upgrade opportunity
    if lead.website_platform and lead.website_platform.lower() in UPGRADE_PLATFORMS:
        score += SCORING_RULES["old_platform"]

    # --- Review intelligence scoring ---
    # Negative sentiment or low rating
    has_negative = False
    if lead.review_sentiment_score is not None and float(lead.review_sentiment_score) < 0:
        has_negative = True
    if lead.yelp_rating and float(lead.yelp_rating) < 3.5:
        has_negative = True
    if lead.google_rating and float(lead.google_rating) < 3.5:
        has_negative = True
    if has_negative:
        score += SCORING_RULES["negative_reviews"]

    # Low review count (low visibility)
    total_reviews = (lead.google_reviews_count or 0) + (lead.yelp_reviews_count or 0)
    if 0 < total_reviews < 10:
        score += SCORING_RULES["low_review_count"]

    # Opportunity flags from review analysis
    if lead.review_opportunity_flags:
        for flag in lead.review_opportunity_flags:
            rule_name = FLAG_SCORE_MAP.get(flag)
            if rule_name and rule_name in SCORING_RULES:
                score += SCORING_RULES[rule_name]

    # Determine tier
    if score >= 60:
        tier = "hot"
    elif score >= 35:
        tier = "warm"
    elif score >= 15:
        tier = "cold"
    else:
        tier = "unscored"

    return score, tier