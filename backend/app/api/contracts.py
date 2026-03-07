"""WaaS Contract Generator — professional website-as-a-service contracts from templates.

Tables: public.contracts, public.contract_templates (auto-created on startup).
Generates printable HTML contracts with Stuff N Things branding.
"""
import asyncio
import json
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
from app.api.contract_templates_data import SEED_TEMPLATES
from app.services.notify import send_notification

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
    "CREATE INDEX IF NOT EXISTS idx_contracts_deal_stage ON public.contracts (deal_stage)",
    # Unique constraint on template name for ON CONFLICT seeding
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_contract_templates_name ON public.contract_templates (name)",
]

# Deal pipeline columns — added via ALTER TABLE so existing DBs get them too
DEAL_PIPELINE_ALTERS = [
    "ALTER TABLE public.contracts ADD COLUMN IF NOT EXISTS deal_stage VARCHAR(30) DEFAULT 'draft'",
    "ALTER TABLE public.contracts ADD COLUMN IF NOT EXISTS google_doc_id TEXT",
    "ALTER TABLE public.contracts ADD COLUMN IF NOT EXISTS google_doc_url TEXT",
    "ALTER TABLE public.contracts ADD COLUMN IF NOT EXISTS esign_requested_at TIMESTAMP",
    "ALTER TABLE public.contracts ADD COLUMN IF NOT EXISTS esign_email_sent_at TIMESTAMP",
    "ALTER TABLE public.contracts ADD COLUMN IF NOT EXISTS esign_email_read_at TIMESTAMP",
    "ALTER TABLE public.contracts ADD COLUMN IF NOT EXISTS esign_signed_at TIMESTAMP",
    "ALTER TABLE public.contracts ADD COLUMN IF NOT EXISTS followup_sent_at TIMESTAMP",
    "ALTER TABLE public.contracts ADD COLUMN IF NOT EXISTS followup_count INTEGER DEFAULT 0",
    "ALTER TABLE public.contracts ADD COLUMN IF NOT EXISTS congratulation_sent_at TIMESTAMP",
    "ALTER TABLE public.contracts ADD COLUMN IF NOT EXISTS deal_notes TEXT",
    "ALTER TABLE public.contracts ADD COLUMN IF NOT EXISTS deal_history JSONB DEFAULT '[]'",
]

VALID_STATUSES = {"draft", "sent", "viewed", "signed", "active", "expired", "cancelled"}

VALID_DEAL_STAGES = {
    "draft", "exported", "sent", "delivered", "read",
    "signing", "signed", "active", "expired", "cancelled",
}

