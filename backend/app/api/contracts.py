"""WaaS Contract Generator — professional website-as-a-service contracts from templates.

Tables: public.contracts, public.contract_templates (auto-created on startup).
Generates printable HTML contracts with Stuff N Things branding.
"""
import logging
import uuid
from datetime import datetime, timezone, date, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse
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
CONTRACTS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS public.contracts (
    id               SERIAL PRIMARY KEY,
    contract_number  TEXT UNIQUE NOT NULL,
    client_name      TEXT NOT NULL,
    client_email     TEXT NOT NULL,
    client_company   TEXT,
    client_address   TEXT,
    template_id      INTEGER,
    plan_name        TEXT NOT NULL,
    monthly_price    DECIMAL(10,2) NOT NULL,
    setup_fee        DECIMAL(10,2) DEFAULT 0,
    contract_terms   JSONB DEFAULT '{}'::jsonb,
    status           VARCHAR(20) DEFAULT 'draft',
    signed_at        TIMESTAMP WITH TIME ZONE,
    start_date       DATE,
    end_date         DATE,
    created_at       TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at       TIMESTAMP WITH TIME ZONE DEFAULT now()
);
"""

TEMPLATES_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS public.contract_templates (
    id             SERIAL PRIMARY KEY,
    name           TEXT NOT NULL,
    plan_name      TEXT NOT NULL,
    monthly_price  DECIMAL(10,2) NOT NULL,
    setup_fee      DECIMAL(10,2) DEFAULT 0,
    default_terms  JSONB DEFAULT '{}'::jsonb,
    sections       JSONB DEFAULT '[]'::jsonb,
    is_active      BOOLEAN DEFAULT TRUE,
    created_at     TIMESTAMP WITH TIME ZONE DEFAULT now()
);
"""

INDEX_SQLS = [
    "CREATE INDEX IF NOT EXISTS idx_contracts_status ON public.contracts (status)",
    "CREATE INDEX IF NOT EXISTS idx_contracts_client_email ON public.contracts (client_email)",
    "CREATE INDEX IF NOT EXISTS idx_contracts_contract_number ON public.contracts (contract_number)",
    "CREATE INDEX IF NOT EXISTS idx_contract_templates_active ON public.contract_templates (is_active)",
]

VALID_STATUSES = {"draft", "sent", "viewed", "signed", "active", "expired", "cancelled"}

