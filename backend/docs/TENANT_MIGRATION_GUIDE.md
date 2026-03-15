# Tenant Migration Guide — Converting Endpoints to Multi-Tenant

## Overview

All endpoints currently use `get_crm_db()` which has no org filtering.
To enforce tenant isolation, endpoints must be migrated to use `get_tenant_db()`
and include `org_id` in their queries.

## The Pattern

### Before (single-tenant):
```python
from app.db.crm_db import get_crm_db

@router.get("/deals")
async def list_deals(db: AsyncSession = Depends(get_crm_db)):
    query = select(Deal).order_by(Deal.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()
```

### After (multi-tenant):
```python
from fastapi import Request
from app.db.crm_db import get_tenant_db
from app.services.tenant import get_org_id

@router.get("/deals")
async def list_deals(request: Request, db: AsyncSession = Depends(get_tenant_db)):
    org_id = get_org_id(request)
    query = select(Deal).where(Deal.org_id == org_id).order_by(Deal.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()
```

### With RBAC visibility (user can only see their own + subordinates' data):
```python
from app.services.tenant import get_org_id, get_user_id, get_visible_user_ids

@router.get("/deals")
async def list_deals(request: Request, db: AsyncSession = Depends(get_tenant_db)):
    org_id = get_org_id(request)
    user_id = get_user_id(request)
    visible_users = await get_visible_user_ids(db, user_id, org_id)
    
    query = (
        select(Deal)
        .where(Deal.org_id == org_id)
        .where(Deal.user_id.in_(visible_users))
        .order_by(Deal.created_at.desc())
    )
    result = await db.execute(query)
    return result.scalars().all()
```

### Creating records (always stamp org_id):
```python
@router.post("/deals")
async def create_deal(body: DealCreate, request: Request, db: AsyncSession = Depends(get_tenant_db)):
    org_id = get_org_id(request)
    user_id = get_user_id(request)
    
    deal = Deal(
        title=body.title,
        org_id=org_id,      # ← Always stamp
        user_id=user_id,    # ← Always stamp
        ...
    )
    db.add(deal)
    await db.commit()
```

### Single-record access (verify org ownership):
```python
@router.get("/deals/{deal_id}")
async def get_deal(deal_id: int, request: Request, db: AsyncSession = Depends(get_tenant_db)):
    org_id = get_org_id(request)
    deal = await db.execute(
        select(Deal).where(Deal.id == deal_id, Deal.org_id == org_id)
    )
    deal = deal.scalar_one_or_none()
    if not deal:
        raise HTTPException(404, "Deal not found")
    return deal
```

## Migration Checklist Per Endpoint

1. [ ] Change `get_crm_db` → `get_tenant_db` in `Depends()`
2. [ ] Add `request: Request` parameter
3. [ ] Add `org_id = get_org_id(request)` 
4. [ ] Add `.where(Model.org_id == org_id)` to all SELECT queries
5. [ ] Add `org_id=org_id` to all INSERT/CREATE operations
6. [ ] For single-record GETs/UPDATEs/DELETEs: verify `org_id` matches
7. [ ] For RBAC-sensitive endpoints: add visibility filtering
8. [ ] Test with multiple orgs to confirm isolation

## Priority Order

1. **Deals** (revenue-critical)
2. **Contacts** (persons, organizations)
3. **Social accounts** (OAuth tokens — security-critical)
4. **Competitors** (intelligence data)
5. **Pipelines** (config per org)
6. **Activities** (tied to deals/contacts)
7. **Everything else**

## Files

- Tenant middleware: `app/middleware/tenant_guard.py`
- DB dependency: `app/db/crm_db.py` → `get_tenant_db()`
- Tenant service: `app/services/tenant.py` (visibility, filters, helpers)
- Migration SQL: `app/db/multi_tenant_migration.sql`
