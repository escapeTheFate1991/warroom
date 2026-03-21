"""Service for managing audience profile data from commenter information."""

import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from collections import Counter

from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.crm.audience_profile import AudienceProfile

logger = logging.getLogger(__name__)


async def populate_audience_profiles_from_comments(db: AsyncSession, org_id: int) -> Dict[str, int]:
    """Populate audience_profiles table from existing competitor_posts comment data.
    
    Returns: {"created": count, "updated": count}
    """
    try:
        # Get all posts with comments_data containing commenter information
        result = await db.execute(
            text("""
            SELECT 
                id,
                commenter_username,
                commenter_profile_url,
                comment_likes,
                is_reply,
                posted_at,
                comments_data,
                platform
            FROM crm.competitor_posts 
            WHERE org_id = :org_id 
              AND comments_data IS NOT NULL
              AND (comments_data->>'analyzed')::int > 0
            ORDER BY posted_at DESC
            """),
            {"org_id": org_id}
        )
        posts = result.fetchall()
        
        if not posts:
            logger.info("No posts with comment data found for org %s", org_id)
            return {"created": 0, "updated": 0}
        
        # Extract commenter data from comments_data JSONB
        commenter_stats = {}  # username -> {platform, interactions, first_seen, last_seen, total_likes}
        
        for post in posts:
            try:
                comments_data = post.comments_data
                if isinstance(comments_data, str):
                    comments_data = json.loads(comments_data)
                
                posted_at = post.posted_at or datetime.now()
                platform = post.platform or "instagram"
                
                # Extract from top_commenters in comments_data
                top_commenters = comments_data.get("top_commenters", [])
                for commenter in top_commenters:
                    username = commenter.get("username")
                    if not username:
                        continue
                    
                    interaction_count = commenter.get("count", 0)
                    if username not in commenter_stats:
                        commenter_stats[username] = {
                            "platform": platform,
                            "interactions": 0,
                            "first_seen": posted_at,
                            "last_seen": posted_at,
                            "total_likes": 0
                        }
                    
                    commenter_stats[username]["interactions"] += interaction_count
                    commenter_stats[username]["last_seen"] = max(commenter_stats[username]["last_seen"], posted_at)
                    commenter_stats[username]["first_seen"] = min(commenter_stats[username]["first_seen"], posted_at)
                
                # Also extract from individual comment records if we have them
                if post.commenter_username:
                    username = post.commenter_username
                    if username not in commenter_stats:
                        commenter_stats[username] = {
                            "platform": platform,
                            "interactions": 0,
                            "first_seen": posted_at,
                            "last_seen": posted_at,
                            "total_likes": 0
                        }
                    
                    commenter_stats[username]["interactions"] += 1
                    commenter_stats[username]["total_likes"] += (post.comment_likes or 0)
                    commenter_stats[username]["last_seen"] = max(commenter_stats[username]["last_seen"], posted_at)
                    commenter_stats[username]["first_seen"] = min(commenter_stats[username]["first_seen"], posted_at)
                    
            except Exception as e:
                logger.warning("Error processing comments data for post %s: %s", post.id, e)
                continue
        
        if not commenter_stats:
            logger.info("No commenter data extracted from posts")
            return {"created": 0, "updated": 0}
        
        # Determine engagement levels
        interaction_counts = [stats["interactions"] for stats in commenter_stats.values()]
        if len(interaction_counts) > 1:
            sorted_counts = sorted(interaction_counts, reverse=True)
            high_threshold = sorted_counts[len(sorted_counts) // 5] if len(sorted_counts) >= 5 else sorted_counts[0]
            low_threshold = sorted_counts[len(sorted_counts) * 4 // 5] if len(sorted_counts) >= 5 else 1
        else:
            high_threshold = interaction_counts[0] if interaction_counts else 1
            low_threshold = 1
        
        created_count = 0
        updated_count = 0
        
        for username, stats in commenter_stats.items():
            try:
                # Determine engagement level
                if stats["interactions"] >= high_threshold:
                    engagement_level = "high"
                elif stats["interactions"] >= low_threshold:
                    engagement_level = "medium"
                else:
                    engagement_level = "low"
                
                # Check if profile already exists
                existing_result = await db.execute(
                    select(AudienceProfile)
                    .where(
                        AudienceProfile.org_id == org_id,
                        AudienceProfile.username == username,
                        AudienceProfile.platform == stats["platform"]
                    )
                )
                existing = existing_result.scalar_one_or_none()
                
                profile_url = f"https://www.instagram.com/{username}/" if stats["platform"] == "instagram" else None
                
                if existing:
                    # Update existing profile
                    existing.interaction_count = max(existing.interaction_count, stats["interactions"])
                    existing.engagement_level = engagement_level
                    existing.last_seen_at = max(existing.last_seen_at, stats["last_seen"])
                    existing.first_seen_at = min(existing.first_seen_at, stats["first_seen"])
                    existing.updated_at = datetime.now()
                    
                    # Update profile_data with additional stats
                    profile_data = existing.profile_data or {}
                    profile_data.update({
                        "total_comment_likes": stats["total_likes"],
                        "last_updated_from_comments": datetime.now().isoformat()
                    })
                    existing.profile_data = profile_data
                    
                    updated_count += 1
                    
                else:
                    # Create new profile
                    new_profile = AudienceProfile(
                        org_id=org_id,
                        username=username,
                        platform=stats["platform"],
                        profile_url=profile_url,
                        engagement_level=engagement_level,
                        first_seen_at=stats["first_seen"],
                        last_seen_at=stats["last_seen"],
                        interaction_count=stats["interactions"],
                        profile_data={
                            "total_comment_likes": stats["total_likes"],
                            "created_from_comments": datetime.now().isoformat()
                        }
                    )
                    db.add(new_profile)
                    created_count += 1
                    
            except Exception as e:
                logger.error("Error creating/updating profile for %s: %s", username, e)
                continue
        
        await db.commit()
        
        logger.info(
            "Audience profile sync complete for org %s: %d created, %d updated",
            org_id, created_count, updated_count
        )
        
        return {"created": created_count, "updated": updated_count}
        
    except Exception as e:
        await db.rollback()
        logger.error("Failed to populate audience profiles: %s", e)
        raise


async def enrich_audience_profile(db: AsyncSession, username: str, platform: str, org_id: int, 
                                profile_data: Dict[str, Any]) -> bool:
    """Enrich an audience profile with scraped data (followers, bio, etc.)."""
    try:
        result = await db.execute(
            select(AudienceProfile)
            .where(
                AudienceProfile.org_id == org_id,
                AudienceProfile.username == username,
                AudienceProfile.platform == platform
            )
        )
        profile = result.scalar_one_or_none()
        
        if not profile:
            logger.warning("Profile not found for enrichment: %s@%s", username, platform)
            return False
        
        # Update profile with enriched data
        profile.display_name = profile_data.get("display_name") or profile.display_name
        profile.bio = profile_data.get("bio") or profile.bio
        profile.followers = profile_data.get("followers") or profile.followers
        profile.following = profile_data.get("following") or profile.following
        profile.post_count = profile_data.get("post_count") or profile.post_count
        profile.is_verified = profile_data.get("is_verified", profile.is_verified)
        profile.is_business = profile_data.get("is_business", profile.is_business)
        profile.updated_at = datetime.now()
        
        # Update profile_data with additional metadata
        existing_data = profile.profile_data or {}
        existing_data.update({
            "last_enriched": datetime.now().isoformat(),
            **profile_data  # Add any additional metadata
        })
        profile.profile_data = existing_data
        
        await db.commit()
        
        logger.info("Enriched profile for %s@%s", username, platform)
        return True
        
    except Exception as e:
        await db.rollback()
        logger.error("Failed to enrich profile %s@%s: %s", username, platform, e)
        return False


async def calculate_engagement_levels(db: AsyncSession, org_id: int) -> Dict[str, int]:
    """Recalculate engagement levels for all profiles based on interaction distribution."""
    try:
        # Get all profiles for this org
        result = await db.execute(
            select(AudienceProfile.id, AudienceProfile.interaction_count)
            .where(AudienceProfile.org_id == org_id)
        )
        profiles = result.fetchall()
        
        if len(profiles) < 5:
            # Not enough data for meaningful distribution
            return {"high": 0, "medium": 0, "low": 0}
        
        # Calculate percentile thresholds
        interaction_counts = sorted([p.interaction_count for p in profiles], reverse=True)
        high_threshold = interaction_counts[len(interaction_counts) // 5]  # Top 20%
        low_threshold = interaction_counts[len(interaction_counts) * 4 // 5]  # Bottom 20%
        
        updated = {"high": 0, "medium": 0, "low": 0}
        
        for profile_id, interaction_count in profiles:
            if interaction_count >= high_threshold:
                new_level = "high"
            elif interaction_count >= low_threshold:
                new_level = "medium"
            else:
                new_level = "low"
            
            await db.execute(
                text("UPDATE crm.audience_profiles SET engagement_level = :level, updated_at = NOW() WHERE id = :id"),
                {"level": new_level, "id": profile_id}
            )
            
            updated[new_level] += 1
        
        await db.commit()
        
        logger.info(
            "Recalculated engagement levels for org %s: %d high, %d medium, %d low",
            org_id, updated["high"], updated["medium"], updated["low"]
        )
        
        return updated
        
    except Exception as e:
        await db.rollback()
        logger.error("Failed to calculate engagement levels: %s", e)
        raise