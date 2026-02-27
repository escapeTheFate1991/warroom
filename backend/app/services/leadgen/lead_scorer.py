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