"""Smart Multi-Account Distribution Service

Advanced content distribution system with anti-detection measures,
caption variations, staggered scheduling, and visibility scoring.
"""

import hashlib
import json
import logging
import random
import re
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


def generate_caption_variations(
    original_caption: str, 
    count: int, 
    platform: str = None
) -> List[str]:
    """Generate unique caption variants to avoid duplicate content detection.
    
    Uses rule-based variations (upgradeable to AI later):
    1. Synonym replacement for key phrases
    2. Sentence reordering where possible  
    3. Hashtag set rotation
    4. Emoji variation
    5. Platform-specific adaptation
    """
    variations = [original_caption]
    
    # Common synonym replacements
    synonyms = {
        r'\bnobody\b': ['no one', 'not a single person', 'barely anyone'],
        r'\btalking about\b': ['mentioning', 'discussing', 'bringing up'],
        r'\bthis\b': ['this thing', 'it', 'what happened'],
        r'\bbut\b': ['however', 'yet', 'though'],
        r'\bhere\'s\b': ['here is', 'check this out:', 'look at this:'],
        r'\bwhy\b': ['the reason', 'how come', 'what makes'],
        r'\beveryone\b': ['people', 'most folks', 'the majority'],
        r'\bmissed\b': ['overlooked', 'ignored', 'didn\'t catch'],
        r'\bflew under\b': ['slipped under', 'went under', 'stayed under'],
        r'\bradar\b': ['notice', 'the radar', 'attention']
    }
    
    # Common sentence starters for variety
    starters = [
        'Why is nobody mentioning',
        'This flew under everyone\'s radar:',
        'Am I the only one who noticed',
        'Everyone missed this but',
        'Not enough people are talking about',
        'This should be bigger news:'
    ]
    
    # Generate variations
    for i in range(count - 1):
        variant = original_caption
        
        # Apply 1-2 synonym replacements
        applied_synonyms = random.sample(list(synonyms.keys()), min(2, len(synonyms)))
        for pattern in applied_synonyms:
            replacements = synonyms[pattern]
            if re.search(pattern, variant, re.IGNORECASE):
                replacement = random.choice(replacements)
                variant = re.sub(pattern, replacement, variant, count=1, flags=re.IGNORECASE)
        
        # Try sentence restructuring for some variations
        if i % 2 == 0 and any(starter in original_caption for starter in ['Nobody', 'No one', 'Everyone']):
            # Replace opening with a different starter
            new_starter = random.choice(starters)
            if variant.startswith('Nobody'):
                variant = re.sub(r'^Nobody[^.!?]*', f'{new_starter}', variant)
            elif variant.startswith('Everyone'):
                variant = re.sub(r'^Everyone[^.!?]*', f'{new_starter}', variant)
        
        # Platform-specific adaptations
        if platform == 'instagram':
            # Add varied hashtag patterns
            hashtag_sets = [
                '#trending #viral #fyp',
                '#hidden #truth #exposed',  
                '#breaking #news #update',
                '#shocking #reveal #omg'
            ]
            if '#' not in variant and random.random() < 0.7:
                variant += '\n\n' + random.choice(hashtag_sets)
        elif platform == 'twitter':
            # Keep it shorter, remove hashtags
            variant = variant.replace('\n\n#', '\n').replace('#', '')
        
        # Emoji variations
        emoji_options = ['👀', '🤯', '😱', '🚨', '💯', '🔥', '⚡', '🎯']
        if random.random() < 0.5:
            variant = random.choice(emoji_options) + ' ' + variant
        
        variations.append(variant)
    
    return variations[:count]


def calculate_stagger_schedule(
    accounts: List[dict],
    stagger_hours: float,
    cluster_size: int = 5,
    base_time: datetime = None
) -> List[dict]:
    """Calculate posting schedule with cluster-based staggering.
    
    Posts to `cluster_size` accounts, waits `stagger_hours`, posts to next cluster.
    Within each cluster, posts are 5-10 minutes apart.
    """
    if base_time is None:
        base_time = datetime.now(timezone.utc) + timedelta(hours=1)  # Default to 1 hour from now
    
    schedule = []
    current_time = base_time
    
    # Group accounts into clusters
    for cluster_start in range(0, len(accounts), cluster_size):
        cluster = accounts[cluster_start:cluster_start + cluster_size]
        
        # Schedule posts within the cluster (5-10 minutes apart)
        cluster_time = current_time
        for i, account in enumerate(cluster):
            for platform in account.get('platforms', [account.get('platform', 'instagram')]):
                post_time = cluster_time + timedelta(minutes=random.randint(5, 10) * i)
                schedule.append({
                    'account_id': account['id'],
                    'account_type': account.get('type', 'sub'),
                    'platform': platform,
                    'scheduled_time': post_time
                })
        
        # Move to next cluster time
        current_time = current_time + timedelta(hours=stagger_hours)
    
    return schedule


