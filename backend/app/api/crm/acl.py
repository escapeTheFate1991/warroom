"""CRM Access Control API endpoints."""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.crm_db import get_crm_db
from app.models.crm.user import User, Role, Group, UserGroup
from app.models.crm.audit import AuditLog
from .schemas import (
    UserResponse, UserCreate, UserUpdate,
    RoleResponse, RoleCreate, RoleUpdate
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


# ===== Roles CRUD =====

@router.get("/roles", response_model=List[RoleResponse])
async def list_roles(db: AsyncSession = Depends(get_crm_db)):
    """List all roles."""
    result = await db.execute(select(Role).order_by(Role.name))
    return result.scalars().all()


@router.get("/roles/{role_id}", response_model=RoleResponse)
async def get_role(role_id: int, db: AsyncSession = Depends(get_crm_db)):
    """Get single role."""
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()
    
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    return role


@router.post("/roles", response_model=RoleResponse)
async def create_role(role_data: RoleCreate, user_id: Optional[int] = None,
                     db: AsyncSession = Depends(get_crm_db)):
    """Create a new role."""
    # Check for duplicate name
    existing = await db.execute(select(Role).where(Role.name == role_data.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Role name already exists")
    
    role = Role(**role_data.model_dump(exclude_unset=True))
    db.add(role)
    await db.commit()
    await db.refresh(role)
    
    # Log audit
    await log_audit(db, "role", role.id, "created", user_id, 
                   new_values=role_data.model_dump())
    await db.commit()
    
    return role


@router.put("/roles/{role_id}", response_model=RoleResponse)
async def update_role(role_id: int, role_data: RoleUpdate,
                     user_id: Optional[int] = None, db: AsyncSession = Depends(get_crm_db)):
    """Update an existing role."""
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()
    
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    # Check for duplicate name if changing
    if role_data.name and role_data.name != role.name:
        existing = await db.execute(
            select(Role).where(Role.name == role_data.name, Role.id != role_id)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Role name already exists")
    
    # Store old values for audit
    old_values = {
        "name": role.name,
        "description": role.description,
        "permission_type": role.permission_type,
        "permissions": role.permissions
    }
    
    # Update fields
    update_data = role_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(role, field, value)
    
    await db.commit()
    await db.refresh(role)
    
    # Log audit
    await log_audit(db, "role", role.id, "updated", user_id, old_values, update_data)
    await db.commit()
    
    return role


@router.delete("/roles/{role_id}")
async def delete_role(role_id: int, user_id: Optional[int] = None,
                     db: AsyncSession = Depends(get_crm_db)):
    """Delete a role."""
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()
    
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    # Check if role is assigned to users
    users_with_role = await db.execute(select(User).where(User.role_id == role_id))
    if users_with_role.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Cannot delete role that is assigned to users")
    
    old_values = {"name": role.name, "permission_type": role.permission_type}
    await db.execute(delete(Role).where(Role.id == role_id))
    
    # Log audit
    await log_audit(db, "role", role_id, "deleted", user_id, old_values)
    await db.commit()
    
    return {"status": "deleted", "role_id": role_id}


# ===== Users CRUD =====

@router.get("/users", response_model=List[UserResponse])
async def list_users(
    status: Optional[bool] = None,
    role_id: Optional[int] = None,
    limit: int = Query(default=50, le=500),
    offset: int = 0,
    db: AsyncSession = Depends(get_crm_db),
):
    """List users."""
    query = select(User)
    
    if status is not None:
        query = query.where(User.status == status)
    if role_id:
        query = query.where(User.role_id == role_id)
    
    query = query.order_by(User.name).offset(offset).limit(limit)
    
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: AsyncSession = Depends(get_crm_db)):
    """Get single user."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user


@router.post("/users", response_model=UserResponse)
async def create_user(user_data: UserCreate, admin_user_id: Optional[int] = None,
                     db: AsyncSession = Depends(get_crm_db)):
    """Create a new user."""
    # Check for duplicate email
    existing = await db.execute(select(User).where(User.email == user_data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="User with this email already exists")
    
    # Verify role exists if provided
    if user_data.role_id:
        role_result = await db.execute(select(Role).where(Role.id == user_data.role_id))
        if not role_result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Role not found")
    
    user = User(**user_data.model_dump(exclude_unset=True))
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    # Log audit
    audit_data = user_data.model_dump()
    audit_data.pop("password_hash", None)  # Don't log password hash
    await log_audit(db, "user", user.id, "created", admin_user_id, new_values=audit_data)
    await db.commit()
    
    return user


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(user_id: int, user_data: UserUpdate,
                     admin_user_id: Optional[int] = None, db: AsyncSession = Depends(get_crm_db)):
    """Update an existing user."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check for duplicate email if changing
    if user_data.email and user_data.email != user.email:
        existing = await db.execute(
            select(User).where(User.email == user_data.email, User.id != user_id)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="User with this email already exists")
    
    # Verify role exists if changing
    if user_data.role_id and user_data.role_id != user.role_id:
        role_result = await db.execute(select(Role).where(Role.id == user_data.role_id))
        if not role_result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Role not found")
    
    # Store old values for audit
    old_values = {
        "name": user.name,
        "email": user.email,
        "status": user.status,
        "role_id": user.role_id
    }
    
    # Update fields
    update_data = user_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    
    await db.commit()
    await db.refresh(user)
    
    # Log audit
    await log_audit(db, "user", user.id, "updated", admin_user_id, old_values, update_data)
    await db.commit()
    
    return user


@router.delete("/users/{user_id}")
async def delete_user(user_id: int, admin_user_id: Optional[int] = None,
                     db: AsyncSession = Depends(get_crm_db)):
    """Delete a user."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Don't allow deletion of the last admin
    if user.role_id:
        role_result = await db.execute(select(Role).where(Role.id == user.role_id))
        role = role_result.scalar_one_or_none()
        if role and role.permission_type == "all":
            admin_count = await db.execute(
                select(User).join(Role).where(Role.permission_type == "all", User.status == True)
            )
            if len(admin_count.scalars().all()) <= 1:
                raise HTTPException(status_code=400, detail="Cannot delete the last admin user")
    
    old_values = {"name": user.name, "email": user.email, "status": user.status}
    await db.execute(delete(User).where(User.id == user_id))
    
    # Log audit
    await log_audit(db, "user", user_id, "deleted", admin_user_id, old_values)
    await db.commit()
    
    return {"status": "deleted", "user_id": user_id}


@router.get("/users/{user_id}/permissions")
async def get_user_permissions(user_id: int, db: AsyncSession = Depends(get_crm_db)):
    """Get effective permissions for a user."""
    # Get user with role
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    permissions = []
    
    if user.role_id:
        role_result = await db.execute(select(Role).where(Role.id == user.role_id))
        role = role_result.scalar_one_or_none()
        
        if role:
            if role.permission_type == "all":
                permissions = ["all"]
            else:
                permissions = role.permissions or []
    
    return {
        "user_id": user_id,
        "role_id": user.role_id,
        "permissions": permissions,
        "has_full_access": "all" in permissions
    }


@router.get("/permissions")
async def get_available_permissions():
    """Get list of available permissions."""
    return {
        "permissions": [
            # Deal permissions
            {"category": "Deals", "permissions": [
                {"name": "deal.view", "description": "View deals"},
                {"name": "deal.create", "description": "Create deals"},
                {"name": "deal.edit", "description": "Edit deals"},
                {"name": "deal.delete", "description": "Delete deals"},
                {"name": "deal.change_stage", "description": "Move deals between stages"}
            ]},
            # Contact permissions
            {"category": "Contacts", "permissions": [
                {"name": "contact.view", "description": "View contacts"},
                {"name": "contact.create", "description": "Create contacts"},
                {"name": "contact.edit", "description": "Edit contacts"},
                {"name": "contact.delete", "description": "Delete contacts"}
            ]},
            # Activity permissions
            {"category": "Activities", "permissions": [
                {"name": "activity.view", "description": "View activities"},
                {"name": "activity.create", "description": "Create activities"},
                {"name": "activity.edit", "description": "Edit activities"},
                {"name": "activity.delete", "description": "Delete activities"}
            ]},
            # Product permissions
            {"category": "Products", "permissions": [
                {"name": "product.view", "description": "View products"},
                {"name": "product.create", "description": "Create products"},
                {"name": "product.edit", "description": "Edit products"},
                {"name": "product.delete", "description": "Delete products"}
            ]},
            # Email permissions
            {"category": "Email", "permissions": [
                {"name": "email.view", "description": "View emails"},
                {"name": "email.send", "description": "Send emails"},
                {"name": "email.delete", "description": "Delete emails"}
            ]},
            # Marketing permissions
            {"category": "Marketing", "permissions": [
                {"name": "marketing.view", "description": "View campaigns"},
                {"name": "marketing.create", "description": "Create campaigns"},
                {"name": "marketing.edit", "description": "Edit campaigns"},
                {"name": "marketing.send", "description": "Send campaigns"}
            ]},
            # Admin permissions
            {"category": "Administration", "permissions": [
                {"name": "admin.users", "description": "Manage users"},
                {"name": "admin.roles", "description": "Manage roles"},
                {"name": "admin.settings", "description": "Manage settings"},
                {"name": "admin.audit", "description": "View audit logs"}
            ]},
            # Data permissions
            {"category": "Data", "permissions": [
                {"name": "data.import", "description": "Import data"},
                {"name": "data.export", "description": "Export data"},
                {"name": "data.delete", "description": "Bulk delete data"}
            ]}
        ]
    }