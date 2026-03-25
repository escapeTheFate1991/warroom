"""
Video Record Service

Service for constructing VideoRecord models from competitor_posts data.
Handles data transformation and normalization for the CDR platform.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import json

from app.models.video_record import VideoRecord

logger = logging.getLogger(__name__)


class VideoRecordService:
    """Service for building VideoRecord models from database data"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_video_record(self, post_id: int) -> Optional[VideoRecord]:
        """
        Get a single VideoRecord by post ID
        
        Args:
            post_id: ID of the competitor_posts record
            
        Returns:
            VideoRecord or None if not found
        """
        try:
            result = await self.db.execute(
                text("""
                    SELECT 
                        cp.id,
                        cp.competitor_id,
                        cp.platform,
                        cp.post_text,
                        cp.hook,
                        cp.post_url,
                        cp.posted_at,
                        cp.fetched_at,
                        cp.likes,
                        cp.comments,
                        cp.shares,
                        cp.engagement_score,
                        cp.media_type,
                        cp.transcript,
                        cp.video_analysis,
                        cp.frame_chunks,
                        cp.content_analysis,
                        cp.detected_format,
                        cp.format_confidence,
                        c.handle as competitor_handle
                    FROM crm.competitor_posts cp
                    LEFT JOIN crm.competitors c ON cp.competitor_id = c.id
                    WHERE cp.id = :post_id
                """),
                {"post_id": post_id}
            )
            
            row = result.fetchone()
            if not row:
                return None
            
            # Convert row to dict for processing
            post_data = dict(row._mapping)
            competitor_handle = post_data.pop('competitor_handle', 'unknown')
            
            return VideoRecord.from_competitor_post(post_data, competitor_handle)
            
        except Exception as e:
            logger.error("Failed to get video record %s: %s", post_id, e)
            return None
    
    async def get_video_records(
        self, 
        competitor_id: Optional[int] = None,
        limit: int = 20,
        days: Optional[int] = None,
        platform: Optional[str] = None,
        org_id: Optional[int] = None
    ) -> List[VideoRecord]:
        """
        Get multiple VideoRecords with filtering
        
        Args:
            competitor_id: Optional filter by competitor
            limit: Maximum number of records to return
            days: Optional filter by days back from now
            platform: Optional filter by platform
            org_id: Optional filter by organization (for multi-tenant)
            
        Returns:
            List of VideoRecord objects
        """
        try:
            # Build query with optional filters
            query_parts = ["""
                SELECT 
                    cp.id,
                    cp.competitor_id,
                    cp.platform,
                    cp.post_text,
                    cp.hook,
                    cp.post_url,
                    cp.posted_at,
                    cp.fetched_at,
                    cp.likes,
                    cp.comments,
                    cp.shares,
                    cp.engagement_score,
                    cp.media_type,
                    cp.transcript,
                    cp.video_analysis,
                    cp.frame_chunks,
                    cp.content_analysis,
                    cp.detected_format,
                    cp.format_confidence,
                    c.handle as competitor_handle
                FROM crm.competitor_posts cp
                LEFT JOIN crm.competitors c ON cp.competitor_id = c.id
                WHERE 1=1
            """]
            
            params = {}
            
            # Add filters
            if competitor_id:
                query_parts.append("AND cp.competitor_id = :competitor_id")
                params["competitor_id"] = competitor_id
            
            if days:
                query_parts.append("AND cp.posted_at >= :cutoff_date")
                cutoff = datetime.now() - timedelta(days=days)
                params["cutoff_date"] = cutoff
            
            if platform:
                query_parts.append("AND cp.platform = :platform")
                params["platform"] = platform.lower()
            
            if org_id:
                query_parts.append("AND c.org_id = :org_id")
                params["org_id"] = org_id
            
            # Order by engagement and recency
            query_parts.append("""
                ORDER BY 
                    COALESCE(cp.engagement_score, 0) DESC,
                    cp.posted_at DESC
                LIMIT :limit
            """)
            params["limit"] = limit
            
            query = "\n".join(query_parts)
            
            result = await self.db.execute(text(query), params)
            rows = result.fetchall()
            
            video_records = []
            for row in rows:
                try:
                    post_data = dict(row._mapping)
                    competitor_handle = post_data.pop('competitor_handle', 'unknown')
                    
                    video_record = VideoRecord.from_competitor_post(post_data, competitor_handle)
                    video_records.append(video_record)
                    
                except Exception as e:
                    logger.warning("Failed to process post %s: %s", row.id, e)
                    continue
            
            return video_records
            
        except Exception as e:
            logger.error("Failed to get video records: %s", e)
            return []
    
    async def get_video_records_for_competitor(
        self,
        competitor_id: int,
        limit: int = 10
    ) -> List[VideoRecord]:
        """
        Get video records for a specific competitor
        
        Args:
            competitor_id: Competitor ID
            limit: Maximum records to return
            
        Returns:
            List of VideoRecord objects
        """
        return await self.get_video_records(
            competitor_id=competitor_id,
            limit=limit
        )
    
    async def get_recent_video_records(
        self,
        days: int = 30,
        limit: int = 50
    ) -> List[VideoRecord]:
        """
        Get recent video records across all competitors
        
        Args:
            days: How many days back to look
            limit: Maximum records to return
            
        Returns:
            List of VideoRecord objects ordered by engagement
        """
        return await self.get_video_records(
            days=days,
            limit=limit
        )
    
    async def analyze_runtime_issues(self) -> Dict[str, Any]:
        """
        Analyze runtime data quality issues in the database
        
        Returns:
            Dict with analysis results
        """
        try:
            result = await self.db.execute(
                text("""
                    SELECT 
                        id,
                        video_analysis::text as video_analysis,
                        frame_chunks::text as frame_chunks
                    FROM crm.competitor_posts 
                    WHERE video_analysis IS NOT NULL 
                       OR frame_chunks IS NOT NULL
                    LIMIT 100
                """)
            )
            
            rows = result.fetchall()
            
            analysis = {
                "total_posts": len(rows),
                "runtime_formats": [],
                "broken_formats": [],
                "duration_sources": {
                    "video_analysis_runtime": 0,
                    "video_analysis_total_duration": 0, 
                    "frame_chunks_duration": 0,
                    "estimated": 0
                },
                "format_issues": []
            }
            
            for row in rows:
                try:
                    # Check video_analysis
                    if row.video_analysis:
                        va = json.loads(row.video_analysis)
                        if 'runtime' in va:
                            runtime_val = va['runtime']
                            analysis["runtime_formats"].append(str(runtime_val))
                            analysis["duration_sources"]["video_analysis_runtime"] += 1
                            
                            # Check for broken formats
                            if isinstance(runtime_val, str) and ':' in runtime_val:
                                if '.' in runtime_val.split(':')[1]:
                                    analysis["broken_formats"].append({
                                        "post_id": row.id,
                                        "value": runtime_val,
                                        "issue": "decimal_seconds_in_mm_ss_format"
                                    })
                        
                        if 'total_duration' in va:
                            analysis["duration_sources"]["video_analysis_total_duration"] += 1
                    
                    # Check frame_chunks
                    if row.frame_chunks:
                        fc = json.loads(row.frame_chunks)
                        if isinstance(fc, list) and fc:
                            analysis["duration_sources"]["frame_chunks_duration"] += 1
                    
                except json.JSONDecodeError:
                    analysis["format_issues"].append({
                        "post_id": row.id,
                        "issue": "invalid_json"
                    })
                except Exception as e:
                    analysis["format_issues"].append({
                        "post_id": row.id,
                        "issue": str(e)
                    })
            
            # Count estimated durations
            analysis["duration_sources"]["estimated"] = (
                analysis["total_posts"] - 
                analysis["duration_sources"]["video_analysis_runtime"] -
                analysis["duration_sources"]["video_analysis_total_duration"] -
                analysis["duration_sources"]["frame_chunks_duration"]
            )
            
            return analysis
            
        except Exception as e:
            logger.error("Failed to analyze runtime issues: %s", e)
            return {"error": str(e)}
    
    async def get_metrics_audit(self) -> Dict[str, Any]:
        """
        Audit engagement metrics and their calculations
        
        Returns:
            Dict with metrics analysis
        """
        try:
            result = await self.db.execute(
                text("""
                    SELECT 
                        COUNT(*) as total_posts,
                        COUNT(engagement_score) as has_engagement_score,
                        COUNT(likes) as has_likes,
                        COUNT(comments) as has_comments,
                        COUNT(shares) as has_shares,
                        AVG(engagement_score) as avg_engagement_score,
                        AVG(likes + COALESCE(comments, 0) + COALESCE(shares, 0)) as avg_calculated_engagement,
                        MAX(engagement_score) as max_engagement_score,
                        MAX(likes + COALESCE(comments, 0) + COALESCE(shares, 0)) as max_calculated_engagement
                    FROM crm.competitor_posts
                    WHERE engagement_score IS NOT NULL
                """)
            )
            
            row = result.fetchone()
            
            # Check for discrepancies between stored and calculated
            discrepancy_result = await self.db.execute(
                text("""
                    SELECT 
                        id,
                        engagement_score,
                        likes,
                        comments, 
                        shares,
                        (likes + COALESCE(comments, 0) + COALESCE(shares, 0)) as calculated,
                        ABS(engagement_score - (likes + COALESCE(comments, 0) + COALESCE(shares, 0))) as difference
                    FROM crm.competitor_posts 
                    WHERE engagement_score IS NOT NULL
                      AND ABS(engagement_score - (likes + COALESCE(comments, 0) + COALESCE(shares, 0))) > 1
                    LIMIT 10
                """)
            )
            
            discrepancies = []
            for disc_row in discrepancy_result.fetchall():
                discrepancies.append({
                    "post_id": disc_row.id,
                    "stored_score": disc_row.engagement_score,
                    "calculated_score": disc_row.calculated,
                    "difference": disc_row.difference,
                    "likes": disc_row.likes,
                    "comments": disc_row.comments,
                    "shares": disc_row.shares
                })
            
            return {
                "total_posts": row.total_posts,
                "coverage": {
                    "engagement_score": row.has_engagement_score,
                    "likes": row.has_likes,
                    "comments": row.has_comments,
                    "shares": row.has_shares
                },
                "averages": {
                    "stored_engagement": round(row.avg_engagement_score or 0, 2),
                    "calculated_engagement": round(row.avg_calculated_engagement or 0, 2)
                },
                "maximums": {
                    "stored_engagement": row.max_engagement_score,
                    "calculated_engagement": row.max_calculated_engagement
                },
                "formula_confirmed": "likes + comments + shares",
                "discrepancies": discrepancies,
                "discrepancy_count": len(discrepancies)
            }
            
        except Exception as e:
            logger.error("Failed to audit metrics: %s", e)
            return {"error": str(e)}


# Utility function for creating service instances
def create_video_record_service(db: AsyncSession) -> VideoRecordService:
    """Create a VideoRecordService instance"""
    return VideoRecordService(db)