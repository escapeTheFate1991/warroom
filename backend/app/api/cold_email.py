"""Cold Email Generator — personalized cold outreach emails using CRM context.

Tables: public.cold_email_templates, public.cold_email_drafts (auto-created on startup).
Template variable substitution: {{name}}, {{company}}, {{service}}, {{pain_point}}.
"""
import logging
import re
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, EmailStr
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.services.email import _send_email

logger = logging.getLogger(__name__)

# ── DB Setup (public schema, knowledge DB) ───────────────────────────
DB_URL = "postgresql+asyncpg://friday:friday-brain2-2026@10.0.0.11:5433/knowledge"
_engine = create_async_engine(DB_URL, echo=False, pool_size=3, max_overflow=5)
_session = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)

router = APIRouter()

# ── Table DDL ────────────────────────────────────────────────────────
TEMPLATES_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS public.cold_email_templates (
    id               SERIAL PRIMARY KEY,
    name             TEXT NOT NULL,
    subject_template TEXT NOT NULL,
    body_template    TEXT NOT NULL,
    tone             VARCHAR(30) DEFAULT 'professional',
    industry         TEXT,
    created_at       TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at       TIMESTAMP WITH TIME ZONE DEFAULT now(),
    is_active        BOOLEAN DEFAULT TRUE
);
"""

DRAFTS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS public.cold_email_drafts (
    id                     SERIAL PRIMARY KEY,
    contact_submission_id  INTEGER,
    lead_id                INTEGER,
    recipient_name         TEXT NOT NULL,
    recipient_email        TEXT NOT NULL,
    subject                TEXT NOT NULL,
    body                   TEXT NOT NULL,
    template_id            INTEGER,
    status                 VARCHAR(20) DEFAULT 'draft',
    sent_at                TIMESTAMP WITH TIME ZONE,
    created_at             TIMESTAMP WITH TIME ZONE DEFAULT now(),
    company_context        JSONB DEFAULT '{}'::jsonb
);
"""

INDEX_SQLS = [
    "CREATE INDEX IF NOT EXISTS idx_cold_email_drafts_status ON public.cold_email_drafts (status)",
    "CREATE INDEX IF NOT EXISTS idx_cold_email_drafts_template ON public.cold_email_drafts (template_id)",
    "CREATE INDEX IF NOT EXISTS idx_cold_email_drafts_contact ON public.cold_email_drafts (contact_submission_id)",
    "CREATE INDEX IF NOT EXISTS idx_cold_email_drafts_lead ON public.cold_email_drafts (lead_id)",
]

SEED_TEMPLATES = [
    {
        "name": "Introduction",
        "subject_template": "Quick question about {{company}}'s web presence",
        "body_template": (
            "Hi {{name}},\n\n"
            "I came across {{company}} and was impressed by what you're building. "
            "I noticed a few areas where your web presence could be working harder for you — "
            "especially around {{pain_point}}.\n\n"
            "We specialize in {{service}} and have helped businesses like yours turn their "
            "online presence into a real growth engine.\n\n"
            "Would you be open to a quick 15-minute chat this week to explore how we might help?\n\n"
            "Best,\nThe Stuff N Things Team"
        ),
        "tone": "professional",
    },
    {
        "name": "Follow Up",
        "subject_template": "Following up — {{service}} for {{company}}",
        "body_template": (
            "Hi {{name}},\n\n"
            "I reached out last week about helping {{company}} with {{service}} "
            "and wanted to check in. I know things get busy.\n\n"
            "We've been seeing great results helping businesses tackle {{pain_point}} — "
            "if that's still a priority for you, I'd love to share a few ideas.\n\n"
            "No pressure at all. Just reply to this email or grab a time on my calendar "
            "if you'd like to chat.\n\n"
            "Best,\nThe Stuff N Things Team"
        ),
        "tone": "friendly",
    },
    {
        "name": "Value Prop",
        "subject_template": "How we helped a business like {{company}} solve {{pain_point}}",
        "body_template": (
            "Hi {{name}},\n\n"
            "I wanted to share a quick win from one of our recent projects. A business "
            "in a similar space to {{company}} came to us struggling with {{pain_point}}.\n\n"
            "After implementing our {{service}} solution, they saw measurable improvements "
            "within the first 30 days — more traffic, better conversions, and a web presence "
            "that actually works for them instead of against them.\n\n"
            "I'd love to put together a similar game plan for {{company}}. "
            "Would a quick call this week work?\n\n"
            "Best,\nThe Stuff N Things Team"
        ),
        "tone": "professional",
    },
]


