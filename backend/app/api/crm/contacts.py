"""CRM Contacts API endpoints."""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.crm_db import get_crm_db
from app.api.agent_assignment_helpers import load_assignment_summaries
from app.models.crm.contact import Person, Organization
from app.models.crm.deal import Deal
from app.models.crm.audit import AuditLog
from .schemas import (
    CRMContactResponse, ContactPersonResponse, OrganizationCreate,
    OrganizationResponse, OrganizationUpdate, PersonCreate,
    PersonResponse, PersonSearchRequest, PersonUpdate,
)

logger = logging.getLogger(__name__)
router = APIRouter()

PERSON_SEARCH_SQL = {
    "name": "p.name ILIKE :search_like",
    "email": "COALESCE(CAST(p.emails AS TEXT), '') ILIKE :search_like",
    "phone": "COALESCE(CAST(p.contact_numbers AS TEXT), '') ILIKE :search_like",
    "job_title": "COALESCE(p.job_title, '') ILIKE :search_like",
    "organization": "COALESCE(o.name, '') ILIKE :search_like",
}


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


def _search_like(query: Optional[str]) -> Optional[str]:
    if query is None:
        return None
    cleaned = query.strip()
    if not cleaned:
        return None
    return f"%{cleaned}%"


def _normalize_contact_items(items: Any) -> List[Dict[str, str]]:
    if not isinstance(items, list):
        return []

    normalized: List[Dict[str, str]] = []
    for item in items:
        if isinstance(item, dict):
            value = item.get("value") or item.get("email") or item.get("address") or item.get("name")
            if value:
                normalized.append(
                    {
                        "value": str(value),
                        "label": str(item.get("label") or item.get("type") or "primary"),
                    }
                )
        elif isinstance(item, str) and item:
            normalized.append({"value": item, "label": "primary"})

    return normalized


def _first_contact_value(items: Any) -> Optional[str]:
    normalized = _normalize_contact_items(items)
    if not normalized:
        return None
    return normalized[0]["value"]


