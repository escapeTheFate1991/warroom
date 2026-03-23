#!/usr/bin/env python3
"""
War Room Context Management Skill

OpenClaw skill for intelligent context loading and coordination.
Integrates with War Room's context management infrastructure.
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any

# Add War Room project to path
WARROOM_PATH = Path("/home/eddy/Development/warroom")
sys.path.append(str(WARROOM_PATH))

from backend.app.services.vector_memory import search_memory, store_memory
from backend.app.services.agent_comms import AgentComms

logger = logging.getLogger(__name__)

class WarRoomContextSkill:
    """Context management skill for War Room development."""
    
    def __init__(self):
        self.project_root = WARROOM_PATH
        self.context_dir = self.project_root / ".context"
        
    async def load_context_for_request(self, request: str, context_type: str = "auto", org_id: str = "1") -> Dict[str, Any]:
        """Load relevant context for a user request."""
        context_result = {
            "request": request,
            "context_type": context_type,
            "sources": [],
            "recommendations": [],
            "session_context": None,
            "related_patterns": []
        }
        
        # Determine context type if auto
        if context_type == "auto":
            context_type = self._classify_request(request)
        
        # Load context based on type
        if context_type == "error":
            context_result["sources"].append(await self._load_error_context(request, org_id))
            
        elif context_type == "code_search":
            context_result["sources"].append(await self._load_code_context(request, org_id))
            
        elif context_type == "api":
            context_result["sources"].append(await self._load_api_context(request, org_id))
            
        elif context_type == "database":
            context_result["sources"].append(await self._load_database_context(request, org_id))
        
        # Always check session context
        try:
            session_context = await self._get_current_session_context(org_id)
            context_result["session_context"] = session_context
        except Exception as e:
            logger.warning(f"Failed to load session context: {e}")
        
        # Find related patterns
        try:
            patterns = await self._find_related_patterns(request, org_id)
            context_result["related_patterns"] = patterns
        except Exception as e:
            logger.warning(f"Failed to find patterns: {e}")
        
        # Generate recommendations
        context_result["recommendations"] = await self._generate_recommendations(context_result)
        
        # Update session with this context request
        try:
            await self._update_session_activity(request, context_result, org_id)
        except Exception as e:
            logger.warning(f"Failed to update session: {e}")
        
        return context_result
    
    async def share_context_with_agents(self, context: Dict[str, Any], target_agents: List[str], org_id: str = "1") -> Dict[str, Any]:
        """Share context with other agents via Network-AI."""
        sharing_results = {
            "context_shared": False,
            "target_agents": target_agents,
            "shared_data": {},
            "errors": []
        }
        
        # Prepare context summary for sharing
        context_summary = {
            "type": "war_room_context",
            "request": context["request"],
            "context_type": context["context_type"],
            "key_sources": [s.get("type", "unknown") for s in context["sources"]],
            "recommendations": context["recommendations"][:3],  # Top 3 recommendations
            "session_active": bool(context["session_context"]),
            "shared_at": asyncio.get_event_loop().time()
        }
        
        # Share with each target agent
        for agent_id in target_agents:
            try:
                result = await AgentComms.post_message(
                    from_agent_id=0,  # Context system
                    to_agent_id=int(agent_id),
                    org_id=int(org_id),
                    message=f"Context shared: {context['request']}",
                    task_id=f"context_share_{agent_id}"
                )
                
                if result.get("success", False):
                    sharing_results["shared_data"][agent_id] = context_summary
                else:
                    sharing_results["errors"].append(f"Failed to share with agent {agent_id}")
                    
            except Exception as e:
                error_msg = f"Error sharing with agent {agent_id}: {e}"
                logger.error(error_msg)
                sharing_results["errors"].append(error_msg)
        
        sharing_results["context_shared"] = len(sharing_results["shared_data"]) > 0
        
        return sharing_results
    
    async def monitor_context_quality(self, org_id: str = "1") -> Dict[str, Any]:
        """Monitor context system quality and usage."""
        quality_metrics = {
            "timestamp": asyncio.get_event_loop().time(),
            "session_health": {},
            "context_coverage": {},
            "usage_stats": {},
            "degradation_alerts": []
        }
        
        # Check session health
        try:
            session_stats = await self._get_session_health_metrics(org_id)
            quality_metrics["session_health"] = session_stats
        except Exception as e:
            quality_metrics["degradation_alerts"].append(f"Session health check failed: {e}")
        
        # Check context coverage
        try:
            coverage_stats = await self._get_context_coverage_metrics(org_id)
            quality_metrics["context_coverage"] = coverage_stats
        except Exception as e:
            quality_metrics["degradation_alerts"].append(f"Coverage check failed: {e}")
        
        # Check usage patterns
        try:
            usage_stats = await self._get_context_usage_stats(org_id)
            quality_metrics["usage_stats"] = usage_stats
        except Exception as e:
            quality_metrics["degradation_alerts"].append(f"Usage stats failed: {e}")
        
        return quality_metrics
    
    def _classify_request(self, request: str) -> str:
        """Classify request to determine context type."""
        request_lower = request.lower()
        
        # Error indicators
        error_keywords = ["error", "exception", "failed", "broken", "bug", "issue", "problem"]
        if any(keyword in request_lower for keyword in error_keywords):
            return "error"
        
        # API indicators
        api_keywords = ["api", "endpoint", "request", "response", "/api/", "post", "get", "put", "delete"]
        if any(keyword in request_lower for keyword in api_keywords):
            return "api"
        
        # Database indicators
        db_keywords = ["database", "sql", "table", "query", "schema", "migration", "postgres"]
        if any(keyword in request_lower for keyword in db_keywords):
            return "database"
        
        # Code search indicators
        code_keywords = ["function", "class", "method", "import", "component", "file", "code"]
        if any(keyword in request_lower for keyword in code_keywords):
            return "code_search"
        
        return "general"
    
    async def _load_error_context(self, request: str, org_id: str) -> Dict[str, Any]:
        """Load context for error-related requests."""
        error_context = {
            "type": "error_context",
            "similar_errors": [],
            "resolution_patterns": [],
            "relevant_files": []
        }
        
        # Search for similar errors in memory
        try:
            similar_errors = await search_memory(org_id, f"error: {request}", limit=5, score_threshold=0.7)
            error_context["similar_errors"] = [
                {
                    "relevance": hit.get("score", 0.0),
                    "content": hit.get("payload", {}).get("text", "")[:200],
                    "metadata": hit.get("payload", {}).get("metadata", {})
                }
                for hit in similar_errors
            ]
        except Exception as e:
            logger.error(f"Error searching similar errors: {e}")
        
        # Search for resolutions
        try:
            resolutions = await search_memory(org_id, f"resolution: {request}", limit=3, score_threshold=0.6)
            error_context["resolution_patterns"] = [
                {
                    "relevance": hit.get("score", 0.0),
                    "solution": hit.get("payload", {}).get("text", "")[:300]
                }
                for hit in resolutions
            ]
        except Exception as e:
            logger.error(f"Error searching resolutions: {e}")
        
        return error_context
    
    async def _load_code_context(self, request: str, org_id: str) -> Dict[str, Any]:
        """Load context for code search requests."""
        code_context = {
            "type": "code_context",
            "relevant_files": [],
            "patterns": [],
            "dependencies": []
        }
        
        # Search code embeddings
        try:
            code_results = await search_memory(org_id, f"code: {request}", limit=10, score_threshold=0.6)
            code_context["relevant_files"] = [
                {
                    "file_path": hit.get("payload", {}).get("metadata", {}).get("file_path", "unknown"),
                    "relevance": hit.get("score", 0.0),
                    "file_type": hit.get("payload", {}).get("metadata", {}).get("file_type", "unknown"),
                    "excerpt": hit.get("payload", {}).get("text", "")[:200]
                }
                for hit in code_results
            ]
        except Exception as e:
            logger.error(f"Error searching code: {e}")
        
        return code_context
    
    async def _load_api_context(self, request: str, org_id: str) -> Dict[str, Any]:
        """Load context for API-related requests."""
        api_context = {
            "type": "api_context",
            "endpoints": [],
            "auth_patterns": [],
            "request_examples": []
        }
        
        # Search API embeddings
        try:
            api_results = await search_memory(org_id, f"api: {request}", limit=5, score_threshold=0.7)
            api_context["endpoints"] = [
                {
                    "endpoint": hit.get("payload", {}).get("metadata", {}).get("endpoint", "unknown"),
                    "method": hit.get("payload", {}).get("metadata", {}).get("method", "unknown"),
                    "file": hit.get("payload", {}).get("metadata", {}).get("file", "unknown"),
                    "relevance": hit.get("score", 0.0)
                }
                for hit in api_results
            ]
        except Exception as e:
            logger.error(f"Error searching APIs: {e}")
        
        return api_context
    
    async def _load_database_context(self, request: str, org_id: str) -> Dict[str, Any]:
        """Load context for database-related requests."""
        db_context = {
            "type": "database_context",
            "schemas": [],
            "migrations": [],
            "relationships": []
        }
        
        # Search database-related content
        try:
            db_results = await search_memory(org_id, f"database: {request}", limit=5, score_threshold=0.6)
            # Process results based on metadata type
            for hit in db_results:
                metadata = hit.get("payload", {}).get("metadata", {})
                result_data = {
                    "relevance": hit.get("score", 0.0),
                    "content": hit.get("payload", {}).get("text", "")[:200],
                    "metadata": metadata
                }
                
                if "schema" in metadata.get("type", ""):
                    db_context["schemas"].append(result_data)
                elif "migration" in metadata.get("type", ""):
                    db_context["migrations"].append(result_data)
                
        except Exception as e:
            logger.error(f"Error searching database context: {e}")
        
        return db_context
    
    async def _get_current_session_context(self, org_id: str) -> Optional[Dict[str, Any]]:
        """Get current development session context."""
        session_file = self.context_dir / "sessions" / "current.json"
        
        if not session_file.exists():
            return None
        
        try:
            with open(session_file, 'r') as f:
                content = f.read()
                if content.strip():
                    session_data = json.loads(content)
                    return {
                        "session_id": session_data.get("session_id"),
                        "current_task": session_data.get("current_task"),
                        "started_at": session_data.get("started_at"),
                        "last_activity": session_data.get("last_activity"),
                        "files_modified": session_data.get("files_modified", [])[-5:],  # Last 5 files
                        "error_count": len(session_data.get("error_patterns", [])),
                        "context_quality": session_data.get("context_quality", 1.0)
                    }
        except Exception as e:
            logger.error(f"Error loading session context: {e}")
        
        return None
    
    async def _find_related_patterns(self, request: str, org_id: str) -> List[Dict[str, Any]]:
        """Find related patterns from AI analysis."""
        try:
            pattern_results = await search_memory(org_id, f"pattern: {request}", limit=3, score_threshold=0.6)
            return [
                {
                    "pattern_type": hit.get("payload", {}).get("metadata", {}).get("pattern_type", "unknown"),
                    "relevance": hit.get("score", 0.0),
                    "description": hit.get("payload", {}).get("text", "")[:150]
                }
                for hit in pattern_results
            ]
        except Exception as e:
            logger.error(f"Error finding patterns: {e}")
            return []
    
    async def _generate_recommendations(self, context_result: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations based on loaded context."""
        recommendations = []
        
        # Based on context type
        context_type = context_result["context_type"]
        
        if context_type == "error":
            if context_result["sources"]:
                error_context = context_result["sources"][0]
                if error_context.get("similar_errors"):
                    recommendations.append("Review similar past errors for common solutions")
                if error_context.get("resolution_patterns"):
                    recommendations.append("Apply proven resolution patterns from history")
                else:
                    recommendations.append("Document solution for future reference")
        
        elif context_type == "code_search":
            if context_result["sources"]:
                code_context = context_result["sources"][0]
                if code_context.get("relevant_files"):
                    recommendations.append(f"Review {len(code_context['relevant_files'])} relevant files found")
                else:
                    recommendations.append("Consider creating documentation for this code pattern")
        
        elif context_type == "api":
            recommendations.append("Check API documentation and authentication patterns")
            recommendations.append("Validate request/response formats")
        
        elif context_type == "database":
            recommendations.append("Review schema migrations and relationships")
            recommendations.append("Check for recent database changes")
        
        # Session-based recommendations
        if context_result["session_context"]:
            session = context_result["session_context"]
            if session["error_count"] > 3:
                recommendations.append("Consider session refresh due to high error count")
            if session["context_quality"] < 0.7:
                recommendations.append("Context quality degraded - consider updating session")
        
        return recommendations[:5]  # Top 5 recommendations
    
    async def _update_session_activity(self, request: str, context_result: Dict[str, Any], org_id: str):
        """Update session tracking with context activity."""
        # This would integrate with session_manager.py
        # For now, store the context request in memory
        try:
            context_text = f"Context request: {request} | Type: {context_result['context_type']} | Sources: {len(context_result['sources'])}"
            await store_memory(
                org_id=org_id,
                user_id="context_skill",
                text=context_text,
                metadata={
                    "type": "context_request",
                    "context_type": context_result["context_type"],
                    "request": request,
                    "sources_count": len(context_result["sources"]),
                    "timestamp": asyncio.get_event_loop().time()
                }
            )
        except Exception as e:
            logger.error(f"Failed to store context activity: {e}")
    
    async def _get_session_health_metrics(self, org_id: str) -> Dict[str, Any]:
        """Get session health metrics."""
        session_context = await self._get_current_session_context(org_id)
        
        if not session_context:
            return {"status": "no_active_session"}
        
        return {
            "status": "active",
            "session_id": session_context["session_id"],
            "context_quality": session_context["context_quality"],
            "error_count": session_context["error_count"],
            "files_modified": len(session_context["files_modified"]),
            "last_activity": session_context["last_activity"]
        }
    
    async def _get_context_coverage_metrics(self, org_id: str) -> Dict[str, Any]:
        """Get context coverage metrics."""
        # Check how much of the codebase is indexed
        try:
            # Count indexed files
            code_memories = await search_memory(org_id, "code:", limit=100, score_threshold=0.1)
            api_memories = await search_memory(org_id, "api:", limit=50, score_threshold=0.1)
            
            return {
                "code_files_indexed": len(code_memories),
                "api_endpoints_indexed": len(api_memories),
                "last_index_update": "unknown"  # Would need to track this
            }
        except Exception as e:
            logger.error(f"Error getting coverage metrics: {e}")
            return {"error": str(e)}
    
    async def _get_context_usage_stats(self, org_id: str) -> Dict[str, Any]:
        """Get context usage statistics."""
        try:
            # Search for recent context requests
            recent_requests = await search_memory(org_id, "context_request", limit=20, score_threshold=0.1)
            
            # Analyze request types
            request_types = {}
            for hit in recent_requests:
                metadata = hit.get("payload", {}).get("metadata", {})
                context_type = metadata.get("context_type", "unknown")
                request_types[context_type] = request_types.get(context_type, 0) + 1
            
            return {
                "total_requests": len(recent_requests),
                "request_types": request_types,
                "most_common": max(request_types.items(), key=lambda x: x[1])[0] if request_types else "none"
            }
        except Exception as e:
            logger.error(f"Error getting usage stats: {e}")
            return {"error": str(e)}


