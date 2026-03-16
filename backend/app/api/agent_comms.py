"""
Agent Communications API - Internal Network-AI Integration

This API provides access to the Network-AI blackboard and swarm guard
for inter-agent communication and budget tracking.

**SECURITY NOTE**: These endpoints are for internal agent coordination.
Admin-only access for blackboard view and audit logs.
"""

import logging
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from pydantic import BaseModel, Field

from app.db.crm_db import get_tenant_db
from app.services.tenant import get_org_id, get_user_id
from app.services.agent_comms import AgentComms
# Admin check will be added later - for now all authenticated users can access

logger = logging.getLogger(__name__)
router = APIRouter()

# ── Models ───────────────────────────────────────────────────────

class BlackboardWriteRequest(BaseModel):
    key: str = Field(..., min_length=1, max_length=200)
    value: Dict[str, Any] | List[Any] | str | int | float | bool
    ttl_seconds: Optional[int] = Field(default=None, ge=1, le=86400)  # Max 24 hours

class BlackboardEntry(BaseModel):
    key: str
    value: Any
    source_agent: Optional[str] = None
    timestamp: str
    ttl: Optional[int] = None

class BudgetInitRequest(BaseModel):
    task_id: str = Field(..., min_length=1, max_length=100)
    budget: int = Field(default=10000, ge=100, le=100000)
    description: str = Field(default="", max_length=500)

class BudgetStatus(BaseModel):
    task_id: str
    initialized: bool
    max_tokens: Optional[int] = None
    used_tokens: Optional[int] = None
    remaining_tokens: Optional[int] = None
    usage_percentage: Optional[float] = None
    status: Optional[str] = None
    can_continue: Optional[bool] = None

class HandoffRequest(BaseModel):
    task_id: str = Field(..., min_length=1, max_length=100)
    from_agent: str = Field(..., min_length=1, max_length=100)
    to_agent: str = Field(..., min_length=1, max_length=100)
    message: str = Field(..., min_length=1, max_length=2000)
    has_artifact: bool = False

# ── Blackboard Endpoints (Admin Only) ───────────────────────────

@router.get("/agent-comms/blackboard")
async def view_blackboard(
    request: Request,
    limit: int = Query(20, ge=1, le=100)
):
    """View the current state of the Network-AI blackboard."""
    org_id = get_org_id(request)
    
    try:
        # Get snapshot of blackboard
        snapshot = AgentComms._run_blackboard("snapshot")
        
        if not snapshot.get("success", True):
            raise HTTPException(status_code=500, detail="Failed to read blackboard")
        
        # Filter entries for this org if they have org_id in the key
        org_entries = []
        entries = snapshot if isinstance(snapshot, list) else [snapshot] if snapshot else []
        
        for entry in entries:
            if isinstance(entry, dict):
                key = entry.get("key", "")
                # Show org-specific entries or global entries
                if f"org_{org_id}" in key or not any(f"org_{i}" in key for i in range(1, 1000)):
                    org_entries.append(entry)
        
        # Limit results
        limited_entries = org_entries[:limit]
        
        return {
            "entries": limited_entries,
            "total_shown": len(limited_entries),
            "org_id": org_id
        }
    except Exception as e:
        logger.error(f"Error viewing blackboard: {e}")
        raise HTTPException(status_code=500, detail="Failed to view blackboard")

@router.post("/agent-comms/blackboard")
async def write_to_blackboard(
    request: Request,
    body: BlackboardWriteRequest
):
    """Write an entry to the Network-AI blackboard."""
    org_id = get_org_id(request)
    user_id = get_user_id(request)
    
    try:
        # Ensure key is org-scoped
        org_key = f"org_{org_id}:{body.key}" if not body.key.startswith(f"org_{org_id}:") else body.key
        
        # Convert value to JSON string
        import json
        value_str = json.dumps(body.value) if not isinstance(body.value, str) else body.value
        
        result = AgentComms._run_blackboard(
            "write", 
            org_key, 
            value_str, 
            body.ttl_seconds
        )
        
        if not result.get("success", True):
            raise HTTPException(status_code=500, detail=f"Failed to write to blackboard: {result.get('error')}")
        
        return {
            "success": True,
            "key": org_key,
            "written": True,
            "ttl": body.ttl_seconds
        }
    except Exception as e:
        logger.error(f"Error writing to blackboard: {e}")
        raise HTTPException(status_code=500, detail="Failed to write to blackboard")

# ── Budget Management Endpoints ─────────────────────────────────

