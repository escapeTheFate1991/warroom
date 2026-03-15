"""Token metering service for War Room.

3-tier token tracking and enforcement:
- Organization level (org)
- Department level (dept)  
- User level (user)

Each tier has allocation limits and usage tracking with soft/hard limits.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


@dataclass
class TokenBudgetStatus:
    """Token budget status for a user across all tiers."""
    org_remaining: int
    dept_remaining: int  
    user_remaining: int
    org_limit: int
    dept_limit: int
    user_limit: int
    soft_limit_reached: bool
    hard_limit_reached: bool
    warning_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass 
class UsageSummary:
    """Usage summary for reporting."""
    total_tokens: int
    total_cost: float
    period_days: int
    breakdown_by_model: Dict[str, int]
    breakdown_by_user: Dict[str, int]
    breakdown_by_agent: Dict[str, int]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


async def check_token_budget(db: AsyncSession, org_id: int, user_id: int) -> TokenBudgetStatus:
    """Check remaining token budget at all tiers."""
    
    # Get allocations for org, dept (using user's dept), and user
    # For MVP, assume dept_id = user_id (no dept table yet)
    dept_id = user_id  # TODO: Replace with actual dept lookup when dept tables exist
    
    allocations_query = text("""
        SELECT tier, target_id, monthly_limit, used_this_month, reset_day, last_reset
        FROM public.token_allocations 
        WHERE org_id = :org_id 
        AND ((tier = 'org' AND target_id = :org_id)
             OR (tier = 'dept' AND target_id = :dept_id) 
             OR (tier = 'user' AND target_id = :user_id))
    """)
    
    result = await db.execute(allocations_query, {
        "org_id": org_id,
        "dept_id": dept_id,
        "user_id": user_id
    })
    allocations = result.fetchall()
    
    # Parse allocations by tier
    limits = {"org": 0, "dept": 0, "user": 0}
    used = {"org": 0, "dept": 0, "user": 0}
    
    for row in allocations:
        tier, target_id, monthly_limit, used_this_month, reset_day, last_reset = row
        
        # Check if we need to reset monthly usage
        now = datetime.now()
        should_reset = False
        
        if last_reset:
            # Reset if we've passed the reset day of this month
            reset_date = datetime(now.year, now.month, reset_day)
            if now.date() >= reset_date.date() and last_reset.date() < reset_date.date():
                should_reset = True
            # Or if we're in a new month and haven't reset yet
            elif now.month != last_reset.month or now.year != last_reset.year:
                should_reset = True
        else:
            should_reset = True  # First time, reset to 0
            
        if should_reset:
            reset_query = text("""
                UPDATE public.token_allocations 
                SET used_this_month = 0, last_reset = NOW()
                WHERE org_id = :org_id AND tier = :tier AND target_id = :target_id
            """)
            await db.execute(reset_query, {
                "org_id": org_id,
                "tier": tier, 
                "target_id": target_id
            })
            used_this_month = 0
        
        limits[tier] = monthly_limit
        used[tier] = used_this_month
    
    # Calculate remaining tokens (0 = unlimited)
    def remaining(tier):
        if limits[tier] == 0:
            return float('inf')  # Unlimited
        return max(0, limits[tier] - used[tier])
    
    org_remaining = remaining("org")
    dept_remaining = remaining("dept") 
    user_remaining = remaining("user")
    
    # Find the most restrictive limit
    finite_remaining = [r for r in [org_remaining, dept_remaining, user_remaining] if r != float('inf')]
    effective_remaining = min(finite_remaining) if finite_remaining else float('inf')
    
    # Check soft/hard limits
    soft_limit_reached = False
    hard_limit_reached = False
    warning_message = None
    
    if effective_remaining != float('inf'):
        # Find which tier is most restrictive for warning message
        restrictive_tier = None
        if org_remaining == effective_remaining:
            restrictive_tier = "organization"
        elif dept_remaining == effective_remaining:
            restrictive_tier = "department"
        elif user_remaining == effective_remaining:
            restrictive_tier = "user"
        
        # Check 80% threshold for soft limit
        for tier, limit in limits.items():
            if limit > 0 and used[tier] >= limit * 0.8:
                soft_limit_reached = True
                if not warning_message:
                    pct = int(used[tier] / limit * 100)
                    warning_message = f"Token usage at {pct}% of {tier} limit"
        
        # Hard limit at 100%
        if effective_remaining <= 0:
            hard_limit_reached = True
            warning_message = f"Token limit exceeded at {restrictive_tier} level"
    
    return TokenBudgetStatus(
        org_remaining=int(org_remaining) if org_remaining != float('inf') else 0,
        dept_remaining=int(dept_remaining) if dept_remaining != float('inf') else 0,
        user_remaining=int(user_remaining) if user_remaining != float('inf') else 0,
        org_limit=limits["org"],
        dept_limit=limits["dept"], 
        user_limit=limits["user"],
        soft_limit_reached=soft_limit_reached,
        hard_limit_reached=hard_limit_reached,
        warning_message=warning_message
    )


async def enforce_limit(db: AsyncSession, org_id: int, user_id: int, estimated_tokens: int) -> None:
    """Enforce token limits before starting a request.
    
    Raises HTTPException 402 if the request would exceed hard limits.
    Never cuts off mid-task - only enforce before new requests.
    """
    budget = await check_token_budget(db, org_id, user_id)
    
    if budget.hard_limit_reached:
        raise HTTPException(
            status_code=402,
            detail=f"Token limit exceeded: {budget.warning_message}. Please upgrade your plan or contact support."
        )
    
    # Check if estimated tokens would exceed remaining budget
    finite_remaining = [
        r for r in [budget.org_remaining, budget.dept_remaining, budget.user_remaining] 
        if r > 0
    ]
    
    if finite_remaining:
        min_remaining = min(finite_remaining)
        if estimated_tokens > min_remaining:
            raise HTTPException(
                status_code=402,
                detail=f"Request would exceed token limit. Estimated: {estimated_tokens}, Remaining: {min_remaining}"
            )


async def record_usage(
    db: AsyncSession, 
    org_id: int, 
    user_id: int, 
    model: str, 
    input_tokens: int, 
    output_tokens: int,
    agent_id: Optional[str] = None,
    endpoint: Optional[str] = None,
    cost_usd: float = 0.0
) -> None:
    """Record token usage and update allocation counters."""
    
    total_tokens = input_tokens + output_tokens
    
    # Log the usage (append-only audit trail)
    log_query = text("""
        INSERT INTO public.token_usage_log 
        (org_id, user_id, agent_id, model, input_tokens, output_tokens, total_tokens, cost_usd, endpoint)
        VALUES (:org_id, :user_id, :agent_id, :model, :input_tokens, :output_tokens, :total_tokens, :cost_usd, :endpoint)
    """)
    
    await db.execute(log_query, {
        "org_id": org_id,
        "user_id": user_id, 
        "agent_id": agent_id,
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "cost_usd": cost_usd,
        "endpoint": endpoint
    })
    
    # Update allocation counters for all applicable tiers
    dept_id = user_id  # TODO: Replace with actual dept lookup
    
    update_allocations_query = text("""
        UPDATE public.token_allocations 
        SET used_this_month = used_this_month + :total_tokens
        WHERE org_id = :org_id 
        AND ((tier = 'org' AND target_id = :org_id)
             OR (tier = 'dept' AND target_id = :dept_id)
             OR (tier = 'user' AND target_id = :user_id))
    """)
    
    await db.execute(update_allocations_query, {
        "total_tokens": total_tokens,
        "org_id": org_id,
        "dept_id": dept_id,
        "user_id": user_id
    })
    
    await db.commit()
    
    logger.info(
        f"Recorded {total_tokens} tokens for user {user_id} in org {org_id} using {model}"
    )


async def get_usage_summary(
    db: AsyncSession, 
    org_id: int, 
    user_id: Optional[int] = None, 
    days: int = 30
) -> UsageSummary:
    """Get usage summary for reporting."""
    
    since = datetime.now() - timedelta(days=days)
    
    base_query = """
        SELECT 
            SUM(total_tokens) as total_tokens,
            SUM(cost_usd) as total_cost
        FROM public.token_usage_log 
        WHERE org_id = :org_id 
        AND created_at >= :since
    """
    
    params = {"org_id": org_id, "since": since}
    
    if user_id is not None:
        base_query += " AND user_id = :user_id"
        params["user_id"] = user_id
    
    # Get totals
    totals_query = text(base_query)
    totals_result = await db.execute(totals_query, params)
    totals_row = totals_result.fetchone()
    
    total_tokens = totals_row[0] if totals_row and totals_row[0] else 0
    total_cost = float(totals_row[1]) if totals_row and totals_row[1] else 0.0
    
    # Breakdown by model
    model_query = text("SELECT model, SUM(total_tokens) FROM public.token_usage_log WHERE org_id = :org_id AND created_at >= :since" + (" AND user_id = :user_id" if user_id else "") + " GROUP BY model")
    model_result = await db.execute(model_query, params)
    breakdown_by_model = {row[0]: row[1] for row in model_result.fetchall() if row[0]}
    
    # Breakdown by user (only for org-wide queries)
    breakdown_by_user = {}
    if user_id is None:
        user_query = text("SELECT user_id, SUM(total_tokens) FROM public.token_usage_log WHERE org_id = :org_id AND created_at >= :since GROUP BY user_id")
        user_result = await db.execute(user_query, params)
        breakdown_by_user = {str(row[0]): row[1] for row in user_result.fetchall() if row[0]}
    
    # Breakdown by agent
    agent_query = text("SELECT agent_id, SUM(total_tokens) FROM public.token_usage_log WHERE org_id = :org_id AND created_at >= :since AND agent_id IS NOT NULL" + (" AND user_id = :user_id" if user_id else "") + " GROUP BY agent_id")
    agent_result = await db.execute(agent_query, params)
    breakdown_by_agent = {row[0]: row[1] for row in agent_result.fetchall() if row[0]}
    
    return UsageSummary(
        total_tokens=total_tokens,
        total_cost=total_cost,
        period_days=days,
        breakdown_by_model=breakdown_by_model,
        breakdown_by_user=breakdown_by_user,
        breakdown_by_agent=breakdown_by_agent
    )


async def set_allocation(
    db: AsyncSession,
    org_id: int,
    tier: str,
    target_id: int,
    monthly_limit: int,
    reset_day: int = 1
) -> None:
    """Set or update token allocation for a tier."""
    
    if tier not in ['org', 'dept', 'user']:
        raise ValueError("Tier must be 'org', 'dept', or 'user'")
    
    upsert_query = text("""
        INSERT INTO public.token_allocations 
        (org_id, tier, target_id, monthly_limit, reset_day, used_this_month, last_reset)
        VALUES (:org_id, :tier, :target_id, :monthly_limit, :reset_day, 0, NOW())
        ON CONFLICT (org_id, tier, target_id)
        DO UPDATE SET 
            monthly_limit = EXCLUDED.monthly_limit,
            reset_day = EXCLUDED.reset_day,
            updated_at = NOW()
    """)
    
    await db.execute(upsert_query, {
        "org_id": org_id,
        "tier": tier,
        "target_id": target_id, 
        "monthly_limit": monthly_limit,
        "reset_day": reset_day
    })
    
    await db.commit()
    
    logger.info(f"Set {tier} allocation for target {target_id} in org {org_id}: {monthly_limit} tokens/month")


async def init_token_metering_tables(engine) -> None:
    """Initialize token metering tables on startup."""
    from pathlib import Path
    
    # Load and execute the migration SQL
    migration_path = Path(__file__).parent.parent / "db" / "token_metering_migration.sql"
    
    try:
        with open(migration_path, 'r') as f:
            migration_sql = f.read()
        
        async with engine.begin() as conn:
            raw = await conn.get_raw_connection()
            await raw.driver_connection.execute(migration_sql)
            
        logger.info("Token metering tables initialized")
        
    except Exception as e:
        logger.error(f"Failed to initialize token metering tables: {e}")
        raise