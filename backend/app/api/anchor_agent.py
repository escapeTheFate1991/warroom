"""Anchor Agent API — Platform-Wide AI Assistant "Alex"

API endpoints for the Anchor Agent "Alex" that can answer questions about 
any War Room feature through natural language queries.
"""
import logging
from typing import Dict, Any, List

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.crm_db import get_tenant_db
from app.services.tenant import get_org_id, get_user_id
from app.services.anchor_agent import AnchorAgent

logger = logging.getLogger(__name__)

router = APIRouter()


class QueryRequest(BaseModel):
    """Natural language query request to Alex."""
    query: str = Field(..., description="Natural language question about War Room features")


class QuickStatsResponse(BaseModel):
    """Quick stats dashboard summary."""
    deals: Dict[str, Any] = Field(default_factory=dict)
    contacts: Dict[str, Any] = Field(default_factory=dict)
    social: Dict[str, Any] = Field(default_factory=dict)
    content: Dict[str, Any] = Field(default_factory=dict)
    tasks: Dict[str, Any] = Field(default_factory=dict)


class CapabilityInfo(BaseModel):
    """Information about an Alex capability."""
    name: str
    keywords: List[str]
    description: str


class QueryResponse(BaseModel):
    """Response from Alex query."""
    capability: str
    confidence: int
    summary: str
    data: Dict[str, Any] = Field(default_factory=dict)
    error: str = None


@router.post("/api/alex/query", response_model=QueryResponse)
async def process_query(
    request_data: QueryRequest,
    request: Request,
    db: AsyncSession = Depends(get_tenant_db)
):
    """Process a natural language query through Alex.
    
    Alex can answer questions about:
    - Sales data: "What are my sales this week?"
    - Social metrics: "Show me engagement for the last month"
    - Content schedule: "What posts are scheduled?"
    - Contacts: "Find contacts named John"
    - Platform help: "How do I use the CRM?"
    - Agent tasks: "What tasks are running?"
    """
    try:
        org_id = get_org_id(request)
        user_id = get_user_id(request)
        
        if not org_id:
            raise HTTPException(status_code=403, detail="Organization context required")
        
        result = await AnchorAgent.process_query(
            db=db,
            org_id=org_id,
            user_id=user_id,
            query=request_data.query
        )
        
        return QueryResponse(**result)
        
    except Exception as e:
        logger.error(f"Alex query failed: {e}")
        raise HTTPException(status_code=500, detail="Query processing failed")


@router.get("/api/alex/capabilities", response_model=List[CapabilityInfo])
async def get_capabilities():
    """List what Alex can do."""
    capabilities = []
    
    capability_descriptions = {
        "sales_report": "Get sales data, pipeline reports, and deal forecasts",
        "social_metrics": "View social media engagement, analytics, and performance",
        "content_schedule": "Check scheduled posts, content calendar, and publishing status",
        "contacts": "Search contacts, leads, and organizations in your CRM",
        "platform_help": "Get help navigating War Room features and tools",
        "agent_tasks": "View agent task status, assignments, and progress"
    }
    
    for capability_name, capability_info in AnchorAgent.CAPABILITIES.items():
        capabilities.append(CapabilityInfo(
            name=capability_name,
            keywords=capability_info["keywords"],
            description=capability_descriptions.get(capability_name, "Unknown capability")
        ))
    
    return capabilities


@router.get("/api/alex/quick-stats", response_model=QuickStatsResponse)
async def get_quick_stats(
    request: Request,
    db: AsyncSession = Depends(get_tenant_db)
):
    """Get dashboard summary for quick overview."""
    try:
        org_id = get_org_id(request)
        user_id = get_user_id(request)
        
        if not org_id:
            raise HTTPException(status_code=403, detail="Organization context required")
        
        # Get quick stats from each capability
        stats = QuickStatsResponse()
        
        # Sales summary (last 30 days)
        try:
            sales_result = await AnchorAgent._handle_sales_query(
                db, org_id, user_id, "sales last 30 days"
            )
            if "data" in sales_result:
                summary_data = sales_result["data"].get("summary", [])
                total_deals = sum(s.get("count", 0) for s in summary_data)
                total_value = sum(s.get("total_value", 0) for s in summary_data)
                won_deals = next((s for s in summary_data if s.get("deal_status") == "Won"), {})
                
                stats.deals = {
                    "total_deals": total_deals,
                    "total_value": total_value,
                    "won_count": won_deals.get("count", 0),
                    "won_value": won_deals.get("total_value", 0)
                }
        except Exception as e:
            logger.warning(f"Quick stats - sales failed: {e}")
            stats.deals = {"error": "Unable to fetch sales data"}
        
        # Contacts summary
        try:
            contacts_result = await AnchorAgent._handle_contacts_query(
                db, org_id, user_id, "contacts summary"
            )
            stats.contacts = {"summary": contacts_result.get("summary", "No contact data")}
        except Exception as e:
            logger.warning(f"Quick stats - contacts failed: {e}")
            stats.contacts = {"error": "Unable to fetch contacts"}
        
        # Social summary (last 7 days)
        try:
            social_result = await AnchorAgent._handle_social_query(
                db, org_id, user_id, "social metrics last 7 days"
            )
            if "data" in social_result:
                platform_metrics = social_result["data"].get("platform_metrics", [])
                total_engagement = sum(p.get("total_engagement", 0) or 0 for p in platform_metrics)
                total_impressions = sum(p.get("total_impressions", 0) or 0 for p in platform_metrics)
                
                stats.social = {
                    "platforms": len(platform_metrics),
                    "total_engagement": total_engagement,
                    "total_impressions": total_impressions
                }
        except Exception as e:
            logger.warning(f"Quick stats - social failed: {e}")
            stats.social = {"error": "Unable to fetch social data"}
        
        # Content summary (next 7 days)
        try:
            content_result = await AnchorAgent._handle_content_query(
                db, org_id, user_id, "upcoming content"
            )
            if "data" in content_result:
                upcoming_posts = content_result["data"].get("upcoming_posts", [])
                stats.content = {
                    "upcoming_count": len(upcoming_posts),
                    "next_scheduled": upcoming_posts[0].get("scheduled_for") if upcoming_posts else None
                }
        except Exception as e:
            logger.warning(f"Quick stats - content failed: {e}")
            stats.content = {"error": "Unable to fetch content data"}
        
        # Tasks summary
        try:
            tasks_result = await AnchorAgent._handle_tasks_query(
                db, org_id, user_id, "agent tasks last 7 days"
            )
            if "data" in tasks_result:
                task_summary = tasks_result["data"].get("task_summary", [])
                active_tasks = tasks_result["data"].get("active_tasks", [])
                
                in_progress = sum(s.get("count", 0) for s in task_summary if s.get("status") == "in_progress")
                pending = sum(s.get("count", 0) for s in task_summary if s.get("status") == "pending")
                
                stats.tasks = {
                    "in_progress": in_progress,
                    "pending": pending,
                    "active_count": len(active_tasks)
                }
        except Exception as e:
            logger.warning(f"Quick stats - tasks failed: {e}")
            stats.tasks = {"error": "Unable to fetch task data"}
        
        return stats
        
    except Exception as e:
        logger.error(f"Quick stats failed: {e}")
        raise HTTPException(status_code=500, detail="Unable to fetch quick stats")


@router.get("/api/alex/health")
async def health_check():
    """Health check for Alex service."""
    return {
        "status": "healthy",
        "service": "anchor_agent",
        "capabilities": list(AnchorAgent.CAPABILITIES.keys()),
        "version": "1.0.0"
    }