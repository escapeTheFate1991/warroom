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

from app.db.leadgen_db import leadgen_engine, leadgen_session
from app.services.email import _send_email

logger = logging.getLogger(__name__)

# ── DB Setup — uses shared leadgen engine (same knowledge DB, public schema)
_engine = leadgen_engine
_session = leadgen_session

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
        "name": "Introduction — Audit-Based",
        "subject_template": "We audited {{company}}'s website — here's what we found",
        "body_template": (
            "Hi {{name}},\n\n"
            "I came across {{company}} while researching {{category}} businesses in {{city}}. "
            "We ran a quick audit on your website and found a few things worth flagging:\n\n"
            "{{pain_point}}\n\n"
            "{{audit_blurb}}\n\n"
            "We specialize in {{service}} and have helped businesses like yours turn "
            "these exact issues into growth opportunities.\n\n"
            "Would you be open to a quick 15-minute chat this week? "
            "I can walk you through the full audit results — no strings attached.\n\n"
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
        "name": "Value Prop — Specific Findings",
        "subject_template": "3 things we'd fix on {{company}}'s website",
        "body_template": (
            "Hi {{name}},\n\n"
            "I took a look at {{company}}'s online presence and wanted to share "
            "three specific things that could make a real difference:\n\n"
            "{{pain_point}}\n\n"
            "We recently helped a {{category}} business tackle similar issues and saw "
            "measurable improvements within the first 30 days — more traffic, better "
            "conversions, and a web presence that actually works for them.\n\n"
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

        # Resolve recipient from lead if provided — pull ALL enrichment data
        if lead_id:
            result = await db.execute(
                text(
                    "SELECT business_name, owner_name, emails, phone, website, "
                    "business_category, city, state, "
                    "audit_lite_flags, website_audit_score, website_audit_grade, "
                    "website_audit_summary, website_audit_top_fixes, "
                    "yelp_rating, yelp_reviews_count, google_rating, google_reviews_count, "
                    "review_pain_points, review_opportunity_flags "
                    "FROM leadgen.leads WHERE id = :id"
                ),
                {"id": lead_id},
            )
            lead = result.fetchone()
            if not lead:
                raise HTTPException(404, "Lead not found")
            recipient_name = recipient_name or lead.owner_name or lead.business_name
            # Use first email from emails array if available
            if not recipient_email and lead.emails:
                recipient_email = lead.emails[0] if lead.emails else None
            if not company_context.get("company") and lead.business_name:
                company_context["company"] = lead.business_name

            # Build rich pain_point from actual audit data
            pain_points = []
            if lead.website_audit_top_fixes:
                pain_points.extend(lead.website_audit_top_fixes[:3])
            elif lead.audit_lite_flags:
                pain_points.extend(lead.audit_lite_flags[:3])
            if lead.review_pain_points:
                pain_points.extend(lead.review_pain_points[:2])

            if pain_points:
                company_context.setdefault("pain_point", "; ".join(pain_points))

            # Add audit score context
            if lead.website_audit_score is not None:
                company_context["audit_score"] = lead.website_audit_score
                company_context["audit_grade"] = lead.website_audit_grade or ""
            if lead.website_audit_summary:
                company_context["audit_summary"] = lead.website_audit_summary
            if lead.website:
                company_context["website"] = lead.website
            if lead.city:
                company_context["city"] = lead.city
            if lead.state:
                company_context["state"] = lead.state
            if lead.business_category:
                company_context["category"] = lead.business_category
            if lead.yelp_rating:
                company_context["yelp_rating"] = float(lead.yelp_rating)
            if lead.google_rating:
                company_context["google_rating"] = float(lead.google_rating)

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

        # Build substitution variables with rich lead data
        pain_point = company_context.get("pain_point", "online visibility and lead generation")
        audit_score = company_context.get("audit_score")
        audit_blurb = ""
        if audit_score is not None:
            audit_blurb = f"Your website scored {audit_score}/100 on our audit"
            if company_context.get("audit_grade"):
                audit_blurb += f" (Grade: {company_context['audit_grade']})"
            audit_blurb += "."

        variables = {
            "name": recipient_name,
            "company": company_context.get("company", "your company"),
            "service": company_context.get("service", "web development & digital strategy"),
            "pain_point": pain_point,
            "audit_score": str(audit_score) if audit_score is not None else "",
            "audit_blurb": audit_blurb,
            "website": company_context.get("website", ""),
            "city": company_context.get("city", ""),
            "state": company_context.get("state", ""),
            "category": company_context.get("category", ""),
            "yelp_rating": str(company_context.get("yelp_rating", "")),
            "google_rating": str(company_context.get("google_rating", "")),
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
                "VALUES (:csid, :lid, :rname, :remail, :subject, :body, :tid, CAST(:ctx AS jsonb)) "
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
