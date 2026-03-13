"""Settings API — manage app configuration and API keys."""

import logging
import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.leadgen_db import get_leadgen_db
from app.models.settings import Setting, SettingsBase
from app.api.auth import get_current_user, require_superadmin
from app.models.crm.user import User

logger = logging.getLogger(__name__)
router = APIRouter()

LEGACY_SETTING_KEYS = {
    "openai_api_key": "openclaw_auth_token",
}

API_KEY_ENV_MAP = {
    "google_maps_api_key": "GOOGLE_MAPS_API_KEY",
    "serp_api_key": "SERP_API_KEY",
    "openclaw_auth_token": "OPENCLAW_AUTH_TOKEN",
    "google_ai_studio_api_key": "GOOGLE_AI_STUDIO_API_KEY",
}


def _normalize_setting_key(key: str) -> str:
    """Map legacy setting keys to their canonical key names."""
    return LEGACY_SETTING_KEYS.get(key, key)


def _sync_setting_env(key: str, value: str) -> None:
    """Load or clear a supported API key in the process environment."""
    env_name = API_KEY_ENV_MAP.get(_normalize_setting_key(key))
    if not env_name:
        return

    if value:
        os.environ[env_name] = value
        logger.info("Loaded %s from DB into environment", env_name)
    else:
        os.environ.pop(env_name, None)
        logger.info("Cleared %s from environment", env_name)


