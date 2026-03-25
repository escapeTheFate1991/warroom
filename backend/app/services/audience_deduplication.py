"""Audience Deduplication Service

Removes shared audience members and top engagers across multiple posts/competitors
to focus on unique behavioral insights rather than the same power users appearing everywhere.
"""

import logging
from collections import Counter, defaultdict
from typing import Dict, List, Set, Tuple, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

logger = logging.getLogger(__name__)


class AudienceDeduplicator:
    """Removes audience overlap to focus on unique behavioral insights."""
    
    def __init__(self):
        self.power_user_threshold = 0.7  # Top 70% influence score = power user
        self.cross_post_threshold = 3    # Appears on 3+ posts = shared audience
        
    async def get_power_users(self, db: AsyncSession, competitor_id: int) -> Set[str]:
        """Get usernames of power users (high influence, frequent commenters)."""
        # Query for frequent commenters across all posts for this competitor
        query = """
        SELECT username, COUNT(*) as comment_count, AVG(likes) as avg_likes
        FROM (
            SELECT 
                JSONB_ARRAY_ELEMENTS(comment_analysis->'top_commenters') ->> 'username' as username,
                (JSONB_ARRAY_ELEMENTS(comment_analysis->'top_commenters') ->> 'count')::int as likes
            FROM crm.competitor_posts 
            WHERE competitor_id = :competitor_id 
            AND comment_analysis IS NOT NULL
        ) comments
        GROUP BY username
        HAVING COUNT(*) >= 3 OR AVG(likes) > 10
        ORDER BY comment_count DESC, avg_likes DESC
        """
        
        result = await db.execute(text(query), {"competitor_id": competitor_id})
        power_users = {row.username for row in result.fetchall()}
        
        logger.info(f"Identified {len(power_users)} power users for competitor {competitor_id}")
        return power_users
    
    async def get_cross_post_commenters(self, db: AsyncSession, competitor_ids: List[int]) -> Set[str]:
        """Get usernames that appear across multiple competitors' posts."""
        if not competitor_ids:
            return set()
        
        # Query for commenters that appear on multiple competitors
        query = """
        SELECT username, COUNT(DISTINCT competitor_id) as competitor_count
        FROM (
            SELECT 
                competitor_id,
                JSONB_ARRAY_ELEMENTS(comment_analysis->'top_commenters') ->> 'username' as username
            FROM crm.competitor_posts 
            WHERE competitor_id = ANY(:competitor_ids)
            AND comment_analysis IS NOT NULL
        ) cross_comments
        GROUP BY username
        HAVING COUNT(DISTINCT competitor_id) >= 2
        ORDER BY competitor_count DESC
        """
        
        result = await db.execute(
            text(query), 
            {"competitor_ids": competitor_ids}
        )
        cross_commenters = {row.username for row in result.fetchall()}
        
        logger.info(f"Identified {len(cross_commenters)} cross-post commenters")
        return cross_commenters
    
    def filter_psychological_profiles(
        self, 
        profiles: List[Dict], 
        power_users: Set[str],
        cross_commenters: Set[str]
    ) -> List[Dict]:
        """Remove power users and cross-commenters from psychological profiles."""
        excluded_users = power_users | cross_commenters
        
        filtered_profiles = []
        for profile in profiles:
            username = profile.get("username", "")
            
            # Skip if user is in exclusion sets
            if username.lower() in {u.lower() for u in excluded_users}:
                continue
                
            # Skip very high influence scores (likely power users we missed)
            if profile.get("influence_score", 0) > self.power_user_threshold:
                continue
            
            filtered_profiles.append(profile)
        
        logger.info(
            f"Filtered profiles: {len(profiles)} -> {len(filtered_profiles)} "
            f"(removed {len(profiles) - len(filtered_profiles)} shared/power users)"
        )
        
        return filtered_profiles
    
    def calculate_audience_uniqueness_score(
        self, 
        total_profiles: int, 
        filtered_profiles: int,
        cross_commenters: int,
        power_users: int
    ) -> Dict[str, float]:
        """Calculate metrics about audience uniqueness."""
        if total_profiles == 0:
            return {
                "uniqueness_ratio": 0.0,
                "power_user_ratio": 0.0,
                "cross_commenter_ratio": 0.0,
                "unique_insights_available": False
            }
        
        uniqueness_ratio = filtered_profiles / total_profiles
        power_user_ratio = power_users / total_profiles
        cross_commenter_ratio = cross_commenters / total_profiles
        
        return {
            "uniqueness_ratio": round(uniqueness_ratio, 3),
            "power_user_ratio": round(power_user_ratio, 3), 
            "cross_commenter_ratio": round(cross_commenter_ratio, 3),
            "unique_insights_available": uniqueness_ratio > 0.3  # At least 30% unique
        }
    
    async def deduplicate_audience_analysis(
        self, 
        db: AsyncSession,
        psychology_analysis: Dict,
        competitor_id: int,
        related_competitor_ids: List[int] = None
    ) -> Dict:
        """
        Remove shared audience members from psychology analysis.
        
        Args:
            psychology_analysis: Raw psychology analysis with all profiles
            competitor_id: Current competitor being analyzed
            related_competitor_ids: Other competitors to check for overlap
        
        Returns:
            Deduplicated psychology analysis with uniqueness metrics
        """
        if not psychology_analysis.get("psychological_profiles"):
            return psychology_analysis
        
        # Get exclusion sets
        power_users = await self.get_power_users(db, competitor_id)
        
        cross_commenters = set()
        if related_competitor_ids:
            cross_commenters = await self.get_cross_post_commenters(
                db, [competitor_id] + related_competitor_ids
            )
        
        # Filter profiles
        original_profiles = psychology_analysis["psychological_profiles"]
        filtered_profiles = self.filter_psychological_profiles(
            original_profiles, power_users, cross_commenters
        )
        
        # Calculate uniqueness metrics
        uniqueness_metrics = self.calculate_audience_uniqueness_score(
            total_profiles=len(original_profiles),
            filtered_profiles=len(filtered_profiles),
            cross_commenters=len(cross_commenters),
            power_users=len(power_users)
        )
        
        # Update the analysis
        deduplicated_analysis = psychology_analysis.copy()
        deduplicated_analysis["psychological_profiles"] = filtered_profiles
        deduplicated_analysis["audience_uniqueness"] = uniqueness_metrics
        deduplicated_analysis["excluded_profiles"] = {
            "power_users": len(power_users),
            "cross_commenters": len(cross_commenters),
            "total_excluded": len(power_users) + len(cross_commenters)
        }
        
        # Recalculate behavioral insights with filtered data
        if filtered_profiles:
            deduplicated_analysis["behavioral_insights"] = self._recalculate_behavioral_insights(
                filtered_profiles
            )
            deduplicated_analysis["sharing_psychology"] = self._recalculate_sharing_psychology(
                filtered_profiles
            )
        
        return deduplicated_analysis
    
    def _recalculate_behavioral_insights(self, filtered_profiles: List[Dict]) -> Dict:
        """Recalculate behavioral insights with filtered profiles."""
        if not filtered_profiles:
            return {}
        
        # Motivation distribution
        motivations = [p.get("share_motivation", "") for p in filtered_profiles]
        motivation_dist = dict(Counter(motivations))
        
        # Depth distribution  
        depths = [p.get("comment_depth", "") for p in filtered_profiles]
        depth_dist = dict(Counter(depths))
        
        # Psychology distribution
        psychologies = [p.get("engagement_psychology", "") for p in filtered_profiles]
        psychology_dist = dict(Counter(psychologies))
        
        # Common pain points
        all_pain_points = []
        for p in filtered_profiles:
            pain_points = p.get("pain_points", [])
            if isinstance(pain_points, list):
                all_pain_points.extend(pain_points)
        top_pain_points = dict(Counter(all_pain_points).most_common(10))
        
        # Identity signals
        all_identities = []
        for p in filtered_profiles:
            identities = p.get("identity_signals", [])
            if isinstance(identities, list):
                all_identities.extend(identities)
        top_identities = dict(Counter(all_identities).most_common(10))
        
        # Calculate averages
        influence_scores = [p.get("influence_score", 0) for p in filtered_profiles]
        avg_influence = sum(influence_scores) / len(influence_scores)
        high_influence_count = sum(1 for score in influence_scores if score > 0.5)
        
        return {
            "motivation_distribution": motivation_dist,
            "engagement_depth_distribution": depth_dist,
            "psychology_distribution": psychology_dist,
            "top_pain_points": top_pain_points,
            "dominant_identities": top_identities,
            "average_influence_score": round(avg_influence, 3),
            "high_influence_percentage": round(high_influence_count / len(filtered_profiles), 3)
        }
    
    def _recalculate_sharing_psychology(self, filtered_profiles: List[Dict]) -> Dict:
        """Recalculate sharing psychology with filtered profiles."""
        if not filtered_profiles:
            return {}
        
        # Count sharing motivations
        utility_count = sum(1 for p in filtered_profiles 
                           if p.get("share_motivation") == "utility")
        identity_count = sum(1 for p in filtered_profiles 
                            if p.get("share_motivation") == "identity_signal")
        relatability_count = sum(1 for p in filtered_profiles 
                                if p.get("share_motivation") == "relatability")
        
        total = len(filtered_profiles)
        
        # Determine primary driver
        driver_counts = [
            ("utility", utility_count),
            ("identity_signal", identity_count),
            ("relatability", relatability_count)
        ]
        primary_driver = max(driver_counts, key=lambda x: x[1])[0]
        
        return {
            "primary_sharing_driver": primary_driver,
            "utility_share_signals": round(utility_count / total, 3) if total > 0 else 0,
            "identity_share_signals": round(identity_count / total, 3) if total > 0 else 0,
            "relatability_share_signals": round(relatability_count / total, 3) if total > 0 else 0,
            "sharing_psychology_breakdown": {
                "this_is_how_i_feel": relatability_count,
                "you_need_this": utility_count,
                "this_represents_me": identity_count
            }
        }
    
    async def get_competitor_niche_overlap(
        self, 
        db: AsyncSession,
        target_competitor_id: int,
        niche_competitor_ids: List[int]
    ) -> Dict[str, Any]:
        """
        Analyze audience overlap between a target competitor and niche competitors.
        
        Returns insights about shared vs unique audience segments.
        """
        if not niche_competitor_ids:
            return {"overlap_analysis": {}, "unique_segments": []}
        
        # Get all commenters for target competitor
        target_query = """
        SELECT DISTINCT
            JSONB_ARRAY_ELEMENTS(comment_analysis->'top_commenters') ->> 'username' as username,
            (JSONB_ARRAY_ELEMENTS(comment_analysis->'top_commenters') ->> 'count')::int as engagement_count
        FROM crm.competitor_posts 
        WHERE competitor_id = :target_id 
        AND comment_analysis IS NOT NULL
        """
        
        result = await db.execute(text(target_query), {"target_id": target_competitor_id})
        target_audience = {row.username: row.engagement_count for row in result.fetchall()}
        
        # Get commenters for niche competitors
        niche_query = """
        SELECT 
            competitor_id,
            JSONB_ARRAY_ELEMENTS(comment_analysis->'top_commenters') ->> 'username' as username,
            (JSONB_ARRAY_ELEMENTS(comment_analysis->'top_commenters') ->> 'count')::int as engagement_count
        FROM crm.competitor_posts 
        WHERE competitor_id = ANY(:niche_ids)
        AND comment_analysis IS NOT NULL
        """
        
        result = await db.execute(text(niche_query), {"niche_ids": niche_competitor_ids})
        niche_audiences = defaultdict(dict)
        for row in result.fetchall():
            niche_audiences[row.competitor_id][row.username] = row.engagement_count
        
        # Calculate overlap metrics
        overlap_analysis = {}
        for niche_id, niche_audience in niche_audiences.items():
            shared_users = set(target_audience.keys()) & set(niche_audience.keys())
            overlap_ratio = len(shared_users) / len(target_audience) if target_audience else 0
            
            overlap_analysis[niche_id] = {
                "shared_users": len(shared_users),
                "overlap_ratio": round(overlap_ratio, 3),
                "unique_to_target": len(target_audience) - len(shared_users),
                "unique_to_niche": len(niche_audience) - len(shared_users)
            }
        
        # Identify unique audience segments
        all_niche_users = set()
        for niche_audience in niche_audiences.values():
            all_niche_users.update(niche_audience.keys())
        
        unique_to_target = set(target_audience.keys()) - all_niche_users
        unique_segments = [
            {
                "username": username,
                "engagement_level": target_audience[username],
                "exclusivity": "high"  # Only engages with target, not niche competitors
            }
            for username in unique_to_target
        ]
        
        return {
            "overlap_analysis": overlap_analysis,
            "unique_segments": sorted(
                unique_segments, 
                key=lambda x: x["engagement_level"], 
                reverse=True
            )[:20]  # Top 20 unique audience members
        }


# Singleton instance
audience_deduplicator = AudienceDeduplicator()