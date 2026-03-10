"""Stripe Settings API — products, pricing, and connection management.

Table: public.products (auto-created on startup via init_products_table).
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text

from app.db.leadgen_db import leadgen_engine, leadgen_session
from app.services import stripe_service

logger = logging.getLogger(__name__)
router = APIRouter()

# ── Pydantic schemas ─────────────────────────────────────────────────


class StripeConfigUpdate(BaseModel):
    mode: str  # "test" or "live"


class ProductCreate(BaseModel):
    name: str
    description: Optional[str] = None
    price_cents: int
    interval: str = "month"
    features: list[str] = []
    sort_order: int = 0


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price_cents: Optional[int] = None
    interval: Optional[str] = None
    features: Optional[list[str]] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


# ── Table init + seeding ─────────────────────────────────────────────

SEED_PRODUCTS = [
    # ── Monthly retainers ──
    {
        "name": "Foundation",
        "description": "Custom website with hosting, maintenance, and monthly health reports",
        "price_cents": 29900,
        "interval": "month",
        "features": [
            "Custom-designed, mobile-first website",
            "SSL, fast hosting, CDN",
            "Monthly maintenance and updates",
            "Contact form with email notifications",
            "Google Analytics 4 + conversion tracking",
            "LocalBusiness schema markup",
            "Google Business Profile optimization",
            "Monthly uptime and health reports",
        ],
        "sort_order": 1,
    },
    {
        "name": "Operational",
        "description": "Website + SEO + AI workflows that compound month over month",
        "price_cents": 59900,
        "interval": "month",
        "features": [
            "Everything in Foundation",
            "Monthly SEO content (blog posts)",
            "Local SEO strategy (citations, reviews)",
            "AI-powered chatbot for lead capture",
            "AI workflow automation",
            "Review collection and display",
            "Monthly performance reports",
            "Social media profile optimization",
        ],
        "sort_order": 2,
    },
    {
        "name": "Growth",
        "description": "Full digital presence with paid ads, competitor intel, and dedicated manager",
        "price_cents": 120000,
        "interval": "month",
        "features": [
            "Everything in Operational",
            "AI automation (follow-up emails, lead scoring, CRM)",
            "Video content strategy support",
            "Google Ads + Facebook Ads management",
            "Competitor monitoring and intelligence",
            "Branded proposal and estimate system",
            "Priority support with dedicated manager",
            "Quarterly strategy reviews",
        ],
        "sort_order": 3,
    },
    # ── One-time setup fees ──
    {
        "name": "Foundation Setup",
        "description": "One-time setup: custom website design, build, and launch",
        "price_cents": 99700,
        "interval": "one_time",
        "features": [
            "Custom website design and build",
            "5-7 optimized pages",
            "SEO-optimized titles, meta descriptions, headings",
            "LocalBusiness schema markup",
            "Google Analytics 4 + conversion tracking setup",
            "Contact form with email notifications",
            "SSL, hosting, CDN setup",
            "Google Business Profile optimization",
        ],
        "sort_order": 4,
    },
    {
        "name": "Growth Setup",
        "description": "One-time setup: website + SEO foundation + AI chatbot + portfolio",
        "price_cents": 199700,
        "interval": "one_time",
        "features": [
            "Everything in Foundation Setup",
            "SEO content strategy and initial blog posts",
            "Local SEO citation building",
            "Before/after project portfolio with case studies",
            "AI-powered chatbot setup",
            "Review collection system setup",
            "Social media profile optimization",
        ],
        "sort_order": 5,
    },
    {
        "name": "Dominate Setup",
        "description": "One-time setup: full digital presence build with ads, AI automation, CRM",
        "price_cents": 349700,
        "interval": "one_time",
        "features": [
            "Everything in Growth Setup",
            "AI automation setup (follow-up emails, lead scoring, CRM)",
            "Video content strategy and production plan",
            "Google Ads + Facebook Ads campaign setup",
            "Competitor monitoring and intelligence dashboard",
            "Branded proposal and estimate system",
        ],
        "sort_order": 6,
    },
]


async def init_products_table(engine) -> None:
    """Create products table and seed defaults on first run."""
    async with engine.begin() as conn:
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS public.products_stripe (
                id SERIAL PRIMARY KEY,
                stripe_product_id TEXT UNIQUE,
                stripe_price_id TEXT,
                name TEXT NOT NULL,
                description TEXT,
                price_cents INTEGER NOT NULL DEFAULT 0,
                interval TEXT DEFAULT 'month',
                features JSONB DEFAULT '[]',
                is_active BOOLEAN DEFAULT TRUE,
                sort_order INTEGER DEFAULT 0,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
            )
        """))

        # Check if empty — seed if so
        result = await conn.execute(text("SELECT COUNT(*) FROM public.products_stripe"))
        count = result.scalar()
        if count == 0:
            logger.info("Seeding Stuff N Things products...")
            for p in SEED_PRODUCTS:
                await conn.execute(
                    text("""
                        INSERT INTO public.products_stripe
                            (name, description, price_cents, interval, features, sort_order)
                        VALUES (:name, :description, :price_cents, :interval, CAST(:features AS jsonb), :sort_order)
                    """),
                    {**p, "features": json.dumps(p["features"])},
                )
            logger.info("Seeded %d products", len(SEED_PRODUCTS))


