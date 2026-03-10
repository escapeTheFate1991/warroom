"""Stripe service — product/price management and sync."""

import logging
import os
from typing import Optional

import stripe

logger = logging.getLogger(__name__)


def _init_stripe() -> None:
    """Initialize Stripe with the correct key based on STRIPE_MODE."""
    mode = os.getenv("STRIPE_MODE", "test").lower()
    if mode == "live":
        stripe.api_key = os.getenv("STRIPE_LIVE_SK", "")
    else:
        stripe.api_key = os.getenv("STRIPE_TEST_SK", "")
    logger.info("Stripe initialized in %s mode", mode)


def get_public_key() -> str:
    """Return the publishable key for the current mode."""
    mode = os.getenv("STRIPE_MODE", "test").lower()
    if mode == "live":
        return os.getenv("STRIPE_LIVE_PK", "")
    return os.getenv("STRIPE_TEST_PK", "")


def get_mode() -> str:
    return os.getenv("STRIPE_MODE", "test").lower()


def test_connection() -> dict:
    """Verify the API key works by listing 1 product."""
    _init_stripe()
    try:
        stripe.Product.list(limit=1)
        return {"connected": True, "mode": get_mode()}
    except stripe.error.AuthenticationError:
        return {"connected": False, "mode": get_mode(), "error": "Invalid API key"}
    except Exception as e:
        return {"connected": False, "mode": get_mode(), "error": str(e)}


# ── Product CRUD ─────────────────────────────────────────────────────


def create_product(
    name: str,
    description: Optional[str] = None,
    price_cents: int = 0,
    interval: str = "month",
) -> dict:
    """Create a Stripe product with a default price. Returns product + price IDs."""
    _init_stripe()
    product = stripe.Product.create(
        name=name,
        description=description or "",
        metadata={"source": "warroom"},
    )

    price_data: dict = {
        "product": product.id,
        "unit_amount": price_cents,
        "currency": "usd",
    }
    if interval and interval != "one_time":
        price_data["recurring"] = {"interval": interval}

    price = stripe.Price.create(**price_data)

    # Set as default price
    stripe.Product.modify(product.id, default_price=price.id)

    return {
        "stripe_product_id": product.id,
        "stripe_price_id": price.id,
    }


def update_product(
    stripe_product_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> dict:
    """Update a Stripe product's metadata."""
    _init_stripe()
    params: dict = {}
    if name is not None:
        params["name"] = name
    if description is not None:
        params["description"] = description
    if is_active is not None:
        params["active"] = is_active
    product = stripe.Product.modify(stripe_product_id, **params)
    return {"stripe_product_id": product.id, "active": product.active}


def update_price(
    stripe_product_id: str,
    old_price_id: Optional[str],
    price_cents: int,
    interval: str = "month",
) -> str:
    """Create a new price (Stripe prices are immutable) and set as default."""
    _init_stripe()
    price_data: dict = {
        "product": stripe_product_id,
        "unit_amount": price_cents,
        "currency": "usd",
    }
    if interval and interval != "one_time":
        price_data["recurring"] = {"interval": interval}

    new_price = stripe.Price.create(**price_data)

    # Set as default
    stripe.Product.modify(stripe_product_id, default_price=new_price.id)

    # Archive old price
    if old_price_id:
        try:
            stripe.Price.modify(old_price_id, active=False)
        except Exception:
            pass

    return new_price.id


def archive_product(stripe_product_id: str) -> None:
    """Archive (deactivate) a product in Stripe."""
    _init_stripe()
    stripe.Product.modify(stripe_product_id, active=False)


def list_stripe_products() -> list[dict]:
    """List all products from Stripe with their default prices."""
    _init_stripe()
    products = stripe.Product.list(limit=100, active=True)
    result = []
    for p in products.data:
        price_info = None
        if p.default_price:
            try:
                price = stripe.Price.retrieve(p.default_price)
                price_info = {
                    "id": price.id,
                    "unit_amount": price.unit_amount,
                    "currency": price.currency,
                    "interval": price.recurring.interval if price.recurring else "one_time",
                }
            except Exception:
                pass
        result.append({
            "stripe_product_id": p.id,
            "name": p.name,
            "description": p.description,
            "active": p.active,
            "default_price": price_info,
        })
    return result
