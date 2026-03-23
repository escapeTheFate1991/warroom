"""
Thumbnail URL refresh API for handling expired S3 URLs
"""
from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from typing import List, Dict
import logging

from app.db.crm_db import crm_session
from app.services.garage_s3 import extract_s3_key_from_url, generate_signed_url

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/refresh-thumbnails")
async def refresh_thumbnails(post_ids: List[int] = None):
    """Refresh thumbnail URLs by generating fresh signed URLs for S3 stored thumbnails.
    
    Args:
        post_ids: List of post IDs to refresh (optional, defaults to all S3 thumbnails)
        
    Returns:
        Dict with refresh results
    """
    async with crm_session() as db:
        try:
            # Build query to get S3 thumbnail URLs
            if post_ids:
                # Refresh specific posts
                placeholders = ','.join([f':post_id_{i}' for i in range(len(post_ids))])
                query = f"""
                    SELECT cp.id, cp.thumbnail_url, cp.media_url
                    FROM crm.competitor_posts cp
                    WHERE cp.id IN ({placeholders})
                      AND (cp.thumbnail_url LIKE '%10.0.0.11:3900%' 
                           OR cp.media_url LIKE '%10.0.0.11:3900%')
                """
                params = {f'post_id_{i}': post_id for i, post_id in enumerate(post_ids)}
            else:
                # Refresh all S3 thumbnails
                query = """
                    SELECT cp.id, cp.thumbnail_url, cp.media_url
                    FROM crm.competitor_posts cp
                    WHERE cp.thumbnail_url LIKE '%10.0.0.11:3900%' 
                       OR cp.media_url LIKE '%10.0.0.11:3900%'
                    LIMIT 100
                """
                params = {}
            
            result = await db.execute(text(query), params)
            posts = result.mappings().all()
            
            if not posts:
                return {
                    "status": "success",
                    "message": "No S3 thumbnails found to refresh",
                    "refreshed": 0
                }
            
            refreshed_count = 0
            errors = []
            
            for post in posts:
                post_id = post['id']
                thumbnail_url = post['thumbnail_url']
                media_url = post['media_url']
                
                updates = {}
                
                # Refresh thumbnail URL if it's S3
                if thumbnail_url and '10.0.0.11:3900' in thumbnail_url:
                    s3_key = extract_s3_key_from_url(thumbnail_url)
                    if s3_key:
                        try:
                            new_thumbnail_url = generate_signed_url(s3_key, expiration=86400)  # 24 hours
                            if new_thumbnail_url:
                                updates['thumbnail_url'] = new_thumbnail_url
                        except Exception as e:
                            errors.append(f"Post {post_id} thumbnail: {str(e)}")
                
                # Refresh media URL if it's S3
                if media_url and '10.0.0.11:3900' in media_url:
                    s3_key = extract_s3_key_from_url(media_url)
                    if s3_key:
                        try:
                            new_media_url = generate_signed_url(s3_key, expiration=86400)  # 24 hours
                            if new_media_url:
                                updates['media_url'] = new_media_url
                        except Exception as e:
                            errors.append(f"Post {post_id} media: {str(e)}")
                
                # Update database if we have new URLs
                if updates:
                    try:
                        update_parts = []
                        update_params = {'post_id': post_id}
                        
                        if 'thumbnail_url' in updates:
                            update_parts.append("thumbnail_url = :thumbnail_url")
                            update_params['thumbnail_url'] = updates['thumbnail_url']
                        
                        if 'media_url' in updates:
                            update_parts.append("media_url = :media_url")
                            update_params['media_url'] = updates['media_url']
                        
                        if update_parts:
                            update_query = f"""
                                UPDATE crm.competitor_posts 
                                SET {', '.join(update_parts)}
                                WHERE id = :post_id
                            """
                            await db.execute(text(update_query), update_params)
                            refreshed_count += 1
                            
                    except Exception as e:
                        errors.append(f"Post {post_id} update: {str(e)}")
            
            # Commit all updates
            await db.commit()
            
            logger.info(f"Refreshed {refreshed_count} thumbnail URLs")
            
            return {
                "status": "success",
                "message": f"Refreshed {refreshed_count} thumbnail URLs",
                "refreshed": refreshed_count,
                "total_posts": len(posts),
                "errors": errors[:5] if errors else []  # Return max 5 errors
            }
            
        except Exception as e:
            logger.error(f"Error refreshing thumbnails: {e}")
            await db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to refresh thumbnails: {str(e)}")


@router.get("/thumbnail-stats")
async def thumbnail_stats():
    """Get thumbnail URL statistics."""
    async with crm_session() as db:
        try:
            result = await db.execute(text("""
                SELECT 
                    COUNT(*) as total_posts,
                    COUNT(CASE WHEN thumbnail_url LIKE '%10.0.0.11:3900%' THEN 1 END) as s3_thumbnails,
                    COUNT(CASE WHEN thumbnail_url LIKE '%cdninstagram%' THEN 1 END) as cdn_thumbnails,
                    COUNT(CASE WHEN media_url LIKE '%10.0.0.11:3900%' THEN 1 END) as s3_media,
                    COUNT(CASE WHEN media_url LIKE '%cdninstagram%' THEN 1 END) as cdn_media
                FROM crm.competitor_posts cp
                JOIN crm.competitors c ON cp.competitor_id = c.id
            """))
            
            stats = result.mappings().first()
            
            return {
                "total_posts": stats['total_posts'],
                "thumbnails": {
                    "s3": stats['s3_thumbnails'],
                    "cdn": stats['cdn_thumbnails'],
                    "migration_rate": round((stats['s3_thumbnails'] / stats['total_posts']) * 100, 1) if stats['total_posts'] > 0 else 0
                },
                "media": {
                    "s3": stats['s3_media'], 
                    "cdn": stats['cdn_media'],
                    "migration_rate": round((stats['s3_media'] / stats['total_posts']) * 100, 1) if stats['total_posts'] > 0 else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting thumbnail stats: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")