def _serialize_person_row(row: Any, agent_assignments: Optional[List[Any]] = None) -> Dict[str, Any]:
    emails = _normalize_contact_items(row["emails"])
    contact_numbers = _normalize_contact_items(row["contact_numbers"])
    return {
        "id": row["id"],
        "name": row["name"],
        "emails": emails,
        "contact_numbers": contact_numbers or None,
        "job_title": row["job_title"],
        "organization_id": row["organization_id"],
        "organization_name": row["organization_name"],
        "user_id": row["user_id"],
        "agent_assignments": agent_assignments or [],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _serialize_crm_contact(row: Any, agent_assignments: Optional[List[Any]] = None) -> Dict[str, Any]:
    assigned_to = row["assigned_to"] or row["assigned_email"]
    return {
        "id": row["id"],
        "name": row["name"],
        "email": _first_contact_value(row["emails"]) or "",
        "phone": _first_contact_value(row["contact_numbers"]),
        "company": row["organization_name"],
        "source": "crm",
        "assigned_to": assigned_to,
        "agent_assignments": agent_assignments or [],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


async def _serialize_person_rows(db: AsyncSession, rows: List[Any]) -> List[Dict[str, Any]]:
    assignment_map = await load_assignment_summaries(
        db,
        entity_type="crm_contact",
        entity_ids=[row["id"] for row in rows],
    )
    return [
        _serialize_person_row(row, assignment_map.get(str(row["id"]), []))
        for row in rows
    ]


async def _serialize_crm_contacts(db: AsyncSession, rows: List[Any]) -> List[Dict[str, Any]]:
    assignment_map = await load_assignment_summaries(
        db,
        entity_type="crm_contact",
        entity_ids=[row["id"] for row in rows],
    )
    return [
        _serialize_crm_contact(row, assignment_map.get(str(row["id"]), []))
        for row in rows
    ]


async def _query_person_rows(
    db: AsyncSession,
    *,
    organization_id: Optional[int] = None,
    person_id: Optional[int] = None,
    search: Optional[str] = None,
    search_fields: Optional[List[str]] = None,
    limit: int = 50,
    offset: int = 0,
):
    selected_fields = search_fields or list(PERSON_SEARCH_SQL.keys())
    search_conditions = [PERSON_SEARCH_SQL[field] for field in selected_fields if field in PERSON_SEARCH_SQL]
    search_clause = " OR ".join(search_conditions) if search_conditions else "FALSE"

    query = text(
        f"""
        SELECT
            p.id,
            p.name,
            COALESCE(p.emails, '[]'::jsonb) AS emails,
            COALESCE(p.contact_numbers, '[]'::jsonb) AS contact_numbers,
            p.job_title,
            p.organization_id,
            o.name AS organization_name,
            p.user_id,
            u.name AS assigned_to,
            u.email AS assigned_email,
            p.created_at,
            p.updated_at
        FROM crm.persons p
        LEFT JOIN crm.organizations o ON o.id = p.organization_id
        LEFT JOIN crm.users u ON u.id = p.user_id
        WHERE (CAST(:organization_id AS INTEGER) IS NULL OR p.organization_id = :organization_id)
          AND (CAST(:person_id AS INTEGER) IS NULL OR p.id = :person_id)
          AND (CAST(:search_like AS TEXT) IS NULL OR ({search_clause}))
        ORDER BY p.name
        OFFSET :offset
        LIMIT :limit
        """
    )

    result = await db.execute(
        query,
        {
            "organization_id": organization_id,
            "person_id": person_id,
            "search_like": _search_like(search),
            "offset": offset,
            "limit": limit,
        },
    )
    return result.mappings().all()


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
    rows = await _query_person_rows(
        db,
        organization_id=organization_id,
        search=search,
        limit=limit,
        offset=offset,
    )
    return await _serialize_person_rows(db, rows)


@router.get("/persons/{person_id}", response_model=PersonResponse)
async def get_person(person_id: int, db: AsyncSession = Depends(get_crm_db)):
    """Get single person by ID."""
    rows = await _query_person_rows(db, person_id=person_id, limit=1)
    if not rows:
        raise HTTPException(status_code=404, detail="Person not found")

    serialized_rows = await _serialize_person_rows(db, rows)
    return serialized_rows[0]


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

    # Fire workflow triggers (non-blocking)
    from app.services.workflow_triggers import fire_triggers_background
    fire_triggers_background(
        entity_type="person",
        event="created",
        entity_data={
            **person_data.model_dump(),
            "id": person.id,
            "event": "created",
        },
        entity_id=person.id,
    )
    
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

    # Fire workflow triggers (non-blocking)
    from app.services.workflow_triggers import fire_triggers_background
    fire_triggers_background(
        entity_type="person",
        event="updated",
        entity_data={
            **update_data,
            "id": person.id,
            "old_values": old_values,
            "event": "updated",
        },
        entity_id=person.id,
    )
    
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
    search_fields = search_request.search_fields or ["name", "email", "phone"]
    if not search_fields:
        return []

    rows = await _query_person_rows(
        db,
        search=search_request.query,
        search_fields=search_fields,
        limit=50,
    )
    return await _serialize_person_rows(db, rows)


@router.get("/contacts", response_model=List[CRMContactResponse])
async def list_contacts(
    search: Optional[str] = None,
    limit: int = Query(default=50, le=500),
    offset: int = 0,
    db: AsyncSession = Depends(get_crm_db),
):
    """List flattened CRM contacts for the contacts manager."""
    rows = await _query_person_rows(db, search=search, limit=limit, offset=offset)
    return await _serialize_crm_contacts(db, rows)


@router.get("/contacts/persons", response_model=List[ContactPersonResponse])
async def list_contact_persons(
    organization_id: Optional[int] = None,
    search: Optional[str] = None,
    limit: int = Query(default=50, le=500),
    offset: int = 0,
    db: AsyncSession = Depends(get_crm_db),
):
    """Compatibility wrapper for person lookup under /contacts."""
    rows = await _query_person_rows(
        db,
        organization_id=organization_id,
        search=search,
        limit=limit,
        offset=offset,
    )
    return await _serialize_person_rows(db, rows)


@router.get("/contacts/persons/search", response_model=List[ContactPersonResponse])
async def search_contact_persons(
    q: str = Query(..., min_length=1),
    limit: int = Query(default=50, le=500),
    db: AsyncSession = Depends(get_crm_db),
):
    """Compatibility GET search endpoint for person lookups."""
    rows = await _query_person_rows(db, search=q, limit=limit)
    return await _serialize_person_rows(db, rows)


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


@router.get("/contacts/organizations", response_model=List[OrganizationResponse])
async def list_contact_organizations(
    search: Optional[str] = None,
    limit: int = Query(default=50, le=500),
    offset: int = 0,
    db: AsyncSession = Depends(get_crm_db),
):
    """Compatibility wrapper for organization lookup under /contacts."""
    return await list_organizations(search=search, limit=limit, offset=offset, db=db)


@router.get("/contacts/organizations/search", response_model=List[OrganizationResponse])
async def search_contact_organizations(
    q: str = Query(..., min_length=1),
    limit: int = Query(default=50, le=500),
    db: AsyncSession = Depends(get_crm_db),
):
    """Compatibility GET search endpoint for organization lookups."""
    return await list_organizations(search=q, limit=limit, offset=0, db=db)


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
    rows = await _query_person_rows(db, organization_id=org_id, limit=500)
    return await _serialize_person_rows(db, rows)