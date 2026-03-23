"""
Thumbnail proxy to serve S3 images through the backend
"""
from fastapi import APIRouter, HTTPException, Response
from app.services.garage_s3 import create_s3_client, extract_s3_key_from_url
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/proxy/{path:path}")
async def proxy_thumbnail(path: str):
    """Proxy S3 thumbnails through the backend to avoid CORS issues.
    
    Args:
        path: S3 object key path (e.g., instagram/handle/file.jpg)
        
    Returns:
        Image response
    """
    try:
        s3_client = create_s3_client()
        
        # Get the object from S3
        response = s3_client.get_object(Bucket='media', Key=path)
        content = response['Body'].read()
        content_type = response.get('ContentType', 'image/jpeg')
        
        # Return the image with proper headers
        return Response(
            content=content,
            media_type=content_type,
            headers={
                "Cache-Control": "public, max-age=86400",  # Cache for 24 hours
                "Access-Control-Allow-Origin": "*"
            }
        )
        
    except Exception as e:
        logger.error(f"Error proxying thumbnail {path}: {e}")
        raise HTTPException(status_code=404, detail="Thumbnail not found")


@router.post("/update-urls")
async def update_thumbnail_urls():
    """Update all S3 thumbnail URLs to use the proxy endpoint."""
    from app.db.crm_db import crm_session
    from sqlalchemy import text
    
    async with crm_session() as db:
        try:
            # Get all S3 thumbnail URLs
            result = await db.execute(text("""
                SELECT cp.id, cp.thumbnail_url, cp.media_url
                FROM crm.competitor_posts cp
                WHERE cp.thumbnail_url LIKE '%10.0.0.11:3900/media/%' 
                   OR cp.media_url LIKE '%10.0.0.11:3900/media/%'
            """))
            
            posts = result.mappings().all()
            updated_count = 0
            
            for post in posts:
                post_id = post['id']
                thumbnail_url = post['thumbnail_url']
                media_url = post['media_url']
                
                updates = {}
                
                # Convert S3 URL to proxy URL for thumbnail
                if thumbnail_url and '10.0.0.11:3900/media/' in thumbnail_url:
                    s3_key = extract_s3_key_from_url(thumbnail_url)
                    if s3_key:
                        proxy_url = f"http://localhost:8300/api/thumbnails/proxy/{s3_key}"
                        updates['thumbnail_url'] = proxy_url
                
                # Convert S3 URL to proxy URL for media
                if media_url and '10.0.0.11:3900/media/' in media_url:
                    s3_key = extract_s3_key_from_url(media_url)
                    if s3_key:
                        proxy_url = f"http://localhost:8300/api/thumbnails/proxy/{s3_key}"
                        updates['media_url'] = proxy_url
                
                # Update database if we have new URLs
                if updates:
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
                        updated_count += 1
            
            # Commit all updates
            await db.commit()
            
            logger.info(f"Updated {updated_count} posts to use proxy URLs")
            
            return {
                "status": "success",
                "message": f"Updated {updated_count} posts to use proxy URLs",
                "updated": updated_count,
                "total_posts": len(posts)
            }
            
        except Exception as e:
            logger.error(f"Error updating thumbnail URLs: {e}")
            await db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to update URLs: {str(e)}")