# ── Config endpoints ─────────────────────────────────────────────────


@router.get("/stripe")
async def get_stripe_config():
    """Get current Stripe config — mode, public key, connection status."""
    mode = stripe_service.get_mode()
    pk = stripe_service.get_public_key()
    conn = stripe_service.test_connection()
    return {
        "mode": mode,
        "public_key": pk,
        "connected": conn["connected"],
        "error": conn.get("error"),
    }


@router.put("/stripe")
async def update_stripe_config(body: StripeConfigUpdate):
    """Toggle test/live mode."""
    if body.mode not in ("test", "live"):
        raise HTTPException(400, "Mode must be 'test' or 'live'")
    os.environ["STRIPE_MODE"] = body.mode
    return {"mode": body.mode, "public_key": stripe_service.get_public_key()}


@router.get("/stripe/test-connection")
async def test_stripe_connection():
    """Verify the current API key works."""
    return stripe_service.test_connection()


# ── Product CRUD ─────────────────────────────────────────────────────


@router.get("/stripe/products")
async def list_products():
    """List all local products (with Stripe IDs if synced)."""
    async with leadgen_session() as db:
        result = await db.execute(
            text("SELECT * FROM public.products_stripe ORDER BY sort_order, id")
        )
        rows = result.mappings().all()
        return [dict(r) for r in rows]


@router.post("/stripe/products")
async def create_product(body: ProductCreate):
    """Create a product locally and optionally push to Stripe."""
    features_json = json.dumps(body.features)

    # Try to create in Stripe
    stripe_ids = {"stripe_product_id": None, "stripe_price_id": None}
    try:
        stripe_ids = stripe_service.create_product(
            name=body.name,
            description=body.description,
            price_cents=body.price_cents,
            interval=body.interval,
        )
    except Exception as e:
        logger.warning("Stripe create failed (will save locally): %s", e)

    async with leadgen_session() as db:
        result = await db.execute(
            text("""
                INSERT INTO public.products_stripe
                    (name, description, price_cents, interval, features, sort_order,
                     stripe_product_id, stripe_price_id)
                VALUES (:name, :description, :price_cents, :interval, :features::jsonb,
                        :sort_order, :stripe_product_id, :stripe_price_id)
                RETURNING *
            """),
            {
                "name": body.name,
                "description": body.description,
                "price_cents": body.price_cents,
                "interval": body.interval,
                "features": features_json,
                "sort_order": body.sort_order,
                **stripe_ids,
            },
        )
        await db.commit()
        row = result.mappings().first()
        return dict(row)


