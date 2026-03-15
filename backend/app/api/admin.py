"""Admin API — organization & user management (superadmin only)."""
import logging
import re
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.crm_db import get_tenant_db
from app.services.tenant import get_org_id, get_user_id
from app.models.crm.user import User, Role
from app.models.crm.organization import Tenant as Organization
from app.api.auth import get_current_user, require_superadmin, require_permission, _hash_password
from app.services.email import generate_code, send_invite_email

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Request Models ───────────────────────────────────────────────────

class CreateOrgRequest(BaseModel):
    name: str
    slug: Optional[str] = None
    plan: str = "free"
    max_users: int = 10


class UpdateOrgRequest(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None
    plan: Optional[str] = None
    max_users: Optional[int] = None


class InviteUserRequest(BaseModel):
    email: EmailStr
    name: str
    org_id: int
    role_id: Optional[int] = None


class UpdateUserRequest(BaseModel):
    name: Optional[str] = None
    org_id: Optional[int] = None
    role_id: Optional[int] = None
    status: Optional[bool] = None
    is_superadmin: Optional[bool] = None


class CreateRoleRequest(BaseModel):
    name: str
    description: Optional[str] = None
    permission_type: str = "custom"  # all, custom
    permissions: list[str] = []


# ── Organization Endpoints ───────────────────────────────────────────

@router.get("/orgs")
async def list_orgs(
    request: Request,
    admin: User = Depends(require_superadmin()),
    db: AsyncSession = Depends(get_tenant_db),
):
    """List all organizations."""
    org_id = get_org_id(request)
    result = await db.execute(select(Organization).order_by(Organization.created_at.desc()))
    orgs = result.scalars().all()
    return [
        {
            "id": o.id, "name": o.name, "slug": o.slug,
            "is_active": o.is_active, "plan": o.plan,
            "max_users": o.max_users, "created_at": str(o.created_at),
        }
        for o in orgs
    ]


@router.post("/orgs", status_code=201)
async def create_org(
    request: Request,
    data: CreateOrgRequest,
    admin: User = Depends(require_superadmin()),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Create a new organization."""
    org_id = get_org_id(request)
    slug = data.slug or re.sub(r'[^a-z0-9]+', '-', data.name.lower()).strip('-')

    # Check slug uniqueness
    existing = await db.execute(select(Organization).where(Organization.slug == slug))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Organization slug '{slug}' already exists")

    org = Organization(
        name=data.name,
        slug=slug,
        plan=data.plan,
        max_users=data.max_users,
        is_active=True,
    )
    db.add(org)
    await db.commit()
    await db.refresh(org)

    return {"id": org.id, "name": org.name, "slug": org.slug}


@router.put("/orgs/{org_id}")
async def update_org(
    request: Request,
    org_id: int,
    data: UpdateOrgRequest,
    admin: User = Depends(require_superadmin()),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Update an organization."""
    org_id = get_org_id(request)
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(org, field, value)

    await db.commit()
    return {"message": "Organization updated"}


@router.delete("/orgs/{org_id}")
async def delete_org(
    request: Request,
    org_id: int,
    admin: User = Depends(require_superadmin()),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Deactivate an organization (soft delete)."""
    org_id = get_org_id(request)
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    org.is_active = False
    await db.commit()
    return {"message": f"Organization '{org.name}' deactivated"}


# ── User Management ─────────────────────────────────────────────────

@router.get("/users")
async def list_users(
    request: Request,
    org_id: Optional[int] = None,
    admin: User = Depends(require_superadmin()),
    db: AsyncSession = Depends(get_tenant_db),
):
    """List all users, optionally filtered by org."""
    org_id = get_org_id(request)
    query = select(User).options(selectinload(User.org), selectinload(User.role))
    if org_id:
        query = query.where(User.org_id == org_id)
    query = query.order_by(User.created_at.desc())

    result = await db.execute(query)
    users = result.scalars().all()
    return [
        {
            "id": u.id, "name": u.name, "email": u.email,
            "email_verified": u.email_verified or False,
            "is_superadmin": u.is_superadmin or False,
            "status": u.status,
            "org": {"id": u.org.id, "name": u.org.name} if u.org else None,
            "role": {"id": u.role.id, "name": u.role.name} if u.role else None,
            "last_login": str(u.last_login) if u.last_login else None,
            "created_at": str(u.created_at),
        }
        for u in users
    ]


@router.put("/users/{user_id}")
async def update_user(
    request: Request,
    user_id: int,
    data: UpdateUserRequest,
    admin: User = Depends(require_superadmin()),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Update a user (assign org, role, status, superadmin)."""
    org_id = get_org_id(request)
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(user, field, value)

    await db.commit()
    return {"message": f"User '{user.name}' updated"}


@router.post("/users/invite", status_code=201)
async def invite_user(
    request: Request,
    data: InviteUserRequest,
    admin: User = Depends(require_superadmin()),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Create a pre-registered user and send invite email."""
    org_id = get_org_id(request)
    # Check existing
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    # Verify org exists
    org_result = await db.execute(select(Organization).where(Organization.id == data.org_id))
    org = org_result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Check org user limit
    count_result = await db.execute(
        select(func.count()).select_from(User).where(User.org_id == data.org_id)
    )
    current_count = count_result.scalar()
    if current_count >= org.max_users:
        raise HTTPException(status_code=400, detail=f"Organization at max capacity ({org.max_users} users)")

    # Generate temp password (user will set their own on first login)
    invite_code = generate_code(8)

    user = User(
        name=data.name,
        email=data.email,
        password_hash=_hash_password(invite_code),  # Temporary
        org_id=data.org_id,
        role_id=data.role_id,
        email_verified=False,
        status=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Send invite email
    send_invite_email(data.email, org.name, admin.name, invite_code)

    return {"id": user.id, "email": user.email, "invite_code": invite_code}


@router.delete("/users/{user_id}")
async def deactivate_user(
    request: Request,
    user_id: int,
    admin: User = Depends(require_superadmin()),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Deactivate a user (soft delete)."""
    org_id = get_org_id(request)
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.is_superadmin:
        raise HTTPException(status_code=400, detail="Cannot deactivate a superadmin")

    user.status = False
    await db.commit()
    return {"message": f"User '{user.name}' deactivated"}


# ── Role Management ─────────────────────────────────────────────────

@router.get("/roles")
async def list_roles(
    request: Request,
    admin: User = Depends(require_permission("users:manage")),
    db: AsyncSession = Depends(get_tenant_db),
):
    """List all roles."""
    org_id = get_org_id(request)
    result = await db.execute(select(Role).order_by(Role.name))
    roles = result.scalars().all()
    return [
        {
            "id": r.id, "name": r.name, "description": r.description,
            "permission_type": r.permission_type,
            "permissions": r.permissions or [],
        }
        for r in roles
    ]


@router.post("/roles", status_code=201)
async def create_role(
    request: Request,
    data: CreateRoleRequest,
    admin: User = Depends(require_superadmin()),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Create a new role."""
    org_id = get_org_id(request)
    role = Role(
        name=data.name,
        description=data.description,
        permission_type=data.permission_type,
        permissions=data.permissions,
    )
    db.add(role)
    await db.commit()
    await db.refresh(role)
    return {"id": role.id, "name": role.name}


@router.put("/roles/{role_id}")
async def update_role(
    request: Request,
    role_id: int,
    data: CreateRoleRequest,
    admin: User = Depends(require_superadmin()),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Update a role."""
    org_id = get_org_id(request)
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    role.name = data.name
    role.description = data.description
    role.permission_type = data.permission_type
    role.permissions = data.permissions
    await db.commit()
    return {"message": f"Role '{role.name}' updated"}
