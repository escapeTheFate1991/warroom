#!/usr/bin/env python3
"""Wave 3 Bulk Processor: Classify remaining posts and generate CDRs for high-power content.

Tasks:
1. Calculate power scores for all classified posts (580 posts)
2. Generate CDRs for posts with Power Score > 2000  
3. Classify remaining unclassified posts (287 posts)
4. Generate CDRs for newly classified high-power posts

This script processes everything in batches to avoid overwhelming the system.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from sqlalchemy import text
from app.db.crm_db import crm_session
from app.services.creator_directive import (
    CreatorDirectiveService, 
    get_post_data,
    mock_intent_classifier,
    CreatorDirectiveReport
)
from app.services.comment_analyzer import analyze_comments_ml

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Wave3BulkProcessor:
    """Bulk processor for Wave 3 CDR generation and post classification"""
    
    def __init__(self):
        self.cdr_service = CreatorDirectiveService()
        self.stats = {
            'total_processed': 0,
            'power_scores_added': 0,
            'cdrs_generated': 0,
            'posts_classified': 0,
            'errors': 0
        }

    async def run_complete_processing(self):
        """Run all Wave 3 processing tasks"""
        logger.info("🚀 Starting Wave 3 Bulk Processing...")
        start_time = datetime.utcnow()
        
        try:
            # Task 1: Add power scores to all classified posts
            await self.add_power_scores_to_classified_posts()
            
            # Task 2: Generate CDRs for high-power classified posts  
            await self.generate_cdrs_for_high_power_posts()
            
            # Task 3: Classify remaining unclassified posts
            await self.classify_remaining_posts()
            
            # Task 4: Generate CDRs for newly classified high-power posts
            await self.generate_cdrs_for_new_high_power_posts()
            
            # Final reporting
            await self.generate_final_report()
            
        except Exception as e:
            logger.error(f"❌ Wave 3 processing failed: {e}")
            raise
        finally:
            await self.cdr_service.close()
            
        duration = (datetime.utcnow() - start_time).total_seconds()
        logger.info(f"✅ Wave 3 processing completed in {duration:.1f}s")

    async def add_power_scores_to_classified_posts(self):
        """Add power scores to all classified posts that don't have them"""
        logger.info("📊 Adding power scores to classified posts...")
        
        async with crm_session() as db:
            # Get classified posts without power scores
            result = await db.execute(text("""
                SELECT id, likes, comments, shares, engagement_score, content_analysis
                FROM crm.competitor_posts
                WHERE content_analysis IS NOT NULL 
                AND NOT (content_analysis::jsonb ? 'power_score')
                ORDER BY engagement_score DESC NULLS LAST
            """))
            
            posts = result.fetchall()
            logger.info(f"Found {len(posts)} classified posts needing power scores")
            
            batch_size = 50
            for i in range(0, len(posts), batch_size):
                batch = posts[i:i + batch_size]
                logger.info(f"Processing power score batch {i//batch_size + 1}/{(len(posts) + batch_size - 1)//batch_size}")
                
                await self._process_power_score_batch(db, batch)
                await asyncio.sleep(0.1)  # Brief pause between batches

    async def _process_power_score_batch(self, db, posts_batch):
        """Process a batch of posts for power score calculation"""
        for post in posts_batch:
            try:
                post_id, likes, comments, shares, engagement_score, content_analysis = post
                
                if not content_analysis:
                    continue
                    
                # Parse content analysis
                if isinstance(content_analysis, str):
                    content_analysis = json.loads(content_analysis)
                
                # Mock intent scores for power calculation (using existing logic)
                intent_scores = mock_intent_classifier(content_analysis)
                
                # Calculate power score using simplified version of CDR logic
                power_score = self._calculate_power_score(
                    likes or 0, 
                    comments or 0, 
                    shares or 0,
                    engagement_score or 0,
                    intent_scores,
                    content_analysis
                )
                
                # Update content_analysis with power_score
                content_analysis['power_score'] = power_score
                
                # Save back to database
                await db.execute(text("""
                    UPDATE crm.competitor_posts 
                    SET content_analysis = :content_analysis
                    WHERE id = :post_id
                """), {
                    'post_id': post_id,
                    'content_analysis': json.dumps(content_analysis)
                })
                
                self.stats['power_scores_added'] += 1
                
                if power_score > 2000:
                    logger.info(f"  🔥 Post {post_id}: Power Score {power_score:.0f} (CDR candidate)")
                
            except Exception as e:
                logger.error(f"❌ Power score calculation failed for post {post[0]}: {e}")
                self.stats['errors'] += 1
        
        await db.commit()

    def _calculate_power_score(
        self, 
        likes: int, 
        comments: int, 
        shares: int,
        engagement_score: float, 
        intent_scores: Dict[str, float],
        content_analysis: Dict
    ) -> float:
        """Simplified power score calculation"""
        base_engagement = max(engagement_score, 1.0)
        
        # Intent amplification factor (1.0 - 2.5x)
        max_intent_score = max(intent_scores.values()) if intent_scores else 0
        intent_multiplier = 1.0 + (max_intent_score * 1.5)
        
        # Viral indicators boost
        viral_boost = 1.0
        if shares > 100:
            viral_boost += 0.3
        if comments > likes * 0.1:  # High comment ratio
            viral_boost += 0.2
        if likes > 10000:
            viral_boost += 0.2
            
        # Hook quality boost
        hook_data = content_analysis.get('hook', {})
        if isinstance(hook_data, dict):
            hook_strength = hook_data.get('strength', 0)
        else:
            hook_strength = 0
        hook_boost = 1.0 + (hook_strength * 0.3)
        
        power_score = base_engagement * intent_multiplier * viral_boost * hook_boost
        
        return round(power_score, 1)

    async def generate_cdrs_for_high_power_posts(self):
        """Generate CDRs for all classified posts with Power Score > 2000"""
        logger.info("🎯 Generating CDRs for high-power classified posts...")
        
        async with crm_session() as db:
            # Get classified posts with power_score > 2000 that don't have CDRs
            result = await db.execute(text("""
                SELECT id
                FROM crm.competitor_posts
                WHERE content_analysis IS NOT NULL 
                AND (content_analysis::jsonb->>'power_score')::float > 2000
                AND NOT (content_analysis::jsonb ? 'cdr')
                ORDER BY (content_analysis::jsonb->>'power_score')::float DESC
            """))
            
            high_power_posts = [row[0] for row in result.fetchall()]
            logger.info(f"Found {len(high_power_posts)} high-power posts needing CDRs")
            
            for i, post_id in enumerate(high_power_posts):
                logger.info(f"Generating CDR {i+1}/{len(high_power_posts)} for post {post_id}")
                
                try:
                    await self._generate_single_cdr(db, post_id)
                    await asyncio.sleep(0.5)  # Pause between CDR generations
                    
                except Exception as e:
                    logger.error(f"❌ CDR generation failed for post {post_id}: {e}")
                    self.stats['errors'] += 1

    async def _generate_single_cdr(self, db, post_id: int):
        """Generate CDR for a single post"""
        # Get post data
        post_data = await get_post_data(db, post_id)
        if not post_data:
            logger.warning(f"Could not retrieve post data for {post_id}")
            return
            
        # Get intent scores
        intent_scores = mock_intent_classifier(post_data.content_analysis)
        
        # Generate CDR
        cdr = await self.cdr_service.generate_cdr(post_data, intent_scores)
        
        if not cdr:
            logger.warning(f"CDR generation returned None for post {post_id}")
            return
        
        # Store CDR in content_analysis
        content_analysis = post_data.content_analysis.copy()
        content_analysis['cdr'] = cdr.model_dump()
        
        await db.execute(text("""
            UPDATE crm.competitor_posts 
            SET content_analysis = :content_analysis
            WHERE id = :post_id
        """), {
            'post_id': post_id,
            'content_analysis': json.dumps(content_analysis)
        })
        
        await db.commit()
        self.stats['cdrs_generated'] += 1
        
        logger.info(f"  ✅ CDR generated for post {post_id}: Power={cdr.power_score:.0f}, Intent={cdr.dominant_intent}")

    async def classify_remaining_posts(self):
        """Classify all remaining unclassified posts"""
        logger.info("🔍 Classifying remaining unclassified posts...")
        
        async with crm_session() as db:
            # Get unclassified posts with comments data
            result = await db.execute(text("""
                SELECT 
                    id, competitor_id, post_text, likes, comments, shares,
                    engagement_score, hook, comments_data, shortcode
                FROM crm.competitor_posts
                WHERE content_analysis IS NULL 
                AND comments_data IS NOT NULL
                ORDER BY engagement_score DESC NULLS LAST
                LIMIT 100
            """))
            
            unclassified_posts = result.fetchall()
            logger.info(f"Processing {len(unclassified_posts)} unclassified posts")
            
            batch_size = 10  # Smaller batches for classification
            for i in range(0, len(unclassified_posts), batch_size):
                batch = unclassified_posts[i:i + batch_size]
                logger.info(f"Processing classification batch {i//batch_size + 1}/{(len(unclassified_posts) + batch_size - 1)//batch_size}")
                
                await self._process_classification_batch(db, batch)
                await asyncio.sleep(1.0)  # Longer pause for ML processing

    async def _process_classification_batch(self, db, posts_batch):
        """Process a batch of posts for classification"""
        for post in posts_batch:
            try:
                (post_id, competitor_id, post_text, likes, comments_count, 
                 shares, engagement_score, hook, comments_data, shortcode) = post
                
                if not comments_data:
                    continue
                
                # Parse comments data
                if isinstance(comments_data, str):
                    comments_data = json.loads(comments_data)
                
                comments_list = comments_data.get('comments', []) if isinstance(comments_data, dict) else []
                
                if not comments_list:
                    logger.warning(f"Post {post_id} has no comments to analyze")
                    continue
                
                # Run ML comment analysis
                logger.info(f"  Analyzing post {post_id} with {len(comments_list)} comments")
                analysis_result = await analyze_comments_ml(
                    comments_list, 
                    post_caption=post_text or "", 
                    creator_username=""
                )
                
                # Create content analysis structure
                content_analysis = {
                    'hook': {
                        'text': hook or '',
                        'type': 'unknown',
                        'strength': 0.5
                    },
                    'value': {
                        'type': 'entertainment',
                        'score': 0.5
                    },
                    'cta': {
                        'type': 'engagement',
                        'strength': 0.3
                    },
                    'is_clip': False,
                    'full_script': post_text or hook or '',
                    'total_duration': 30,
                    'structure_score': 0.6,
                    'comment_analysis': analysis_result
                }
                
                # Calculate power score
                intent_scores = mock_intent_classifier(content_analysis)
                power_score = self._calculate_power_score(
                    likes or 0,
                    comments_count or 0, 
                    shares or 0,
                    engagement_score or 0,
                    intent_scores,
                    content_analysis
                )
                content_analysis['power_score'] = power_score
                
                # Save classification
                await db.execute(text("""
                    UPDATE crm.competitor_posts 
                    SET 
                        content_analysis = :content_analysis,
                        classified_at = NOW()
                    WHERE id = :post_id
                """), {
                    'post_id': post_id,
                    'content_analysis': json.dumps(content_analysis)
                })
                
                self.stats['posts_classified'] += 1
                
                if power_score > 2000:
                    logger.info(f"  🔥 Newly classified post {post_id}: Power Score {power_score:.0f} (CDR candidate)")
                else:
                    logger.info(f"  ✅ Post {post_id} classified: Power Score {power_score:.0f}")
                    
            except Exception as e:
                logger.error(f"❌ Classification failed for post {post[0]}: {e}")
                self.stats['errors'] += 1
        
        await db.commit()

    async def generate_cdrs_for_new_high_power_posts(self):
        """Generate CDRs for newly classified high-power posts"""
        logger.info("🎯 Generating CDRs for newly classified high-power posts...")
        
        async with crm_session() as db:
            # Get newly classified posts with power_score > 2000
            result = await db.execute(text("""
                SELECT id
                FROM crm.competitor_posts
                WHERE content_analysis IS NOT NULL 
                AND (content_analysis::jsonb->>'power_score')::float > 2000
                AND NOT (content_analysis::jsonb ? 'cdr')
                AND classified_at > NOW() - INTERVAL '1 hour'
                ORDER BY (content_analysis::jsonb->>'power_score')::float DESC
            """))
            
            new_high_power_posts = [row[0] for row in result.fetchall()]
            logger.info(f"Found {len(new_high_power_posts)} newly classified high-power posts")
            
            for post_id in new_high_power_posts:
                try:
                    await self._generate_single_cdr(db, post_id)
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    logger.error(f"❌ CDR generation failed for newly classified post {post_id}: {e}")
                    self.stats['errors'] += 1

    async def generate_final_report(self):
        """Generate comprehensive final report"""
        logger.info("📋 Generating final report...")
        
        async with crm_session() as db:
            # Get current stats
            stats = await db.execute(text("""
                SELECT 
                    COUNT(*) as total_posts,
                    COUNT(CASE WHEN content_analysis IS NOT NULL THEN 1 END) as classified_posts,
                    COUNT(CASE WHEN content_analysis IS NULL THEN 1 END) as unclassified_posts,
                    COUNT(CASE WHEN content_analysis::jsonb ? 'cdr' THEN 1 END) as posts_with_cdrs,
                    COUNT(CASE WHEN (content_analysis::jsonb->>'power_score')::float > 2000 THEN 1 END) as high_power_posts,
                    COUNT(CASE WHEN content_analysis::jsonb ? 'power_score' THEN 1 END) as posts_with_power_scores
                FROM crm.competitor_posts
            """))
            
            row = stats.fetchone()
            total_posts, classified_posts, unclassified_posts, posts_with_cdrs, high_power_posts, posts_with_power_scores = row
            
            # Power score distribution
            power_distribution = await db.execute(text("""
                SELECT 
                    CASE 
                        WHEN (content_analysis::jsonb->>'power_score')::float > 5000 THEN '> 5000'
                        WHEN (content_analysis::jsonb->>'power_score')::float > 3000 THEN '3000-5000'
                        WHEN (content_analysis::jsonb->>'power_score')::float > 2000 THEN '2000-3000' 
                        WHEN (content_analysis::jsonb->>'power_score')::float > 1000 THEN '1000-2000'
                        WHEN (content_analysis::jsonb->>'power_score')::float > 500 THEN '500-1000'
                        ELSE '< 500'
                    END as power_range,
                    COUNT(*) as count
                FROM crm.competitor_posts 
                WHERE content_analysis IS NOT NULL 
                AND content_analysis::jsonb ? 'power_score'
                GROUP BY power_range
                ORDER BY 
                    CASE power_range
                        WHEN '> 5000' THEN 1
                        WHEN '3000-5000' THEN 2
                        WHEN '2000-3000' THEN 3  
                        WHEN '1000-2000' THEN 4
                        WHEN '500-1000' THEN 5
                        ELSE 6
                    END
            """))
            
            print("\n" + "="*80)
            print("🎯 WAVE 3 BULK PROCESSING - FINAL REPORT")
            print("="*80)
            
            print(f"\n📊 OVERALL STATISTICS:")
            print(f"  Total posts: {total_posts:,}")
            print(f"  Classified posts: {classified_posts:,}")
            print(f"  Unclassified posts: {unclassified_posts:,}")
            print(f"  Posts with Power Scores: {posts_with_power_scores:,}")
            print(f"  High-power posts (>2000): {high_power_posts:,}")
            print(f"  Posts with CDRs: {posts_with_cdrs:,}")
            
            print(f"\n⚡ PROCESSING STATISTICS:")
            print(f"  Power scores added: {self.stats['power_scores_added']:,}")
            print(f"  CDRs generated: {self.stats['cdrs_generated']:,}")
            print(f"  Posts classified: {self.stats['posts_classified']:,}")
            print(f"  Errors encountered: {self.stats['errors']:,}")
            
            print(f"\n📈 POWER SCORE DISTRIBUTION:")
            for row in power_distribution.fetchall():
                power_range, count = row
                print(f"  {power_range:>10}: {count:,} posts")
            
            # Show top CDR posts
            top_cdrs = await db.execute(text("""
                SELECT 
                    cp.id,
                    cp.shortcode,
                    c.handle,
                    (cp.content_analysis::jsonb->>'power_score')::float as power_score,
                    cp.content_analysis::jsonb->'cdr'->>'dominant_intent' as dominant_intent,
                    cp.likes,
                    cp.comments
                FROM crm.competitor_posts cp
                LEFT JOIN crm.competitors c ON cp.competitor_id = c.id
                WHERE cp.content_analysis::jsonb ? 'cdr'
                ORDER BY (cp.content_analysis::jsonb->>'power_score')::float DESC
                LIMIT 10
            """))
            
            print(f"\n🏆 TOP 10 CDR POSTS:")
            for row in top_cdrs.fetchall():
                post_id, shortcode, handle, power_score, dominant_intent, likes, comments = row
                print(f"  Post {post_id} (@{handle or 'unknown'}): Power={power_score:.0f}, Intent={dominant_intent or 'unknown'}")
                print(f"    {likes:,} likes, {comments:,} comments, Code: {shortcode or 'none'}")
            
            print("\n" + "="*80)
            print("✅ Wave 3 processing completed successfully!")
            print("="*80 + "\n")


async def main():
    """Main execution function"""
    processor = Wave3BulkProcessor()
    await processor.run_complete_processing()

if __name__ == "__main__":
    asyncio.run(main())