# ── Seed Templates ───────────────────────────────────────────────────
SEED_TEMPLATES = [
    {
        "name": "Foundation",
        "plan_name": "Foundation",
        "monthly_price": 299.00,
        "setup_fee": 999.00,
        "default_terms": {
            "term_months": 12,
            "auto_renew": True,
            "cancellation_notice_days": 30,
            "includes": [
                "Custom website design & build",
                "Managed hosting",
                "SSL certificate",
                "Daily backups",
                "Monthly maintenance",
                "Email support",
            ],
        },
        "sections": [
            {
                "title": "Scope of Services",
                "content": (
                    "Provider shall deliver a professionally designed and developed custom website "
                    "tailored to Client's brand and business requirements. Services include managed "
                    "hosting on enterprise-grade infrastructure, SSL certificate provisioning and "
                    "renewal, automated daily backups with 30-day retention, monthly maintenance "
                    "including software updates and security patches, and email-based technical support "
                    "during standard business hours (Mon–Fri, 9 AM – 5 PM EST)."
                ),
            },
            {
                "title": "Payment Terms",
                "content": (
                    "Client agrees to pay a one-time setup fee and recurring monthly service fee as "
                    "specified in the Plan Details section. Monthly fees are billed on the first of "
                    "each month and are due within fifteen (15) days of invoice date. Late payments "
                    "are subject to a 1.5% monthly finance charge. Provider reserves the right to "
                    "suspend services for accounts more than thirty (30) days past due."
                ),
            },
            {
                "title": "Term & Renewal",
                "content": (
                    "This Agreement shall commence on the Start Date and continue for the initial "
                    "term specified in the Plan Details. Unless either party provides written notice "
                    "of non-renewal at least thirty (30) days prior to the end of the current term, "
                    "this Agreement shall automatically renew for successive periods equal to the "
                    "initial term at the then-current rates."
                ),
            },
            {
                "title": "Termination",
                "content": (
                    "Either party may terminate this Agreement for cause upon thirty (30) days' "
                    "written notice if the other party materially breaches any provision and fails "
                    "to cure such breach within the notice period. Client may terminate for "
                    "convenience with the required notice period specified in the Plan Details, "
                    "subject to payment of any outstanding fees through the end of the notice period. "
                    "Upon termination, Provider shall deliver all Client content and assist with "
                    "migration for up to fifteen (15) business days."
                ),
            },
            {
                "title": "Intellectual Property",
                "content": (
                    "All custom design work, code, and content created specifically for Client "
                    "shall become Client's property upon full payment. Provider retains ownership "
                    "of proprietary tools, frameworks, and pre-existing code used in delivery. "
                    "Provider grants Client a perpetual, non-exclusive license to any Provider IP "
                    "incorporated into the deliverables. Client grants Provider permission to "
                    "display the completed work in Provider's portfolio unless otherwise agreed."
                ),
            },
            {
                "title": "Limitation of Liability",
                "content": (
                    "IN NO EVENT SHALL EITHER PARTY BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL, "
                    "CONSEQUENTIAL, OR PUNITIVE DAMAGES ARISING OUT OF OR RELATED TO THIS AGREEMENT. "
                    "PROVIDER'S TOTAL AGGREGATE LIABILITY SHALL NOT EXCEED THE TOTAL FEES PAID BY "
                    "CLIENT DURING THE TWELVE (12) MONTHS PRECEDING THE CLAIM. This limitation "
                    "applies regardless of the theory of liability, whether in contract, tort, or "
                    "otherwise."
                ),
            },
            {
                "title": "General Provisions",
                "content": (
                    "This Agreement constitutes the entire understanding between the parties and "
                    "supersedes all prior agreements. Any amendments must be in writing and signed "
                    "by both parties. This Agreement shall be governed by the laws of the State of "
                    "New York. If any provision is found unenforceable, the remaining provisions "
                    "shall continue in full force. Neither party may assign this Agreement without "
                    "the other party's written consent, except in connection with a merger or "
                    "acquisition. Notices shall be delivered via email to the addresses specified herein."
                ),
            },
        ],
    },
    {
        "name": "Operational",
        "plan_name": "Operational",
        "monthly_price": 599.00,
        "setup_fee": 1499.00,
        "default_terms": {
            "term_months": 12,
            "auto_renew": True,
            "cancellation_notice_days": 30,
            "includes": [
                "Everything in Foundation plan",
                "SEO optimization",
                "Monthly analytics report",
                "Content updates (up to 4/mo)",
                "Priority support",
                "Social media integration",
            ],
        },
        "sections": [
            {
                "title": "Scope of Services",
                "content": (
                    "Provider shall deliver all services included in the Foundation plan, plus: "
                    "search engine optimization (SEO) including keyword research, on-page optimization, "
                    "and technical SEO audits; monthly analytics reports covering traffic, engagement, "
                    "and conversion metrics; up to four (4) content updates per month including text, "
                    "image, and minor layout changes; priority technical support with guaranteed "
                    "4-hour response time during business hours; and social media integration including "
                    "feed embedding, share buttons, and Open Graph optimization."
                ),
            },
            {
                "title": "Payment Terms",
                "content": (
                    "Client agrees to pay a one-time setup fee and recurring monthly service fee as "
                    "specified in the Plan Details section. Monthly fees are billed on the first of "
                    "each month and are due within fifteen (15) days of invoice date. Late payments "
                    "are subject to a 1.5% monthly finance charge. Provider reserves the right to "
                    "suspend services for accounts more than thirty (30) days past due."
                ),
            },
            {
                "title": "Term & Renewal",
                "content": (
                    "This Agreement shall commence on the Start Date and continue for the initial "
                    "term specified in the Plan Details. Unless either party provides written notice "
                    "of non-renewal at least thirty (30) days prior to the end of the current term, "
                    "this Agreement shall automatically renew for successive periods equal to the "
                    "initial term at the then-current rates."
                ),
            },
            {
                "title": "Termination",
                "content": (
                    "Either party may terminate this Agreement for cause upon thirty (30) days' "
                    "written notice if the other party materially breaches any provision and fails "
                    "to cure such breach within the notice period. Client may terminate for "
                    "convenience with the required notice period specified in the Plan Details, "
                    "subject to payment of any outstanding fees through the end of the notice period. "
                    "Upon termination, Provider shall deliver all Client content and assist with "
                    "migration for up to fifteen (15) business days."
                ),
            },
            {
                "title": "Intellectual Property",
                "content": (
                    "All custom design work, code, and content created specifically for Client "
                    "shall become Client's property upon full payment. Provider retains ownership "
                    "of proprietary tools, frameworks, and pre-existing code used in delivery. "
                    "Provider grants Client a perpetual, non-exclusive license to any Provider IP "
                    "incorporated into the deliverables. Client grants Provider permission to "
                    "display the completed work in Provider's portfolio unless otherwise agreed."
                ),
            },
            {
                "title": "Limitation of Liability",
                "content": (
                    "IN NO EVENT SHALL EITHER PARTY BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL, "
                    "CONSEQUENTIAL, OR PUNITIVE DAMAGES ARISING OUT OF OR RELATED TO THIS AGREEMENT. "
                    "PROVIDER'S TOTAL AGGREGATE LIABILITY SHALL NOT EXCEED THE TOTAL FEES PAID BY "
                    "CLIENT DURING THE TWELVE (12) MONTHS PRECEDING THE CLAIM. This limitation "
                    "applies regardless of the theory of liability, whether in contract, tort, or "
                    "otherwise."
                ),
            },
            {
                "title": "General Provisions",
                "content": (
                    "This Agreement constitutes the entire understanding between the parties and "
                    "supersedes all prior agreements. Any amendments must be in writing and signed "
                    "by both parties. This Agreement shall be governed by the laws of the State of "
                    "New York. If any provision is found unenforceable, the remaining provisions "
                    "shall continue in full force. Neither party may assign this Agreement without "
                    "the other party's written consent, except in connection with a merger or "
                    "acquisition. Notices shall be delivered via email to the addresses specified herein."
                ),
            },
        ],
    },
    {
        "name": "Growth",
        "plan_name": "Growth",
        "monthly_price": 1200.00,
        "setup_fee": 2499.00,
        "default_terms": {
            "term_months": 12,
            "auto_renew": True,
            "cancellation_notice_days": 30,
            "includes": [
                "Everything in Operational plan",
                "Advanced SEO strategy",
                "Blog content creation",
                "A/B testing",
                "Conversion optimization",
                "Dedicated account manager",
                "Bi-weekly strategy calls",
            ],
        },
        "sections": [
            {
                "title": "Scope of Services",
                "content": (
                    "Provider shall deliver all services included in the Operational plan, plus: "
                    "advanced SEO strategy including competitor analysis, link building, and content "
                    "gap analysis; professional blog content creation including research, writing, "
                    "and publication of SEO-optimized articles; A/B testing of landing pages, CTAs, "
                    "and key conversion points; ongoing conversion rate optimization with monthly "
                    "recommendations; a dedicated account manager as Client's single point of contact; "
                    "and bi-weekly strategy calls to review performance and align on priorities."
                ),
            },
            {
                "title": "Payment Terms",
                "content": (
                    "Client agrees to pay a one-time setup fee and recurring monthly service fee as "
                    "specified in the Plan Details section. Monthly fees are billed on the first of "
                    "each month and are due within fifteen (15) days of invoice date. Late payments "
                    "are subject to a 1.5% monthly finance charge. Provider reserves the right to "
                    "suspend services for accounts more than thirty (30) days past due."
                ),
            },
            {
                "title": "Term & Renewal",
                "content": (
                    "This Agreement shall commence on the Start Date and continue for the initial "
                    "term specified in the Plan Details. Unless either party provides written notice "
                    "of non-renewal at least thirty (30) days prior to the end of the current term, "
                    "this Agreement shall automatically renew for successive periods equal to the "
                    "initial term at the then-current rates."
                ),
            },
            {
                "title": "Termination",
                "content": (
                    "Either party may terminate this Agreement for cause upon thirty (30) days' "
                    "written notice if the other party materially breaches any provision and fails "
                    "to cure such breach within the notice period. Client may terminate for "
                    "convenience with the required notice period specified in the Plan Details, "
                    "subject to payment of any outstanding fees through the end of the notice period. "
                    "Upon termination, Provider shall deliver all Client content and assist with "
                    "migration for up to fifteen (15) business days."
                ),
            },
            {
                "title": "Intellectual Property",
                "content": (
                    "All custom design work, code, and content created specifically for Client "
                    "shall become Client's property upon full payment. Provider retains ownership "
                    "of proprietary tools, frameworks, and pre-existing code used in delivery. "
                    "Provider grants Client a perpetual, non-exclusive license to any Provider IP "
                    "incorporated into the deliverables. Client grants Provider permission to "
                    "display the completed work in Provider's portfolio unless otherwise agreed."
                ),
            },
            {
                "title": "Limitation of Liability",
                "content": (
                    "IN NO EVENT SHALL EITHER PARTY BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL, "
                    "CONSEQUENTIAL, OR PUNITIVE DAMAGES ARISING OUT OF OR RELATED TO THIS AGREEMENT. "
                    "PROVIDER'S TOTAL AGGREGATE LIABILITY SHALL NOT EXCEED THE TOTAL FEES PAID BY "
                    "CLIENT DURING THE TWELVE (12) MONTHS PRECEDING THE CLAIM. This limitation "
                    "applies regardless of the theory of liability, whether in contract, tort, or "
                    "otherwise."
                ),
            },
            {
                "title": "General Provisions",
                "content": (
                    "This Agreement constitutes the entire understanding between the parties and "
                    "supersedes all prior agreements. Any amendments must be in writing and signed "
                    "by both parties. This Agreement shall be governed by the laws of the State of "
                    "New York. If any provision is found unenforceable, the remaining provisions "
                    "shall continue in full force. Neither party may assign this Agreement without "
                    "the other party's written consent, except in connection with a merger or "
                    "acquisition. Notices shall be delivered via email to the addresses specified herein."
                ),
            },
        ],
    },
]


