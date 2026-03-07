"""Invoicing system — manage invoices for client billing.

Tables: public.invoices, public.invoice_templates (auto-created on startup).
Statuses: draft, sent, viewed, paid, overdue, cancelled.
"""
import asyncio
import json
import logging
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.services.email import _send_email
from app.services.notify import send_notification

logger = logging.getLogger(__name__)

# ── DB Setup ─────────────────────────────────────────────────────────
DB_URL = "postgresql+asyncpg://friday:friday-brain2-2026@10.0.0.11:5433/knowledge"
_engine = create_async_engine(DB_URL, echo=False, pool_size=3, max_overflow=5)
_session = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)

router = APIRouter()

VALID_STATUSES = {"draft", "sent", "viewed", "paid", "overdue", "cancelled"}

# ── Table DDL ────────────────────────────────────────────────────────
CREATE_INVOICES_SQL = """
CREATE TABLE IF NOT EXISTS public.invoices (
    id                    SERIAL PRIMARY KEY,
    invoice_number        TEXT UNIQUE NOT NULL,
    client_name           TEXT NOT NULL,
    client_email          TEXT NOT NULL,
    client_company        TEXT,
    contact_submission_id INTEGER,
    items                 JSONB DEFAULT '[]'::jsonb,
    subtotal              DECIMAL(10,2) DEFAULT 0,
    tax_rate              DECIMAL(5,4) DEFAULT 0,
    tax_amount            DECIMAL(10,2) DEFAULT 0,
    total                 DECIMAL(10,2) DEFAULT 0,
    currency              VARCHAR(3) DEFAULT 'USD',
    status                VARCHAR(20) DEFAULT 'draft',
    notes                 TEXT,
    due_date              DATE,
    paid_at               TIMESTAMP WITH TIME ZONE,
    created_at            TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at            TIMESTAMP WITH TIME ZONE DEFAULT now()
);
"""

CREATE_TEMPLATES_SQL = """
CREATE TABLE IF NOT EXISTS public.invoice_templates (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    items       JSONB DEFAULT '[]'::jsonb,
    notes       TEXT,
    is_default  BOOLEAN DEFAULT FALSE,
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT now()
);
"""

INDEX_SQLS = [
    "CREATE INDEX IF NOT EXISTS idx_invoices_status ON public.invoices (status)",
    "CREATE INDEX IF NOT EXISTS idx_invoices_client_email ON public.invoices (client_email)",
    "CREATE INDEX IF NOT EXISTS idx_invoices_invoice_number ON public.invoices (invoice_number)",
]

SEED_TEMPLATES = [
    {
        "name": "Website Package",
        "items": json.dumps([
            {"description": "Website Design & Development", "quantity": 1, "unit_price": 2499.00, "amount": 2499.00},
            {"description": "Monthly Hosting & Maintenance (first month)", "quantity": 1, "unit_price": 299.00, "amount": 299.00},
        ]),
        "notes": "Thank you for choosing Stuff N Things for your website project!",
        "is_default": True,
    },
    {
        "name": "Monthly Retainer",
        "items": json.dumps([
            {"description": "Monthly Website Management", "quantity": 1, "unit_price": 599.00, "amount": 599.00},
        ]),
        "notes": "Monthly retainer for ongoing website management and support.",
        "is_default": False,
    },
]


async def init_invoicing_tables():
    """Auto-create invoicing tables and seed default templates on startup."""
    try:
        async with _engine.begin() as conn:
            await conn.execute(text(CREATE_INVOICES_SQL))
            await conn.execute(text(CREATE_TEMPLATES_SQL))
            for idx_sql in INDEX_SQLS:
                await conn.execute(text(idx_sql))

            # Seed default templates if none exist
            result = await conn.execute(text("SELECT COUNT(*) FROM public.invoice_templates"))
            count = result.scalar()
            if count == 0:
                for tmpl in SEED_TEMPLATES:
                    await conn.execute(
                        text("""
                            INSERT INTO public.invoice_templates (name, items, notes, is_default)
                            VALUES (:name, CAST(:items AS jsonb), :notes, :is_default)
                        """),
                        tmpl,
                    )
                logger.info("Seeded %d default invoice templates", len(SEED_TEMPLATES))

        logger.info("Invoicing tables ready")
    except Exception as e:
        logger.error("Failed to init invoicing tables: %s", e)