@router.put("/stripe/products/{product_id}")
async def update_product(product_id: int, body: ProductUpdate):
    """Update a product locally and sync to Stripe if connected."""
    async with leadgen_session() as db:
        # Fetch current
        result = await db.execute(
            text("SELECT * FROM public.products_stripe WHERE id = :id"), {"id": product_id}
        )
        existing = result.mappings().first()
        if not existing:
            raise HTTPException(404, "Product not found")

        # Build update fields
        updates = {}
        if body.name is not None:
            updates["name"] = body.name
        if body.description is not None:
            updates["description"] = body.description
        if body.price_cents is not None:
            updates["price_cents"] = body.price_cents
        if body.interval is not None:
            updates["interval"] = body.interval
        if body.features is not None:
            updates["features"] = json.dumps(body.features)
        if body.is_active is not None:
            updates["is_active"] = body.is_active
        if body.sort_order is not None:
            updates["sort_order"] = body.sort_order

        if not updates:
            return dict(existing)

        updates["updated_at"] = datetime.now(timezone.utc)

        # Build dynamic SET clause
        set_parts = [f"{k} = :{k}" for k in updates]
        if "features" in updates:
            set_parts = [
                f"{k} = :{k}::jsonb" if k == "features" else f"{k} = :{k}"
                for k in updates
            ]
        set_clause = ", ".join(set_parts)

        result = await db.execute(
            text(f"UPDATE public.products_stripe SET {set_clause} WHERE id = :id RETURNING *"),
            {**updates, "id": product_id},
        )
        await db.commit()
        row = result.mappings().first()

        # Sync to Stripe if we have a Stripe ID
        if existing["stripe_product_id"]:
            try:
                stripe_service.update_product(
                    existing["stripe_product_id"],
                    name=body.name,
                    description=body.description,
                    is_active=body.is_active,
                )
                # If price changed, create new price in Stripe
                if body.price_cents is not None and body.price_cents != existing["price_cents"]:
                    new_price_id = stripe_service.update_price(
                        existing["stripe_product_id"],
                        existing["stripe_price_id"],
                        body.price_cents,
                        body.interval or existing["interval"],
                    )
                    await db.execute(
                        text("UPDATE public.products_stripe SET stripe_price_id = :pid WHERE id = :id"),
                        {"pid": new_price_id, "id": product_id},
                    )
                    await db.commit()
            except Exception as e:
                logger.warning("Stripe sync failed: %s", e)

        return dict(row)


@router.delete("/stripe/products/{product_id}")
async def delete_product(product_id: int):
    """Archive a product (deactivate in Stripe, soft-delete locally)."""
    async with leadgen_session() as db:
        result = await db.execute(
            text("SELECT * FROM public.products_stripe WHERE id = :id"), {"id": product_id}
        )
        existing = result.mappings().first()
        if not existing:
            raise HTTPException(404, "Product not found")

        # Archive in Stripe
        if existing["stripe_product_id"]:
            try:
                stripe_service.archive_product(existing["stripe_product_id"])
            except Exception as e:
                logger.warning("Stripe archive failed: %s", e)

        # Soft-delete locally (mark inactive)
        await db.execute(
            text("""
                UPDATE public.products_stripe
                SET is_active = FALSE, updated_at = now()
                WHERE id = :id
            """),
            {"id": product_id},
        )
        await db.commit()
        return {"deleted": True, "id": product_id}


# ── Sync ─────────────────────────────────────────────────────────────


@router.post("/stripe/sync")
async def sync_products():
    """Push all local products to Stripe (create if missing, update if exists)."""
    async with leadgen_session() as db:
        result = await db.execute(
            text("SELECT * FROM public.products_stripe WHERE is_active = TRUE ORDER BY sort_order")
        )
        products = result.mappings().all()

    synced = 0
    errors = []
    for p in products:
        try:
            if p["stripe_product_id"]:
                # Update existing
                stripe_service.update_product(
                    p["stripe_product_id"],
                    name=p["name"],
                    description=p["description"],
                )
                # Check if price needs update
                if p["price_cents"]:
                    new_price_id = stripe_service.update_price(
                        p["stripe_product_id"],
                        p["stripe_price_id"],
                        p["price_cents"],
                        p["interval"] or "month",
                    )
                    async with leadgen_session() as db:
                        await db.execute(
                            text("UPDATE public.products_stripe SET stripe_price_id = :pid WHERE id = :id"),
                            {"pid": new_price_id, "id": p["id"]},
                        )
                        await db.commit()
            else:
                # Create new in Stripe
                ids = stripe_service.create_product(
                    name=p["name"],
                    description=p["description"],
                    price_cents=p["price_cents"],
                    interval=p["interval"] or "month",
                )
                async with leadgen_session() as db:
                    await db.execute(
                        text("""
                            UPDATE public.products_stripe
                            SET stripe_product_id = :spid, stripe_price_id = :sprid, updated_at = now()
                            WHERE id = :id
                        """),
                        {"spid": ids["stripe_product_id"], "sprid": ids["stripe_price_id"], "id": p["id"]},
                    )
                    await db.commit()
            synced += 1
        except Exception as e:
            errors.append({"product": p["name"], "error": str(e)})
            logger.warning("Sync failed for %s: %s", p["name"], e)

    return {"synced": synced, "errors": errors, "total": len(products)}
