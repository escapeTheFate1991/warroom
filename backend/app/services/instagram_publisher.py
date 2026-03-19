"""Instagram Publisher Service

Implements Instagram Graph API carousel posting functionality.
Handles image container creation, carousel assembly, and publishing.
"""

import logging
import httpx
from typing import List, Dict, Any, Optional
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

INSTAGRAM_API_BASE = "https://graph.facebook.com/v18.0"


class InstagramPublisher:
    """Handles Instagram Graph API carousel posting."""
    
    async def get_instagram_credentials(self, org_id: int, db: AsyncSession) -> Dict[str, str]:
        """Get Instagram credentials for the organization."""
        # Query social oauth tokens for Instagram
        query = text("""
            SELECT access_token, account_id, account_username 
            FROM crm.social_oauth_tokens 
            WHERE org_id = :org_id 
            AND platform = 'instagram' 
            AND status = 'active'
            ORDER BY updated_at DESC
            LIMIT 1
        """)
        
        result = await db.execute(query, {"org_id": org_id})
        row = result.first()
        
        if not row:
            raise ValueError("No active Instagram account connected for this organization")
        
        return {
            "access_token": row.access_token,
            "ig_user_id": row.account_id,
            "username": row.account_username
        }
    
    async def create_image_container(
        self, 
        ig_user_id: str, 
        image_url: str, 
        access_token: str
    ) -> str:
        """Create single image container via Graph API.
        
        Args:
            ig_user_id: Instagram user ID
            image_url: URL to the image (must be publicly accessible)
            access_token: Instagram access token
            
        Returns:
            Container ID for the created image
        """
        url = f"{INSTAGRAM_API_BASE}/{ig_user_id}/media"
        
        params = {
            "image_url": image_url,
            "access_token": access_token
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, params=params, timeout=30.0)
            
            if response.status_code != 200:
                error_data = response.json() if response.content else {}
                error_msg = error_data.get("error", {}).get("message", f"HTTP {response.status_code}")
                raise Exception(f"Failed to create image container: {error_msg}")
            
            data = response.json()
            return data["id"]
    
    async def create_carousel_container(
        self, 
        ig_user_id: str, 
        children_ids: List[str], 
        caption: str, 
        access_token: str
    ) -> str:
        """Create carousel container referencing image containers.
        
        Args:
            ig_user_id: Instagram user ID
            children_ids: List of image container IDs
            caption: Post caption text
            access_token: Instagram access token
            
        Returns:
            Container ID for the created carousel
        """
        url = f"{INSTAGRAM_API_BASE}/{ig_user_id}/media"
        
        params = {
            "media_type": "CAROUSEL",
            "children": ",".join(children_ids),
            "caption": caption,
            "access_token": access_token
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, params=params, timeout=30.0)
            
            if response.status_code != 200:
                error_data = response.json() if response.content else {}
                error_msg = error_data.get("error", {}).get("message", f"HTTP {response.status_code}")
                raise Exception(f"Failed to create carousel container: {error_msg}")
            
            data = response.json()
            return data["id"]
    
    async def publish_container(
        self, 
        ig_user_id: str, 
        container_id: str, 
        access_token: str
    ) -> str:
        """Publish the container to Instagram.
        
        Args:
            ig_user_id: Instagram user ID
            container_id: Container ID to publish
            access_token: Instagram access token
            
        Returns:
            Published media ID
        """
        url = f"{INSTAGRAM_API_BASE}/{ig_user_id}/media_publish"
        
        params = {
            "creation_id": container_id,
            "access_token": access_token
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, params=params, timeout=30.0)
            
            if response.status_code != 200:
                error_data = response.json() if response.content else {}
                error_msg = error_data.get("error", {}).get("message", f"HTTP {response.status_code}")
                raise Exception(f"Failed to publish container: {error_msg}")
            
            data = response.json()
            return data["id"]
    
    async def get_published_post_url(
        self, 
        media_id: str, 
        access_token: str
    ) -> Optional[str]:
        """Get the permalink URL for a published post.
        
        Args:
            media_id: Published media ID
            access_token: Instagram access token
            
        Returns:
            Permalink URL or None if not available
        """
        url = f"{INSTAGRAM_API_BASE}/{media_id}"
        
        params = {
            "fields": "permalink",
            "access_token": access_token
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=30.0)
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get("permalink")
        except Exception as e:
            logger.error(f"Failed to get post URL for media {media_id}: {e}")
        
        return None
    
    async def post_carousel(
        self, 
        org_id: int, 
        slides: List[Dict[str, Any]], 
        caption: str, 
        db: AsyncSession,
        base_url: str = "https://your-domain.com"  # TODO: Replace with actual domain
    ) -> Dict[str, Any]:
        """Full flow: create image containers → carousel container → publish.
        
        Args:
            org_id: Organization ID
            slides: List of slide dicts with image_url field
            caption: Post caption
            db: Database session
            base_url: Base URL for converting relative paths to absolute URLs
            
        Returns:
            Dict with post details: {"media_id": str, "permalink": str, "container_ids": [...]}
        """
        try:
            # Get Instagram credentials
            credentials = await self.get_instagram_credentials(org_id, db)
            ig_user_id = credentials["ig_user_id"]
            access_token = credentials["access_token"]
            
            # Validate slides have images
            slides_with_images = [s for s in slides if s.get("image_url")]
            if len(slides_with_images) < 2:
                raise ValueError("At least 2 slides with images are required for a carousel")
            
            if len(slides_with_images) > 10:
                raise ValueError("Maximum 10 slides allowed for Instagram carousel")
            
            # Convert relative URLs to absolute URLs
            image_urls = []
            for slide in slides_with_images:
                image_url = slide["image_url"]
                if image_url.startswith("/"):
                    # Convert relative path to absolute URL
                    image_url = base_url.rstrip("/") + image_url
                image_urls.append(image_url)
            
            # Create image containers
            logger.info(f"Creating {len(image_urls)} image containers for carousel")
            container_ids = []
            
            for i, image_url in enumerate(image_urls):
                try:
                    container_id = await self.create_image_container(
                        ig_user_id, image_url, access_token
                    )
                    container_ids.append(container_id)
                    logger.info(f"Created image container {i+1}/{len(image_urls)}: {container_id}")
                    
                except Exception as e:
                    logger.error(f"Failed to create container for image {i+1}: {e}")
                    raise Exception(f"Failed to create image container {i+1}: {str(e)}")
            
            # Create carousel container
            logger.info("Creating carousel container")
            carousel_container_id = await self.create_carousel_container(
                ig_user_id, container_ids, caption, access_token
            )
            logger.info(f"Created carousel container: {carousel_container_id}")
            
            # Publish carousel
            logger.info("Publishing carousel")
            media_id = await self.publish_container(
                ig_user_id, carousel_container_id, access_token
            )
            logger.info(f"Published carousel media: {media_id}")
            
            # Get permalink
            permalink = await self.get_published_post_url(media_id, access_token)
            
            return {
                "media_id": media_id,
                "permalink": permalink,
                "container_ids": container_ids,
                "carousel_container_id": carousel_container_id,
                "slides_count": len(slides_with_images)
            }
            
        except Exception as e:
            logger.error(f"Carousel posting failed for org {org_id}: {e}")
            raise
    
    async def get_post_insights(
        self, 
        media_id: str, 
        access_token: str
    ) -> Dict[str, Any]:
        """Get insights/metrics for a published post.
        
        Args:
            media_id: Published media ID
            access_token: Instagram access token
            
        Returns:
            Dict with post metrics
        """
        url = f"{INSTAGRAM_API_BASE}/{media_id}/insights"
        
        params = {
            "metric": "impressions,reach,engagement,saves,shares",
            "access_token": access_token
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=30.0)
                
                if response.status_code == 200:
                    data = response.json()
                    metrics = {}
                    
                    for metric_data in data.get("data", []):
                        metric_name = metric_data.get("name")
                        metric_values = metric_data.get("values", [])
                        
                        if metric_values:
                            metrics[metric_name] = metric_values[0].get("value", 0)
                    
                    return metrics
                else:
                    logger.error(f"Failed to get insights for media {media_id}: {response.text}")
                    return {}
                    
        except Exception as e:
            logger.error(f"Failed to get insights for media {media_id}: {e}")
            return {}
    
    async def validate_image_url(self, image_url: str) -> bool:
        """Validate that an image URL is accessible by Instagram.
        
        Args:
            image_url: URL to validate
            
        Returns:
            True if URL is accessible, False otherwise
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.head(image_url, timeout=10.0)
                
                # Check if URL returns 200 and is an image
                if response.status_code == 200:
                    content_type = response.headers.get("content-type", "").lower()
                    return content_type.startswith("image/")
                
                return False
                
        except Exception as e:
            logger.error(f"Failed to validate image URL {image_url}: {e}")
            return False