async def init_cold_email_tables():
    """Auto-create tables and seed default templates on startup."""
    try:
        async with _engine.begin() as conn:
            await conn.execute(text(TEMPLATES_TABLE_SQL))
            await conn.execute(text(DRAFTS_TABLE_SQL))
            for idx_sql in INDEX_SQLS:
                await conn.execute(text(idx_sql))

            # Seed defaults only if table is empty
            result = await conn.execute(
                text("SELECT COUNT(*) FROM public.cold_email_templates")
            )
            count = result.scalar()
            if count == 0:
                for tpl in SEED_TEMPLATES:
                    await conn.execute(
                        text(
                            "INSERT INTO public.cold_email_templates "
                            "(name, subject_template, body_template, tone) "
                            "VALUES (:name, :subject_template, :body_template, :tone)"
                        ),
                        tpl,
                    )
                logger.info("Seeded %d default cold email templates", len(SEED_TEMPLATES))

        logger.info("Cold email tables initialized")
    except Exception as e:
        logger.error("Failed to initialize cold email tables: %s", e)


# ── Helpers ──────────────────────────────────────────────────────────

def _substitute(template: str, variables: dict) -> str:
    """Replace {{var}} placeholders with values from the variables dict."""
    def replacer(match):
        key = match.group(1).strip()
        return variables.get(key, match.group(0))
    return re.sub(r"\{\{(\s*\w+\s*)\}\}", replacer, template)


def _row_to_template(row) -> dict:
    return {
        "id": row.id,
        "name": row.name,
        "subject_template": row.subject_template,
        "body_template": row.body_template,
        "tone": row.tone,
        "industry": row.industry,
        "is_active": row.is_active,
        "created_at": str(row.created_at),
        "updated_at": str(row.updated_at),
    }


def _row_to_draft(row) -> dict:
    return {
        "id": row.id,
        "contact_submission_id": row.contact_submission_id,
        "lead_id": row.lead_id,
        "recipient_name": row.recipient_name,
        "recipient_email": row.recipient_email,
        "subject": row.subject,
        "body": row.body,
        "template_id": row.template_id,
        "status": row.status,
        "sent_at": str(row.sent_at) if row.sent_at else None,
        "created_at": str(row.created_at),
        "company_context": row.company_context,
    }


# ── Request / Response Models ────────────────────────────────────────

class CreateTemplateRequest(BaseModel):
    name: str
    subject_template: str
    body_template: str
    tone: str = "professional"
    industry: Optional[str] = None


class GenerateEmailRequest(BaseModel):
    contact_submission_id: Optional[int] = None
    lead_id: Optional[int] = None
    recipient_name: Optional[str] = None
    recipient_email: Optional[str] = None
    company_info: Optional[dict] = None
    template_id: Optional[int] = None
    variables: Optional[dict] = None  # explicit overrides: name, company, service, pain_point


class UpdateDraftRequest(BaseModel):
    subject: Optional[str] = None
    body: Optional[str] = None
    status: Optional[str] = None


# ── Template Endpoints ───────────────────────────────────────────────

@router.get("/cold-emails/templates")
async def list_templates(active_only: bool = Query(True)):
    """List all cold email templates."""
    clause = "WHERE is_active = TRUE" if active_only else ""
    async with _session() as db:
        result = await db.execute(
            text(f"SELECT * FROM public.cold_email_templates {clause} ORDER BY created_at DESC")
        )
        rows = result.fetchall()
    return [_row_to_template(r) for r in rows]


