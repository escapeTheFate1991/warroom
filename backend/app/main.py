"""WAR ROOM — Unified API Gateway"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import kanban, team, library, leadgen, chat, health, mental_library, library_ingest, voice, settings, auth, admin, social, social_oauth, social_content, social_sync, files, competitors, content_intel, scraper, skills_manager, usage, soul, calendar as cal_api, google_calendar, ai_planning, task_deps, task_execution, blackboard, agents, contact_webhook, notifications, cold_email, lead_enrichment, email_inbox, contracts, invoicing, prospects, content_tracker, content_ai, telnyx, twilio, twilio_voice, comms, stripe_settings, google_ai_studio, ugc_studio, video_editor, audit_trail, token_metering, vector_memory, content_scheduler, agent_onboarding, video_copycat, video_assets, agent_chat, agent_comms
from app.api.crm import deals, contacts, activities, pipelines, products, emails, marketing, attributes, acl, data, audit, pipeline_board, workflows, workflow_executions
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


async def _init_agent_chat_tables(engine):
    """Initialize agent chat tables from migration file."""
    try:
        from pathlib import Path
        
        migration_path = Path(__file__).parent / "db" / "agent_chat_migration.sql"
        if not migration_path.exists():
            logger.error(f"Agent chat migration file not found: {migration_path}")
            return False
            
        with open(migration_path, 'r') as f:
            migration_sql = f.read()
        
        async with engine.begin() as conn:
            raw = await conn.get_raw_connection()
            await raw.driver_connection.execute(migration_sql)
        
        return True
        
    except Exception as e:
        logger.error(f"Agent chat table initialization failed: {e}")
        return False


async def _init_network_ai_blackboard():
    """Initialize Network-AI blackboard (ensure blackboard file exists)."""
    try:
        from pathlib import Path
        import subprocess
        
        network_ai_dir = Path.home() / ".openclaw/workspace/skills/network-ai"
        blackboard_script = network_ai_dir / "scripts" / "blackboard.py"
        
        if not blackboard_script.exists():
            logger.error(f"Network-AI blackboard script not found: {blackboard_script}")
            return False
        
        # Initialize blackboard by calling it with a simple command (this creates the file)
        result = subprocess.run([
            "python3", str(blackboard_script), "list"
        ], capture_output=True, text=True, timeout=10, cwd=str(network_ai_dir))
        
        if result.returncode != 0:
            logger.warning(f"Network-AI blackboard init warning: {result.stderr}")
            # Don't fail startup for this - blackboard will be created on first write
        
        return True
        
    except Exception as e:
        logger.error(f"Network-AI blackboard initialization failed: {e}")
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

        if crm_schema_ok:
            await telnyx.init_telnyx_tables()
            logger.info("Telnyx CRM tables initialized")
        
        # Agents tables (crm schema — must exist before any feature queries agent_assignments)
        from app.api.agents import ensure_tables as ensure_agent_tables
        async with crm_session() as db:
            await db.execute(sa_text("SET search_path TO crm, public"))
            await ensure_agent_tables(db)
        from app.api import agents as _agents_mod
        _agents_mod._tables_ready = True
        logger.info("Agent tables initialized (crm schema)")
        
        # Agent Provisioning tables (crm schema — Anchor Agent templates and instances)
        if crm_schema_ok:
            try:
                from app.api.agent_onboarding import ensure_tables as ensure_onboarding_tables, seed_skill_templates
                async with crm_session() as db:
                    await ensure_onboarding_tables(db)
                    await seed_skill_templates(db, org_id=1)  # Seed skill templates for org 1
                logger.info("Agent provisioning tables initialized with skill templates")
            except Exception as e:
                logger.error("Failed to initialize agent provisioning tables: %s", e)
                
        # Agent Multi-Instance migration (crm schema + public knowledge pool)
        try:
            from app.db.crm_db import run_agent_multi_instance_migration
            multi_ok = await run_agent_multi_instance_migration()
            if multi_ok:
                logger.info("Agent multi-instance migration applied")
            else:
                logger.warning("Agent multi-instance migration skipped or failed")
        except Exception as e:
            logger.error("Agent multi-instance migration error: %s", e)
        
        # Contact submissions table (public schema)
        await contact_webhook.init_contact_table()
        logger.info("Contact submissions table initialized")

        # Outbound emails table (public schema — comms hub tracking)
        await comms.init_outbound_emails_table()
        logger.info("Outbound emails table initialized")
        
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
        
        # Stripe products table (public schema) + seed defaults
        await stripe_settings.init_products_table(leadgen_engine)
        logger.info("Stripe products table initialized")
        
        # AI Call intakes table (public schema)
        await twilio_voice._ensure_table()
        logger.info("Call intakes table initialized")
        
        # Token metering system (public schema)
        from app.services.token_metering import init_token_metering_tables
        await init_token_metering_tables(leadgen_engine)
        logger.info("Token metering system initialized")
        
        # Agent chat tables (public schema) — user-agent conversations and tasks
        await _init_agent_chat_tables(leadgen_engine)
        logger.info("Agent chat tables initialized")
        
        # Network-AI blackboard initialization (ensure blackboard file exists)
        await _init_network_ai_blackboard()
        logger.info("Network-AI blackboard initialized")
        
        # Audit Trail table (public schema) — immutable activity logging
        from app.services.audit_trail import init_audit_trail_table
        audit_ok = await init_audit_trail_table(leadgen_engine)
        if audit_ok:
            logger.info("Audit trail table initialized")
        else:
            logger.warning("Audit trail table initialization failed")
        
        # Video Copycat tables — must run before content scheduler (compositions FK → storyboards)
        try:
            await video_copycat.init_video_copycat_tables()
            logger.info("Video Copycat tables initialized")
        except Exception as e:
            logger.error("Failed to initialize Video Copycat tables: %s", e)

        # Content Scheduler tables (public schema) — compositions + scheduling
        await _init_content_scheduler_tables(leadgen_engine)
        logger.info("Content scheduler tables initialized")

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

    # Multi-tenant migration (own try/except — must not be blocked by other init failures)
    try:
        from app.db.crm_db import run_multi_tenant_migration
        mt_ok = await run_multi_tenant_migration()
        if mt_ok:
            logger.info("Multi-tenant migration applied")
        else:
            logger.warning("Multi-tenant migration skipped or failed")
    except Exception as e:
        logger.error("Multi-tenant migration error: %s", e)

    # OAuth scoping migration (adds visibility_type to social_accounts)
    try:
        from app.db.crm_db import run_oauth_scoping_migration
        oauth_ok = await run_oauth_scoping_migration()
        if oauth_ok:
            logger.info("OAuth scoping migration applied")
        else:
            logger.warning("OAuth scoping migration skipped or failed")
    except Exception as e:
        logger.error("OAuth scoping migration error: %s", e)

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
app.include_router(agent_onboarding.router, tags=["agent-onboarding"])
app.include_router(agents.router, prefix="/api", tags=["agents"])
app.include_router(agent_chat.router, prefix="/api", tags=["agent-chat"])
app.include_router(agent_comms.router, prefix="/api", tags=["agent-comms"])
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
app.include_router(stripe_settings.router, prefix="/api", tags=["stripe"])
app.include_router(google_ai_studio.router, prefix="/api/ai-studio", tags=["google-ai-studio"])
app.include_router(ugc_studio.router, prefix="/api/ai-studio/ugc", tags=["ugc-studio"])
app.include_router(video_copycat.router, prefix="/api/video-copycat", tags=["video-copycat"])
app.include_router(video_assets.router, prefix="/api/video-copycat", tags=["video-assets"])
app.include_router(video_editor.router, prefix="/api/video", tags=["video-editor", "video-copycat"])
app.include_router(token_metering.router, prefix="/api/tokens", tags=["token-metering"])
app.include_router(audit_trail.router, prefix="/api/audit", tags=["audit-trail"])
app.include_router(vector_memory.router, prefix="/api/memory", tags=["vector-memory"])
app.include_router(content_scheduler.router, prefix="/api/scheduler", tags=["content-scheduler"])

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
app.include_router(workflow_executions.router, prefix="/api/crm", tags=["crm-workflow-executions"])