# ── Pydantic Models ──────────────────────────────────────────────────

class ContractCreate(BaseModel):
    template_id: int
    client_name: str
    client_email: EmailStr
    client_company: Optional[str] = None
    client_address: Optional[str] = None
    start_date: Optional[date] = None
    custom_terms: Optional[dict] = None


class ContractUpdate(BaseModel):
    client_name: Optional[str] = None
    client_email: Optional[EmailStr] = None
    client_company: Optional[str] = None
    client_address: Optional[str] = None
    monthly_price: Optional[float] = None
    setup_fee: Optional[float] = None
    contract_terms: Optional[dict] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[str] = None


class TemplateCreate(BaseModel):
    name: str
    plan_name: str
    monthly_price: float
    setup_fee: float = 0.0
    default_terms: Optional[dict] = None
    sections: Optional[list] = None


# ── Init / Seed ──────────────────────────────────────────────────────

async def init_contracts_tables():
    """Create tables, indexes, and seed templates if empty."""
    async with _session() as db:
        await db.execute(text(CONTRACTS_TABLE_SQL))
        await db.execute(text(TEMPLATES_TABLE_SQL))
        for idx_sql in INDEX_SQLS:
            await db.execute(text(idx_sql))
        await db.commit()

        # Seed templates if none exist
        result = await db.execute(text("SELECT COUNT(*) FROM public.contract_templates"))
        count = result.scalar()
        if count == 0:
            for tpl in SEED_TEMPLATES:
                await db.execute(
                    text("""
                        INSERT INTO public.contract_templates
                            (name, plan_name, monthly_price, setup_fee, default_terms, sections)
                        VALUES (:name, :plan_name, :monthly_price, :setup_fee,
                                :default_terms::jsonb, :sections::jsonb)
                    """),
                    {
                        "name": tpl["name"],
                        "plan_name": tpl["plan_name"],
                        "monthly_price": tpl["monthly_price"],
                        "setup_fee": tpl["setup_fee"],
                        "default_terms": _json_dumps(tpl["default_terms"]),
                        "sections": _json_dumps(tpl["sections"]),
                    },
                )
            await db.commit()
            logger.info("Seeded %d contract templates", len(SEED_TEMPLATES))

    logger.info("Contract tables initialized")


