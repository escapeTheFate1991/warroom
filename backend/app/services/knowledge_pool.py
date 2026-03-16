"""Knowledge Pool Service — Shared org knowledge management.

Manages the org-wide knowledge pool where completed task results from all agents
are stored and made searchable for future reference.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class KnowledgePoolService:
    """Manage shared org knowledge pool for agent task results."""

    @staticmethod
    async def contribute_knowledge(
        db: AsyncSession,
        org_id: int,
        agent_id: int,
        user_id: int,
        task_type: str,
        title: str,
        summary: str,
        result_data: Dict[str, Any],
        tags: List[str]
    ) -> int:
        """Add completed task result to knowledge pool.
        
        Args:
            db: Database session
            org_id: Organization ID
            agent_id: Agent instance that contributed this
            user_id: User who owns the agent
            task_type: Type of task (research, analysis, code, content, design)
            title: Brief title for the knowledge
            summary: Human-readable summary
            result_data: Structured task output
            tags: Searchable tags
            
        Returns:
            ID of created knowledge entry
        """
        result = await db.execute(
            text("""
                INSERT INTO public.org_knowledge_pool (
                    org_id, contributed_by_agent_id, contributed_by_user_id,
                    task_type, title, summary, result_data, tags
                ) VALUES (
                    :org_id, :agent_id, :user_id, :task_type, :title, :summary,
                    CAST(:result_data AS jsonb), CAST(:tags AS jsonb)
                ) RETURNING id
            """),
            {
                "org_id": org_id,
                "agent_id": agent_id,
                "user_id": user_id,
                "task_type": task_type,
                "title": title,
                "summary": summary,
                "result_data": str(result_data).replace("'", '"'),
                "tags": str(tags).replace("'", '"')
            }
        )
        
        knowledge_id = result.fetchone()[0]
        await db.commit()
        
        logger.info(
            "Added knowledge %d to pool for org %d (agent %d, type %s)", 
            knowledge_id, org_id, agent_id, task_type
        )
        
        return knowledge_id

    @staticmethod
    async def search_knowledge(
        db: AsyncSession,
        org_id: int,
        query: str,
        task_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search knowledge pool with text search and filters.
        
        Args:
            db: Database session
            org_id: Organization ID
            query: Text to search in title and summary
            task_type: Filter by task type (optional)
            tags: Filter by tags (optional)
            limit: Maximum results to return
            
        Returns:
            List of knowledge entries
        """
        # Build dynamic WHERE clause
        where_conditions = ["org_id = :org_id", "status = 'active'"]
        params = {"org_id": org_id, "query": f"%{query}%", "limit": limit}
        
        if query:
            where_conditions.append("(title ILIKE :query OR summary ILIKE :query)")
        
        if task_type:
            where_conditions.append("task_type = :task_type")
            params["task_type"] = task_type
            
        if tags:
            # Check if any of the provided tags exist in the tags JSONB array
            tag_conditions = []
            for i, tag in enumerate(tags):
                tag_key = f"tag_{i}"
                tag_conditions.append(f"tags ? :{tag_key}")
                params[tag_key] = tag
            where_conditions.append(f"({' OR '.join(tag_conditions)})")
        
        where_clause = " AND ".join(where_conditions)
        
        result = await db.execute(
            text(f"""
                SELECT id, task_type, title, summary, result_data, tags,
                       quality_score, usage_count, contributed_by_user_id,
                       created_at, updated_at
                FROM public.org_knowledge_pool
                WHERE {where_clause}
                ORDER BY quality_score DESC, usage_count DESC, created_at DESC
                LIMIT :limit
            """),
            params
        )
        
        knowledge_entries = []
        for row in result:
            knowledge_entries.append({
                "id": row[0],
                "task_type": row[1],
                "title": row[2],
                "summary": row[3],
                "result_data": row[4],
                "tags": row[5],
                "quality_score": float(row[6]) if row[6] else 0.0,
                "usage_count": row[7],
                "contributed_by_user_id": row[8],
                "created_at": row[9],
                "updated_at": row[10]
            })
        
        return knowledge_entries

    @staticmethod
    async def get_relevant_knowledge(
        db: AsyncSession,
        org_id: int,
        task_description: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Find relevant past results for a new task using text similarity.
        
        Args:
            db: Database session
            org_id: Organization ID
            task_description: Description of the new task
            limit: Maximum results to return
            
        Returns:
            List of relevant knowledge entries
        """
        # Simple keyword-based similarity for now
        # In future could use vector similarity with embeddings
        keywords = task_description.lower().split()
        query_pattern = "%".join(keywords)
        
        result = await db.execute(
            text("""
                SELECT id, task_type, title, summary, result_data, tags,
                       quality_score, usage_count, contributed_by_user_id,
                       created_at
                FROM public.org_knowledge_pool
                WHERE org_id = :org_id 
                AND status = 'active'
                AND (
                    LOWER(title || ' ' || summary) LIKE :query_pattern
                    OR task_type IN (
                        SELECT DISTINCT task_type 
                        FROM public.org_knowledge_pool 
                        WHERE LOWER(title || ' ' || summary) LIKE :query_pattern
                    )
                )
                ORDER BY quality_score DESC, usage_count DESC
                LIMIT :limit
            """),
            {
                "org_id": org_id,
                "query_pattern": f"%{query_pattern}%",
                "limit": limit
            }
        )
        
        relevant_entries = []
        for row in result:
            relevant_entries.append({
                "id": row[0],
                "task_type": row[1],
                "title": row[2],
                "summary": row[3],
                "result_data": row[4],
                "tags": row[5],
                "quality_score": float(row[6]) if row[6] else 0.0,
                "usage_count": row[7],
                "contributed_by_user_id": row[8],
                "created_at": row[9]
            })
        
        return relevant_entries

    @staticmethod
    async def record_usage(db: AsyncSession, knowledge_id: int) -> bool:
        """Increment usage count when an agent references a result.
        
        Args:
            db: Database session
            knowledge_id: ID of knowledge entry being referenced
            
        Returns:
            True if usage was recorded, False if entry not found
        """
        result = await db.execute(
            text("""
                UPDATE public.org_knowledge_pool
                SET usage_count = usage_count + 1, updated_at = NOW()
                WHERE id = :knowledge_id AND status = 'active'
            """),
            {"knowledge_id": knowledge_id}
        )
        
        if result.rowcount > 0:
            await db.commit()
            logger.info("Recorded usage for knowledge %d", knowledge_id)
            return True
        
        return False

    @staticmethod
    async def get_pool_stats(db: AsyncSession, org_id: int) -> Dict[str, Any]:
        """Get knowledge pool statistics for the org.
        
        Args:
            db: Database session
            org_id: Organization ID
            
        Returns:
            Dictionary with pool statistics
        """
        # Total entries and by type
        type_stats = await db.execute(
            text("""
                SELECT task_type, COUNT(*) as count
                FROM public.org_knowledge_pool
                WHERE org_id = :org_id AND status = 'active'
                GROUP BY task_type
                ORDER BY count DESC
            """),
            {"org_id": org_id}
        )
        
        # Top contributors
        contributors = await db.execute(
            text("""
                SELECT contributed_by_user_id, COUNT(*) as contributions
                FROM public.org_knowledge_pool
                WHERE org_id = :org_id AND status = 'active'
                GROUP BY contributed_by_user_id
                ORDER BY contributions DESC
                LIMIT 5
            """),
            {"org_id": org_id}
        )
        
        # Most referenced entries
        top_referenced = await db.execute(
            text("""
                SELECT id, title, usage_count
                FROM public.org_knowledge_pool
                WHERE org_id = :org_id AND status = 'active'
                ORDER BY usage_count DESC
                LIMIT 5
            """),
            {"org_id": org_id}
        )
        
        # Total count
        total_result = await db.execute(
            text("""
                SELECT COUNT(*) 
                FROM public.org_knowledge_pool 
                WHERE org_id = :org_id AND status = 'active'
            """),
            {"org_id": org_id}
        )
        
        total_entries = total_result.fetchone()[0]
        
        return {
            "total_entries": total_entries,
            "by_type": [{"task_type": row[0], "count": row[1]} for row in type_stats],
            "top_contributors": [
                {"user_id": row[0], "contributions": row[1]} 
                for row in contributors
            ],
            "most_referenced": [
                {"id": row[0], "title": row[1], "usage_count": row[2]} 
                for row in top_referenced
            ]
        }

    @staticmethod
    async def archive_knowledge(db: AsyncSession, org_id: int, knowledge_id: int) -> bool:
        """Archive knowledge entry (soft delete).
        
        Args:
            db: Database session
            org_id: Organization ID (for security)
            knowledge_id: ID of knowledge to archive
            
        Returns:
            True if archived, False if not found
        """
        result = await db.execute(
            text("""
                UPDATE public.org_knowledge_pool
                SET status = 'archived', updated_at = NOW()
                WHERE id = :knowledge_id AND org_id = :org_id AND status = 'active'
            """),
            {"knowledge_id": knowledge_id, "org_id": org_id}
        )
        
        if result.rowcount > 0:
            await db.commit()
            logger.info("Archived knowledge %d in org %d", knowledge_id, org_id)
            return True
        
        return False