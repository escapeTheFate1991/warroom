"""WAR ROOM — Unified API Gateway"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import kanban, team, library, leadgen, chat, health, mental_library, voice, settings, auth, admin, social, social_oauth, social_content, social_sync, files, competitors, content_intel, scraper, skills_manager, usage, soul, calendar as cal_api, google_calendar, ai_planning, task_deps, task_execution, contact_webhook, notifications
from app.api.crm import deals, contacts, activities, pipelines, products, emails, marketing, attributes, acl, data, audit
from app.db.leadgen_db import leadgen_engine
from app.db.crm_db import crm_engine
from app.models.lead import Base

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database tables on startup."""
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
        
        # Initialize notifications table
        await notifications.init_notifications_table(leadgen_engine)
        logger.info("Notifications table initialized")
        
        # Verify CRM schema exists (don't re-create, just verify)
        await verify_crm_schema()
        logger.info("CRM schema verified")
        
        # Contact submissions table (public schema)
        await contact_webhook.init_contact_table()
        logger.info("Contact submissions table initialized")
        
    except Exception as e:
        logger.error("Failed to initialize databases: %s", e)
    
    yield


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
                logger.warning(f"CRM schema incomplete - only {table_count} tables found")
                return False
                
            logger.info(f"CRM schema verified with {table_count} tables")
            return True
            
    except Exception as e:
        logger.error(f"Failed to verify CRM schema: {e}")
        return False


app = FastAPI(title="WAR ROOM", version="0.1.0", lifespan=lifespan)

# Auth guard — requires valid JWT for all /api/* routes except whitelist.
# Must be added before CORS so CORS headers are always present (even on 401).
from app.middleware.auth_guard import AuthGuardMiddleware
app.add_middleware(AuthGuardMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["health"])
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(kanban.router, prefix="/api/kanban", tags=["kanban"])
app.include_router(team.router, prefix="/api/team", tags=["team"])
app.include_router(library.router, prefix="/api/library", tags=["library"])
app.include_router(leadgen.router, prefix="/api/leadgen", tags=["leadgen"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(mental_library.router, prefix="/api/ml", tags=["mental-library"])
app.include_router(voice.router, prefix="/api/voice", tags=["voice"])
app.include_router(settings.router, prefix="/api/settings", tags=["settings"])
app.include_router(usage.router, prefix="/api/usage", tags=["usage"])
app.include_router(social.router, prefix="/api/social", tags=["social"])
app.include_router(social_oauth.router, prefix="/api/social", tags=["social-oauth"])
app.include_router(social_content.router, prefix="/api/social/content", tags=["social-content"])
app.include_router(social_sync.router, prefix="/api/social", tags=["social-sync"])
app.include_router(competitors.router, prefix="/api", tags=["competitors"])
app.include_router(content_intel.router, prefix="/api/content-intel", tags=["content-intelligence"])
app.include_router(files.router, prefix="/api/files", tags=["files"])
app.include_router(scraper.router, prefix="/api", tags=["scraper"])
app.include_router(skills_manager.router, prefix="/api", tags=["skills"])
app.include_router(soul.router, prefix="/api", tags=["soul"])
app.include_router(cal_api.router, prefix="/api", tags=["calendar"])
app.include_router(google_calendar.router, prefix="/api", tags=["google-calendar"])
app.include_router(ai_planning.router, prefix="/api", tags=["ai-planning"])
app.include_router(task_deps.router, prefix="/api", tags=["task-dependencies"])
app.include_router(task_execution.router, prefix="/api", tags=["task-execution"])
app.include_router(contact_webhook.router, prefix="/api", tags=["contact-webhook"])
app.include_router(notifications.router, prefix="/api", tags=["notifications"])

# CRM Routes
app.include_router(deals.router, prefix="/api/crm", tags=["crm-deals"])
app.include_router(contacts.router, prefix="/api/crm", tags=["crm-contacts"])
app.include_router(activities.router, prefix="/api/crm", tags=["crm-activities"])
app.include_router(pipelines.router, prefix="/api/crm", tags=["crm-pipelines"])
app.include_router(products.router, prefix="/api/crm", tags=["crm-products"])
app.include_router(emails.router, prefix="/api/crm", tags=["crm-emails"])
app.include_router(marketing.router, prefix="/api/crm", tags=["crm-marketing"])
app.include_router(attributes.router, prefix="/api/crm", tags=["crm-attributes"])
app.include_router(acl.router, prefix="/api/crm", tags=["crm-acl"])
app.include_router(data.router, prefix="/api/crm", tags=["crm-data"])
app.include_router(audit.router, prefix="/api/crm", tags=["crm-audit"])