def calculate_visibility_score(
    accounts: List[dict],
    stagger_hours: float,
    auto_variations: bool,
    randomizer_enabled: bool,
    cluster_size: int = 5
) -> int:
    """Calculate predicted visibility score (1-100).
    
    Formula: V_h (Hash Uniqueness) × 0.4 + V_t (Temporal Stagger) × 0.3 + 
             V_c (Caption Entropy) × 0.2 + V_a (Account Health) × 0.1
    """
    # V_h: Hash uniqueness (40%)
    v_h = 100 if randomizer_enabled else 30
    
    # V_t: Temporal stagger (30%) 
    if stagger_hours >= 2:
        v_t = 100
    elif stagger_hours >= 1:
        v_t = 80
    elif stagger_hours >= 0.5:
        v_t = 60
    else:
        v_t = 30
    
    # V_c: Caption entropy (20%)
    v_c = 100 if auto_variations else 20
    
    # V_a: Account health (10%) — placeholder, will use real data later
    v_a = 70  # Default assumed health
    
    # Calculate base score
    score = int(v_h * 0.4 + v_t * 0.3 + v_c * 0.2 + v_a * 0.1)
    
    # Anti-burst penalty: if 10+ accounts from same proxy/cluster in 5 min, -30 points
    account_count = len(accounts)
    posts_per_cluster = min(cluster_size, account_count)
    
    if posts_per_cluster >= 10 and stagger_hours < 0.1:  # 10+ posts in under 6 minutes
        score -= 30
    
    # Bonus for good distribution patterns
    if account_count >= 5 and stagger_hours >= 1 and auto_variations:
        score += 10
    
    return min(100, max(0, score))


def generate_video_variant_hash(
    video_url: str,
    randomizer_config: dict
) -> str:
    """Generate a unique hash for video variant tracking.
    
    For now, just hash the URL + timestamp. Later this could represent
    actual video modifications (subtle timing changes, etc.)
    """
    if not randomizer_config.get('enabled', False):
        # No randomization, same hash
        return hashlib.md5(video_url.encode()).hexdigest()
    
    # Add some randomization to the hash
    timestamp = datetime.now(timezone.utc).isoformat()
    intensity = randomizer_config.get('intensity', 'subtle')
    
    # Different levels of hash variation
    if intensity == 'aggressive':
        salt = f"{timestamp}:{random.randint(1000, 9999)}"
    elif intensity == 'moderate':
        salt = f"{timestamp}:{random.randint(100, 999)}"
    else:  # subtle
        salt = f"{timestamp[:19]}:{random.randint(10, 99)}"  # Remove microseconds
    
    combined = f"{video_url}:{salt}"
    return hashlib.md5(combined.encode()).hexdigest()


