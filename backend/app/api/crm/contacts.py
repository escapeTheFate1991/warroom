"""CRM Contacts API endpoints."""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, delete, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.crm_db import get_crm_db
from app.models.crm.contact import Person, Organization
from app.models.crm.deal import Deal
from app.models.crm.audit import AuditLog
from .schemas import (
    PersonResponse, PersonCreate, PersonUpdate, PersonSearchRequest,
    OrganizationResponse, OrganizationCreate, OrganizationUpdate
)

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


# ===== Persons CRUD =====

@router.get("/persons", response_model=List[PersonResponse])
async def list_persons(
    organization_id: Optional[int] = None,
    search: Optional[str] = None,
    limit: int = Query(default=50, le=500),
    offset: int = 0,
    db: AsyncSession = Depends(get_crm_db),
):
    """List persons with filtering."""
    query = select(Person).options(selectinload(Person.organization))
    
    if organization_id:
        query = query.where(Person.organization_id == organization_id)
    if search:
        query = query.where(
            or_(
                Person.name.ilike(f"%{search}%"),
                Person.job_title.ilike(f"%{search}%")
            )
        )
    
    query = query.order_by(Person.name).offset(offset).limit(limit)
    
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/persons/{person_id}", response_model=PersonResponse)
async def get_person(person_id: int, db: AsyncSession = Depends(get_crm_db)):
    """Get single person by ID."""
    result = await db.execute(
        select(Person)
        .options(selectinload(Person.organization))
        .where(Person.id == person_id)
    )
    person = result.scalar_one_or_none()
    
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")
    
    return person


@router.post("/persons", response_model=PersonResponse)
async def create_person(person_data: PersonCreate, db: AsyncSession = Depends(get_crm_db)):
    """Create a new person."""
    person = Person(**person_data.model_dump(exclude_unset=True))
    db.add(person)
    await db.commit()
    await db.refresh(person)
    
    # Log audit
    await log_audit(db, "person", person.id, "created", person_data.user_id, 
                   new_values=person_data.model_dump())
    await db.commit()
    
    return person


@router.put("/persons/{person_id}", response_model=PersonResponse)
async def update_person(person_id: int, person_data: PersonUpdate, 
                       db: AsyncSession = Depends(get_crm_db)):
    """Update an existing person."""
    result = await db.execute(select(Person).where(Person.id == person_id))
    person = result.scalar_one_or_none()
    
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")
    
    # Store old values for audit
    old_values = {
        "name": person.name,
        "emails": person.emails,
        "contact_numbers": person.contact_numbers,
        "job_title": person.job_title,
        "organization_id": person.organization_id
    }
    
    # Update fields
    update_data = person_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(person, field, value)
    
    await db.commit()
    await db.refresh(person)
    
    # Log audit
    await log_audit(db, "person", person.id, "updated", person_data.user_id, old_values, update_data)
    await db.commit()
    
    return person


@router.delete("/persons/{person_id}")
async def delete_person(person_id: int, user_id: Optional[int] = None, 
                       db: AsyncSession = Depends(get_crm_db)):
    """Delete a person."""
    result = await db.execute(select(Person).where(Person.id == person_id))
    person = result.scalar_one_or_none()
    
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")
    
    old_values = {"name": person.name, "emails": person.emails}
    await db.execute(delete(Person).where(Person.id == person_id))
    
    # Log audit
    await log_audit(db, "person", person_id, "deleted", user_id, old_values)
    await db.commit()
    
    return {"status": "deleted", "person_id": person_id}


@router.get("/persons/{person_id}/deals", response_model=List)
async def get_person_deals(person_id: int, db: AsyncSession = Depends(get_crm_db)):
    """Get deals for a person."""
    result = await db.execute(
        select(Deal)
        .options(selectinload(Deal.pipeline), selectinload(Deal.stage))
        .where(Deal.person_id == person_id)
        .order_by(Deal.created_at.desc())
    )
    return result.scalars().all()


@router.post("/persons/search", response_model=List[PersonResponse])
async def search_persons(search_request: PersonSearchRequest, db: AsyncSession = Depends(get_crm_db)):
    """Search persons by name/email/phone."""
    conditions = []
    
    if "name" in search_request.search_fields:
        conditions.append(Person.name.ilike(f"%{search_request.query}%"))
    
    if "email" in search_request.search_fields:
        # Search in JSON emails array
        conditions.append(Person.emails.op('::text')(f'%{search_request.query}%'))
    
    if "phone" in search_request.search_fields:
        # Search in JSON contact_numbers array
        conditions.append(Person.contact_numbers.op('::text')(f'%{search_request.query}%'))
    
    if not conditions:
        return []
    
    query = select(Person).where(or_(*conditions)).limit(50)
    result = await db.execute(query)
    return result.scalars().all()


# ===== Organizations CRUD =====

@router.get("/organizations", response_model=List[OrganizationResponse])
async def list_organizations(
    search: Optional[str] = None,
    limit: int = Query(default=50, le=500),
    offset: int = 0,
    db: AsyncSession = Depends(get_crm_db),
):
    """List organizations with filtering."""
    query = select(Organization)
    
    if search:
        query = query.where(Organization.name.ilike(f"%{search}%"))
    
    query = query.order_by(Organization.name).offset(offset).limit(limit)
    
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/organizations/{org_id}", response_model=OrganizationResponse)
async def get_organization(org_id: int, db: AsyncSession = Depends(get_crm_db)):
    """Get single organization by ID."""
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    return org


@router.post("/organizations", response_model=OrganizationResponse)
async def create_organization(org_data: OrganizationCreate, db: AsyncSession = Depends(get_crm_db)):
    """Create a new organization."""
    org = Organization(**org_data.model_dump(exclude_unset=True))
    db.add(org)
    await db.commit()
    await db.refresh(org)
    
    # Log audit
    await log_audit(db, "organization", org.id, "created", org_data.user_id, 
                   new_values=org_data.model_dump())
    await db.commit()
    
    return org


@router.put("/organizations/{org_id}", response_model=OrganizationResponse)
async def update_organization(org_id: int, org_data: OrganizationUpdate, 
                            db: AsyncSession = Depends(get_crm_db)):
    """Update an existing organization."""
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    # Store old values for audit
    old_values = {
        "name": org.name,
        "address": org.address,
        "user_id": org.user_id
    }
    
    # Update fields
    update_data = org_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(org, field, value)
    
    await db.commit()
    await db.refresh(org)
    
    # Log audit
    await log_audit(db, "organization", org.id, "updated", org_data.user_id, old_values, update_data)
    await db.commit()
    
    return org


@router.delete("/organizations/{org_id}")
async def delete_organization(org_id: int, user_id: Optional[int] = None, 
                            db: AsyncSession = Depends(get_crm_db)):
    """Delete an organization."""
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    old_values = {"name": org.name, "address": org.address}
    await db.execute(delete(Organization).where(Organization.id == org_id))
    
    # Log audit
    await log_audit(db, "organization", org_id, "deleted", user_id, old_values)
    await db.commit()
    
    return {"status": "deleted", "organization_id": org_id}


@router.get("/organizations/{org_id}/persons", response_model=List[PersonResponse])
async def get_organization_persons(org_id: int, db: AsyncSession = Depends(get_crm_db)):
    """Get persons in an organization."""
    result = await db.execute(
        select(Person).where(Person.organization_id == org_id).order_by(Person.name)
    )
    return result.scalars().all()