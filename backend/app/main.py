"""socialRecycle — Social Media Management API"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import chat, health, settings, auth, social, social_oauth, social_content, social_sync, files, competitors, content_intel, calendar as cal_api, google_calendar, notifications, stripe_settings, google_ai_studio, ugc_studio, video_editor, content_scheduler, video_copycat, video_assets, video_formats, content_social, carousel, auto_reply, social_accounts, mirofish

from app.api.webhooks.instagram import router as instagram_webhook_router

from app.db.leadgen_db import leadgen_engine
from app.db.crm_db import crm_engine, crm_session
from app.models.lead import Base

logger = logging.getLogger(__name__)


async def _init_content_scheduler_tables(engine):
    """Initialize content scheduler tables from migration file."""
    try:
        import os
        from pathlib import Path
        
        migration_path = Path(__file__).parent / "db" / "content_scheduler_migration.sql"
        if not migration_path.exists():
            logger.error(f"Content scheduler migration file not found: {migration_path}")
            return False
            
        with open(migration_path, 'r') as f:
            migration_sql = f.read()
        
        async with engine.begin() as conn:
            raw = await conn.get_raw_connection()
            await raw.driver_connection.execute(migration_sql)
        
        return True
        
    except Exception as e:
        logger.error(f"Content scheduler table initialization failed: {e}")
        return False


async def _init_carousel_tables(engine):
    """Initialize carousel tables from migration file."""
    try:
        import os
        from pathlib import Path
        
        migration_path = Path(__file__).parent / "db" / "carousel_migration.sql"
        if not migration_path.exists():
            logger.error(f"Carousel migration file not found: {migration_path}")
            return False
            
        with open(migration_path, 'r') as f:
            migration_sql = f.read()
        
        async with engine.begin() as conn:
            raw = await conn.get_raw_connection()
            await raw.driver_connection.execute(migration_sql)
        
        return True
        
    except Exception as e:
        logger.error(f"Carousel table initialization failed: {e}")
        return False










def _validate_jwt_secret():
    """Validate JWT secret strength at startup."""
    from app.config import settings
    
    jwt_secret = settings.JWT_SECRET
    if not jwt_secret:
        logger.error("JWT_SECRET environment variable not set")
        raise ValueError("JWT_SECRET is required")
    
    if len(jwt_secret) < 32:
        logger.warning(
            "JWT_SECRET is only %d characters - recommend at least 32 characters for security",
            len(jwt_secret)
        )
        # Don't fail startup, but warn loudly
        
    logger.info("JWT secret validation passed (%d characters)", len(jwt_secret))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database tables on startup."""
    # Validate JWT secret strength
    _validate_jwt_secret()
    
    try:
        # Ensure leadgen schema exists, then create tables
        from sqlalchemy import text as sa_text
        async with leadgen_engine.begin() as conn:
            await conn.execute(sa_text("CREATE SCHEMA IF NOT EXISTS leadgen"))
            await conn.run_sync(Base.metadata.create_all)
        logger.info("LeadGen database initialized (schema: leadgen)")
        
        # Create settings table and seed defaults
        await settings.init_settings_table(leadgen_engine)
        logger.info("Settings initialized")
        
        # Initialize notifications table (shared leadgen engine — same DB)
        await notifications.init_notifications_table(leadgen_engine)
        logger.info("Notifications table initialized")
        
        # Verify CRM schema exists (don't re-create, just verify)
        crm_schema_ok = await verify_crm_schema()
        logger.info("CRM schema verified")

        # Ensure metadata JSONB column on deals (idempotent)
        if crm_schema_ok:
            try:
                from app.db.crm_db import crm_engine
                async with crm_engine.begin() as conn:
                    await conn.execute(sa_text(
                        "ALTER TABLE crm.deals ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'::jsonb"
                    ))
                    await conn.execute(sa_text(
                        "ALTER TABLE crm.organizations ADD COLUMN IF NOT EXISTS emails JSONB DEFAULT '[]'::jsonb"
                    ))
                    await conn.execute(sa_text(
                        "ALTER TABLE crm.organizations ADD COLUMN IF NOT EXISTS contact_numbers JSONB DEFAULT '[]'::jsonb"
                    ))
                logger.info("Deals metadata and organization contact columns ensured")
            except Exception as e:
                logger.warning("Failed to ensure CRM metadata/contact columns: %s", e)


        
        # Video Copycat tables — must run before content scheduler (compositions FK → storyboards)
        try:
            await video_copycat.init_video_copycat_tables()
            logger.info("Video Copycat tables initialized")
        except Exception as e:
            logger.error("Failed to initialize Video Copycat tables: %s", e)

        # Content Scheduler tables (public schema) — compositions + scheduling
        await _init_content_scheduler_tables(leadgen_engine)
        logger.info("Content scheduler tables initialized")

        # Carousel tables (crm schema) — text-to-carousel + Instagram posting
        await _init_carousel_tables(crm_engine)
        logger.info("Carousel tables initialized")

    except Exception as e:
        logger.error("Failed to initialize databases: %s", e)

    # UGC Studio tables — isolated because of known jsonb cast issue
    try:
        await ugc_studio.init_ugc_tables()
        await ugc_studio.seed_templates()
        logger.info("UGC Studio tables initialized")
    except Exception as e:
        logger.error("Failed to initialize UGC Studio tables: %s", e)

    # Video Editor tables (Remotion-based) — isolated
    try:
        await video_editor.init_video_editor_tables()
        await video_editor.seed_remotion_templates()
        logger.info("Video Editor tables initialized")
    except Exception as e:
        logger.error("Failed to initialize Video Editor tables: %s", e)

    # Video Assets tables (assets + digital copies) — isolated
    try:
        await video_assets.init_video_copycat_tables()
        logger.info("Video Assets tables initialized")
    except Exception as e:
        logger.error("Failed to initialize Video Assets tables: %s", e)



    # Start background scheduler (competitor syncs, etc.)
    from app.services.scheduler import start_scheduler, stop_scheduler
    await start_scheduler()

    yield

    # Shutdown scheduler
    await stop_scheduler()