# ── Helpers ──────────────────────────────────────────────────────────
async def _next_invoice_number() -> str:
    """Generate next invoice number: INV-YYYY-NNNN."""
    year = datetime.now(timezone.utc).year
    prefix = f"INV-{year}-"
    async with _session() as sess:
        result = await sess.execute(
            text("""
                SELECT invoice_number FROM public.invoices
                WHERE invoice_number LIKE :prefix
                ORDER BY invoice_number DESC LIMIT 1
            """),
            {"prefix": f"{prefix}%"},
        )
        row = result.fetchone()
    if row:
        last_num = int(row[0].split("-")[-1])
        return f"{prefix}{last_num + 1:04d}"
    return f"{prefix}0001"


def _calculate_totals(items: list, tax_rate: Decimal) -> dict:
    """Calculate subtotal, tax_amount, and total from line items."""
    subtotal = Decimal("0")
    for item in items:
        qty = Decimal(str(item.get("quantity", 1)))
        price = Decimal(str(item.get("unit_price", 0)))
        amount = qty * price
        item["amount"] = float(amount)
        subtotal += amount
    tax_amount = (subtotal * Decimal(str(tax_rate))).quantize(Decimal("0.01"))
    total = subtotal + tax_amount
    return {
        "subtotal": float(subtotal),
        "tax_amount": float(tax_amount),
        "total": float(total),
        "items": items,
    }


def _row_to_dict(row) -> dict:
    """Convert a Row to a serializable dict."""
    d = dict(row._mapping)
    for k, v in d.items():
        if isinstance(v, (datetime, date)):
            d[k] = v.isoformat()
        elif isinstance(v, Decimal):
            d[k] = float(v)
    return d


# ── Pydantic Schemas ─────────────────────────────────────────────────
class InvoiceCreate(BaseModel):
    client_name: str
    client_email: EmailStr
    client_company: Optional[str] = None
    contact_submission_id: Optional[int] = None
    items: list = []
    tax_rate: float = 0.0
    currency: str = "USD"
    notes: Optional[str] = None
    due_date: Optional[date] = None

    @field_validator("client_name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Client name must be at least 2 characters")
        return v


class InvoiceUpdate(BaseModel):
    client_name: Optional[str] = None
    client_email: Optional[str] = None
    client_company: Optional[str] = None
    items: Optional[list] = None
    tax_rate: Optional[float] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    due_date: Optional[date] = None

    @field_validator("status")
    @classmethod
    def valid_status(cls, v):
        if v and v not in VALID_STATUSES:
            raise ValueError(f"Invalid status. Must be one of: {', '.join(VALID_STATUSES)}")
        return v


class TemplateCreate(BaseModel):
    name: str
    items: list = []
    notes: Optional[str] = None
    is_default: bool = False


# ── Invoice Endpoints ────────────────────────────────────────────────
@router.get("/invoices")
async def list_invoices(
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
):
    """List invoices with pagination, status filter, and search."""
    offset = (page - 1) * per_page
    conditions = ["status != 'cancelled'"]
    params: dict = {"limit": per_page, "offset": offset}

    if status:
        if status == "cancelled":
            conditions = ["status = 'cancelled'"]
        else:
            conditions.append("status = :status")
            params["status"] = status

    if search:
        conditions.append("(client_name ILIKE :search OR client_email ILIKE :search)")
        params["search"] = f"%{search}%"

    where = " AND ".join(conditions)

    async with _session() as sess:
        count_result = await sess.execute(
            text(f"SELECT COUNT(*) FROM public.invoices WHERE {where}"), params
        )
        total = count_result.scalar()

        result = await sess.execute(
            text(f"""
                SELECT * FROM public.invoices
                WHERE {where}
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :offset
            """),
            params,
        )
        rows = result.fetchall()

    return {
        "invoices": [_row_to_dict(r) for r in rows],
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page if total else 0,
    }