async def _migrate_legacy_ai_setting(db: AsyncSession) -> bool:
    """Rename the legacy AI key so existing DB-stored values keep working."""
    legacy_key = "openai_api_key"
    canonical_key = _normalize_setting_key(legacy_key)

    legacy_result = await db.execute(select(Setting).where(Setting.key == legacy_key))
    legacy_setting = legacy_result.scalar_one_or_none()
    if not legacy_setting:
        return False

    current_result = await db.execute(select(Setting).where(Setting.key == canonical_key))
    current_setting = current_result.scalar_one_or_none()

    if current_setting:
        if not current_setting.value and legacy_setting.value:
            current_setting.value = legacy_setting.value
        current_setting.category = "api_keys"
        current_setting.description = "OpenClaw auth token for AI-powered features"
        current_setting.is_secret = 1
        await db.delete(legacy_setting)
    else:
        legacy_setting.key = canonical_key
        legacy_setting.category = "api_keys"
        legacy_setting.description = "OpenClaw auth token for AI-powered features"
        legacy_setting.is_secret = 1

    logger.info("Migrated legacy setting %s to %s", legacy_key, canonical_key)
    return True


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
        "key": "openclaw_auth_token",
        "value": "",
        "category": "api_keys",
        "description": "OpenClaw auth token for AI-powered features",
        "is_secret": True,
    },
    {
        "key": "company_name",
        "value": "stuffnthings",
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
    {
        "key": "your_email",
        "value": "",
        "category": "general",
        "description": "Your email address (used in cold email signatures)",
        "is_secret": False,
    },
    {
        "key": "outreach_timing_alerts",
        "value": "enabled",
        "category": "general",
        "description": "Show cold outreach timing recommendations (enabled/disabled)",
        "is_secret": False,
    },
    # ── Business Details (for contracts, invoices, proposals) ──
    {
        "key": "business_legal_name",
        "value": "",
        "category": "business",
        "description": "Legal entity name (e.g., Stuff N Things LLC)",
        "is_secret": False,
    },
    {
        "key": "business_dba",
        "value": "",
        "category": "business",
        "description": "DBA / Trade name (if different from legal name)",
        "is_secret": False,
    },
    {
        "key": "business_address_line1",
        "value": "",
        "category": "business",
        "description": "Street address line 1",
        "is_secret": False,
    },
    {
        "key": "business_address_line2",
        "value": "",
        "category": "business",
        "description": "Street address line 2",
        "is_secret": False,
    },
    {
        "key": "business_city",
        "value": "",
        "category": "business",
        "description": "City",
        "is_secret": False,
    },
    {
        "key": "business_state",
        "value": "",
        "category": "business",
        "description": "State / Province",
        "is_secret": False,
    },
    {
        "key": "business_zip",
        "value": "",
        "category": "business",
        "description": "ZIP / Postal code",
        "is_secret": False,
    },
    {
        "key": "business_country",
        "value": "US",
        "category": "business",
        "description": "Country",
        "is_secret": False,
    },
    {
        "key": "business_phone",
        "value": "",
        "category": "business",
        "description": "Business phone number",
        "is_secret": False,
    },
    {
        "key": "business_email",
        "value": "",
        "category": "business",
        "description": "Primary business email",
        "is_secret": False,
    },
    {
        "key": "business_website",
        "value": "",
        "category": "business",
        "description": "Business website URL",
        "is_secret": False,
    },
    {
        "key": "business_ein",
        "value": "",
        "category": "business",
        "description": "EIN / Tax ID number",
        "is_secret": True,
    },
    {
        "key": "business_entity_type",
        "value": "",
        "category": "business",
        "description": "Entity type (LLC, Corp, Sole Prop, etc.)",
        "is_secret": False,
    },
    {
        "key": "business_state_of_formation",
        "value": "",
        "category": "business",
        "description": "State of formation / registration",
        "is_secret": False,
    },
    {
        "key": "business_logo_url",
        "value": "",
        "category": "business",
        "description": "URL to business logo (used in contracts/invoices)",
        "is_secret": False,
    },
    {
        "key": "business_authorized_signer",
        "value": "",
        "category": "business",
        "description": "Name of authorized contract signer",
        "is_secret": False,
    },
    {
        "key": "business_signer_title",
        "value": "",
        "category": "business",
        "description": "Title of authorized signer (e.g., Managing Member, CEO)",
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
        "description": "Meta (Facebook) App Secret",
        "is_secret": True,
    },
    {
        "key": "instagram_app_id",
        "value": "",
        "category": "api_keys",
        "description": "Instagram App ID (from Meta Dashboard → Instagram API settings)",
        "is_secret": False,
    },
    {
        "key": "instagram_app_secret",
        "value": "",
        "category": "api_keys",
        "description": "Instagram App Secret",
        "is_secret": True,
    },
    {
        "key": "threads_client_id",
        "value": "",
        "category": "api_keys",
        "description": "Threads Client ID (from Meta Dashboard → Threads API settings)",
        "is_secret": False,
    },
    {
        "key": "threads_client_secret",
        "value": "",
        "category": "api_keys",
        "description": "Threads Client Secret",
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
        "description": "Google OAuth Client ID (YouTube + Calendar)",
        "is_secret": False,
    },
    {
        "key": "google_oauth_client_secret",
        "value": "",
        "category": "api_keys",
        "description": "Google OAuth Client Secret (YouTube + Calendar)",
        "is_secret": True,
    },
    {
        "key": "google_ai_studio_api_key",
        "value": "",
        "category": "api_keys",
        "description": "Google AI Studio (Gemini) API key for AI generation",
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
    async with engine.begin() as conn:
        await conn.run_sync(SettingsBase.metadata.create_all)

    # Seed defaults — upsert so new settings are always added
    from app.db.leadgen_db import leadgen_session
    async with leadgen_session() as db:
        migrated = await _migrate_legacy_ai_setting(db)
        seeded = 0
        for s in DEFAULT_SETTINGS:
            existing = await db.execute(select(Setting).where(Setting.key == s["key"]))
            if not existing.scalar_one_or_none():
                db.add(Setting(**s))
                seeded += 1
        if seeded or migrated:
            await db.commit()
            if seeded:
                logger.info("Seeded %d new default settings", seeded)

        # Load API keys from DB into environment so services can use them
        api_key_settings = await db.execute(
            select(Setting).where(Setting.category == "api_keys")
        )
        for setting in api_key_settings.scalars().all():
            _sync_setting_env(setting.key, setting.value)


def _mask_value(value: str) -> str:
    """Mask a secret value, showing only last 4 chars."""
    if not value or len(value) <= 4:
        return "••••" if value else ""
    return "••••••••" + value[-4:]


# --- Endpoints ---

@router.get("")
async def list_settings(
    category: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_leadgen_db),
):
    """List all settings, optionally filtered by category. Secret values masked for non-superadmin."""
    query = select(Setting)
    if category:
        query = query.where(Setting.category == category)
    query = query.order_by(Setting.category, Setting.key)

    result = await db.execute(query)
    settings = result.scalars().all()

    # Superadmins see raw secret values; others see masked
    is_superadmin = getattr(user, "is_superadmin", False)

    return [
        SettingResponse(
            key=s.key,
            value=s.value if (not s.is_secret or is_superadmin) else _mask_value(s.value),
            category=s.category,
            description=s.description,
            is_secret=bool(s.is_secret),
        )
        for s in settings
    ]


# ── Email settings (must be above /{key} catch-all) ──────────────────

EMAIL_DEFAULTS = {
    "smtp_host": "",
    "smtp_port": "587",
    "smtp_username": "",
    "smtp_password": "",
    "imap_host": "",
    "imap_port": "993",
    "from_name": "",
    "from_email": "",
}

LEAD_SCORING_DEFAULTS = {
    "weights": {
        "no_website": 30,
        "bad_website_score": 20,
        "mediocre_website": 10,
        "has_email": 10,
        "has_phone": 10,
        "high_google_rating": 10,
        "many_reviews": 5,
        "has_socials": 5,
        "old_platform": 15,
    },
    "thresholds": {"hot": 70, "warm": 40, "cold": 0},
}


@router.get("/email")
async def get_email_settings(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_leadgen_db),
):
    """Return email/SMTP configuration from stored settings."""
    result = {}
    for field in EMAIL_DEFAULTS:
        key = f"email_{field}"
        row = await db.execute(select(Setting).where(Setting.key == key))
        setting = row.scalars().first()
        result[field] = setting.value if setting else EMAIL_DEFAULTS[field]
    return result


