"""WAR ROOM — Unified API Gateway"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import kanban, team, library, leadgen, chat, health, mental_library, library_ingest, voice, settings, auth, admin, social, social_oauth, social_content, social_sync, files, competitors, content_intel, scraper, skills_manager, usage, soul, calendar as cal_api, google_calendar, ai_planning, task_deps, task_execution, blackboard, agents, contact_webhook, notifications, cold_email, lead_enrichment, email_inbox, contracts, invoicing, prospects, content_tracker, content_ai, telnyx, twilio, twilio_voice, comms
from app.api.crm import deals, contacts, activities, pipelines, products, emails, marketing, attributes, acl, data, audit, pipeline_board, workflows
from app.db.leadgen_db import leadgen_engine
from app.db.crm_db import crm_engine, crm_session
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
        
        # Initialize notifications table (shared leadgen engine — same DB)
        await notifications.init_notifications_table(leadgen_engine)
        logger.info("Notifications table initialized")
        
        # Verify CRM schema exists (don't re-create, just verify)
        crm_schema_ok = await verify_crm_schema()
        logger.info("CRM schema verified")

        if crm_schema_ok:
            await telnyx.init_telnyx_tables()
            logger.info("Telnyx CRM tables initialized")
        
        # Agents tables (crm schema — must exist before any feature queries agent_assignments)
        from app.api.agents import ensure_tables as ensure_agent_tables
        async with crm_session() as db:
            await db.execute(sa_text("SET search_path TO crm, public"))
            await ensure_agent_tables(db)
        logger.info("Agent tables initialized (crm schema)")
        
        # Contact submissions table (public schema)
        await contact_webhook.init_contact_table()
        logger.info("Contact submissions table initialized")
        
        # Cold email tables (public schema)
        await cold_email.init_cold_email_tables()
        logger.info("Cold email tables initialized")
        
        # Lead enrichments table (public schema)
        await lead_enrichment.init_enrichments_table()
        logger.info("Lead enrichments table initialized")
        
        # Email inbox tables (public schema)
        await email_inbox.init_email_tables()
        logger.info("Email inbox tables initialized")

        # Warm Resend API key cache (so sync _send_email works immediately)
        from app.services.email import _get_resend_key
        resend_key = await _get_resend_key()
        logger.info("Resend API key %s", "loaded" if resend_key else "NOT configured")
        
        # Contract tables (public schema)
        await contracts.init_contracts_tables()
        logger.info("Contract tables initialized")
        
        # Invoicing tables (public schema)
        await invoicing.init_invoicing_tables()
        logger.info("Invoicing tables initialized")
        
        # Prospects meta table (public schema)
        await prospects.init_prospects_table()
        logger.info("Prospects meta table initialized")
        
        # AI Call intakes table (public schema)
        await twilio_voice._ensure_table()
        logger.info("Call intakes table initialized")
        
    except Exception as e:
        logger.error("Failed to initialize databases: %s", e)

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


app = FastAPI(title="WAR ROOM", version="0.1.0", lifespan=lifespan)

# Auth guard — requires valid JWT for all /api/* routes except whitelist.
# Must be added before CORS so CORS headers are always present (even on 401).
from app.middleware.auth_guard import AuthGuardMiddleware
app.add_middleware(AuthGuardMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://warroom.stuffnthings.io",
        "https://stuffnthings.io",
        "https://www.stuffnthings.io",
        "http://localhost:3300",
        "http://localhost:3000",
        "http://192.168.1.94:3300",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["health"])
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(kanban.router, prefix="/api/kanban", tags=["kanban"])
app.include_router(team.router, prefix="/api/team", tags=["team"])
app.include_router(agents.router, prefix="/api", tags=["agents"])
app.include_router(library.router, prefix="/api/library", tags=["library"])
app.include_router(leadgen.router, prefix="/api/leadgen", tags=["leadgen"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(mental_library.router, prefix="/api/ml", tags=["mental-library"])
app.include_router(library_ingest.router, prefix="/api/library", tags=["library-ingest"])
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
app.include_router(blackboard.router, prefix="/api", tags=["blackboard"])
app.include_router(contact_webhook.router, prefix="/api", tags=["contact-webhook"])
app.include_router(notifications.router, prefix="/api", tags=["notifications"])
app.include_router(cold_email.router, prefix="/api", tags=["cold-email"])
app.include_router(lead_enrichment.router, prefix="/api", tags=["lead-enrichment"])
app.include_router(email_inbox.router, prefix="/api", tags=["email-inbox"])
app.include_router(invoicing.router, prefix="/api", tags=["invoicing"])
app.include_router(contracts.router, prefix="/api", tags=["contracts"])
app.include_router(prospects.router, prefix="/api", tags=["prospects"])
app.include_router(content_tracker.router, prefix="/api", tags=["content-tracker"])
app.include_router(content_ai.router, prefix="/api/content", tags=["content-ai"])
app.include_router(telnyx.router, prefix="/api", tags=["telnyx"])
app.include_router(twilio.router, prefix="/api", tags=["twilio"])
app.include_router(twilio_voice.router, prefix="/api/twilio", tags=["twilio-voice"])
app.include_router(comms.router, prefix="/api/comms", tags=["communications"])

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
app.include_router(pipeline_board.router, prefix="/api/crm", tags=["crm-pipeline-board"])
app.include_router(workflows.router, prefix="/api/crm", tags=["crm-workflows"])