@router.post("/invoices")
async def create_invoice(body: InvoiceCreate):
    """Create a new invoice with auto-generated invoice number."""
    invoice_number = await _next_invoice_number()
    totals = _calculate_totals(body.items, Decimal(str(body.tax_rate)))

    async with _session() as sess:
        result = await sess.execute(
            text("""
                INSERT INTO public.invoices
                    (invoice_number, client_name, client_email, client_company,
                     contact_submission_id, items, subtotal, tax_rate, tax_amount,
                     total, currency, notes, due_date)
                VALUES
                    (:invoice_number, :client_name, :client_email, :client_company,
                     :contact_submission_id, CAST(:items AS jsonb), :subtotal, :tax_rate,
                     :tax_amount, :total, :currency, :notes, :due_date)
                RETURNING *
            """),
            {
                "invoice_number": invoice_number,
                "client_name": body.client_name,
                "client_email": body.client_email,
                "client_company": body.client_company,
                "contact_submission_id": body.contact_submission_id,
                "items": json.dumps(totals["items"]),
                "subtotal": totals["subtotal"],
                "tax_rate": body.tax_rate,
                "tax_amount": totals["tax_amount"],
                "total": totals["total"],
                "currency": body.currency,
                "notes": body.notes,
                "due_date": body.due_date,
            },
        )
        row = result.fetchone()
        await sess.commit()

    return {"invoice": _row_to_dict(row)}


@router.get("/invoices/templates")
async def list_templates():
    """List all invoice templates."""
    async with _session() as sess:
        result = await sess.execute(
            text("SELECT * FROM public.invoice_templates ORDER BY is_default DESC, name ASC")
        )
        rows = result.fetchall()
    return {"templates": [_row_to_dict(r) for r in rows]}


@router.post("/invoices/templates")
async def create_template(body: TemplateCreate):
    """Create a new invoice template."""
    async with _session() as sess:
        result = await sess.execute(
            text("""
                INSERT INTO public.invoice_templates (name, items, notes, is_default)
                VALUES (:name, CAST(:items AS jsonb), :notes, :is_default)
                RETURNING *
            """),
            {
                "name": body.name,
                "items": json.dumps(body.items),
                "notes": body.notes,
                "is_default": body.is_default,
            },
        )
        row = result.fetchone()
        await sess.commit()
    return {"template": _row_to_dict(row)}


@router.get("/invoices/{invoice_id}")
async def get_invoice(invoice_id: int):
    """Get invoice detail by ID."""
    async with _session() as sess:
        result = await sess.execute(
            text("SELECT * FROM public.invoices WHERE id = :id"), {"id": invoice_id}
        )
        row = result.fetchone()
    if not row:
        return JSONResponse(status_code=404, content={"error": "Invoice not found"})
    return {"invoice": _row_to_dict(row)}