@router.post("/agent-comms/budget/init")
async def initialize_budget(
    request: Request,
    body: BudgetInitRequest,
    db=Depends(get_tenant_db)
):
    """Initialize token budget for a task."""
    org_id = get_org_id(request)
    user_id = get_user_id(request)
    
    try:
        # Scope task ID to org
        org_task_id = f"org_{org_id}_{body.task_id}"
        
        result = await AgentComms.init_budget(
            org_task_id, 
            body.budget, 
            body.description
        )
        
        if not result.get("initialized", False):
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to initialize budget"))
        
        return {
            "success": True,
            "task_id": body.task_id,
            "org_task_id": org_task_id,
            "budget": body.budget,
            "description": body.description
        }
    except Exception as e:
        logger.error(f"Error initializing budget for {body.task_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to initialize budget")

@router.get("/agent-comms/budget/{task_id}", response_model=BudgetStatus)
async def check_budget(
    task_id: str,
    request: Request,
    db=Depends(get_tenant_db)
):
    """Check budget status for a task."""
    org_id = get_org_id(request)
    
    try:
        # Scope task ID to org
        org_task_id = f"org_{org_id}_{task_id}"
        
        result = await AgentComms.check_budget(org_task_id)
        
        return BudgetStatus(
            task_id=task_id,
            initialized=result.get("initialized", False),
            max_tokens=result.get("max_tokens"),
            used_tokens=result.get("used_tokens"),
            remaining_tokens=result.get("remaining_tokens"),
            usage_percentage=result.get("usage_percentage"),
            status=result.get("status"),
            can_continue=result.get("can_continue")
        )
    except Exception as e:
        logger.error(f"Error checking budget for {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to check budget")

@router.post("/agent-comms/handoff/check")
async def check_handoff(
    request: Request,
    body: HandoffRequest,
    db=Depends(get_tenant_db)
):
    """Check if an agent-to-agent handoff is allowed (budget-aware)."""
    org_id = get_org_id(request)
    
    try:
        # Scope task ID to org
        org_task_id = f"org_{org_id}_{body.task_id}"
        
        result = await AgentComms.intercept_handoff(
            org_task_id,
            body.from_agent,
            body.to_agent,
            body.message
        )
        
        return {
            "task_id": body.task_id,
            "allowed": result.get("allowed", False),
            "blocked": result.get("blocked", False),
            "reason": result.get("reason"),
            "message": result.get("message"),
            "tokens_spent": result.get("tokens_spent"),
            "remaining_budget": result.get("remaining_budget"),
            "warnings": result.get("warnings", [])
        }
    except Exception as e:
        logger.error(f"Error checking handoff for {body.task_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to check handoff")

# ── Audit Log Endpoint (Admin Only) ─────────────────────────────

@router.get("/agent-comms/audit-log")
async def get_audit_log(
    request: Request,
    limit: int = Query(50, ge=1, le=200)
):
    """View recent Network-AI audit log entries."""
    try:
        # Read audit log from Network-AI
        from pathlib import Path
        audit_log_path = Path.home() / ".openclaw/workspace/skills/network-ai/data/audit_log.jsonl"
        
        if not audit_log_path.exists():
            return {"entries": [], "message": "No audit log found"}
        
        entries = []
        with open(audit_log_path, 'r') as f:
            lines = f.readlines()
            # Get last N lines
            for line in lines[-limit:]:
                try:
                    import json
                    entry = json.loads(line.strip())
                    entries.append(entry)
                except json.JSONDecodeError:
                    continue
        
        return {
            "entries": list(reversed(entries)),  # Most recent first
            "total_shown": len(entries)
        }
    except Exception as e:
        logger.error(f"Error reading audit log: {e}")
        raise HTTPException(status_code=500, detail="Failed to read audit log")

# ── Knowledge Pool Endpoints ────────────────────────────────────

@router.get("/agent-comms/knowledge/{org_id}")
async def get_org_knowledge(
    org_id: int,
    request: Request,
    limit: int = Query(20, ge=1, le=100),
    db=Depends(get_tenant_db)
):
    """Get completed tasks for the org (shared knowledge pool)."""
    request_org_id = get_org_id(request)
    
    # Users can only access their own org's knowledge
    if org_id != request_org_id:
        raise HTTPException(status_code=403, detail="Cannot access other organization's knowledge")
    
    try:
        tasks = await AgentComms.get_org_completed_tasks(org_id)
        
        # Limit results
        limited_tasks = tasks[:limit]
        
        return {
            "tasks": limited_tasks,
            "total_shown": len(limited_tasks),
            "org_id": org_id
        }
    except Exception as e:
        logger.error(f"Error getting org knowledge for {org_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get organization knowledge")