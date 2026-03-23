"""Base publisher with shared helpers for token refresh and account lookup."""

import logging
from typing import Dict, Optional, Tuple

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def get_account_credentials(
    db: AsyncSession, platform: str, org_id: int
) -> Dict[str, Optional[str]]:
    """Get credentials from crm.social_accounts (single source of truth).

    Returns dict with keys: id, access_token, refresh_token, username.
    Raises ValueError if no connected account found.
    """
    result = await db.execute(
        text(
            "SELECT id, access_token, refresh_token, username "
            "FROM crm.social_accounts "
            "WHERE platform = :platform AND status = 'connected' AND org_id = :org_id "
            "ORDER BY connected_at DESC LIMIT 1"
        ),
        {"platform": platform, "org_id": org_id},
    )
    row = result.fetchone()
    if not row:
        raise ValueError(f"No connected {platform} account for org {org_id}")
    return {
        "id": row[0],
        "access_token": row[1],
        "refresh_token": row[2],
        "username": row[3],
    }


async def update_account_token(
    db: AsyncSession, account_id: int, access_token: str, refresh_token: Optional[str] = None
):
    """Persist refreshed tokens back to crm.social_accounts."""
    if refresh_token:
        await db.execute(
            text(
                "UPDATE crm.social_accounts "
                "SET access_token = :token, refresh_token = :refresh, status = 'connected', last_synced = NOW() "
                "WHERE id = :id"
            ),
            {"token": access_token, "refresh": refresh_token, "id": account_id},
        )
    else:
        await db.execute(
            text(
                "UPDATE crm.social_accounts "
                "SET access_token = :token, status = 'connected', last_synced = NOW() "
                "WHERE id = :id"
            ),
            {"token": access_token, "id": account_id},
        )
    await db.commit()


async def get_setting(db: AsyncSession, key: str) -> Optional[str]:
    """Get a setting value (API keys, secrets) from the settings table."""
    from app.api.settings import Setting
    from app.db.leadgen_db import leadgen_session

    async with leadgen_session() as ldb:
        from sqlalchemy import select
        result = await ldb.execute(select(Setting).where(Setting.key == key))
        setting = result.scalar_one_or_none()
        return setting.value if setting and setting.value else None