async def create_smart_distribution(
    db: AsyncSession,
    org_id: int,
    user_id: int,
    video_project_id: int,
    video_url: str,
    caption: str,
    accounts: List[dict],
    stagger_hours: float = 2,
    cluster_size: int = 5,
    auto_variations: bool = True,
    randomizer: dict = None,
    platform_adapt: bool = True
) -> dict:
    """Create a smart content distribution across multiple accounts."""
    try:
        if randomizer is None:
            randomizer = {"enabled": True, "intensity": "subtle"}
        
        # Calculate schedule
        schedule = calculate_stagger_schedule(accounts, stagger_hours, cluster_size)
        
        # Generate caption variations if enabled
        if auto_variations and len(schedule) > 1:
            unique_captions = generate_caption_variations(
                caption, 
                len(schedule),
                platform=schedule[0]['platform'] if schedule else None
            )
        else:
            unique_captions = [caption] * len(schedule)
        
        # Calculate visibility score
        visibility_score = calculate_visibility_score(
            accounts, stagger_hours, auto_variations, 
            randomizer.get('enabled', False), cluster_size
        )
        
        # Insert distribution record
        insert_distribution = text("""
            INSERT INTO crm.content_distributions (
                org_id, user_id, video_project_id, original_caption,
                total_posts, stagger_hours, cluster_size, visibility_score,
                randomizer_config, status
            ) VALUES (
                :org_id, :user_id, :video_project_id, :original_caption,
                :total_posts, :stagger_hours, :cluster_size, :visibility_score,
                :randomizer_config, 'scheduled'
            ) RETURNING id
        """)
        
        result = await db.execute(insert_distribution, {
            "org_id": org_id,
            "user_id": user_id,
            "video_project_id": video_project_id,
            "original_caption": caption,
            "total_posts": len(schedule),
            "stagger_hours": stagger_hours,
            "cluster_size": cluster_size,
            "visibility_score": visibility_score,
            "randomizer_config": json.dumps(randomizer)
        })
        
        distribution_id = result.fetchone()[0]
        
        # Insert distribution posts
        for i, post_schedule in enumerate(schedule):
            caption_variant = unique_captions[i % len(unique_captions)]
            video_hash = generate_video_variant_hash(video_url, randomizer)
            
            insert_post = text("""
                INSERT INTO crm.distribution_posts (
                    distribution_id, account_id, platform, scheduled_time,
                    caption_variant, video_variant_hash, status
                ) VALUES (
                    :distribution_id, :account_id, :platform, :scheduled_time,
                    :caption_variant, :video_variant_hash, 'queued'
                )
            """)
            
            await db.execute(insert_post, {
                "distribution_id": distribution_id,
                "account_id": post_schedule['account_id'],
                "platform": post_schedule['platform'],
                "scheduled_time": post_schedule['scheduled_time'],
                "caption_variant": caption_variant,
                "video_variant_hash": video_hash
            })
        
        await db.commit()
        
        # Build response
        response_schedule = []
        for i, post_schedule in enumerate(schedule):
            response_schedule.append({
                "account_id": post_schedule['account_id'],
                "platform": post_schedule['platform'],
                "scheduled_time": post_schedule['scheduled_time'].isoformat(),
                "caption_variant": unique_captions[i % len(unique_captions)]
            })
        
        return {
            "distribution_id": distribution_id,
            "status": "scheduled",
            "total_posts": len(schedule),
            "schedule": response_schedule,
            "randomizer_applied": randomizer.get('enabled', False),
            "visibility_score": visibility_score
        }
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create smart distribution: {e}")
        raise


async def get_distribution_status(
    db: AsyncSession,
    org_id: int,
    distribution_id: int
) -> dict:
    """Get status of a content distribution with all post statuses."""
    try:
        # Get distribution details
        distribution_query = text("""
            SELECT 
                id, video_project_id, original_caption, total_posts,
                stagger_hours, cluster_size, visibility_score,
                randomizer_config, status, created_at
            FROM crm.content_distributions
            WHERE id = :distribution_id AND org_id = :org_id
        """)
        
        distribution_result = await db.execute(distribution_query, {
            "distribution_id": distribution_id,
            "org_id": org_id
        })
        distribution = distribution_result.fetchone()
        
        if not distribution:
            raise ValueError(f"Distribution {distribution_id} not found")
        
        # Get all posts for this distribution
        posts_query = text("""
            SELECT 
                id, account_id, platform, scheduled_time, caption_variant,
                video_variant_hash, status, post_url, posted_at, error
            FROM crm.distribution_posts
            WHERE distribution_id = :distribution_id
            ORDER BY scheduled_time
        """)
        
        posts_result = await db.execute(posts_query, {
            "distribution_id": distribution_id
        })
        posts = posts_result.fetchall()
        
        # Build response
        post_list = []
        for post in posts:
            post_list.append({
                "id": post[0],
                "account_id": post[1],
                "platform": post[2],
                "scheduled_time": post[3].isoformat() if post[3] else None,
                "caption_variant": post[4],
                "video_variant_hash": post[5],
                "status": post[6],
                "post_url": post[7],
                "posted_at": post[8].isoformat() if post[8] else None,
                "error": post[9]
            })
        
        return {
            "distribution_id": distribution[0],
            "video_project_id": distribution[1],
            "original_caption": distribution[2],
            "total_posts": distribution[3],
            "stagger_hours": distribution[4],
            "cluster_size": distribution[5],
            "visibility_score": distribution[6],
            "randomizer_config": json.loads(distribution[7]) if distribution[7] else {},
            "status": distribution[8],
            "created_at": distribution[9].isoformat() if distribution[9] else None,
            "posts": post_list
        }
        
    except Exception as e:
        logger.error(f"Failed to get distribution status: {e}")
        raise