def _generate_contract_number() -> str:
    """Generate a unique contract number like SNT-2026-A3F9."""
    short_id = uuid.uuid4().hex[:4].upper()
    year = datetime.now(timezone.utc).year
    return f"SNT-{year}-{short_id}"


def _json_dumps(obj) -> str:
    import json
    return json.dumps(obj)


def _parse_json(val):
    import json
    if isinstance(val, str):
        return json.loads(val)
    return val


# ── Template Endpoints ───────────────────────────────────────────────

@router.get("/contracts/templates")
async def list_templates():
    """List all active contract templates."""
    async with _session() as db:
        result = await db.execute(
            text("""
                SELECT id, name, plan_name, monthly_price, setup_fee,
                       default_terms, sections, is_active, created_at
                FROM public.contract_templates
                WHERE is_active = TRUE
                ORDER BY monthly_price ASC
            """)
        )
        rows = result.mappings().all()
        return [
            {
                "id": r["id"],
                "name": r["name"],
                "plan_name": r["plan_name"],
                "monthly_price": float(r["monthly_price"]),
                "setup_fee": float(r["setup_fee"]),
                "default_terms": _parse_json(r["default_terms"]),
                "sections": _parse_json(r["sections"]),
                "is_active": r["is_active"],
                "created_at": str(r["created_at"]),
            }
            for r in rows
        ]


@router.post("/contracts/templates", status_code=201)
async def create_template(data: TemplateCreate):
    """Create a new contract template."""
    async with _session() as db:
        result = await db.execute(
            text("""
                INSERT INTO public.contract_templates
                    (name, plan_name, monthly_price, setup_fee, default_terms, sections)
                VALUES (:name, :plan_name, :monthly_price, :setup_fee,
                        :default_terms::jsonb, :sections::jsonb)
                RETURNING id, created_at
            """),
            {
                "name": data.name,
                "plan_name": data.plan_name,
                "monthly_price": data.monthly_price,
                "setup_fee": data.setup_fee,
                "default_terms": _json_dumps(data.default_terms or {}),
                "sections": _json_dumps(data.sections or []),
            },
        )
        row = result.mappings().fetchone()
        await db.commit()
        return {"id": row["id"], "created_at": str(row["created_at"]), "status": "created"}


# ── Contract Endpoints ───────────────────────────────────────────────

@router.get("/contracts")
async def list_contracts(
    status: Optional[str] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
):
    """List contracts with pagination and optional status filter."""
    offset = (page - 1) * per_page
    params: dict = {"limit": per_page, "offset": offset}
    where_clause = ""

    if status:
        if status not in VALID_STATUSES:
            raise HTTPException(400, f"Invalid status. Must be one of: {', '.join(sorted(VALID_STATUSES))}")
        where_clause = "WHERE c.status = :status"
        params["status"] = status

    async with _session() as db:
        # Get total count
        count_result = await db.execute(
            text(f"SELECT COUNT(*) FROM public.contracts c {where_clause}"), params
        )
        total = count_result.scalar()

        result = await db.execute(
            text(f"""
                SELECT c.id, c.contract_number, c.client_name, c.client_email,
                       c.client_company, c.plan_name, c.monthly_price, c.setup_fee,
                       c.status, c.start_date, c.end_date, c.created_at
                FROM public.contracts c
                {where_clause}
                ORDER BY c.created_at DESC
                LIMIT :limit OFFSET :offset
            """),
            params,
        )
        rows = result.mappings().all()

        return {
            "contracts": [
                {
                    "id": r["id"],
                    "contract_number": r["contract_number"],
                    "client_name": r["client_name"],
                    "client_email": r["client_email"],
                    "client_company": r["client_company"],
                    "plan_name": r["plan_name"],
                    "monthly_price": float(r["monthly_price"]),
                    "setup_fee": float(r["setup_fee"]),
                    "status": r["status"],
                    "start_date": str(r["start_date"]) if r["start_date"] else None,
                    "end_date": str(r["end_date"]) if r["end_date"] else None,
                    "created_at": str(r["created_at"]),
                }
                for r in rows
            ],
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": (total + per_page - 1) // per_page if total else 0,
        }


@router.post("/contracts", status_code=201)
async def create_contract(data: ContractCreate):
    """Create a new contract from a template."""
    async with _session() as db:
        # Fetch template
        tpl_result = await db.execute(
            text("SELECT * FROM public.contract_templates WHERE id = :id AND is_active = TRUE"),
            {"id": data.template_id},
        )
        tpl = tpl_result.mappings().fetchone()
        if not tpl:
            raise HTTPException(404, "Template not found or inactive")

        default_terms = _parse_json(tpl["default_terms"])
        contract_terms = {**default_terms}
        if data.custom_terms:
            contract_terms.update(data.custom_terms)

        term_months = contract_terms.get("term_months", 12)
        start = data.start_date or date.today()
        end = start + timedelta(days=term_months * 30)
        contract_number = _generate_contract_number()

        result = await db.execute(
            text("""
                INSERT INTO public.contracts
                    (contract_number, client_name, client_email, client_company, client_address,
                     template_id, plan_name, monthly_price, setup_fee, contract_terms,
                     status, start_date, end_date)
                VALUES (:contract_number, :client_name, :client_email, :client_company,
                        :client_address, :template_id, :plan_name, :monthly_price, :setup_fee,
                        :contract_terms::jsonb, 'draft', :start_date, :end_date)
                RETURNING id, contract_number, created_at
            """),
            {
                "contract_number": contract_number,
                "client_name": data.client_name,
                "client_email": data.client_email,
                "client_company": data.client_company,
                "client_address": data.client_address,
                "template_id": data.template_id,
                "plan_name": tpl["plan_name"],
                "monthly_price": float(tpl["monthly_price"]),
                "setup_fee": float(tpl["setup_fee"]),
                "contract_terms": _json_dumps(contract_terms),
                "start_date": start,
                "end_date": end,
            },
        )
        row = result.mappings().fetchone()
        await db.commit()

        return {
            "id": row["id"],
            "contract_number": row["contract_number"],
            "plan_name": tpl["plan_name"],
            "status": "draft",
            "created_at": str(row["created_at"]),
        }


