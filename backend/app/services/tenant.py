"""Multi-tenant services — visibility, org-scoped queries, and RBAC helpers.

This is the central place for all tenant isolation logic. Every endpoint
that touches org-scoped data should use these helpers instead of
hand-rolling WHERE clauses.

Hierarchy levels:
    admin    = 40  (sees everything in org)
    director = 30  (sees managers + employees in their tree)
    manager  = 20  (sees employees reporting to them)
    employee = 10  (sees only their own data)
"""
import logging
from typing import Optional

from fastapi import Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


# ── Request helpers ──────────────────────────────────────────────────

def get_org_id(request: Request) -> Optional[int]:
    """Get org_id from request state. Returns None for superadmins without org."""
    return getattr(request.state, "org_id", None)


def get_user_id(request: Request) -> int:
    """Get user_id from request state."""
    return getattr(request.state, "user_id", None)


def is_superadmin(request: Request) -> bool:
    """Check if current user is a platform superadmin."""
    return getattr(request.state, "is_superadmin", False)


# ── Org-scoped query builder ────────────────────────────────────────

def org_filter(
    table_alias: str = "",
    param_name: str = "org_id",
) -> str:
    """Return a SQL WHERE fragment for org isolation.

    Usage:
        query = f"SELECT * FROM deals WHERE {org_filter()} AND status = true"
        result = await db.execute(text(query), {"org_id": org_id})

    With table alias:
        query = f"SELECT d.* FROM deals d WHERE {org_filter('d')} AND d.status = true"
    """
    prefix = f"{table_alias}." if table_alias else ""
    return f"{prefix}org_id = :{param_name}"


# ── Visibility service ──────────────────────────────────────────────

async def get_visible_user_ids(
    db: AsyncSession,
    user_id: int,
    org_id: int,
) -> list[int]:
    """Get list of user IDs this user can see based on RBAC hierarchy.

    - admin (40): all users in org
    - director (30): self + managers reporting to them + employees under those managers
    - manager (20): self + employees reporting directly to them
    - employee (10): self only

    Returns list of user IDs whose data is visible to the requesting user.
    """
    # Get current user's role hierarchy level
    result = await db.execute(
        text("""
            SELECT u.id, r.hierarchy_level, r.name as role_name
            FROM users u
            JOIN roles r ON u.role_id = r.id
            WHERE u.id = :user_id AND u.org_id = :org_id
        """),
        {"user_id": user_id, "org_id": org_id},
    )
    row = result.mappings().first()

    if not row:
        return [user_id]  # Fallback: can only see self

    level = row["hierarchy_level"] or 10

    # Admin: sees everyone in org
    if level >= 40:
        result = await db.execute(
            text("SELECT id FROM users WHERE org_id = :org_id"),
            {"org_id": org_id},
        )
        return [r["id"] for r in result.mappings().all()]

    # Director/Manager: sees self + direct reports (recursive)
    if level >= 20:
        # Recursive CTE: find all users in the reporting tree below this user
        result = await db.execute(
            text("""
                WITH RECURSIVE subordinates AS (
                    -- Base: direct reports
                    SELECT id FROM users
                    WHERE reports_to = :user_id AND org_id = :org_id
                    
                    UNION ALL
                    
                    -- Recursive: their reports
                    SELECT u.id FROM users u
                    INNER JOIN subordinates s ON u.reports_to = s.id
                    WHERE u.org_id = :org_id
                )
                SELECT id FROM subordinates
            """),
            {"user_id": user_id, "org_id": org_id},
        )
        subordinate_ids = [r["id"] for r in result.mappings().all()]
        return [user_id] + subordinate_ids

    # Employee: self only
    return [user_id]


async def can_see_user(
    db: AsyncSession,
    viewer_id: int,
    target_id: int,
    org_id: int,
) -> bool:
    """Check if viewer can see target user's data."""
    visible = await get_visible_user_ids(db, viewer_id, org_id)
    return target_id in visible


def visibility_filter(
    visible_user_ids: list[int],
    owner_column: str = "user_id",
    table_alias: str = "",
) -> str:
    """Return SQL fragment filtering by visible user IDs.

    Usage:
        visible = await get_visible_user_ids(db, user_id, org_id)
        vf = visibility_filter(visible)
        query = f"SELECT * FROM deals WHERE {org_filter()} AND {vf}"

    For admin users this returns a broad filter; for employees it's tight.
    """
    prefix = f"{table_alias}." if table_alias else ""
    if not visible_user_ids:
        return "FALSE"
    ids_str = ", ".join(str(int(uid)) for uid in visible_user_ids)
    return f"{prefix}{owner_column} IN ({ids_str})"


# ── Convenience: combined org + visibility filter ────────────────────

async def build_data_filter(
    db: AsyncSession,
    request: Request,
    owner_column: str = "user_id",
    table_alias: str = "",
) -> tuple[str, dict]:
    """Build a complete WHERE clause for org isolation + RBAC visibility.

    Returns (sql_fragment, params) ready to inject into a query.

    Usage:
        where_clause, params = await build_data_filter(db, request)
        query = f"SELECT * FROM deals WHERE {where_clause}"
        result = await db.execute(text(query), params)
    """
    org_id = get_org_id(request)
    user_id = get_user_id(request)
    prefix = f"{table_alias}." if table_alias else ""

    if not org_id:
        # Superadmin without org — sees everything (platform-level)
        if is_superadmin(request):
            return "TRUE", {}
        return "FALSE", {}

    # Get visible user IDs
    visible = await get_visible_user_ids(db, user_id, org_id)

    # Combine org + visibility
    of = f"{prefix}org_id = :_filter_org_id"
    vf = visibility_filter(visible, owner_column, table_alias)

    return f"({of} AND {vf})", {"_filter_org_id": org_id}
