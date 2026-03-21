"""Instagram CDN → Garage S3 Migration Job

Downloads expired Instagram CDN URLs and stores them permanently in Garage S3.
Updates database records to point to the permanent S3 URLs.
"""

import os
import asyncio
import logging
import httpx
import hashlib
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urlparse, unquote
import mimetypes

import boto3
import asyncpg
from botocore.exceptions import ClientError, NoCredentialsError

logger = logging.getLogger(__name__)

# Global state for tracking job progress
_migration_state = {
    "status": "idle",  # idle, running, complete, error
    "progress": 0,
    "total": 0,
    "success_count": 0,
    "error_count": 0,
    "started_at": None,
    "completed_at": None,
    "errors": [],
    "last_error": None
}

# Garage S3 configuration (from Qdrant memory)
GARAGE_CONFIG = {
    "endpoint_url": "http://10.0.0.11:3900",
    "access_key_id": "GK891b44277c4af3277a8a3e93", 
    "secret_access_key": "d2c208430df9781a66562617379fa2d8470fb1aebcd011096475fa0a3b47c8b9",
    "region_name": "ai-local",
    "bucket": "media"
}

DATABASE_URL = "postgresql://friday:friday-brain2-2026@10.0.0.11:5433/knowledge"


def _create_s3_client():
    """Create S3 client for Garage."""
    try:
        return boto3.client(
            's3',
            endpoint_url=GARAGE_CONFIG["endpoint_url"],
            aws_access_key_id=GARAGE_CONFIG["access_key_id"],
            aws_secret_access_key=GARAGE_CONFIG["secret_access_key"],
            region_name=GARAGE_CONFIG["region_name"],
        )
    except Exception as e:
        logger.error(f"Failed to create S3 client: {e}")
        raise


def _get_file_extension(url: str, content_type: str = None) -> str:
    """Extract file extension from URL or content type."""
    # Try to get extension from URL
    parsed = urlparse(url)
    path = unquote(parsed.path)
    
    # Instagram URLs often have .jpg or .mp4 in the path
    if '.jpg' in path:
        return '.jpg'
    elif '.jpeg' in path:
        return '.jpeg'
    elif '.png' in path:
        return '.png'
    elif '.mp4' in path:
        return '.mp4'
    elif '.webm' in path:
        return '.webm'
    
    # Fallback to content type
    if content_type:
        ext = mimetypes.guess_extension(content_type.split(';')[0])
        if ext:
            return ext
    
    # Default fallback
    return '.jpg'


def _generate_s3_key(competitor_handle: str, post_id: int, timestamp: str, url_type: str, extension: str) -> str:
    """Generate S3 key following the specified format.
    
    Format: instagram/{competitor_name}/{post_id}_{timestamp}_{thumb|media}.{ext}
    """
    return f"instagram/{competitor_handle}/{post_id}_{timestamp}_{url_type}{extension}"


def _generate_s3_url(s3_key: str) -> str:
    """Generate public S3 URL."""
    return f"{GARAGE_CONFIG['endpoint_url']}/{GARAGE_CONFIG['bucket']}/{s3_key}"


async def _download_url(url: str, timeout: int = 30) -> Tuple[bytes, str]:
    """Download content from URL and return bytes + content type."""
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.get(url, follow_redirects=True)
            response.raise_for_status()
            content_type = response.headers.get('content-type', '')
            return response.content, content_type
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                raise ValueError(f"URL expired (403): {url}")
            elif e.response.status_code == 404:
                raise ValueError(f"URL not found (404): {url}")
            else:
                raise ValueError(f"HTTP {e.response.status_code}: {url}")
        except Exception as e:
            raise ValueError(f"Download failed: {str(e)}")


async def _upload_to_s3(s3_client, content: bytes, s3_key: str, content_type: str) -> bool:
    """Upload content to S3. Returns True on success."""
    try:
        # Run the synchronous S3 operation in a thread pool
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: s3_client.put_object(
                Bucket=GARAGE_CONFIG["bucket"],
                Key=s3_key,
                Body=content,
                ContentType=content_type
            )
        )
        return True
    except ClientError as e:
        logger.error(f"S3 upload failed for {s3_key}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected S3 error for {s3_key}: {e}")
        return False


async def _update_post_urls(conn: asyncpg.Connection, post_id: int, thumbnail_s3_url: str = None, media_s3_url: str = None):
    """Update post URLs in database."""
    updates = []
    params = {"post_id": post_id}
    
    if thumbnail_s3_url:
        updates.append("thumbnail_url = $2")
        params["thumbnail_s3_url"] = thumbnail_s3_url
    
    if media_s3_url:
        if thumbnail_s3_url:
            updates.append("media_url = $3")
            params["media_s3_url"] = media_s3_url
        else:
            updates.append("media_url = $2")
            params["media_s3_url"] = media_s3_url
    
    if not updates:
        return
        
    query = f"UPDATE crm.competitor_posts SET {', '.join(updates)} WHERE id = $1"
    values = [post_id]
    
    if thumbnail_s3_url:
        values.append(thumbnail_s3_url)
    if media_s3_url:
        values.append(media_s3_url)
        
    await conn.execute(query, *values)