@router.get("/contracts/{contract_id}")
async def get_contract(contract_id: int):
    """Get full contract details."""
    async with _session() as db:
        result = await db.execute(
            text("SELECT * FROM public.contracts WHERE id = :id"),
            {"id": contract_id},
        )
        row = result.mappings().fetchone()
        if not row:
            raise HTTPException(404, "Contract not found")

        return {
            "id": row["id"],
            "contract_number": row["contract_number"],
            "client_name": row["client_name"],
            "client_email": row["client_email"],
            "client_company": row["client_company"],
            "client_address": row["client_address"],
            "template_id": row["template_id"],
            "plan_name": row["plan_name"],
            "monthly_price": float(row["monthly_price"]),
            "setup_fee": float(row["setup_fee"]),
            "contract_terms": _parse_json(row["contract_terms"]),
            "status": row["status"],
            "signed_at": str(row["signed_at"]) if row["signed_at"] else None,
            "start_date": str(row["start_date"]) if row["start_date"] else None,
            "end_date": str(row["end_date"]) if row["end_date"] else None,
            "created_at": str(row["created_at"]),
            "updated_at": str(row["updated_at"]),
        }


@router.patch("/contracts/{contract_id}")
async def update_contract(contract_id: int, data: ContractUpdate):
    """Update a contract (only draft/sent contracts can be edited)."""
    async with _session() as db:
        # Check current status
        existing = await db.execute(
            text("SELECT status FROM public.contracts WHERE id = :id"),
            {"id": contract_id},
        )
        row = existing.mappings().fetchone()
        if not row:
            raise HTTPException(404, "Contract not found")
        if row["status"] not in ("draft", "sent"):
            raise HTTPException(400, f"Cannot edit contract in '{row['status']}' status")

        if data.status and data.status not in VALID_STATUSES:
            raise HTTPException(400, f"Invalid status. Must be one of: {', '.join(sorted(VALID_STATUSES))}")

        # Build dynamic SET clause
        updates = []
        params: dict = {"id": contract_id}
        field_map = {
            "client_name": data.client_name,
            "client_email": data.client_email,
            "client_company": data.client_company,
            "client_address": data.client_address,
            "monthly_price": data.monthly_price,
            "setup_fee": data.setup_fee,
            "start_date": data.start_date,
            "end_date": data.end_date,
            "status": data.status,
        }
        for field, value in field_map.items():
            if value is not None:
                updates.append(f"{field} = :{field}")
                params[field] = value

        if data.contract_terms is not None:
            updates.append("contract_terms = :contract_terms::jsonb")
            params["contract_terms"] = _json_dumps(data.contract_terms)

        if not updates:
            raise HTTPException(400, "No fields to update")

        updates.append("updated_at = now()")
        set_clause = ", ".join(updates)

        await db.execute(
            text(f"UPDATE public.contracts SET {set_clause} WHERE id = :id"),
            params,
        )
        await db.commit()

        return {"id": contract_id, "status": "updated"}


