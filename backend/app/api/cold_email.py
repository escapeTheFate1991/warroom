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
from app.services.tenant import get_org_id

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
    # ── 1. Audit Hook — lead has website audit data ──
    {
        "name": "Audit Hook",
        "subject_template": "{{company}} scored {{audit_score}}/100 on our site audit",
        "body_template": (
            "Hi {{name}},\n\n"
            "I ran a free audit on {{company}}'s website and it scored {{audit_score}} out of 100. "
            "Here's what stood out:\n\n"
            "{{pain_point}}\n\n"
            "These are the kinds of issues that quietly cost {{category}} businesses "
            "customers every week — people land on the site, hit a wall, and bounce to a competitor.\n\n"
            "I put together a full breakdown with fixes. Want me to send it over? "
            "No cost, no pitch — just the data.\n\n"
            "— {{sender_name}}\n"
            "{{sender_phone}}"
        ),
        "tone": "direct",
    },
    # ── 2. No Website — lead has no website ──
    {
        "name": "No Website",
        "subject_template": "{{company}} — customers can't find you online",
        "body_template": (
            "Hi {{name}},\n\n"
            "I was looking into {{category}} businesses in {{city}} and noticed "
            "{{company}} doesn't have a website yet.\n\n"
            "That means when someone in {{city}} searches for a {{category}} provider, "
            "they're finding your competitors instead. Every day without a site is "
            "leads going to someone else.\n\n"
            "We build and manage websites for local businesses — "
            "the whole thing, done-for-you, starting at $299/mo. No upfront cost.\n\n"
            "Worth a 10-minute call to see if it makes sense?\n\n"
            "— {{sender_name}}\n"
            "{{sender_phone}}"
        ),
        "tone": "direct",
    },
    # ── 3. Low Google Rating — lead has poor reviews ──
    {
        "name": "Low Google Rating",
        "subject_template": "{{company}}'s {{google_rating}}-star rating is costing you",
        "body_template": (
            "Hi {{name}},\n\n"
            "I noticed {{company}} has a {{google_rating}}-star rating on Google. "
            "For {{category}} businesses, anything under 4.2 stars means "
            "most people scroll right past you.\n\n"
            "The fix isn't just asking for more reviews — it starts with your website. "
            "A site that makes it easy for happy customers to leave reviews, "
            "shows off your best work, and builds trust before they even call.\n\n"
            "I've got a few ideas specific to {{company}}. "
            "Can I send you a quick breakdown?\n\n"
            "— {{sender_name}}\n"
            "{{sender_phone}}"
        ),
        "tone": "direct",
    },
    # ── 4. Competitor Gap — competitors are doing better ──
    {
        "name": "Competitor Gap",
        "subject_template": "{{company}} vs your competitors in {{city}}",
        "body_template": (
            "Hi {{name}},\n\n"
            "I compared {{company}}'s online presence to a few other "
            "{{category}} businesses in {{city}}. Honest take: they're ahead.\n\n"
            "{{pain_point}}\n\n"
            "The good news — most of these gaps are straightforward to close. "
            "A better site, cleaner SEO, and a review strategy can flip the script in 60-90 days.\n\n"
            "I put together a side-by-side comparison. Want me to send it?\n\n"
            "— {{sender_name}}\n"
            "{{sender_phone}}"
        ),
        "tone": "direct",
    },
    # ── 5. Follow Up #1 — 3 days after initial ──
    {
        "name": "Follow Up #1",
        "subject_template": "Re: {{company}}'s website",
        "body_template": (
            "Hi {{name}},\n\n"
            "Sent you a note a few days ago about {{company}}'s online presence. "
            "Figured it might've gotten buried.\n\n"
            "Quick recap: I found some specific issues that are likely costing you "
            "customers. Happy to share the details — takes 5 minutes to review.\n\n"
            "If now's not the right time, no worries. Just don't want you "
            "losing business to a fixable problem.\n\n"
            "— {{sender_name}}\n"
            "{{sender_phone}}"
        ),
        "tone": "friendly",
    },
    # ── 6. Follow Up #2 — 7 days, different angle ──
    {
        "name": "Follow Up #2",
        "subject_template": "One thing I'd change on {{company}}'s site",
        "body_template": (
            "Hi {{name}},\n\n"
            "I know you're busy running {{company}}, so I'll keep this short.\n\n"
            "If I could only fix one thing on your online presence, it'd be this:\n\n"
            "{{pain_point}}\n\n"
            "That single change could make a real difference in how many "
            "{{city}} customers find and trust {{company}}.\n\n"
            "Want me to show you what I mean? 10 minutes, no strings.\n\n"
            "— {{sender_name}}\n"
            "{{sender_phone}}"
        ),
        "tone": "friendly",
    },
    # ── 7. Breakup Email — final touch, creates urgency ──
    {
        "name": "Breakup Email",
        "subject_template": "Closing the loop on {{company}}",
        "body_template": (
            "Hi {{name}},\n\n"
            "I've reached out a couple times about some issues I spotted "
            "with {{company}}'s online presence. I don't want to be a pest.\n\n"
            "I'll leave the audit results on file in case you want them later. "
            "If things change and you want a fresh look at your website, "
            "my door's open.\n\n"
            "Wishing you and {{company}} the best.\n\n"
            "— {{sender_name}}\n"
            "{{sender_phone}}"
        ),
        "tone": "professional",
    },
    # ── 8. Re-engagement — leads that went cold ──
    {
        "name": "Re-engagement",
        "subject_template": "Things have changed for {{company}}",
        "body_template": (
            "Hi {{name}},\n\n"
            "We talked a while back about {{company}}'s website. "
            "I just re-ran your audit and wanted to share what's changed.\n\n"
            "{{audit_blurb}}\n\n"
            "A few of your competitors in {{city}} have made moves since we last spoke. "
            "The gap is wider now than it was before.\n\n"
            "Worth 15 minutes to see where {{company}} stands today?\n\n"
            "— {{sender_name}}\n"
            "{{sender_phone}}"
        ),
        "tone": "direct",
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
    org_id = get_org_id(request)
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
    org_id = get_org_id(request)
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
    org_id = get_org_id(request)
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

        # Fetch sender settings (your_name, your_phone, your_email) from general settings
        sender_settings_result = await db.execute(
            text(
                "SELECT key, value FROM public.settings "
                "WHERE key IN ('your_name', 'your_phone', 'your_email', 'company_name') "
                "AND category = 'general'"
            )
        )
        sender_lookup = {r.key: (r.value or "") for r in sender_settings_result.fetchall()}
        sender_name = sender_lookup.get("your_name", "")
        sender_phone = sender_lookup.get("your_phone", "")
        sender_email = sender_lookup.get("your_email", "")
        if not company_context.get("company") and sender_lookup.get("company_name"):
            company_context["company"] = sender_lookup["company_name"]

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
            "city": company_context.get("city", "your area"),
            "state": company_context.get("state", ""),
            "category": company_context.get("category", "local"),
            "yelp_rating": str(company_context.get("yelp_rating", "")),
            "google_rating": str(company_context.get("google_rating", "")),
            "sender_name": sender_name,
            "sender_phone": sender_phone,
            "sender_email": sender_email,
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
    org_id = get_org_id(request)
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
    org_id = get_org_id(request)
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
    org_id = get_org_id(request)
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
    org_id = get_org_id(request)
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