@router.patch("/invoices/{invoice_id}")
async def update_invoice(invoice_id: int, body: InvoiceUpdate):
    """Update an invoice (items, status, notes, due_date, etc.)."""
    # Fetch current invoice
    async with _session() as sess:
        result = await sess.execute(
            text("SELECT * FROM public.invoices WHERE id = :id"), {"id": invoice_id}
        )
        existing = result.fetchone()
    if not existing:
        return JSONResponse(status_code=404, content={"error": "Invoice not found"})

    updates = {}
    params: dict = {"id": invoice_id}

    if body.client_name is not None:
        updates["client_name"] = ":client_name"
        params["client_name"] = body.client_name
    if body.client_email is not None:
        updates["client_email"] = ":client_email"
        params["client_email"] = body.client_email
    if body.client_company is not None:
        updates["client_company"] = ":client_company"
        params["client_company"] = body.client_company
    if body.status is not None:
        updates["status"] = ":status"
        params["status"] = body.status
    if body.notes is not None:
        updates["notes"] = ":notes"
        params["notes"] = body.notes
    if body.due_date is not None:
        updates["due_date"] = ":due_date"
        params["due_date"] = body.due_date

    # Recalculate totals if items or tax_rate changed
    current_items = existing._mapping["items"] if body.items is None else body.items
    current_tax_rate = existing._mapping["tax_rate"] if body.tax_rate is None else Decimal(str(body.tax_rate))

    if body.items is not None or body.tax_rate is not None:
        totals = _calculate_totals(
            current_items if isinstance(current_items, list) else list(current_items),
            Decimal(str(current_tax_rate)),
        )
        updates["items"] = "CAST(:items AS jsonb)"
        params["items"] = json.dumps(totals["items"])
        updates["subtotal"] = ":subtotal"
        params["subtotal"] = totals["subtotal"]
        updates["tax_rate"] = ":tax_rate"
        params["tax_rate"] = float(current_tax_rate)
        updates["tax_amount"] = ":tax_amount"
        params["tax_amount"] = totals["tax_amount"]
        updates["total"] = ":total"
        params["total"] = totals["total"]

    if not updates:
        return JSONResponse(status_code=400, content={"error": "No fields to update"})

    updates["updated_at"] = "now()"
    set_clause = ", ".join(f"{k} = {v}" for k, v in updates.items())

    async with _session() as sess:
        result = await sess.execute(
            text(f"UPDATE public.invoices SET {set_clause} WHERE id = :id RETURNING *"),
            params,
        )
        row = result.fetchone()
        await sess.commit()

    return {"invoice": _row_to_dict(row)}


@router.delete("/invoices/{invoice_id}")
async def delete_invoice(invoice_id: int):
    """Soft-delete an invoice (set status to cancelled)."""
    async with _session() as sess:
        result = await sess.execute(
            text("""
                UPDATE public.invoices
                SET status = 'cancelled', updated_at = now()
                WHERE id = :id RETURNING id, invoice_number
            """),
            {"id": invoice_id},
        )
        row = result.fetchone()
        await sess.commit()
    if not row:
        return JSONResponse(status_code=404, content={"error": "Invoice not found"})
    return {"message": f"Invoice {row._mapping['invoice_number']} cancelled"}


@router.post("/invoices/{invoice_id}/send")
async def send_invoice(invoice_id: int):
    """Send invoice to client via email."""
    async with _session() as sess:
        result = await sess.execute(
            text("SELECT * FROM public.invoices WHERE id = :id"), {"id": invoice_id}
        )
        row = result.fetchone()
    if not row:
        return JSONResponse(status_code=404, content={"error": "Invoice not found"})

    inv = row._mapping
    html = _render_invoice_html(inv)

    subject = f"Invoice {inv['invoice_number']} from Stuff N Things"
    sent = await asyncio.to_thread(_send_email, inv["client_email"], subject, html)

    if sent:
        async with _session() as sess:
            await sess.execute(
                text("UPDATE public.invoices SET status = 'sent', updated_at = now() WHERE id = :id"),
                {"id": invoice_id},
            )
            await sess.commit()
        return {"message": f"Invoice sent to {inv['client_email']}", "status": "sent"}

    return JSONResponse(
        status_code=500,
        content={"error": "Failed to send email. Check SMTP configuration."},
    )