@router.get("/contracts/{contract_id}/html", response_class=HTMLResponse)
async def get_contract_html(contract_id: int):
    """Render the full contract as a professional, printable HTML document."""
    async with _session() as db:
        # Fetch contract
        result = await db.execute(
            text("SELECT * FROM public.contracts WHERE id = :id"),
            {"id": contract_id},
        )
        contract = result.mappings().fetchone()
        if not contract:
            raise HTTPException(404, "Contract not found")

        # Fetch template sections
        sections = []
        if contract["template_id"]:
            tpl_result = await db.execute(
                text("SELECT sections FROM public.contract_templates WHERE id = :id"),
                {"id": contract["template_id"]},
            )
            tpl_row = tpl_result.mappings().fetchone()
            if tpl_row:
                sections = _parse_json(tpl_row["sections"])

        terms = _parse_json(contract["contract_terms"])
        includes = terms.get("includes", [])
        term_months = terms.get("term_months", 12)
        auto_renew = terms.get("auto_renew", True)
        cancellation_days = terms.get("cancellation_notice_days", 30)

        # Build includes list HTML
        includes_html = "".join(f"<li>{item}</li>" for item in includes)

        # Build sections HTML
        sections_html = ""
        for i, section in enumerate(sections, start=1):
            sections_html += f"""
            <div class="section">
                <h2>{i}. {section['title']}</h2>
                <p>{section['content']}</p>
            </div>
            """

        start_date_str = str(contract["start_date"]) if contract["start_date"] else "_______________"
        end_date_str = str(contract["end_date"]) if contract["end_date"] else "_______________"
        today_str = date.today().strftime("%B %d, %Y")

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Service Agreement — {contract['contract_number']}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Georgia', 'Times New Roman', serif;
            color: #1a1a2e;
            line-height: 1.7;
            background: #fff;
            padding: 0;
        }}
        .contract {{
            max-width: 8.5in;
            margin: 0 auto;
            padding: 1in;
        }}
        @media print {{
            body {{ padding: 0; }}
            .contract {{ padding: 0.75in 1in; }}
            .no-print {{ display: none; }}
        }}

        /* Header */
        .header {{
            text-align: center;
            border-bottom: 3px double #1a1a2e;
            padding-bottom: 24px;
            margin-bottom: 32px;
        }}
        .header .company-name {{
            font-size: 28px;
            font-weight: bold;
            letter-spacing: 3px;
            text-transform: uppercase;
            color: #1a1a2e;
        }}
        .header .tagline {{
            font-size: 11px;
            letter-spacing: 2px;
            text-transform: uppercase;
            color: #666;
            margin-top: 4px;
        }}
        .header .doc-title {{
            font-size: 18px;
            font-weight: bold;
            margin-top: 20px;
            letter-spacing: 1px;
        }}
        .header .contract-number {{
            font-size: 13px;
            color: #555;
            margin-top: 4px;
        }}

        /* Sections */
        .section {{
            margin-bottom: 24px;
        }}
        .section h2 {{
            font-size: 14px;
            font-weight: bold;
            text-transform: uppercase;
            letter-spacing: 1px;
            border-bottom: 1px solid #ccc;
            padding-bottom: 6px;
            margin-bottom: 12px;
            color: #1a1a2e;
        }}
        .section p {{
            font-size: 13px;
            text-align: justify;
        }}

        /* Parties */
        .parties-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 32px;
            margin: 20px 0;
        }}
        .party {{
            font-size: 13px;
        }}
        .party .label {{
            font-weight: bold;
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: #555;
            margin-bottom: 6px;
        }}
        .party .name {{
            font-size: 15px;
            font-weight: bold;
        }}
        .party .detail {{
            color: #444;
            margin-top: 2px;
        }}

        /* Plan table */
        .plan-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 16px 0;
            font-size: 13px;
        }}
        .plan-table th {{
            background: #1a1a2e;
            color: #fff;
            padding: 10px 14px;
            text-align: left;
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .plan-table td {{
            padding: 10px 14px;
            border-bottom: 1px solid #e0e0e0;
        }}
        .plan-table tr:nth-child(even) td {{
            background: #f8f8fa;
        }}
        .plan-table .amount {{
            font-weight: bold;
            text-align: right;
            white-space: nowrap;
        }}

        /* Includes */
        .includes-list {{
            list-style: none;
            padding: 0;
            font-size: 13px;
        }}
        .includes-list li {{
            padding: 5px 0 5px 20px;
            position: relative;
        }}
        .includes-list li::before {{
            content: "✓";
            position: absolute;
            left: 0;
            color: #2d6a4f;
            font-weight: bold;
        }}

        /* Signatures */
        .signatures {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 48px;
            margin-top: 48px;
            padding-top: 24px;
        }}
        .sig-block {{
            font-size: 13px;
        }}
        .sig-line {{
            border-bottom: 1px solid #1a1a2e;
            height: 40px;
            margin-bottom: 6px;
            margin-top: 24px;
        }}
        .sig-label {{
            font-size: 11px;
            color: #555;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .sig-name {{
            margin-top: 12px;
            font-weight: bold;
        }}

        /* Footer */
        .footer {{
            margin-top: 48px;
            padding-top: 16px;
            border-top: 1px solid #ccc;
            text-align: center;
            font-size: 11px;
            color: #888;
        }}
    </style>
</head>
<body>
    <div class="contract">
        <div class="header">
            <div class="company-name">Stuff N Things</div>
            <div class="tagline">Digital Solutions &amp; Web Services</div>
            <div class="doc-title">Website-as-a-Service Agreement</div>
            <div class="contract-number">Contract #{contract['contract_number']}</div>
        </div>

        <div class="section">
            <h2>Parties</h2>
            <p>This Website-as-a-Service Agreement ("Agreement") is entered into as of
               <strong>{today_str}</strong> by and between:</p>
            <div class="parties-grid">
                <div class="party">
                    <div class="label">Provider</div>
                    <div class="name">Stuff N Things LLC</div>
                    <div class="detail">Digital Solutions &amp; Web Services</div>
                </div>
                <div class="party">
                    <div class="label">Client</div>
                    <div class="name">{contract['client_name']}</div>
                    {f'<div class="detail">{contract["client_company"]}</div>' if contract['client_company'] else ''}
                    {f'<div class="detail">{contract["client_email"]}</div>' if contract['client_email'] else ''}
                    {f'<div class="detail">{contract["client_address"]}</div>' if contract['client_address'] else ''}
                </div>
            </div>
        </div>

        <div class="section">
            <h2>Plan Details</h2>
            <table class="plan-table">
                <tr>
                    <th>Item</th>
                    <th style="text-align:right">Amount</th>
                </tr>
                <tr>
                    <td><strong>{contract['plan_name']}</strong> Plan — Monthly Service Fee</td>
                    <td class="amount">${float(contract['monthly_price']):,.2f}/mo</td>
                </tr>
                <tr>
                    <td>One-Time Setup &amp; Development Fee</td>
                    <td class="amount">${float(contract['setup_fee']):,.2f}</td>
                </tr>
                <tr>
                    <td>Contract Term</td>
                    <td class="amount">{term_months} months</td>
                </tr>
                <tr>
                    <td>Auto-Renewal</td>
                    <td class="amount">{'Yes' if auto_renew else 'No'}</td>
                </tr>
                <tr>
                    <td>Cancellation Notice</td>
                    <td class="amount">{cancellation_days} days</td>
                </tr>
                <tr>
                    <td>Start Date</td>
                    <td class="amount">{start_date_str}</td>
                </tr>
                <tr>
                    <td>End Date</td>
                    <td class="amount">{end_date_str}</td>
                </tr>
                <tr>
                    <td><strong>Total First-Year Value</strong></td>
                    <td class="amount"><strong>${(float(contract['monthly_price']) * term_months + float(contract['setup_fee'])):,.2f}</strong></td>
                </tr>
            </table>

            <h3 style="font-size:12px; text-transform:uppercase; letter-spacing:1px; margin:16px 0 8px; color:#555;">Included Services</h3>
            <ul class="includes-list">
                {includes_html}
            </ul>
        </div>

        {sections_html}

        <div class="signatures">
            <div class="sig-block">
                <div class="sig-label">Provider</div>
                <div class="sig-line"></div>
                <div class="sig-label">Authorized Signature</div>
                <div class="sig-name">Stuff N Things LLC</div>
                <div class="sig-line" style="width:60%; margin-top:16px;"></div>
                <div class="sig-label">Date</div>
            </div>
            <div class="sig-block">
                <div class="sig-label">Client</div>
                <div class="sig-line"></div>
                <div class="sig-label">Authorized Signature</div>
                <div class="sig-name">{contract['client_name']}</div>
                {f'<div style="font-size:12px;color:#555;">{contract["client_company"]}</div>' if contract['client_company'] else ''}
                <div class="sig-line" style="width:60%; margin-top:16px;"></div>
                <div class="sig-label">Date</div>
            </div>
        </div>

        <div class="footer">
            <p>Stuff N Things LLC — Website-as-a-Service Agreement — {contract['contract_number']}</p>
            <p>This document is confidential and intended solely for the named parties.</p>
        </div>
    </div>
</body>
</html>"""

        return HTMLResponse(content=html)


@router.post("/contracts/{contract_id}/send")
async def send_contract(contract_id: int):
    """Email the contract to the client."""
    async with _session() as db:
        result = await db.execute(
            text("SELECT id, contract_number, client_name, client_email, plan_name, status FROM public.contracts WHERE id = :id"),
            {"id": contract_id},
        )
        contract = result.mappings().fetchone()
        if not contract:
            raise HTTPException(404, "Contract not found")
        if contract["status"] in ("signed", "active", "cancelled"):
            raise HTTPException(400, f"Cannot send contract in '{contract['status']}' status")

        # Build email
        subject = f"Your {contract['plan_name']} Service Agreement — {contract['contract_number']}"
        html_body = f"""
        <div style="font-family:system-ui;max-width:600px;margin:0 auto;padding:32px;">
            <h2 style="color:#1a1a2e;">Your Service Agreement is Ready</h2>
            <p>Hi {contract['client_name']},</p>
            <p>Your <strong>{contract['plan_name']}</strong> Website-as-a-Service agreement
               (<strong>{contract['contract_number']}</strong>) is ready for your review.</p>
            <p>Please review the agreement and let us know if you have any questions or
               would like to proceed.</p>
            <p style="margin-top:24px;">
                <a href="https://warroom.stuffnthings.io/contracts/{contract['id']}/view"
                   style="background:#1a1a2e;color:#fff;padding:12px 24px;text-decoration:none;
                          border-radius:6px;display:inline-block;">
                    Review Agreement
                </a>
            </p>
            <p style="color:#888;font-size:13px;margin-top:32px;">
                — The Stuff N Things Team
            </p>
        </div>
        """

        sent = _send_email(contract["client_email"], subject, html_body)

        # Update status to 'sent'
        await db.execute(
            text("UPDATE public.contracts SET status = 'sent', updated_at = now() WHERE id = :id"),
            {"id": contract_id},
        )
        await db.commit()

        return {
            "id": contract_id,
            "status": "sent",
            "email_sent": sent,
            "recipient": contract["client_email"],
        }


@router.post("/contracts/{contract_id}/mark-signed")
async def mark_contract_signed(contract_id: int):
    """Mark a contract as signed and set it active."""
    async with _session() as db:
        result = await db.execute(
            text("SELECT id, status FROM public.contracts WHERE id = :id"),
            {"id": contract_id},
        )
        contract = result.mappings().fetchone()
        if not contract:
            raise HTTPException(404, "Contract not found")
        if contract["status"] in ("active", "cancelled", "expired"):
            raise HTTPException(400, f"Cannot sign contract in '{contract['status']}' status")

        await db.execute(
            text("""
                UPDATE public.contracts
                SET status = 'signed', signed_at = now(), updated_at = now()
                WHERE id = :id
            """),
            {"id": contract_id},
        )
        await db.commit()

        return {"id": contract_id, "status": "signed", "signed_at": str(datetime.now(timezone.utc))}


@router.post("/contracts/{contract_id}/export-google-doc")
async def export_to_google_doc(contract_id: int):
    """Export contract as a Google Doc for eSignature via Google Workspace.

    Flow: War Room generates contract → exports to Google Docs → user opens in
    Google Docs → Tools → eSignature → adds signers → Google handles signing
    with identity verification, timestamps, and legally binding signatures.

    Requires google_oauth_client_id/secret in settings + Google Docs API enabled.
    Uses the same OAuth tokens as Calendar/Gmail.
    """
    import httpx
    import json

    # Load contract
    async with _session() as db:
        result = await db.execute(
            text("SELECT * FROM public.contracts WHERE id = :id"),
            {"id": contract_id},
        )
        contract = result.mappings().fetchone()
        if not contract:
            raise HTTPException(404, "Contract not found")

    # Load Google OAuth tokens (reuse Calendar tokens since they include Drive scope)
    # Fall back to Gmail tokens
    token_file = None
    for path in ["/tmp/warroom_google_cal_tokens.json", "/tmp/warroom_gmail_tokens.json"]:
        try:
            with open(path) as f:
                tokens = json.load(f)
                if tokens.get("access_token"):
                    token_file = tokens
                    break
        except (FileNotFoundError, json.JSONDecodeError):
            continue

    if not token_file:
        raise HTTPException(
            503,
            "No Google OAuth tokens found. Connect Google Calendar or Gmail first in Settings → Email & Calendar.",
        )

    access_token = token_file["access_token"]

    # Load contract terms
    terms = contract["contract_terms"] if isinstance(contract["contract_terms"], dict) else {}
    includes = terms.get("includes", [])

    # Build document content as Google Docs API requests
    title = f"Contract {contract['contract_number']} - {contract['client_company'] or contract['client_name']}"

    # Create the Google Doc
    async with httpx.AsyncClient(timeout=30) as client:
        # Step 1: Create empty doc
        create_resp = await client.post(
            "https://docs.googleapis.com/v1/documents",
            headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
            json={"title": title},
        )
        if create_resp.status_code == 401:
            raise HTTPException(401, "Google token expired. Reconnect Google Calendar or Gmail in Settings.")
        if create_resp.status_code != 200:
            logger.error("Google Docs create failed: %s", create_resp.text)
            raise HTTPException(502, f"Failed to create Google Doc: {create_resp.status_code}")

        doc = create_resp.json()
        doc_id = doc["documentId"]
        doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"

        # Step 2: Insert contract content as plain text (structured for eSignature)
        content_lines = [
            "WEBSITE-AS-A-SERVICE AGREEMENT\n\n",
            f"Contract: {contract['contract_number']}\n",
            f"Date: {contract.get('start_date', datetime.now().strftime('%Y-%m-%d'))}\n\n",
            "PARTIES\n\n",
            "Service Provider:\n",
            "Stuff N Things LLC\n",
            "stuffnthings.io\n\n",
            "Client:\n",
            f"{contract['client_name']}\n",
            f"{contract.get('client_company', '') or ''}\n",
            f"{contract.get('client_email', '')}\n",
            f"{contract.get('client_address', '') or ''}\n\n",
            "PLAN DETAILS\n\n",
            f"Plan: {contract.get('plan_name', 'Custom')}\n",
            f"Monthly Fee: ${float(contract.get('monthly_price', 0)):,.2f}\n",
            f"Setup Fee: ${float(contract.get('setup_fee', 0)):,.2f}\n",
            f"Term: {terms.get('term_months', 12)} months\n",
            f"Auto-Renew: {'Yes' if terms.get('auto_renew', True) else 'No'}\n\n",
            "INCLUDED SERVICES\n\n",
        ]
        for svc in includes:
            content_lines.append(f"• {svc.replace('_', ' ').title()}\n")

        content_lines.extend([
            "\n\nSCOPE OF SERVICES\n\n",
            "Provider shall design, develop, host, and maintain a professional website for Client "
            "as specified in the selected plan. All services include managed hosting with 99.9% "
            "uptime guarantee, SSL certificate, daily backups, and ongoing technical support.\n\n",
            "PAYMENT TERMS\n\n",
            f"Client shall pay a one-time setup fee of ${float(contract.get('setup_fee', 0)):,.2f} "
            f"upon execution of this Agreement, followed by monthly payments of "
            f"${float(contract.get('monthly_price', 0)):,.2f} due on the 1st of each month.\n\n",
            "TERM AND RENEWAL\n\n",
            f"This Agreement shall commence on the Start Date and continue for an initial term of "
            f"{terms.get('term_months', 12)} months. ",
        ])
        if terms.get("auto_renew", True):
            content_lines.append(
                f"The Agreement shall automatically renew for successive 12-month periods unless "
                f"either party provides {terms.get('cancellation_notice_days', 30)} days written notice.\n\n"
            )
        else:
            content_lines.append("The Agreement does not auto-renew.\n\n")

        content_lines.extend([
            "SIGNATURES\n\n",
            "Service Provider: ________________________  Date: ____________\n",
            "Name: Stuff N Things LLC\n\n",
            f"Client: ________________________  Date: ____________\n",
            f"Name: {contract['client_name']}\n",
        ])

        full_text = "".join(content_lines)

        # Insert text into the doc
        update_resp = await client.post(
            f"https://docs.googleapis.com/v1/documents/{doc_id}:batchUpdate",
            headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
            json={
                "requests": [
                    {
                        "insertText": {
                            "location": {"index": 1},
                            "text": full_text,
                        }
                    }
                ]
            },
        )
        if update_resp.status_code != 200:
            logger.error("Google Docs update failed: %s", update_resp.text)
            # Doc was created but content insert failed — still return the URL
            return {
                "doc_id": doc_id,
                "doc_url": doc_url,
                "warning": "Document created but content insertion failed. Add content manually.",
            }

    return {
        "doc_id": doc_id,
        "doc_url": doc_url,
        "title": title,
        "message": "Contract exported to Google Docs. Open the doc and use Tools → eSignature to request signatures.",
    }
