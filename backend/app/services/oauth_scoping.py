"""OAuth Token Scoping Service.

Manages visibility control for OAuth tokens and social accounts:
- Private: Only the connecting user's agent can use it
- Shared dept: Users in same department can access
- Shared org: Any user in the org can access

Integrates with tenant.py for department hierarchy (reports_to chain).
"""
import logging
from typing import List, Optional, Dict, Any

from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.crm.social import SocialAccount

logger = logging.getLogger(__name__)


async def can_access_token(
    db: AsyncSession,
    user_id: int,
    org_id: int,
    account_id: int,
) -> bool:
    """Check if user can access the specified social account/token.
    
    Args:
        db: Database session
        user_id: Requesting user ID
        org_id: Organization ID
        account_id: Social account ID to check
        
    Returns:
        True if user can access the token, False otherwise
    """
    try:
        # Get the account with its visibility settings
        result = await db.execute(
            select(SocialAccount).where(
                SocialAccount.id == account_id,
                SocialAccount.org_id == org_id,
                SocialAccount.status == "connected"
            )
        )
        account = result.scalar_one_or_none()
        
        if not account:
            return False
            
        # Private: only the account owner can access
        if account.visibility_type == "private":
            return account.user_id == user_id
            
        # Shared org: any user in the org can access
        if account.visibility_type == "shared_org":
            return True  # Already filtered by org_id above
            
        # Shared dept: users in same department can access
        if account.visibility_type == "shared_dept":
            return await _can_access_dept_shared(db, user_id, account.user_id, org_id)
            
        return False
    except Exception as e:
        logger.error("Failed to check token access: %s", e)
        return False


async def _can_access_dept_shared(
    db: AsyncSession,
    requesting_user_id: int,
    account_owner_id: int,
    org_id: int,
) -> bool:
    """Check if requesting user is in same department as account owner.
    
    Uses the reports_to chain to determine department membership.
    Users are in the same department if they share a common manager
    within the reporting hierarchy.
    """
    try:
        # Get both users' reporting chains up the hierarchy
        result = await db.execute(text("""
            WITH RECURSIVE 
            requester_chain AS (
                SELECT id, reports_to, 0 as level
                FROM crm.users 
                WHERE id = :requester_id AND org_id = :org_id
                
                UNION ALL
                
                SELECT u.id, u.reports_to, rc.level + 1
                FROM crm.users u
                INNER JOIN requester_chain rc ON u.id = rc.reports_to
                WHERE u.org_id = :org_id AND rc.level < 10
            ),
            owner_chain AS (
                SELECT id, reports_to, 0 as level
                FROM crm.users 
                WHERE id = :owner_id AND org_id = :org_id
                
                UNION ALL
                
                SELECT u.id, u.reports_to, oc.level + 1
                FROM crm.users u
                INNER JOIN owner_chain oc ON u.id = oc.reports_to
                WHERE u.org_id = :org_id AND oc.level < 10
            )
            SELECT COUNT(*) > 0 as same_dept
            FROM requester_chain rc
            INNER JOIN owner_chain oc ON rc.id = oc.id
        """), {
            "requester_id": requesting_user_id,
            "owner_id": account_owner_id,
            "org_id": org_id
        })
        
        row = result.fetchone()
        return row[0] if row else False
    except Exception as e:
        logger.error("Failed to check department access: %s", e)
        return False


async def get_accessible_accounts(
    db: AsyncSession,
    user_id: int,
    org_id: int,
    platform: Optional[str] = None,
) -> List[SocialAccount]:
    """Get all social accounts the user can access based on visibility rules.
    
    Args:
        db: Database session
        user_id: Requesting user ID
        org_id: Organization ID
        platform: Optional platform filter (instagram, facebook, etc.)
        
    Returns:
        List of accessible social accounts
    """
    try:
        # Base query for org and status
        where_conditions = [
            "s.org_id = :org_id",
            "s.status = 'connected'"
        ]
        params = {"org_id": org_id, "user_id": user_id}
        
        if platform:
            where_conditions.append("s.platform = :platform")
            params["platform"] = platform
            
        # Build visibility filter
        # This is complex because we need to handle dept sharing with reports_to chain
        visibility_query = f"""
            SELECT DISTINCT s.*
            FROM crm.social_accounts s
            WHERE {' AND '.join(where_conditions)}
              AND (
                -- Private: user owns the account
                (s.visibility_type = 'private' AND s.user_id = :user_id)
                OR
                -- Shared org: any user in org can access
                (s.visibility_type = 'shared_org')
                OR
                -- Shared dept: same department (recursive reports_to check)
                (s.visibility_type = 'shared_dept' AND EXISTS (
                    WITH RECURSIVE 
                    requester_chain AS (
                        SELECT id, reports_to, 0 as level
                        FROM crm.users 
                        WHERE id = :user_id AND org_id = :org_id
                        
                        UNION ALL
                        
                        SELECT u.id, u.reports_to, rc.level + 1
                        FROM crm.users u
                        INNER JOIN requester_chain rc ON u.id = rc.reports_to
                        WHERE u.org_id = :org_id AND rc.level < 10
                    ),
                    owner_chain AS (
                        SELECT id, reports_to, 0 as level
                        FROM crm.users 
                        WHERE id = s.user_id AND org_id = :org_id
                        
                        UNION ALL
                        
                        SELECT u.id, u.reports_to, oc.level + 1
                        FROM crm.users u
                        INNER JOIN owner_chain oc ON u.id = oc.reports_to
                        WHERE u.org_id = :org_id AND oc.level < 10
                    )
                    SELECT 1
                    FROM requester_chain rc
                    INNER JOIN owner_chain oc ON rc.id = oc.id
                    LIMIT 1
                ))
              )
            ORDER BY s.connected_at DESC
        """
        
        result = await db.execute(text(visibility_query), params)
        rows = result.fetchall()
        
        # Convert to SocialAccount objects
        accounts = []
        for row in rows:
            account = SocialAccount()
            for key, value in row._mapping.items():
                setattr(account, key, value)
            accounts.append(account)
            
        return accounts
    except Exception as e:
        logger.error("Failed to get accessible accounts: %s", e)
        return []


