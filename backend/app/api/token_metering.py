"""Token metering API endpoints.

Provides endpoints for checking budget status, viewing usage, and managing allocations.
All endpoints are tenant-isolated using get_tenant_db.
"""
import logging
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user, require_superadmin
from app.db.crm_db import get_tenant_db
from app.services.tenant import get_org_id, get_user_id
from app.services import token_metering

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Request/Response Models ─────────────────────────────────────────


class TokenAllocationRequest(BaseModel):
    """Request to set token allocation."""
    tier: str  # 'org', 'dept', or 'user'
    target_id: int
    monthly_limit: int  # 0 = unlimited
    reset_day: int = 1  # day of month to reset (1-28)


class TokenBudgetResponse(BaseModel):
    """Token budget status response."""
    org_remaining: int
    dept_remaining: int
    user_remaining: int
    org_limit: int
    dept_limit: int
    user_limit: int
    soft_limit_reached: bool
    hard_limit_reached: bool
    warning_message: Optional[str] = None


class UsageSummaryResponse(BaseModel):
    """Usage summary response."""
    total_tokens: int
    total_cost: float
    period_days: int
    breakdown_by_model: Dict[str, int]
    breakdown_by_user: Dict[str, int]
    breakdown_by_agent: Dict[str, int]


# ── Endpoints ───────────────────────────────────────────────────────


@router.get("/budget", response_model=TokenBudgetResponse)
async def get_budget_status(
    request: Request,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: Dict = Depends(get_current_user)
):
    """Get current user's token budget status across all tiers."""
    
    org_id = get_org_id(request)
    user_id = get_user_id()
    
    try:
        budget = await token_metering.check_token_budget(db, org_id, user_id)
        return TokenBudgetResponse(**budget.to_dict())
        
    except Exception as e:
        logger.error(f"Failed to get budget status for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve budget status")


@router.get("/usage", response_model=UsageSummaryResponse)
async def get_usage_history(
    request: Request,
    days: int = Query(30, description="Number of days to look back"),
    db: AsyncSession = Depends(get_tenant_db),
    current_user: Dict = Depends(get_current_user)
):
    """Get token usage history for current user."""
    
    if days < 1 or days > 365:
        raise HTTPException(status_code=400, detail="Days must be between 1 and 365")
    
    org_id = get_org_id(request)
    user_id = get_user_id()
    
    try:
        summary = await token_metering.get_usage_summary(db, org_id, user_id, days)
        return UsageSummaryResponse(**summary.to_dict())
        
    except Exception as e:
        logger.error(f"Failed to get usage history for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve usage history")


@router.get("/usage/org", response_model=UsageSummaryResponse)
async def get_org_usage(
    request: Request,
    days: int = Query(30, description="Number of days to look back"),
    db: AsyncSession = Depends(get_tenant_db),
    current_user: Dict = Depends(get_current_user),
    _admin: None = Depends(require_superadmin)
):
    """Get organization-wide token usage (admin only)."""
    
    if days < 1 or days > 365:
        raise HTTPException(status_code=400, detail="Days must be between 1 and 365")
    
    org_id = get_org_id(request)
    
    try:
        # No user_id filter for org-wide view
        summary = await token_metering.get_usage_summary(db, org_id, None, days)
        return UsageSummaryResponse(**summary.to_dict())
        
    except Exception as e:
        logger.error(f"Failed to get org usage for org {org_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve organization usage")


@router.put("/allocations")
async def set_allocations(
    request: Request,
    allocation: TokenAllocationRequest,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: Dict = Depends(get_current_user),
    _admin: None = Depends(require_superadmin)
):
    """Set token allocation for a tier (admin only)."""
    
    org_id = get_org_id(request)
    
    # Validate inputs
    if allocation.tier not in ['org', 'dept', 'user']:
        raise HTTPException(status_code=400, detail="Tier must be 'org', 'dept', or 'user'")
    
    if allocation.monthly_limit < 0:
        raise HTTPException(status_code=400, detail="Monthly limit cannot be negative")
        
    if allocation.reset_day < 1 or allocation.reset_day > 28:
        raise HTTPException(status_code=400, detail="Reset day must be between 1 and 28")
    
    # For org tier, target_id should match org_id
    if allocation.tier == 'org' and allocation.target_id != org_id:
        raise HTTPException(
            status_code=400, 
            detail="For org tier, target_id must match organization ID"
        )
    
    try:
        await token_metering.set_allocation(
            db, 
            org_id, 
            allocation.tier, 
            allocation.target_id, 
            allocation.monthly_limit,
            allocation.reset_day
        )
        
        return {
            "message": f"Successfully set {allocation.tier} allocation",
            "allocation": allocation.dict()
        }
        
    except Exception as e:
        logger.error(f"Failed to set allocation for org {org_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to set allocation")


@router.post("/enforce")
async def enforce_token_limit(
    request: Request,
    estimated_tokens: int,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: Dict = Depends(get_current_user)
):
    """Check if a request would exceed token limits before starting.
    
    This is meant to be called by other services before making LLM requests.
    Returns 200 if OK to proceed, 402 if would exceed limits.
    """
    
    if estimated_tokens < 0:
        raise HTTPException(status_code=400, detail="Estimated tokens cannot be negative")
    
    org_id = get_org_id(request)
    user_id = get_user_id()
    
    try:
        # This will raise HTTPException 402 if limits would be exceeded
        await token_metering.enforce_limit(db, org_id, user_id, estimated_tokens)
        
        return {
            "allowed": True,
            "message": "Request is within token limits"
        }
        
    except HTTPException:
        # Re-raise 402 from enforce_limit
        raise
    except Exception as e:
        logger.error(f"Failed to check token limits for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to check token limits")


@router.post("/record")
async def record_token_usage(
    request: Request,
    model: str,
    input_tokens: int,
    output_tokens: int,
    agent_id: Optional[str] = None,
    endpoint: Optional[str] = None,
    cost_usd: float = 0.0,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: Dict = Depends(get_current_user)
):
    """Record token usage after an LLM request.
    
    This is meant to be called by other services after making LLM requests.
    Updates allocation counters and logs usage for auditing.
    """
    
    # Validate inputs
    if not model:
        raise HTTPException(status_code=400, detail="Model name is required")
        
    if input_tokens < 0 or output_tokens < 0:
        raise HTTPException(status_code=400, detail="Token counts cannot be negative")
        
    if cost_usd < 0:
        raise HTTPException(status_code=400, detail="Cost cannot be negative")
    
    org_id = get_org_id(request)
    user_id = get_user_id()
    
    try:
        await token_metering.record_usage(
            db, 
            org_id, 
            user_id, 
            model, 
            input_tokens, 
            output_tokens,
            agent_id,
            endpoint,
            cost_usd
        )
        
        total_tokens = input_tokens + output_tokens
        
        return {
            "recorded": True,
            "total_tokens": total_tokens,
            "message": f"Recorded {total_tokens} tokens for {model}"
        }
        
    except Exception as e:
        logger.error(f"Failed to record usage for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to record token usage")