@router.put("/email")
async def update_email_settings(
    body: dict,
    user: User = Depends(require_superadmin()),
    db: AsyncSession = Depends(get_leadgen_db),
):
    """Save email/SMTP configuration."""
    for field in EMAIL_DEFAULTS:
        if field not in body:
            continue
        key = f"email_{field}"
        row = await db.execute(select(Setting).where(Setting.key == key))
        setting = row.scalars().first()
        if setting:
            setting.value = str(body[field])
        else:
            db.add(Setting(
                key=key,
                value=str(body[field]),
                category="email",
                description=f"Email setting: {field}",
                is_secret=1 if "password" in field else 0,
            ))
    await db.commit()
    return {"status": "ok"}


@router.post("/email/test")
async def test_email_connection(
    body: dict,
    user: User = Depends(require_superadmin()),
):
    """Test SMTP connection with provided settings."""
    import smtplib
    try:
        host = body.get("smtp_host", "")
        port = int(body.get("smtp_port", 587))
        with smtplib.SMTP(host, port, timeout=10) as server:
            server.ehlo()
            if port != 25:
                server.starttls()
            username = body.get("smtp_username", "")
            password = body.get("smtp_password", "")
            if username and password:
                server.login(username, password)
        return {"status": "ok", "message": "Connection successful"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Connection failed: {e}")


@router.get("/lead-scoring")
async def get_lead_scoring_settings(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_leadgen_db),
):
    """Return lead scoring weights and thresholds."""
    import json as _json
    row = await db.execute(select(Setting).where(Setting.key == "lead_scoring_config"))
    setting = row.scalars().first()
    if setting and setting.value:
        try:
            return _json.loads(setting.value)
        except _json.JSONDecodeError:
            pass
    return LEAD_SCORING_DEFAULTS


@router.put("/lead-scoring")
async def update_lead_scoring_settings(
    body: dict,
    user: User = Depends(require_superadmin()),
    db: AsyncSession = Depends(get_leadgen_db),
):
    """Save lead scoring weights and thresholds."""
    import json as _json
    row = await db.execute(select(Setting).where(Setting.key == "lead_scoring_config"))
    setting = row.scalars().first()
    payload = _json.dumps(body)
    if setting:
        setting.value = payload
    else:
        db.add(Setting(
            key="lead_scoring_config",
            value=payload,
            category="lead_scoring",
            description="Lead scoring weights and tier thresholds",
            is_secret=0,
        ))
    await db.commit()
    return {"status": "ok"}


@router.get("/{key}")
async def get_setting(
    key: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_leadgen_db),
):
    """Get a single setting by key. Secret values masked for non-superadmin."""
    key = _normalize_setting_key(key)
    result = await db.execute(select(Setting).where(Setting.key == key))
    setting = result.scalars().first()
    if not setting:
        raise HTTPException(status_code=404, detail=f"Setting '{key}' not found")

    is_superadmin = getattr(user, "is_superadmin", False)

    return SettingResponse(
        key=setting.key,
        value=setting.value if (not setting.is_secret or is_superadmin) else _mask_value(setting.value),
        category=setting.category,
        description=setting.description,
        is_secret=bool(setting.is_secret),
    )


@router.put("/{key}")
async def update_setting(
    key: str,
    body: SettingUpdate,
    user: User = Depends(require_superadmin()),
    db: AsyncSession = Depends(get_leadgen_db),
):
    """Update a setting value."""
    key = _normalize_setting_key(key)
    result = await db.execute(select(Setting).where(Setting.key == key))
    setting = result.scalars().first()

    if not setting:
        # Create it if it doesn't exist
        is_secret = key in API_KEY_ENV_MAP
        description = next((s["description"] for s in DEFAULT_SETTINGS if s["key"] == key), None)
        setting = Setting(
            key=key,
            value=body.value,
            category="api_keys" if is_secret else "general",
            description=description,
            is_secret=1 if is_secret else 0,
        )
        db.add(setting)
    else:
        setting.value = body.value

    await db.commit()
    await db.refresh(setting)

    _sync_setting_env(key, body.value)

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
    user: User = Depends(require_superadmin()),
    db: AsyncSession = Depends(get_leadgen_db),
):
    """Create a new setting."""
    body.key = _normalize_setting_key(body.key)
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
async def delete_setting(key: str, user: User = Depends(require_superadmin()), db: AsyncSession = Depends(get_leadgen_db)):
    """Delete a setting."""
    key = _normalize_setting_key(key)
    result = await db.execute(select(Setting).where(Setting.key == key))
    setting = result.scalars().first()
    if not setting:
        raise HTTPException(status_code=404, detail=f"Setting '{key}' not found")

    await db.execute(delete(Setting).where(Setting.key == key))
    await db.commit()
    _sync_setting_env(key, "")
    return {"status": "deleted", "key": key}