@router.post("/cold-emails/templates", status_code=201)
async def create_template(req: CreateTemplateRequest):
    """Create a new cold email template."""
    async with _session() as db:
        result = await db.execute(
            text(
                "INSERT INTO public.cold_email_templates "
                "(name, subject_template, body_template, tone, industry) "
                "VALUES (:name, :subject_template, :body_template, :tone, :industry) "
                "RETURNING *"
            ),
            {
                "name": req.name,
                "subject_template": req.subject_template,
                "body_template": req.body_template,
                "tone": req.tone,
                "industry": req.industry,
            },
        )
        row = result.fetchone()
        await db.commit()
    return _row_to_template(row)


# ── Generate Email Draft ─────────────────────────────────────────────

@router.post("/cold-emails/generate", status_code=201)
async def generate_email(req: GenerateEmailRequest):
    """Generate a personalized cold email draft using template variable substitution.

    Provide either contact_submission_id (pulls name/email from DB) or
    recipient_name + recipient_email directly. Optionally pass template_id
    (defaults to first active template) and variables dict for substitution.
    """
    recipient_name = req.recipient_name
    recipient_email = req.recipient_email
    company_context = req.company_info or {}
    contact_submission_id = req.contact_submission_id
    lead_id = req.lead_id

    async with _session() as db:
        # Resolve recipient from contact_submission if provided
        if contact_submission_id and (not recipient_name or not recipient_email):
            result = await db.execute(
                text("SELECT name, email FROM public.contact_submissions WHERE id = :id"),
                {"id": contact_submission_id},
            )
            contact = result.fetchone()
            if not contact:
                raise HTTPException(404, "Contact submission not found")
            recipient_name = recipient_name or contact.name
            recipient_email = recipient_email or contact.email

        # Resolve recipient from lead if provided
        if lead_id and (not recipient_name or not recipient_email):
            result = await db.execute(
                text("SELECT name, email, company, website FROM leadgen.leads WHERE id = :id"),
                {"id": lead_id},
            )
            lead = result.fetchone()
            if not lead:
                raise HTTPException(404, "Lead not found")
            recipient_name = recipient_name or lead.name
            recipient_email = recipient_email or lead.email
            if not company_context.get("company") and lead.company:
                company_context["company"] = lead.company

        if not recipient_name or not recipient_email:
            raise HTTPException(400, "recipient_name and recipient_email required (or provide contact_submission_id/lead_id)")

        # Get template
        if req.template_id:
            result = await db.execute(
                text("SELECT * FROM public.cold_email_templates WHERE id = :id AND is_active = TRUE"),
                {"id": req.template_id},
            )
        else:
            result = await db.execute(
                text("SELECT * FROM public.cold_email_templates WHERE is_active = TRUE ORDER BY id ASC LIMIT 1")
            )
        template = result.fetchone()
        if not template:
            raise HTTPException(404, "No active template found")

        # Build substitution variables
        variables = {
            "name": recipient_name,
            "company": company_context.get("company", "your company"),
            "service": company_context.get("service", "web development & digital strategy"),
            "pain_point": company_context.get("pain_point", "online visibility and lead generation"),
        }
        # Allow explicit overrides
        if req.variables:
            variables.update(req.variables)

        subject = _substitute(template.subject_template, variables)
        body = _substitute(template.body_template, variables)

        # Insert draft
        import json
        result = await db.execute(
            text(
                "INSERT INTO public.cold_email_drafts "
                "(contact_submission_id, lead_id, recipient_name, recipient_email, "
                "subject, body, template_id, company_context) "
                "VALUES (:csid, :lid, :rname, :remail, :subject, :body, :tid, :ctx::jsonb) "
                "RETURNING *"
            ),
            {
                "csid": contact_submission_id,
                "lid": lead_id,
                "rname": recipient_name,
                "remail": recipient_email,
                "subject": subject,
                "body": body,
                "tid": template.id,
                "ctx": json.dumps(company_context),
            },
        )
        draft = result.fetchone()
        await db.commit()

    return _row_to_draft(draft)