async def set_visibility(
    db: AsyncSession,
    account_id: int,
    user_id: int,
    org_id: int,
    visibility_type: str,
) -> bool:
    """Set visibility for a social account.
    
    Only the account owner or org admin can change visibility.
    
    Args:
        db: Database session
        account_id: Social account ID to modify
        user_id: User making the change
        org_id: Organization ID
        visibility_type: 'private', 'shared_dept', or 'shared_org'
        
    Returns:
        True if visibility was updated, False if not authorized or failed
    """
    if visibility_type not in ("private", "shared_dept", "shared_org"):
        logger.error("Invalid visibility_type: %s", visibility_type)
        return False
        
    try:
        # Check if user can modify this account
        result = await db.execute(
            select(SocialAccount).where(
                SocialAccount.id == account_id,
                SocialAccount.org_id == org_id
            )
        )
        account = result.scalar_one_or_none()
        
        if not account:
            logger.warning("Account not found: %s", account_id)
            return False
            
        # Check authorization: owner or admin can modify
        if not await _can_modify_account(db, user_id, account.user_id, org_id):
            logger.warning("User %s not authorized to modify account %s", user_id, account_id)
            return False
            
        # Update visibility
        await db.execute(
            update(SocialAccount)
            .where(SocialAccount.id == account_id)
            .values(
                visibility_type=visibility_type,
                shared_by_user_id=user_id if visibility_type != "private" else None
            )
        )
        await db.commit()
        
        logger.info("Updated account %s visibility to %s by user %s", account_id, visibility_type, user_id)
        return True
    except Exception as e:
        await db.rollback()
        logger.error("Failed to set visibility: %s", e)
        return False


async def _can_modify_account(
    db: AsyncSession,
    user_id: int,
    account_owner_id: int,
    org_id: int,
) -> bool:
    """Check if user can modify the account (owner or admin)."""
    # Account owner can always modify
    if user_id == account_owner_id:
        return True
        
    # Check if user is admin (hierarchy_level >= 40)
    try:
        result = await db.execute(text("""
            SELECT r.hierarchy_level
            FROM crm.users u
            JOIN crm.roles r ON u.role_id = r.id
            WHERE u.id = :user_id AND u.org_id = :org_id
        """), {"user_id": user_id, "org_id": org_id})
        
        row = result.fetchone()
        if row and row[0] and row[0] >= 40:
            return True
            
        return False
    except Exception as e:
        logger.error("Failed to check admin access: %s", e)
        return False


async def get_account_visibility_info(
    db: AsyncSession,
    account_id: int,
    org_id: int,
) -> Optional[Dict[str, Any]]:
    """Get visibility information for a social account.
    
    Returns dict with visibility_type, shared_by info, etc.
    """
    try:
        result = await db.execute(text("""
            SELECT 
                s.visibility_type,
                s.shared_by_user_id,
                s.user_id as owner_id,
                owner.name as owner_name,
                sharer.name as shared_by_name
            FROM crm.social_accounts s
            LEFT JOIN crm.users owner ON s.user_id = owner.id
            LEFT JOIN crm.users sharer ON s.shared_by_user_id = sharer.id
            WHERE s.id = :account_id AND s.org_id = :org_id
        """), {"account_id": account_id, "org_id": org_id})
        
        row = result.fetchone()
        if not row:
            return None
            
        return {
            "visibility_type": row[0],
            "shared_by_user_id": row[1],
            "owner_id": row[2],
            "owner_name": row[3],
            "shared_by_name": row[4],
        }
    except Exception as e:
        logger.error("Failed to get visibility info: %s", e)
        return None