# OpenClaw Skill Interface
async def main(request: str, context_type: str = "auto", org_id: str = "1", 
              share_with: str = "", monitor: bool = False) -> Dict[str, Any]:
    """Main skill entry point."""
    skill = WarRoomContextSkill()
    
    if monitor:
        return await skill.monitor_context_quality(org_id)
    
    # Load context for request
    context_result = await skill.load_context_for_request(request, context_type, org_id)
    
    # Share with other agents if requested
    if share_with:
        target_agents = [agent.strip() for agent in share_with.split(",")]
        sharing_result = await skill.share_context_with_agents(context_result, target_agents, org_id)
        context_result["sharing_result"] = sharing_result
    
    return context_result


if __name__ == "__main__":
    import asyncio
    import argparse
    
    parser = argparse.ArgumentParser(description="War Room Context Management Skill")
    parser.add_argument("request", help="Context request or description")
    parser.add_argument("--context-type", default="auto", help="Context type (auto, error, code_search, api, database)")
    parser.add_argument("--org-id", default="1", help="Organization ID")
    parser.add_argument("--share-with", default="", help="Comma-separated agent IDs to share context with")
    parser.add_argument("--monitor", action="store_true", help="Monitor context quality instead")
    
    args = parser.parse_args()
    
    result = asyncio.run(main(
        request=args.request,
        context_type=args.context_type,
        org_id=args.org_id,
        share_with=args.share_with,
        monitor=args.monitor
    ))
    
    print(json.dumps(result, indent=2))