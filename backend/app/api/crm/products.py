"""CRM Products API endpoints."""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.crm_db import get_crm_db
from app.models.crm.product import Product
from app.models.crm.audit import AuditLog
from .schemas import ProductResponse, ProductCreate, ProductUpdate

logger = logging.getLogger(__name__)
router = APIRouter()


async def log_audit(db: AsyncSession, entity_type: str, entity_id: int, action: str, 
                   user_id: Optional[int] = None, old_values: dict = None, new_values: dict = None):
    """Log audit trail for CRM operations."""
    audit_log = AuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        user_id=user_id,
        old_values=old_values,
        new_values=new_values
    )
    db.add(audit_log)


@router.get("/products", response_model=List[ProductResponse])
async def list_products(
    search: Optional[str] = None,
    sku: Optional[str] = None,
    limit: int = Query(default=50, le=500),
    offset: int = 0,
    db: AsyncSession = Depends(get_crm_db),
):
    """List products with filtering."""
    query = select(Product)
    
    if search:
        query = query.where(
            Product.name.ilike(f"%{search}%") |
            Product.description.ilike(f"%{search}%")
        )
    if sku:
        query = query.where(Product.sku.ilike(f"%{sku}%"))
    
    query = query.order_by(Product.name).offset(offset).limit(limit)
    
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/products/{product_id}", response_model=ProductResponse)
async def get_product(product_id: int, db: AsyncSession = Depends(get_crm_db)):
    """Get single product by ID."""
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return product


@router.post("/products", response_model=ProductResponse)
async def create_product(product_data: ProductCreate, user_id: Optional[int] = None,
                        db: AsyncSession = Depends(get_crm_db)):
    """Create a new product."""
    # Check for duplicate SKU if provided
    if product_data.sku:
        existing = await db.execute(
            select(Product).where(Product.sku == product_data.sku)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Product with this SKU already exists")
    
    product = Product(**product_data.model_dump(exclude_unset=True))
    db.add(product)
    await db.commit()
    await db.refresh(product)
    
    # Log audit
    await log_audit(db, "product", product.id, "created", user_id, 
                   new_values=product_data.model_dump())
    await db.commit()
    
    return product


@router.put("/products/{product_id}", response_model=ProductResponse)
async def update_product(product_id: int, product_data: ProductUpdate,
                        user_id: Optional[int] = None, db: AsyncSession = Depends(get_crm_db)):
    """Update an existing product."""
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Check for duplicate SKU if changing
    if product_data.sku and product_data.sku != product.sku:
        existing = await db.execute(
            select(Product).where(Product.sku == product_data.sku, Product.id != product_id)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Product with this SKU already exists")
    
    # Store old values for audit
    old_values = {
        "sku": product.sku,
        "name": product.name,
        "description": product.description,
        "quantity": product.quantity,
        "price": str(product.price) if product.price else None
    }
    
    # Update fields
    update_data = product_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product, field, value)
    
    await db.commit()
    await db.refresh(product)
    
    # Log audit
    await log_audit(db, "product", product.id, "updated", user_id, old_values, update_data)
    await db.commit()
    
    return product


@router.delete("/products/{product_id}")
async def delete_product(product_id: int, user_id: Optional[int] = None,
                        db: AsyncSession = Depends(get_crm_db)):
    """Delete a product."""
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Check if product is used in any deals
    from app.models.crm.deal import DealProduct
    deal_usage = await db.execute(
        select(DealProduct).where(DealProduct.product_id == product_id)
    )
    if deal_usage.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Cannot delete product that is used in deals")
    
    old_values = {
        "sku": product.sku,
        "name": product.name,
        "price": str(product.price) if product.price else None
    }
    
    await db.execute(delete(Product).where(Product.id == product_id))
    
    # Log audit
    await log_audit(db, "product", product_id, "deleted", user_id, old_values)
    await db.commit()
    
    return {"status": "deleted", "product_id": product_id}


@router.get("/products/search")
async def search_products(
    q: str = Query(..., description="Search query"),
    limit: int = Query(default=20, le=100),
    db: AsyncSession = Depends(get_crm_db),
):
    """Search products for autocomplete/selection."""
    query = select(Product).where(
        Product.name.ilike(f"%{q}%") |
        Product.sku.ilike(f"%{q}%") |
        Product.description.ilike(f"%{q}%")
    ).order_by(Product.name).limit(limit)
    
    result = await db.execute(query)
    products = result.scalars().all()
    
    return [
        {
            "id": product.id,
            "name": product.name,
            "sku": product.sku,
            "price": str(product.price) if product.price else None,
            "display": f"{product.name} ({product.sku})" if product.sku else product.name
        }
        for product in products
    ]