# Valid stage transitions — maps current stage to allowed next stages
STAGE_TRANSITIONS = {
    "draft":     {"exported", "cancelled"},
    "exported":  {"sent", "cancelled"},
    "sent":      {"delivered", "read", "signing", "signed", "cancelled"},
    "delivered": {"read", "signing", "signed", "cancelled"},
    "read":      {"signing", "signed", "cancelled"},
    "signing":   {"signed", "cancelled"},
    "signed":    {"active"},
    "active":    {"expired", "cancelled"},
    "expired":   set(),
    "cancelled": set(),
}

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
    """Create tables, indexes, deal pipeline columns, and seed templates if empty."""
    async with _session() as db:
        await db.execute(text(CONTRACTS_TABLE_SQL))
        await db.execute(text(TEMPLATES_TABLE_SQL))
        for alter_sql in DEAL_PIPELINE_ALTERS:
            await db.execute(text(alter_sql))
        for idx_sql in INDEX_SQLS:
            await db.execute(text(idx_sql))
        await db.commit()

        # Seed templates — ON CONFLICT (name) DO NOTHING prevents duplicates on restart
        seeded = 0
        for tpl in SEED_TEMPLATES:
            result = await db.execute(
                text("""
                    INSERT INTO public.contract_templates
                        (name, plan_name, monthly_price, setup_fee, default_terms, sections)
                    VALUES (:name, :plan_name, :monthly_price, :setup_fee,
                            CAST(:default_terms AS jsonb), CAST(:sections AS jsonb))
                    ON CONFLICT (name) DO NOTHING
                    RETURNING id
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
            if result.fetchone():
                seeded += 1
        await db.commit()
        if seeded:
            logger.info("Seeded %d new contract templates (%d total defined)", seeded, len(SEED_TEMPLATES))

    logger.info("Contract tables initialized")


def _generate_contract_number() -> str:
    """Generate a unique contract number like SNT-2026-A3F9."""
    short_id = uuid.uuid4().hex[:4].upper()
    year = datetime.now(timezone.utc).year
    return f"SNT-{year}-{short_id}"


def _json_dumps(obj) -> str:
    return json.dumps(obj)


def _parse_json(val):
    if isinstance(val, str):
        return json.loads(val)
    return val


async def _add_deal_event(db, contract_id: int, stage: str, note: str = ""):
    """Append an event to deal_history and update deal_stage."""
    await db.execute(text("""
        UPDATE public.contracts SET
            deal_stage = :stage,
            deal_history = deal_history || CAST(:event AS jsonb),
            updated_at = now()
        WHERE id = :id
    """), {
        "id": contract_id,
        "stage": stage,
        "event": json.dumps({"stage": stage, "timestamp": datetime.now(timezone.utc).isoformat(), "note": note}),
    })


async def _get_business_settings() -> dict:
    """Load business settings from the DB.

    Queries both ``business_*`` keys and legacy ``company_*`` / ``your_*`` keys,
    then normalises everything under the ``business_`` prefix so callers can
    always use ``business_name``, ``business_phone``, etc.
    """
    async with _session() as db:
        result = await db.execute(
            text(
                "SELECT key, value FROM public.settings "
                "WHERE key LIKE 'business_%' OR key LIKE 'company_%' "
                "OR key IN ('your_phone', 'your_name')"
            )
        )
        raw = {r[0]: r[1] for r in result.fetchall()}

    # Normalise: prefer business_* but fall back to company_* / your_*
    out: dict[str, str] = {}
    for biz_key, fallbacks in [
        ("business_name", ["company_name"]),
        ("business_website", ["company_website"]),
        ("business_email", ["company_email"]),
        ("business_address", ["company_address"]),
        ("business_phone", ["company_phone", "your_phone"]),
        ("business_tagline", []),
    ]:
        val = raw.get(biz_key, "")
        if not val:
            for fb in fallbacks:
                val = raw.get(fb, "")
                if val:
                    break
        out[biz_key] = val

    # Also pass through any other business_* keys verbatim
    for k, v in raw.items():
        if k.startswith("business_") and k not in out:
            out[k] = v

    return out


async def _get_contract_or_404(db, contract_id: int):
    """Fetch a contract by ID or raise 404."""
    result = await db.execute(
        text("SELECT * FROM public.contracts WHERE id = :id"),
        {"id": contract_id},
    )
    row = result.mappings().fetchone()
    if not row:
        raise HTTPException(404, "Contract not found")
    return row


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
                        CAST(:default_terms AS jsonb), CAST(:sections AS jsonb))
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
                        CAST(:contract_terms AS jsonb), 'draft', :start_date, :end_date)
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
    """Get full contract details including deal pipeline state."""
    async with _session() as db:
        contract = await _get_contract_or_404(db, contract_id)

        return {
            "id": contract["id"],
            "contract_number": contract["contract_number"],
            "client_name": contract["client_name"],
            "client_email": contract["client_email"],
            "client_company": contract["client_company"],
            "client_address": contract["client_address"],
            "template_id": contract["template_id"],
            "plan_name": contract["plan_name"],
            "monthly_price": float(contract["monthly_price"]),
            "setup_fee": float(contract["setup_fee"]),
            "contract_terms": _parse_json(contract["contract_terms"]),
            "status": contract["status"],
            "deal_stage": contract.get("deal_stage", "draft"),
            "google_doc_id": contract.get("google_doc_id"),
            "google_doc_url": contract.get("google_doc_url"),
            "esign_email_sent_at": str(contract["esign_email_sent_at"]) if contract.get("esign_email_sent_at") else None,
            "esign_signed_at": str(contract["esign_signed_at"]) if contract.get("esign_signed_at") else None,
            "followup_count": contract.get("followup_count", 0),
            "followup_sent_at": str(contract["followup_sent_at"]) if contract.get("followup_sent_at") else None,
            "congratulation_sent_at": str(contract["congratulation_sent_at"]) if contract.get("congratulation_sent_at") else None,
            "deal_notes": contract.get("deal_notes"),
            "deal_history": _parse_json(contract.get("deal_history", "[]")),
            "signed_at": str(contract["signed_at"]) if contract["signed_at"] else None,
            "start_date": str(contract["start_date"]) if contract["start_date"] else None,
            "end_date": str(contract["end_date"]) if contract["end_date"] else None,
            "created_at": str(contract["created_at"]),
            "updated_at": str(contract["updated_at"]),
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
            updates.append("contract_terms = CAST(:contract_terms AS jsonb)")
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

        # Load business settings for branding + placeholder replacement
        try:
            biz = await _get_business_settings()
        except Exception:
            biz = {}
        business_name = biz.get("business_name", "Stuff N Things")
        business_tagline = biz.get("business_tagline", "Digital Solutions & Web Services")
        business_address = biz.get("business_address", "")

        start_date_str = str(contract["start_date"]) if contract["start_date"] else "_______________"
        end_date_str = str(contract["end_date"]) if contract["end_date"] else "_______________"
        today_str = date.today().strftime("%B %d, %Y")

        # ── Placeholder replacement map ──────────────────────────
        _ph = {
            "{{business_name}}": business_name,
            "{{business_website}}": biz.get("business_website", ""),
            "{{business_email}}": biz.get("business_email", ""),
            "{{business_address}}": business_address,
            "{{business_phone}}": biz.get("business_phone", ""),
            "{{client_name}}": contract["client_name"] or "",
            "{{client_company}}": contract.get("client_company") or "",
            "{{client_email}}": contract["client_email"] or "",
            "{{client_address}}": contract.get("client_address") or "",
            "{{plan_name}}": contract["plan_name"] or "",
            "{{monthly_price}}": f"${float(contract['monthly_price']):,.2f}",
            "{{setup_fee}}": f"${float(contract['setup_fee']):,.2f}",
            "{{start_date}}": start_date_str,
            "{{end_date}}": end_date_str,
            "{{term_months}}": str(term_months),
        }

        def _fill(t: str) -> str:
            for k, v in _ph.items():
                t = t.replace(k, v)
            return t

        # Build includes list HTML
        includes_html = "".join(f"<li>{item}</li>" for item in includes)

        # Build sections HTML with placeholder replacement
        sections_html = ""
        for i, section in enumerate(sections, start=1):
            s_title = _fill(section['title'])
            s_content = _fill(section['content'])
            sections_html += f"""
            <div class="section">
                <h2>{i}. {s_title}</h2>
                <p>{s_content}</p>
            </div>
            """

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
            <div class="company-name">{business_name}</div>
            <div class="tagline">{business_tagline}</div>
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
                    <div class="name">{business_name} LLC</div>
                    <div class="detail">{business_tagline}</div>
                    {f'<div class="detail">{business_address}</div>' if business_address else ''}
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
                <div class="sig-name">{business_name} LLC</div>
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
            <p>{business_name} LLC — Website-as-a-Service Agreement — {contract['contract_number']}</p>
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

    # Load Google OAuth tokens from centralized token store (DB)
    from app.services.token_store import load_tokens
    google_tokens = await load_tokens("google_calendar") or await load_tokens("gmail")

    if not google_tokens or not google_tokens.get("access_token"):
        raise HTTPException(
            503,
            "No Google OAuth tokens found. Connect Google Calendar or Gmail first in Settings → Email & Calendar.",
        )

    access_token = google_tokens["access_token"]

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

    # Save doc info to contract and update deal stage
    async with _session() as db:
        await db.execute(text("""
            UPDATE public.contracts SET
                google_doc_id = :doc_id,
                google_doc_url = :doc_url,
                updated_at = now()
            WHERE id = :id
        """), {"id": contract_id, "doc_id": doc_id, "doc_url": doc_url})
        await _add_deal_event(db, contract_id, "exported", "Contract exported to Google Docs")
        await db.commit()

    return {
        "doc_id": doc_id,
        "doc_url": doc_url,
        "title": title,
        "message": "Contract exported to Google Docs. Open the doc and use Tools → eSignature to request signatures.",
    }


# ── Deal Pipeline Pydantic Models ────────────────────────────────────

class MarkStageRequest(BaseModel):
    stage: str
    note: Optional[str] = ""


# ── Deal Pipeline Endpoints ──────────────────────────────────────────

@router.post("/contracts/{contract_id}/send-for-signature")
async def send_for_signature(contract_id: int):
    """Send the contract to the client for eSignature review via email."""
    async with _session() as db:
        contract = await _get_contract_or_404(db, contract_id)

        if not contract.get("google_doc_url"):
            raise HTTPException(
                400,
                "Contract must be exported to Google Docs first. Use the export-google-doc endpoint.",
            )

        current_stage = contract.get("deal_stage", "draft")
        if current_stage not in ("exported", "sent"):
            raise HTTPException(
                400,
                f"Cannot send for signature from '{current_stage}' stage. Export the contract first.",
            )

        # Load business settings for email branding
        try:
            biz = await _get_business_settings()
        except Exception:
            biz = {}
        business_name = biz.get("business_name", "Stuff N Things")
        business_email = biz.get("business_email", "hello@stuffnthings.io")
        business_phone = biz.get("business_phone", "")

        plan_name = contract["plan_name"]
        client_name = contract["client_name"]
        doc_url = contract["google_doc_url"]

        subject = f"Contract Ready for Review - {plan_name} Agreement"
        html_body = f"""
        <div style="font-family: 'Segoe UI', system-ui, sans-serif; max-width: 600px; margin: 0 auto; padding: 40px 32px; color: #1a1a2e;">
            <div style="text-align: center; border-bottom: 2px solid #1a1a2e; padding-bottom: 20px; margin-bottom: 28px;">
                <h1 style="font-size: 22px; font-weight: bold; letter-spacing: 2px; text-transform: uppercase; margin: 0;">{business_name}</h1>
            </div>

            <p style="font-size: 15px; margin-bottom: 16px;">Hi {client_name},</p>

            <p style="font-size: 15px; line-height: 1.6; margin-bottom: 16px;">
                Your <strong>{plan_name}</strong> Website-as-a-Service agreement is ready for your review.
                We've prepared a detailed contract outlining the scope of services, pricing, and terms
                for your project.
            </p>

            <p style="font-size: 15px; line-height: 1.6; margin-bottom: 24px;">
                Please take a moment to review the agreement using the link below. When you're ready,
                you can sign directly in the document using Google Docs' built-in eSignature feature.
            </p>

            <div style="text-align: center; margin: 32px 0;">
                <a href="{doc_url}"
                   style="background: #1a1a2e; color: #ffffff; padding: 14px 32px; text-decoration: none;
                          border-radius: 6px; display: inline-block; font-size: 15px; font-weight: 600;
                          letter-spacing: 0.5px;">
                    Review &amp; Sign Contract
                </a>
            </div>

            <div style="background: #f8f8fa; border-left: 3px solid #1a1a2e; padding: 16px 20px; margin: 24px 0; border-radius: 0 6px 6px 0;">
                <p style="font-size: 13px; color: #555; margin: 0 0 8px 0; font-weight: 600;">How to sign:</p>
                <ol style="font-size: 13px; color: #555; margin: 0; padding-left: 18px; line-height: 1.8;">
                    <li>Click the button above to open the contract in Google Docs</li>
                    <li>Review all sections of the agreement</li>
                    <li>Go to <strong>Tools → eSignature</strong> to add your signature</li>
                    <li>Follow the prompts to complete the signing process</li>
                </ol>
            </div>

            <p style="font-size: 14px; line-height: 1.6; color: #555; margin-top: 24px;">
                If you have any questions or need changes to the agreement, don't hesitate to reach out.
                We're happy to discuss any details before you sign.
            </p>

            <div style="margin-top: 32px; padding-top: 20px; border-top: 1px solid #e0e0e0;">
                <p style="font-size: 14px; color: #333; margin: 0;">Best regards,</p>
                <p style="font-size: 14px; color: #333; font-weight: 600; margin: 4px 0 0 0;">The {business_name} Team</p>
                <p style="font-size: 13px; color: #888; margin: 4px 0 0 0;">{business_email}{f' | {business_phone}' if business_phone else ''}</p>
            </div>
        </div>
        """

        sent = await asyncio.to_thread(_send_email, contract["client_email"], subject, html_body)

        await db.execute(text("""
            UPDATE public.contracts SET
                esign_email_sent_at = now(),
                updated_at = now()
            WHERE id = :id
        """), {"id": contract_id})
        await _add_deal_event(db, contract_id, "sent", f"Contract sent to {contract['client_email']} for signature")
        await db.commit()

        return {
            "id": contract_id,
            "deal_stage": "sent",
            "email_sent": sent,
            "recipient": contract["client_email"],
        }


@router.post("/contracts/{contract_id}/mark-stage")
async def mark_deal_stage(contract_id: int, data: MarkStageRequest):
    """Manually update the deal stage (e.g., read, signing, signed)."""
    if data.stage not in VALID_DEAL_STAGES:
        raise HTTPException(400, f"Invalid stage. Must be one of: {', '.join(sorted(VALID_DEAL_STAGES))}")

    async with _session() as db:
        contract = await _get_contract_or_404(db, contract_id)
        current_stage = contract.get("deal_stage", "draft")

        # Validate transition
        allowed = STAGE_TRANSITIONS.get(current_stage, set())
        if data.stage not in allowed:
            raise HTTPException(
                400,
                f"Cannot transition from '{current_stage}' to '{data.stage}'. "
                f"Allowed transitions: {', '.join(sorted(allowed)) if allowed else 'none'}",
            )

        extra_updates = ""
        if data.stage == "signed":
            extra_updates = ", esign_signed_at = now(), status = 'signed', signed_at = now()"
        elif data.stage == "read":
            extra_updates = ", esign_email_read_at = now()"

        await db.execute(text(f"""
            UPDATE public.contracts SET
                deal_stage = :stage,
                updated_at = now()
                {extra_updates}
            WHERE id = :id
        """), {"id": contract_id, "stage": data.stage})
        await _add_deal_event(db, contract_id, data.stage, data.note or "")
        await db.commit()

        # Notification: contract stage change
        client_name = contract.get("client_name", "Unknown")
        notif_type = "success" if data.stage in ("signed", "active") else "info"
        await send_notification(
            type=notif_type,
            title=f"Contract: {client_name} → {data.stage}",
            message=data.note or f"Contract stage updated to {data.stage}",
            data={"contract_id": contract_id, "link": "/contracts"},
        )

        return {
            "id": contract_id,
            "deal_stage": data.stage,
            "note": data.note,
            "auto_congratulate": data.stage == "signed",
        }


@router.post("/contracts/{contract_id}/send-followup")
async def send_followup(contract_id: int):
    """Send a follow-up reminder email for an unsigned contract."""
    async with _session() as db:
        contract = await _get_contract_or_404(db, contract_id)

        current_stage = contract.get("deal_stage", "draft")
        if current_stage in ("draft", "exported", "signed", "active", "expired", "cancelled"):
            raise HTTPException(400, f"Cannot send follow-up for contract in '{current_stage}' stage")

        if not contract.get("google_doc_url"):
            raise HTTPException(400, "No Google Doc URL — export and send the contract first")

        try:
            biz = await _get_business_settings()
        except Exception:
            biz = {}
        business_name = biz.get("business_name", "Stuff N Things")
        business_email = biz.get("business_email", "hello@stuffnthings.io")
        business_phone = biz.get("business_phone", "")

        client_name = contract["client_name"]
        plan_name = contract["plan_name"]
        doc_url = contract["google_doc_url"]
        followup_num = (contract.get("followup_count") or 0) + 1

        subject = "Friendly Reminder: Contract Awaiting Your Signature"
        html_body = f"""
        <div style="font-family: 'Segoe UI', system-ui, sans-serif; max-width: 600px; margin: 0 auto; padding: 40px 32px; color: #1a1a2e;">
            <div style="text-align: center; border-bottom: 2px solid #1a1a2e; padding-bottom: 20px; margin-bottom: 28px;">
                <h1 style="font-size: 22px; font-weight: bold; letter-spacing: 2px; text-transform: uppercase; margin: 0;">{business_name}</h1>
            </div>

            <p style="font-size: 15px; margin-bottom: 16px;">Hi {client_name},</p>

            <p style="font-size: 15px; line-height: 1.6; margin-bottom: 16px;">
                Just a friendly reminder — your <strong>{plan_name}</strong> agreement is still
                awaiting your signature. We want to make sure you have everything you need to
                move forward.
            </p>

            <p style="font-size: 15px; line-height: 1.6; margin-bottom: 24px;">
                If you've had a chance to review the contract and have any questions or need
                any adjustments, we'd love to hear from you. Otherwise, you can sign at any
                time using the link below.
            </p>

            <div style="text-align: center; margin: 32px 0;">
                <a href="{doc_url}"
                   style="background: #1a1a2e; color: #ffffff; padding: 14px 32px; text-decoration: none;
                          border-radius: 6px; display: inline-block; font-size: 15px; font-weight: 600;">
                    Review &amp; Sign Contract
                </a>
            </div>

            <p style="font-size: 14px; line-height: 1.6; color: #555; margin-top: 24px;">
                We're excited to get started on your project and look forward to working together!
            </p>

            <div style="margin-top: 32px; padding-top: 20px; border-top: 1px solid #e0e0e0;">
                <p style="font-size: 14px; color: #333; margin: 0;">Warm regards,</p>
                <p style="font-size: 14px; color: #333; font-weight: 600; margin: 4px 0 0 0;">The {business_name} Team</p>
                <p style="font-size: 13px; color: #888; margin: 4px 0 0 0;">{business_email}{f' | {business_phone}' if business_phone else ''}</p>
            </div>
        </div>
        """

        sent = await asyncio.to_thread(_send_email, contract["client_email"], subject, html_body)

        await db.execute(text("""
            UPDATE public.contracts SET
                followup_sent_at = now(),
                followup_count = :count,
                updated_at = now()
            WHERE id = :id
        """), {"id": contract_id, "count": followup_num})
        await _add_deal_event(db, contract_id, current_stage, f"Follow-up #{followup_num} sent")
        await db.commit()

        return {
            "id": contract_id,
            "followup_count": followup_num,
            "email_sent": sent,
            "recipient": contract["client_email"],
        }


@router.post("/contracts/{contract_id}/send-congratulation")
async def send_congratulation(contract_id: int):
    """Send a welcome/congratulation email after the contract is signed."""
    async with _session() as db:
        contract = await _get_contract_or_404(db, contract_id)

        current_stage = contract.get("deal_stage", "draft")
        if current_stage not in ("signed", "active"):
            raise HTTPException(400, f"Cannot send congratulation for contract in '{current_stage}' stage. Must be signed first.")

        try:
            biz = await _get_business_settings()
        except Exception:
            biz = {}
        business_name = biz.get("business_name", "Stuff N Things")
        business_email = biz.get("business_email", "hello@stuffnthings.io")
        business_phone = biz.get("business_phone", "")
        business_address = biz.get("business_address", "")

        client_name = contract["client_name"]
        plan_name = contract["plan_name"]
        terms = _parse_json(contract["contract_terms"]) if contract["contract_terms"] else {}
        includes = terms.get("includes", [])

        includes_html = "".join(
            f'<li style="padding: 6px 0; font-size: 14px; color: #333;">✓ {item}</li>'
            for item in includes
        )

        subject = f"Welcome to {business_name}! Your {plan_name} Agreement is Active"
        html_body = f"""
        <div style="font-family: 'Segoe UI', system-ui, sans-serif; max-width: 600px; margin: 0 auto; padding: 40px 32px; color: #1a1a2e;">
            <div style="text-align: center; border-bottom: 2px solid #1a1a2e; padding-bottom: 20px; margin-bottom: 28px;">
                <h1 style="font-size: 22px; font-weight: bold; letter-spacing: 2px; text-transform: uppercase; margin: 0;">{business_name}</h1>
            </div>

            <div style="text-align: center; margin-bottom: 28px;">
                <span style="font-size: 48px;">🎉</span>
                <h2 style="font-size: 20px; color: #1a1a2e; margin: 12px 0 0 0;">Welcome Aboard!</h2>
            </div>

            <p style="font-size: 15px; margin-bottom: 16px;">Hi {client_name},</p>

            <p style="font-size: 15px; line-height: 1.6; margin-bottom: 16px;">
                Thank you for choosing <strong>{business_name}</strong>! Your <strong>{plan_name}</strong>
                agreement is now active, and we're thrilled to get started on your project.
            </p>

            <div style="background: #f0faf4; border: 1px solid #d4edda; border-radius: 8px; padding: 20px; margin: 24px 0;">
                <h3 style="font-size: 14px; text-transform: uppercase; letter-spacing: 1px; color: #2d6a4f; margin: 0 0 12px 0;">
                    Your {plan_name} Plan Includes
                </h3>
                <ul style="list-style: none; padding: 0; margin: 0;">
                    {includes_html}
                </ul>
            </div>

            <div style="background: #f8f8fa; border-radius: 8px; padding: 20px; margin: 24px 0;">
                <h3 style="font-size: 14px; text-transform: uppercase; letter-spacing: 1px; color: #555; margin: 0 0 12px 0;">
                    What Happens Next
                </h3>
                <ol style="font-size: 14px; line-height: 1.8; color: #333; padding-left: 18px; margin: 0;">
                    <li><strong>Kickoff Call</strong> — We'll reach out within 1-2 business days to schedule your onboarding call</li>
                    <li><strong>Discovery &amp; Planning</strong> — We'll gather your requirements, brand assets, and content</li>
                    <li><strong>Design &amp; Development</strong> — Our team builds your site with regular progress updates</li>
                    <li><strong>Review &amp; Launch</strong> — Final review, revisions, and go-live!</li>
                </ol>
            </div>

            <p style="font-size: 14px; line-height: 1.6; color: #555; margin-top: 24px;">
                If you have any questions in the meantime, don't hesitate to reach out.
                We're here to make this process smooth and enjoyable.
            </p>

            <div style="margin-top: 32px; padding-top: 20px; border-top: 1px solid #e0e0e0;">
                <p style="font-size: 14px; color: #333; margin: 0;">Excited to work with you,</p>
                <p style="font-size: 14px; color: #333; font-weight: 600; margin: 4px 0 0 0;">The {business_name} Team</p>
                <p style="font-size: 13px; color: #888; margin: 4px 0 0 0;">{business_email}{f' | {business_phone}' if business_phone else ''}</p>
                {f'<p style="font-size: 13px; color: #888; margin: 2px 0 0 0;">{business_address}</p>' if business_address else ''}
            </div>
        </div>
        """

        sent = await asyncio.to_thread(_send_email, contract["client_email"], subject, html_body)

        await db.execute(text("""
            UPDATE public.contracts SET
                congratulation_sent_at = now(),
                status = 'active',
                updated_at = now()
            WHERE id = :id
        """), {"id": contract_id})
        await _add_deal_event(db, contract_id, "active", "Welcome email sent, contract now active")
        await db.commit()

        return {
            "id": contract_id,
            "deal_stage": "active",
            "email_sent": sent,
            "recipient": contract["client_email"],
        }


@router.get("/contracts/{contract_id}/deal-timeline")
async def get_deal_timeline(contract_id: int):
    """Get the full deal history timeline with computed metrics."""
    async with _session() as db:
        contract = await _get_contract_or_404(db, contract_id)

        deal_history = _parse_json(contract.get("deal_history", "[]"))
        now = datetime.now(timezone.utc)

        # Compute metrics
        esign_sent = contract.get("esign_email_sent_at")
        followup_sent = contract.get("followup_sent_at")
        esign_signed = contract.get("esign_signed_at")

        days_since_sent = None
        if esign_sent:
            sent_dt = esign_sent if isinstance(esign_sent, datetime) else datetime.fromisoformat(str(esign_sent))
            if sent_dt.tzinfo is None:
                sent_dt = sent_dt.replace(tzinfo=timezone.utc)
            days_since_sent = (now - sent_dt).days

        days_since_last_followup = None
        if followup_sent:
            fu_dt = followup_sent if isinstance(followup_sent, datetime) else datetime.fromisoformat(str(followup_sent))
            if fu_dt.tzinfo is None:
                fu_dt = fu_dt.replace(tzinfo=timezone.utc)
            days_since_last_followup = (now - fu_dt).days

        # needs_followup: sent > 24hrs ago AND not signed AND no followup in last 24hrs
        is_signed = contract.get("deal_stage") in ("signed", "active")
        sent_over_24h = days_since_sent is not None and days_since_sent >= 1
        followup_recent = days_since_last_followup is not None and days_since_last_followup < 1
        needs_followup = sent_over_24h and not is_signed and not followup_recent

        return {
            "id": contract_id,
            "deal_stage": contract.get("deal_stage", "draft"),
            "deal_history": deal_history,
            "metrics": {
                "days_since_sent": days_since_sent,
                "days_since_last_followup": days_since_last_followup,
                "needs_followup": needs_followup,
                "total_followups": contract.get("followup_count", 0),
            },
        }
