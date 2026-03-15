"""CRM Products API endpoints."""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.crm_db import get_tenant_db
from app.services.tenant import get_org_id, get_user_id
from app.models.crm.product import Product
from app.models.crm.audit import AuditLog
from .schemas import ProductResponse, ProductCreate, ProductUpdate

logger = logging.getLogger(__name__)
router = APIRouter()


async def log_audit(db: AsyncSession, entity_type: str, entity_id: int, action: str, 
                   user_id: Optional[int] = None, old_values: dict = None, new_values: dict = None,
                   org_id: Optional[int] = None):
    """Log audit trail for CRM operations."""
    audit_log = AuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        user_id=user_id,
        old_values=old_values,
        new_values=new_values,
        org_id=org_id
    )
    db.add(audit_log)


@router.get("/products", response_model=List[ProductResponse])
async def list_products(
    request: Request,
    search: Optional[str] = None,
    sku: Optional[str] = None,
    limit: int = Query(default=50, le=500),
    offset: int = 0,
    db: AsyncSession = Depends(get_tenant_db),
):
    """List products with filtering."""
    org_id = get_org_id(request)
    query = select(Product)
    
    if org_id:
        query = query.where(Product.org_id == org_id)
    
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
async def get_product(request: Request, product_id: int, db: AsyncSession = Depends(get_tenant_db)):
    """Get single product by ID."""
    org_id = get_org_id(request)
    query = select(Product).where(Product.id == product_id)
    if org_id:
        query = query.where(Product.org_id == org_id)
    result = await db.execute(query)
    product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return product


@router.post("/products", response_model=ProductResponse)
async def create_product(request: Request, product_data: ProductCreate, user_id: Optional[int] = None,
                        db: AsyncSession = Depends(get_tenant_db)):
    """Create a new product."""
    org_id = get_org_id(request)
    # Check for duplicate SKU if provided
    if product_data.sku:
        query = select(Product).where(Product.sku == product_data.sku)
        if org_id:
            query = query.where(Product.org_id == org_id)
        existing = await db.execute(query)
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Product with this SKU already exists")
    
    product = Product(**product_data.model_dump(exclude_unset=True), org_id=org_id)
    db.add(product)
    await db.commit()
    await db.refresh(product)
    
    # Log audit
    await log_audit(db, "product", product.id, "created", user_id, 
                   new_values=product_data.model_dump(), org_id=org_id)
    await db.commit()
    
    return product


@router.put("/products/{product_id}", response_model=ProductResponse)
async def update_product(request: Request, product_id: int, product_data: ProductUpdate,
                        user_id: Optional[int] = None, db: AsyncSession = Depends(get_tenant_db)):
    """Update an existing product."""
    org_id = get_org_id(request)
    query = select(Product).where(Product.id == product_id)
    if org_id:
        query = query.where(Product.org_id == org_id)
    result = await db.execute(query)
    product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Check for duplicate SKU if changing
    if product_data.sku and product_data.sku != product.sku:
        sku_query = select(Product).where(Product.sku == product_data.sku, Product.id != product_id)
        if org_id:
            sku_query = sku_query.where(Product.org_id == org_id)
        existing = await db.execute(sku_query)
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
    await log_audit(db, "product", product.id, "updated", user_id, old_values, update_data, org_id=org_id)
    await db.commit()
    
    return product


@router.delete("/products/{product_id}")
async def delete_product(request: Request, product_id: int, user_id: Optional[int] = None,
                        db: AsyncSession = Depends(get_tenant_db)):
    """Delete a product."""
    org_id = get_org_id(request)
    query = select(Product).where(Product.id == product_id)
    if org_id:
        query = query.where(Product.org_id == org_id)
    result = await db.execute(query)
    product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Check if product is used in any deals
    from app.models.crm.deal import DealProduct
    deal_query = select(DealProduct).where(DealProduct.product_id == product_id)
    if org_id:
        deal_query = deal_query.where(DealProduct.org_id == org_id)
    deal_usage = await db.execute(deal_query)
    if deal_usage.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Cannot delete product that is used in deals")
    
    old_values = {
        "sku": product.sku,
        "name": product.name,
        "price": str(product.price) if product.price else None
    }
    
    delete_query = delete(Product).where(Product.id == product_id)
    if org_id:
        delete_query = delete_query.where(Product.org_id == org_id)
    await db.execute(delete_query)
    
    # Log audit
    await log_audit(db, "product", product_id, "deleted", user_id, old_values, org_id=org_id)
    await db.commit()
    
    return {"status": "deleted", "product_id": product_id}


@router.get("/products/search")
async def search_products(
    request: Request,
    q: str = Query(..., description="Search query"),
    limit: int = Query(default=20, le=100),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Search products for autocomplete/selection."""
    org_id = get_org_id(request)
    query = select(Product).where(
        Product.name.ilike(f"%{q}%") |
        Product.sku.ilike(f"%{q}%") |
        Product.description.ilike(f"%{q}%")
    )
    
    if org_id:
        query = query.where(Product.org_id == org_id)
    
    query = query.order_by(Product.name).limit(limit)
    
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