@router.post("/invoices/{invoice_id}/mark-paid")
async def mark_invoice_paid(invoice_id: int):
    """Mark an invoice as paid."""
    async with _session() as sess:
        result = await sess.execute(
            text("""
                UPDATE public.invoices
                SET status = 'paid', paid_at = now(), updated_at = now()
                WHERE id = :id RETURNING id, invoice_number
            """),
            {"id": invoice_id},
        )
        row = result.fetchone()
        await sess.commit()
    if not row:
        return JSONResponse(status_code=404, content={"error": "Invoice not found"})

    inv = row._mapping
    # Notification: invoice paid
    await send_notification(
        type="success",
        title="Invoice Paid",
        message=f"{inv['invoice_number']} marked as paid",
        data={"invoice_id": invoice_id, "link": "/invoices"},
    )

    return {"message": f"Invoice {inv['invoice_number']} marked as paid"}


@router.get("/invoices/{invoice_id}/pdf")
async def get_invoice_pdf(invoice_id: int):
    """Generate and return invoice as HTML (printable to PDF)."""
    async with _session() as sess:
        result = await sess.execute(
            text("SELECT * FROM public.invoices WHERE id = :id"), {"id": invoice_id}
        )
        row = result.fetchone()
    if not row:
        return JSONResponse(status_code=404, content={"error": "Invoice not found"})

    html = _render_invoice_html(row._mapping, full_page=True)
    return HTMLResponse(content=html)