async def _process_single_post(s3_client, conn: asyncpg.Connection, post: Dict) -> Dict[str, Any]:
    """Process a single post's URLs. Returns result summary."""
    post_id = post["id"]
    competitor_handle = post["handle"]
    thumbnail_url = post["thumbnail_url"]
    media_url = post["media_url"]
    
    result = {
        "post_id": post_id,
        "thumbnail_success": False,
        "media_success": False,
        "thumbnail_s3_url": None,
        "media_s3_url": None,
        "errors": []
    }
    
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    
    # Process thumbnail URL
    if thumbnail_url and "cdninstagram" in thumbnail_url:
        try:
            content, content_type = await _download_url(thumbnail_url)
            extension = _get_file_extension(thumbnail_url, content_type)
            s3_key = _generate_s3_key(competitor_handle, post_id, timestamp, "thumb", extension)
            
            if await _upload_to_s3(s3_client, content, s3_key, content_type):
                result["thumbnail_s3_url"] = _generate_s3_url(s3_key)
                result["thumbnail_success"] = True
                logger.info(f"✓ Thumbnail migrated: {post_id} → {s3_key}")
            else:
                result["errors"].append(f"S3 upload failed for thumbnail")
                
        except Exception as e:
            result["errors"].append(f"Thumbnail download failed: {str(e)}")
            logger.warning(f"Thumbnail failed for post {post_id}: {e}")
    
    # Process media URL
    if media_url and "cdninstagram" in media_url:
        try:
            content, content_type = await _download_url(media_url)
            extension = _get_file_extension(media_url, content_type)
            s3_key = _generate_s3_key(competitor_handle, post_id, timestamp, "media", extension)
            
            if await _upload_to_s3(s3_client, content, s3_key, content_type):
                result["media_s3_url"] = _generate_s3_url(s3_key)
                result["media_success"] = True
                logger.info(f"✓ Media migrated: {post_id} → {s3_key}")
            else:
                result["errors"].append(f"S3 upload failed for media")
                
        except Exception as e:
            result["errors"].append(f"Media download failed: {str(e)}")
            logger.warning(f"Media failed for post {post_id}: {e}")
    
    # Update database if any URLs were migrated
    if result["thumbnail_s3_url"] or result["media_s3_url"]:
        try:
            await _update_post_urls(conn, post_id, result["thumbnail_s3_url"], result["media_s3_url"])
            logger.info(f"✓ Database updated for post {post_id}")
        except Exception as e:
            result["errors"].append(f"Database update failed: {str(e)}")
            logger.error(f"Database update failed for post {post_id}: {e}")
    
    return result


async def _migrate_batch(posts_batch: List[Dict]) -> Dict[str, Any]:
    """Process a batch of posts."""
    batch_result = {
        "processed": 0,
        "success": 0,
        "errors": 0,
        "post_results": []
    }
    
    if not posts_batch:
        return batch_result
        
    s3_client = _create_s3_client()
    
    # Connect to database
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        for post in posts_batch:
            try:
                result = await _process_single_post(s3_client, conn, post)
                batch_result["post_results"].append(result)
                batch_result["processed"] += 1
                
                if result["thumbnail_success"] or result["media_success"]:
                    batch_result["success"] += 1
                
                if result["errors"]:
                    batch_result["errors"] += 1
                    
            except Exception as e:
                logger.error(f"Failed to process post {post.get('id', 'unknown')}: {e}")
                batch_result["errors"] += 1
                batch_result["post_results"].append({
                    "post_id": post.get("id"),
                    "thumbnail_success": False,
                    "media_success": False,
                    "errors": [str(e)]
                })
                
            # Small delay between posts to be nice to Instagram/S3
            await asyncio.sleep(0.1)
            
    finally:
        await conn.close()
    
    return batch_result