async def verify_crm_schema():
    """Verify CRM schema exists without re-creating it."""
    from sqlalchemy import text
    
    try:
        async with crm_engine.begin() as conn:
            result = await conn.execute(
                text("SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'crm'")
            )
            schema_exists = result.fetchone()
            
            if not schema_exists:
                logger.warning("CRM schema does not exist - run migration first")
                return False
            
            # Check if we have the basic tables
            table_check = await conn.execute(
                text("SELECT COUNT(*) as count FROM information_schema.tables WHERE table_schema = 'crm'")
            )
            table_count = table_check.fetchone()[0]
            
            if table_count < 10:  # Should have many more than 10 tables
                logger.warning("CRM schema incomplete - only %d tables found", table_count)
                return False
                
            logger.info("CRM schema verified with %d tables", table_count)
            return True
            
    except Exception as e:
        logger.error("Failed to verify CRM schema: %s", e)
        return False


app = FastAPI(title="socialRecycle", version="0.1.0", lifespan=lifespan)

# Request size limits (10MB default) - add early in middleware stack
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
import asyncio

class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Limit request body size to prevent DoS attacks."""
    
    def __init__(self, app, max_size: int = 10 * 1024 * 1024):  # 10MB default
        super().__init__(app)
        self.max_size = max_size
    
    async def dispatch(self, request: Request, call_next):
        if request.headers.get("content-length"):
            content_length = int(request.headers["content-length"])
            if content_length > self.max_size:
                return JSONResponse(
                    status_code=413,
                    content={"error": f"Request body too large (max {self.max_size // (1024*1024)}MB)", "code": "PAYLOAD_TOO_LARGE"}
                )
        return await call_next(request)

app.add_middleware(RequestSizeLimitMiddleware)

# Trusted host middleware 
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])

# CSRF protection for state-changing operations
from app.middleware.csrf_guard import CSRFGuardMiddleware
app.add_middleware(CSRFGuardMiddleware)

# Tenant guard — enforces org_id on authenticated requests.
# Registered BEFORE AuthGuard so it executes AFTER auth (middleware runs in reverse).
from app.middleware.tenant_guard import TenantGuardMiddleware
app.add_middleware(TenantGuardMiddleware)

# Auth guard — requires valid JWT for all /api/* routes except whitelist.
# Must be added before CORS so CORS headers are always present (even on 401).
from app.middleware.auth_guard import AuthGuardMiddleware
app.add_middleware(AuthGuardMiddleware)

from app.config import settings as app_settings

app.add_middleware(
    CORSMiddleware,
    allow_origins=app_settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["health"])
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(settings.router, prefix="/api/settings", tags=["settings"])
app.include_router(stripe_settings.router, prefix="/api", tags=["stripe"])
app.include_router(files.router, prefix="/api/files", tags=["files"])
app.include_router(cal_api.router, prefix="/api", tags=["calendar"])
app.include_router(google_calendar.router, prefix="/api", tags=["google-calendar"])
app.include_router(social.router, prefix="/api/social", tags=["social"])
app.include_router(social_oauth.router, prefix="/api/social", tags=["social-oauth"])
app.include_router(social_content.router, prefix="/api/social", tags=["social-content"])
app.include_router(social_sync.router, prefix="/api/social", tags=["social-sync"])
app.include_router(social_accounts.router, prefix="/api/settings/social-accounts", tags=["social-accounts"])
app.include_router(content_social.router, prefix="/api/content-social", tags=["content-social"])
app.include_router(competitors.router, prefix="/api", tags=["competitors"])
app.include_router(content_intel.router, prefix="/api/content-intel", tags=["content-intelligence"])
app.include_router(content_scheduler.router, prefix="/api/scheduler", tags=["content-scheduler"])
app.include_router(carousel.router, prefix="/api/carousel", tags=["carousel"])
app.include_router(auto_reply.router, prefix="/api/auto-reply", tags=["auto-reply"])
app.include_router(mirofish.router, tags=["mirofish"])
app.include_router(google_ai_studio.router, prefix="/api/ai-studio", tags=["google-ai-studio"])
app.include_router(ugc_studio.router, prefix="/api/ai-studio/ugc", tags=["ugc-studio"])
app.include_router(video_editor.router, prefix="/api/video", tags=["video-editor", "video-copycat"])
app.include_router(video_copycat.router, prefix="/api/video-copycat", tags=["video-copycat"])
app.include_router(video_assets.router, prefix="/api/video-copycat", tags=["video-assets"])
app.include_router(video_formats.router, prefix="/api", tags=["video-formats"])
app.include_router(instagram_webhook_router, tags=["webhooks"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(notifications.router, prefix="/api", tags=["notifications"])


# Static file serving for uploads
import os
UPLOAD_BASE_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_BASE_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_BASE_DIR), name="uploads")
