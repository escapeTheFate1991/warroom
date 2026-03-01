"""Settings API — manage app configuration and API keys."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.leadgen_db import get_leadgen_db
from app.models.settings import Setting, SettingsBase

logger = logging.getLogger(__name__)
router = APIRouter()


# --- Schemas ---

class SettingCreate(BaseModel):
    key: str
    value: str
    category: str = "general"
    description: Optional[str] = None
    is_secret: bool = False


class SettingUpdate(BaseModel):
    value: str


class SettingResponse(BaseModel):
    key: str
    value: str
    category: str
    description: Optional[str]
    is_secret: bool


# Default settings definitions
DEFAULT_SETTINGS = [
    {
        "key": "google_maps_api_key",
        "value": "",
        "category": "api_keys",
        "description": "Google Maps / Places API key for business search",
        "is_secret": True,
    },
    {
        "key": "serp_api_key",
        "value": "",
        "category": "api_keys",
        "description": "SerpAPI key for enhanced search results",
        "is_secret": True,
    },
    {
        "key": "openai_api_key",
        "value": "",
        "category": "api_keys",
        "description": "OpenAI API key for AI-powered features",
        "is_secret": True,
    },
    {
        "key": "company_name",
        "value": "yieldlabs",
        "category": "general",
        "description": "Your company/brand name",
        "is_secret": False,
    },
    {
        "key": "your_name",
        "value": "",
        "category": "general",
        "description": "Your name (used in call scripts and email templates)",
        "is_secret": False,
    },
    {
        "key": "your_phone",
        "value": "",
        "category": "general",
        "description": "Your phone number (used in email signatures)",
        "is_secret": False,
    },
    # ── Social OAuth Credentials ──
    {
        "key": "meta_app_id",
        "value": "",
        "category": "api_keys",
        "description": "Meta (Facebook/Instagram/Threads) App ID",
        "is_secret": False,
    },
    {
        "key": "meta_app_secret",
        "value": "",
        "category": "api_keys",
        "description": "Meta App Secret",
        "is_secret": True,
    },
    {
        "key": "x_client_id",
        "value": "",
        "category": "api_keys",
        "description": "X (Twitter) OAuth 2.0 Client ID",
        "is_secret": False,
    },
    {
        "key": "x_client_secret",
        "value": "",
        "category": "api_keys",
        "description": "X (Twitter) OAuth 2.0 Client Secret",
        "is_secret": True,
    },
    {
        "key": "tiktok_client_key",
        "value": "",
        "category": "api_keys",
        "description": "TikTok Login Kit Client Key",
        "is_secret": False,
    },
    {
        "key": "tiktok_client_secret",
        "value": "",
        "category": "api_keys",
        "description": "TikTok Login Kit Client Secret",
        "is_secret": True,
    },
    {
        "key": "google_oauth_client_id",
        "value": "",
        "category": "api_keys",
        "description": "Google OAuth Client ID (for YouTube)",
        "is_secret": False,
    },
    {
        "key": "google_oauth_client_secret",
        "value": "",
        "category": "api_keys",
        "description": "Google OAuth Client Secret (for YouTube)",
        "is_secret": True,
    },
    {
        "key": "default_search_location",
        "value": "",
        "category": "leadgen",
        "description": "Default location for lead generation searches",
        "is_secret": False,
    },
    {
        "key": "max_search_results",
        "value": "60",
        "category": "leadgen",
        "description": "Maximum results per search (10-100)",
        "is_secret": False,
    },
    {
        "key": "auto_enrich",
        "value": "true",
        "category": "leadgen",
        "description": "Automatically enrich leads after search",
        "is_secret": False,
    },
]


async def init_settings_table(engine):
    """Create settings table and seed defaults, then load secrets into env."""
    import os

    async with engine.begin() as conn:
        await conn.run_sync(SettingsBase.metadata.create_all)

    # Seed defaults if table is empty
    from app.db.leadgen_db import leadgen_session
    async with leadgen_session() as db:
        result = await db.execute(select(Setting))
        if not result.scalars().first():
            for s in DEFAULT_SETTINGS:
                db.add(Setting(**s))
            await db.commit()
            logger.info("Seeded %d default settings", len(DEFAULT_SETTINGS))

        # Load API keys from DB into environment so services can use them
        api_key_settings = await db.execute(
            select(Setting).where(Setting.category == "api_keys")
        )
        env_map = {
            "google_maps_api_key": "GOOGLE_MAPS_API_KEY",
            "serp_api_key": "SERP_API_KEY",
            "openai_api_key": "OPENAI_API_KEY",
        }
        for setting in api_key_settings.scalars().all():
            env_name = env_map.get(setting.key)
            if env_name and setting.value:
                os.environ[env_name] = setting.value
                logger.info("Loaded %s from DB into environment", env_name)


def _mask_value(value: str) -> str:
    """Mask a secret value, showing only last 4 chars."""
    if not value or len(value) <= 4:
        return "••••" if value else ""
    return "••••••••" + value[-4:]


# --- Endpoints ---

@router.get("")
async def list_settings(
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_leadgen_db),
):
    """List all settings, optionally filtered by category."""
    query = select(Setting)
    if category:
        query = query.where(Setting.category == category)
    query = query.order_by(Setting.category, Setting.key)

    result = await db.execute(query)
    settings = result.scalars().all()

    return [
        SettingResponse(
            key=s.key,
            value=_mask_value(s.value) if s.is_secret else s.value,
            category=s.category,
            description=s.description,
            is_secret=bool(s.is_secret),
        )
        for s in settings
    ]


@router.get("/{key}")
async def get_setting(key: str, db: AsyncSession = Depends(get_leadgen_db)):
    """Get a single setting by key."""
    result = await db.execute(select(Setting).where(Setting.key == key))
    setting = result.scalars().first()
    if not setting:
        raise HTTPException(status_code=404, detail=f"Setting '{key}' not found")

    return SettingResponse(
        key=setting.key,
        value=_mask_value(setting.value) if setting.is_secret else setting.value,
        category=setting.category,
        description=setting.description,
        is_secret=bool(setting.is_secret),
    )


@router.put("/{key}")
async def update_setting(
    key: str,
    body: SettingUpdate,
    db: AsyncSession = Depends(get_leadgen_db),
):
    """Update a setting value."""
    result = await db.execute(select(Setting).where(Setting.key == key))
    setting = result.scalars().first()

    if not setting:
        # Create it if it doesn't exist
        setting = Setting(key=key, value=body.value, category="general", is_secret=False)
        db.add(setting)
    else:
        setting.value = body.value

    await db.commit()
    await db.refresh(setting)

    # If this is the Google API key, also set it in the environment for the leadgen service
    if key == "google_maps_api_key":
        import os
        os.environ["GOOGLE_MAPS_API_KEY"] = body.value
        logger.info("Updated GOOGLE_MAPS_API_KEY in environment")

    return SettingResponse(
        key=setting.key,
        value=_mask_value(setting.value) if setting.is_secret else setting.value,
        category=setting.category,
        description=setting.description,
        is_secret=bool(setting.is_secret),
    )


@router.post("")
async def create_setting(
    body: SettingCreate,
    db: AsyncSession = Depends(get_leadgen_db),
):
    """Create a new setting."""
    # Check if key already exists
    result = await db.execute(select(Setting).where(Setting.key == body.key))
    if result.scalars().first():
        raise HTTPException(status_code=409, detail=f"Setting '{body.key}' already exists. Use PUT to update.")

    setting = Setting(
        key=body.key,
        value=body.value,
        category=body.category,
        description=body.description,
        is_secret=1 if body.is_secret else 0,
    )
    db.add(setting)
    await db.commit()
    await db.refresh(setting)

    return SettingResponse(
        key=setting.key,
        value=_mask_value(setting.value) if setting.is_secret else setting.value,
        category=setting.category,
        description=setting.description,
        is_secret=bool(setting.is_secret),
    )


@router.delete("/{key}")
async def delete_setting(key: str, db: AsyncSession = Depends(get_leadgen_db)):
    """Delete a setting."""
    result = await db.execute(select(Setting).where(Setting.key == key))
    setting = result.scalars().first()
    if not setting:
        raise HTTPException(status_code=404, detail=f"Setting '{key}' not found")

    await db.execute(delete(Setting).where(Setting.key == key))
    await db.commit()
    return {"status": "deleted", "key": key}