# ── Invoice HTML Renderer ────────────────────────────────────────────
def _render_invoice_html(inv: dict, full_page: bool = False) -> str:
    """Render a clean, professional invoice as HTML."""
    # Status badge colors
    status_colors = {
        "draft": "#6b7280",
        "sent": "#3b82f6",
        "viewed": "#8b5cf6",
        "paid": "#10b981",
        "overdue": "#ef4444",
        "cancelled": "#9ca3af",
    }

    status = inv.get("status", "draft")
    badge_color = status_colors.get(status, "#6b7280")

    # Line items table rows
    items = inv.get("items", [])
    if isinstance(items, str):
        items = json.loads(items)

    items_html = ""
    for item in items:
        qty = item.get("quantity", 1)
        unit_price = float(item.get("unit_price", 0))
        amount = float(item.get("amount", qty * unit_price))
        items_html += f"""
        <tr>
            <td style="padding:10px 12px;border-bottom:1px solid #e5e7eb">{item.get('description', '')}</td>
            <td style="padding:10px 12px;border-bottom:1px solid #e5e7eb;text-align:center">{qty}</td>
            <td style="padding:10px 12px;border-bottom:1px solid #e5e7eb;text-align:right">${unit_price:,.2f}</td>
            <td style="padding:10px 12px;border-bottom:1px solid #e5e7eb;text-align:right">${amount:,.2f}</td>
        </tr>
        """

    subtotal = float(inv.get("subtotal", 0))
    tax_rate = float(inv.get("tax_rate", 0))
    tax_amount = float(inv.get("tax_amount", 0))
    total = float(inv.get("total", 0))
    currency = inv.get("currency", "USD")

    due_date = inv.get("due_date", "")
    if isinstance(due_date, (date, datetime)):
        due_date = due_date.strftime("%B %d, %Y")

    notes = inv.get("notes") or ""
    notes_html = f'<div style="margin-top:32px;padding:16px;background:#f9fafb;border-radius:8px;font-size:14px;color:#6b7280"><strong>Notes:</strong><br>{notes}</div>' if notes else ""

    invoice_body = f"""
    <div style="font-family:'Inter',system-ui,-apple-system,sans-serif;max-width:800px;margin:0 auto;padding:40px;color:#1f2937">
        <!-- Header -->
        <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:40px">
            <div>
                <h1 style="margin:0;font-size:28px;font-weight:700;color:#1a1a2e">Stuff N Things</h1>
                <p style="margin:4px 0 0;color:#6b7280;font-size:14px">stuffnthings.io</p>
            </div>
            <div style="text-align:right">
                <h2 style="margin:0;font-size:24px;font-weight:600;color:#1a1a2e">INVOICE</h2>
                <p style="margin:4px 0 0;font-size:15px;color:#4b5563">{inv.get('invoice_number', '')}</p>
                <span style="display:inline-block;margin-top:8px;padding:4px 12px;border-radius:12px;font-size:12px;font-weight:600;color:white;background:{badge_color};text-transform:uppercase">{status}</span>
            </div>
        </div>

        <!-- Client Info + Dates -->
        <div style="display:flex;justify-content:space-between;margin-bottom:32px">
            <div>
                <p style="margin:0 0 4px;font-size:12px;font-weight:600;color:#9ca3af;text-transform:uppercase;letter-spacing:0.5px">Bill To</p>
                <p style="margin:0;font-size:16px;font-weight:600;color:#1f2937">{inv.get('client_name', '')}</p>
                <p style="margin:2px 0;font-size:14px;color:#6b7280">{inv.get('client_email', '')}</p>
                {'<p style="margin:2px 0;font-size:14px;color:#6b7280">' + inv.get('client_company', '') + '</p>' if inv.get('client_company') else ''}
            </div>
            <div style="text-align:right">
                <p style="margin:0 0 4px;font-size:12px;font-weight:600;color:#9ca3af;text-transform:uppercase;letter-spacing:0.5px">Due Date</p>
                <p style="margin:0;font-size:16px;font-weight:600;color:#1f2937">{due_date or 'Upon receipt'}</p>
                <p style="margin:8px 0 0;font-size:12px;color:#9ca3af">Currency: {currency}</p>
            </div>
        </div>

        <!-- Line Items -->
        <table style="width:100%;border-collapse:collapse;margin-bottom:24px">
            <thead>
                <tr style="background:#f3f4f6">
                    <th style="padding:10px 12px;text-align:left;font-size:12px;font-weight:600;color:#6b7280;text-transform:uppercase;letter-spacing:0.5px">Description</th>
                    <th style="padding:10px 12px;text-align:center;font-size:12px;font-weight:600;color:#6b7280;text-transform:uppercase;letter-spacing:0.5px">Qty</th>
                    <th style="padding:10px 12px;text-align:right;font-size:12px;font-weight:600;color:#6b7280;text-transform:uppercase;letter-spacing:0.5px">Unit Price</th>
                    <th style="padding:10px 12px;text-align:right;font-size:12px;font-weight:600;color:#6b7280;text-transform:uppercase;letter-spacing:0.5px">Amount</th>
                </tr>
            </thead>
            <tbody>
                {items_html}
            </tbody>
        </table>

        <!-- Totals -->
        <div style="display:flex;justify-content:flex-end">
            <div style="width:280px">
                <div style="display:flex;justify-content:space-between;padding:8px 0;font-size:14px;color:#6b7280">
                    <span>Subtotal</span>
                    <span>${subtotal:,.2f}</span>
                </div>
                <div style="display:flex;justify-content:space-between;padding:8px 0;font-size:14px;color:#6b7280;border-bottom:1px solid #e5e7eb">
                    <span>Tax ({tax_rate:.2%})</span>
                    <span>${tax_amount:,.2f}</span>
                </div>
                <div style="display:flex;justify-content:space-between;padding:12px 0;font-size:20px;font-weight:700;color:#1a1a2e">
                    <span>Total</span>
                    <span>${total:,.2f}</span>
                </div>
            </div>
        </div>

        {notes_html}

        <!-- Footer -->
        <div style="margin-top:48px;padding-top:24px;border-top:1px solid #e5e7eb;text-align:center;font-size:12px;color:#9ca3af">
            <p style="margin:0">Stuff N Things &bull; stuffnthings.io</p>
            <p style="margin:4px 0 0">Thank you for your business!</p>
        </div>
    </div>
    """

    if full_page:
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Invoice {inv.get('invoice_number', '')}</title>
    <style>
        @media print {{
            body {{ margin: 0; padding: 0; }}
            @page {{ margin: 0.5in; }}
        }}
        body {{ margin: 0; padding: 0; background: #fff; }}
    </style>
</head>
<body>
    {invoice_body}
</body>
</html>"""

    return invoice_body