# ── Draft Endpoints ──────────────────────────────────────────────────

@router.get("/cold-emails/drafts")
async def list_drafts(
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    """List cold email drafts with pagination and optional status filter."""
    offset = (page - 1) * per_page
    conditions = []
    params: dict = {"limit": per_page, "offset": offset}

    if status:
        conditions.append("status = :status")
        params["status"] = status

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    async with _session() as db:
        count_result = await db.execute(
            text(f"SELECT COUNT(*) FROM public.cold_email_drafts {where}"), params
        )
        total = count_result.scalar()

        result = await db.execute(
            text(
                f"SELECT * FROM public.cold_email_drafts {where} "
                "ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
            ),
            params,
        )
        rows = result.fetchall()

    return {
        "drafts": [_row_to_draft(r) for r in rows],
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page if total else 0,
    }


@router.get("/cold-emails/drafts/{draft_id}")
async def get_draft(draft_id: int):
    """Get a single cold email draft by ID."""
    async with _session() as db:
        result = await db.execute(
            text("SELECT * FROM public.cold_email_drafts WHERE id = :id"),
            {"id": draft_id},
        )
        row = result.fetchone()
    if not row:
        raise HTTPException(404, "Draft not found")
    return _row_to_draft(row)


@router.patch("/cold-emails/drafts/{draft_id}")
async def update_draft(draft_id: int, req: UpdateDraftRequest):
    """Update a draft's subject, body, or status."""
    updates = []
    params: dict = {"id": draft_id}

    if req.subject is not None:
        updates.append("subject = :subject")
        params["subject"] = req.subject
    if req.body is not None:
        updates.append("body = :body")
        params["body"] = req.body
    if req.status is not None:
        if req.status not in ("draft", "ready", "sent", "failed", "cancelled"):
            raise HTTPException(400, "Invalid status. Use: draft, ready, sent, failed, cancelled")
        updates.append("status = :status")
        params["status"] = req.status

    if not updates:
        raise HTTPException(400, "No fields to update")

    async with _session() as db:
        result = await db.execute(
            text(
                f"UPDATE public.cold_email_drafts SET {', '.join(updates)} "
                "WHERE id = :id RETURNING *"
            ),
            params,
        )
        row = result.fetchone()
        await db.commit()

    if not row:
        raise HTTPException(404, "Draft not found")
    return _row_to_draft(row)


@router.post("/cold-emails/drafts/{draft_id}/send")
async def send_draft(draft_id: int):
    """Send a cold email draft via the email service."""
    async with _session() as db:
        result = await db.execute(
            text("SELECT * FROM public.cold_email_drafts WHERE id = :id"),
            {"id": draft_id},
        )
        draft = result.fetchone()

        if not draft:
            raise HTTPException(404, "Draft not found")
        if draft.status == "sent":
            raise HTTPException(400, "Draft already sent")

        # Build HTML email body (convert newlines to <br> for formatting)
        html_body = f"""
        <div style="font-family:system-ui;max-width:600px;margin:0 auto;padding:32px">
            <div style="color:#333;font-size:15px;line-height:1.6">
                {draft.body.replace(chr(10), '<br>')}
            </div>
        </div>
        """

        success = _send_email(draft.recipient_email, draft.subject, html_body)

        now = datetime.now(timezone.utc).isoformat()
        if success:
            await db.execute(
                text(
                    "UPDATE public.cold_email_drafts "
                    "SET status = 'sent', sent_at = :now WHERE id = :id"
                ),
                {"id": draft_id, "now": now},
            )
            await db.commit()
            return {"status": "sent", "draft_id": draft_id}
        else:
            await db.execute(
                text("UPDATE public.cold_email_drafts SET status = 'failed' WHERE id = :id"),
                {"id": draft_id},
            )
            await db.commit()
            raise HTTPException(502, "Failed to send email — check SMTP configuration")