async def migrate_cdn_urls():
    """Main migration function. Processes all CDN URLs in batches."""
    global _migration_state
    
    if _migration_state["status"] == "running":
        raise ValueError("Migration already in progress")
    
    # Reset state
    _migration_state.update({
        "status": "running",
        "progress": 0,
        "total": 0,
        "success_count": 0,
        "error_count": 0,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None,
        "errors": [],
        "last_error": None
    })
    
    logger.info("🚀 Starting CDN migration job")
    
    try:
        # Get all posts with CDN URLs
        conn = await asyncpg.connect(DATABASE_URL)
        
        try:
            posts = await conn.fetch("""
                SELECT 
                    cp.id,
                    cp.thumbnail_url,
                    cp.media_url,
                    c.handle
                FROM crm.competitor_posts cp
                JOIN crm.competitors c ON cp.competitor_id = c.id
                WHERE cp.thumbnail_url LIKE '%cdninstagram%' 
                   OR cp.media_url LIKE '%cdninstagram%'
                ORDER BY cp.id
            """)
            
            posts_list = [dict(post) for post in posts]
            _migration_state["total"] = len(posts_list)
            
            logger.info(f"Found {len(posts_list)} posts with CDN URLs")
            
            if not posts_list:
                _migration_state["status"] = "complete"
                _migration_state["completed_at"] = datetime.now(timezone.utc).isoformat()
                return
            
            # Process in batches of 15
            batch_size = 15
            total_batches = (len(posts_list) + batch_size - 1) // batch_size
            
            for i in range(0, len(posts_list), batch_size):
                batch = posts_list[i:i + batch_size]
                batch_num = (i // batch_size) + 1
                
                logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} posts)")
                
                try:
                    batch_result = await _migrate_batch(batch)
                    
                    _migration_state["success_count"] += batch_result["success"]
                    _migration_state["error_count"] += batch_result["errors"]
                    _migration_state["progress"] = min(i + len(batch), len(posts_list))
                    
                    logger.info(f"Batch {batch_num} complete: {batch_result['success']} success, {batch_result['errors']} errors")
                    
                    # Log any errors from this batch
                    for post_result in batch_result["post_results"]:
                        if post_result["errors"]:
                            for error in post_result["errors"]:
                                _migration_state["errors"].append(f"Post {post_result['post_id']}: {error}")
                    
                    # Delay between batches
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    error_msg = f"Batch {batch_num} failed: {str(e)}"
                    logger.error(error_msg)
                    _migration_state["errors"].append(error_msg)
                    _migration_state["last_error"] = error_msg
                    _migration_state["error_count"] += len(batch)
        
        finally:
            await conn.close()
        
        # Mark complete
        _migration_state["status"] = "complete"
        _migration_state["completed_at"] = datetime.now(timezone.utc).isoformat()
        
        logger.info(f"🎉 Migration complete! Success: {_migration_state['success_count']}, Errors: {_migration_state['error_count']}")
        
    except Exception as e:
        error_msg = f"Migration failed: {str(e)}"
        logger.error(error_msg)
        _migration_state["status"] = "error"
        _migration_state["last_error"] = error_msg
        _migration_state["completed_at"] = datetime.now(timezone.utc).isoformat()
        raise


def get_migration_status() -> Dict[str, Any]:
    """Get current migration status."""
    return dict(_migration_state)


async def test_migration_sample():
    """Test migration with 5 posts only."""
    global _migration_state
    
    if _migration_state["status"] == "running":
        raise ValueError("Migration already in progress")
    
    logger.info("🧪 Testing CDN migration with 5 posts")
    
    # Temporarily modify the query to limit to 5 posts
    original_migrate = migrate_cdn_urls
    
    async def test_migrate():
        # Reset state
        _migration_state.update({
            "status": "running",
            "progress": 0,
            "total": 0,
            "success_count": 0,
            "error_count": 0,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": None,
            "errors": [],
            "last_error": None
        })
        
        try:
            conn = await asyncpg.connect(DATABASE_URL)
            
            try:
                posts = await conn.fetch("""
                    SELECT 
                        cp.id,
                        cp.thumbnail_url,
                        cp.media_url,
                        c.handle
                    FROM crm.competitor_posts cp
                    JOIN crm.competitors c ON cp.competitor_id = c.id
                    WHERE cp.thumbnail_url LIKE '%cdninstagram%' 
                       OR cp.media_url LIKE '%cdninstagram%'
                    ORDER BY cp.id
                    LIMIT 5
                """)
                
                posts_list = [dict(post) for post in posts]
                _migration_state["total"] = len(posts_list)
                
                logger.info(f"Testing with {len(posts_list)} posts")
                
                if posts_list:
                    batch_result = await _migrate_batch(posts_list)
                    
                    _migration_state["success_count"] = batch_result["success"]
                    _migration_state["error_count"] = batch_result["errors"]
                    _migration_state["progress"] = len(posts_list)
                    
                    for post_result in batch_result["post_results"]:
                        if post_result["errors"]:
                            for error in post_result["errors"]:
                                _migration_state["errors"].append(f"Post {post_result['post_id']}: {error}")
                
            finally:
                await conn.close()
            
            _migration_state["status"] = "complete"
            _migration_state["completed_at"] = datetime.now(timezone.utc).isoformat()
            
            logger.info(f"🧪 Test complete! Success: {_migration_state['success_count']}, Errors: {_migration_state['error_count']}")
            
        except Exception as e:
            error_msg = f"Test migration failed: {str(e)}"
            logger.error(error_msg)
            _migration_state["status"] = "error"
            _migration_state["last_error"] = error_msg
            _migration_state["completed_at"] = datetime.now(timezone.utc).isoformat()
            raise
    
    await test_migrate()