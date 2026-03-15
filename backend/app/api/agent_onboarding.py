"""Agent Onboarding API — Anchor Agent template management and provisioning.

Endpoints for managing agent templates and provisioning personal AI agents
for organization employees.
"""

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.crm_db import get_tenant_db
from app.services.tenant import get_org_id, get_user_id, is_superadmin
from app.services.agent_onboarding import AgentOnboardingService

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Models ─────────────────────────────────────────────────────

class AgentTemplateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    role_id: Optional[int] = None
    soul_template: str = Field(default="", max_length=50000)
    default_skills: List[str] = Field(default_factory=list)
    default_model: str = Field(default="anthropic/claude-sonnet-4-20250514")
    max_daily_tokens: int = Field(default=100000, ge=1000, le=1000000)
    description: str = Field(default="", max_length=1000)
    is_default: bool = Field(default=False)


class AgentTemplateUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    role_id: Optional[int] = None
    soul_template: Optional[str] = Field(None, max_length=50000)
    default_skills: Optional[List[str]] = None
    default_model: Optional[str] = None
    max_daily_tokens: Optional[int] = Field(None, ge=1000, le=1000000)
    description: Optional[str] = Field(None, max_length=1000)
    is_default: Optional[bool] = None


class AgentProvisionRequest(BaseModel):
    user_id: int = Field(..., gt=0)
    template_id: Optional[int] = None


class AgentSoulUpdate(BaseModel):
    soul_md: str = Field(..., max_length=50000)


# ── Template Management ──────────────────────────────────────────

@router.post("/api/agents/templates", response_model=Dict[str, Any])
async def create_template(
    template: AgentTemplateCreate,
    request: Request,
    db: AsyncSession = Depends(get_tenant_db)
):
    """Create agent template (admin only)."""
    org_id = get_org_id(request)
    user_id = get_user_id(request)
    
    if not org_id:
        raise HTTPException(status_code=400, detail="Organization required")
        
    # Check admin permissions
    await db.execute(text("SET search_path TO crm, public"))
    role_result = await db.execute(
        text("""
            SELECT r.permission_type, r.permissions
            FROM users u
            JOIN roles r ON u.role_id = r.id
            WHERE u.id = :user_id AND u.id IN (SELECT user_id FROM organizations_tenant_users WHERE org_id = :org_id)
        """),
        {"user_id": user_id, "org_id": org_id}
    )
    role = role_result.fetchone()
    
    if not role or (role[0] != 'all' and 'agent_templates.create' not in (role[1] or [])):
        raise HTTPException(status_code=403, detail="Admin permissions required")
    
    # If setting as default, clear other defaults first
    if template.is_default:
        await db.execute(
            text("UPDATE agent_templates SET is_default = false WHERE org_id = :org_id"),
            {"org_id": org_id}
        )
    
    # Create template
    result = await db.execute(
        text("""
            INSERT INTO agent_templates (
                org_id, name, role_id, soul_template, default_skills, default_model,
                max_daily_tokens, description, is_default
            ) VALUES (
                :org_id, :name, :role_id, :soul_template, CAST(:default_skills AS jsonb),
                :default_model, :max_daily_tokens, :description, :is_default
            ) RETURNING id, created_at
        """),
        {
            "org_id": org_id,
            "name": template.name,
            "role_id": template.role_id,
            "soul_template": template.soul_template,
            "default_skills": str(template.default_skills).replace("'", '"'),
            "default_model": template.default_model,
            "max_daily_tokens": template.max_daily_tokens,
            "description": template.description,
            "is_default": template.is_default
        }
    )
    
    row = result.fetchone()
    await db.commit()
    
    logger.info("Created agent template %d in org %d", row[0], org_id)
    
    return {
        "id": row[0],
        "name": template.name,
        "org_id": org_id,
        "created_at": row[1],
        "is_default": template.is_default
    }


@router.get("/api/agents/templates", response_model=List[Dict[str, Any]])
async def list_templates(
    request: Request,
    db: AsyncSession = Depends(get_tenant_db)
):
    """List agent templates for organization."""
    org_id = get_org_id(request)
    
    if not org_id:
        raise HTTPException(status_code=400, detail="Organization required")
    
    await db.execute(text("SET search_path TO crm, public"))
    result = await db.execute(
        text("""
            SELECT at.id, at.name, at.role_id, at.soul_template, at.default_skills,
                   at.default_model, at.max_daily_tokens, at.description, at.is_default,
                   at.created_at, at.updated_at, r.name as role_name
            FROM agent_templates at
            LEFT JOIN roles r ON at.role_id = r.id
            WHERE at.org_id = :org_id
            ORDER BY at.is_default DESC, at.created_at DESC
        """),
        {"org_id": org_id}
    )
    
    templates = []
    for row in result:
        templates.append({
            "id": row[0],
            "name": row[1],
            "role_id": row[2],
            "role_name": row[11],
            "soul_template": row[3],
            "default_skills": row[4],
            "default_model": row[5],
            "max_daily_tokens": row[6],
            "description": row[7],
            "is_default": row[8],
            "created_at": row[9],
            "updated_at": row[10]
        })
    
    return templates


@router.put("/api/agents/templates/{template_id}", response_model=Dict[str, Any])
async def update_template(
    template_id: int,
    updates: AgentTemplateUpdate,
    request: Request,
    db: AsyncSession = Depends(get_tenant_db)
):
    """Update agent template (admin only)."""
    org_id = get_org_id(request)
    user_id = get_user_id(request)
    
    if not org_id:
        raise HTTPException(status_code=400, detail="Organization required")
        
    # Check admin permissions
    await db.execute(text("SET search_path TO crm, public"))
    role_result = await db.execute(
        text("""
            SELECT r.permission_type, r.permissions
            FROM users u
            JOIN roles r ON u.role_id = r.id
            WHERE u.id = :user_id AND u.id IN (SELECT user_id FROM organizations_tenant_users WHERE org_id = :org_id)
        """),
        {"user_id": user_id, "org_id": org_id}
    )
    role = role_result.fetchone()
    
    if not role or (role[0] != 'all' and 'agent_templates.update' not in (role[1] or [])):
        raise HTTPException(status_code=403, detail="Admin permissions required")
    
    # Build update query dynamically
    update_fields = []
    params = {"template_id": template_id, "org_id": org_id}
    
    for field, value in updates.dict(exclude_unset=True).items():
        if field == "default_skills":
            update_fields.append(f"{field} = CAST(:{field} AS jsonb)")
            params[field] = str(value).replace("'", '"')
        else:
            update_fields.append(f"{field} = :{field}")
            params[field] = value
    
    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update")
        
    # If setting as default, clear other defaults first
    if updates.is_default:
        await db.execute(
            text("UPDATE agent_templates SET is_default = false WHERE org_id = :org_id"),
            {"org_id": org_id}
        )
    
    update_query = f"""
        UPDATE agent_templates 
        SET {', '.join(update_fields)}, updated_at = NOW()
        WHERE id = :template_id AND org_id = :org_id
    """
    
    result = await db.execute(text(update_query), params)
    
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Template not found")
    
    await db.commit()
    
    logger.info("Updated agent template %d in org %d", template_id, org_id)
    
    return {"id": template_id, "updated": True}


# ── Agent Provisioning ───────────────────────────────────────────

@router.post("/api/agents/provision", response_model=Dict[str, Any])
async def provision_agent(
    provision: AgentProvisionRequest,
    request: Request,
    db: AsyncSession = Depends(get_tenant_db)
):
    """Provision agent for user (admin only)."""
    org_id = get_org_id(request)
    user_id = get_user_id(request)
    
    if not org_id:
        raise HTTPException(status_code=400, detail="Organization required")
        
    # Check admin permissions
    await db.execute(text("SET search_path TO crm, public"))
    role_result = await db.execute(
        text("""
            SELECT r.permission_type, r.permissions
            FROM users u
            JOIN roles r ON u.role_id = r.id
            WHERE u.id = :user_id AND u.id IN (SELECT user_id FROM organizations_tenant_users WHERE org_id = :org_id)
        """),
        {"user_id": user_id, "org_id": org_id}
    )
    role = role_result.fetchone()
    
    if not role or (role[0] != 'all' and 'agents.provision' not in (role[1] or [])):
        raise HTTPException(status_code=403, detail="Admin permissions required")
    
    try:
        agent = await AgentOnboardingService.provision_agent(
            db, org_id, provision.user_id, provision.template_id
        )
        return agent
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/api/agents/provision/{user_id_to_deprovision}")
async def deprovision_agent(
    user_id_to_deprovision: int,
    request: Request,
    db: AsyncSession = Depends(get_tenant_db)
):
    """Deprovision (archive) agent for user (admin only)."""
    org_id = get_org_id(request)
    user_id = get_user_id(request)
    
    if not org_id:
        raise HTTPException(status_code=400, detail="Organization required")
        
    # Check admin permissions
    await db.execute(text("SET search_path TO crm, public"))
    role_result = await db.execute(
        text("""
            SELECT r.permission_type, r.permissions
            FROM users u
            JOIN roles r ON u.role_id = r.id
            WHERE u.id = :user_id AND u.id IN (SELECT user_id FROM organizations_tenant_users WHERE org_id = :org_id)
        """),
        {"user_id": user_id, "org_id": org_id}
    )
    role = role_result.fetchone()
    
    if not role or (role[0] != 'all' and 'agents.deprovision' not in (role[1] or [])):
        raise HTTPException(status_code=403, detail="Admin permissions required")
    
    success = await AgentOnboardingService.deprovision_agent(
        db, org_id, user_id_to_deprovision
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Agent not found or already archived")
    
    return {"deprovisioned": True, "user_id": user_id_to_deprovision}


# ── User Agent Access ────────────────────────────────────────────

@router.get("/api/agents/my-agent", response_model=Dict[str, Any])
async def get_my_agent(
    request: Request,
    db: AsyncSession = Depends(get_tenant_db)
):
    """Get current user's anchor agent."""
    org_id = get_org_id(request)
    user_id = get_user_id(request)
    
    if not org_id or not user_id:
        raise HTTPException(status_code=400, detail="Organization and user required")
    
    agent = await AgentOnboardingService.get_user_agent(db, org_id, user_id)
    
    if not agent:
        raise HTTPException(status_code=404, detail="No anchor agent found")
    
    return agent


@router.put("/api/agents/my-agent/soul", response_model=Dict[str, Any])
async def update_my_agent_soul(
    soul_update: AgentSoulUpdate,
    request: Request,
    db: AsyncSession = Depends(get_tenant_db)
):
    """Update current user's agent SOUL.md."""
    org_id = get_org_id(request)
    user_id = get_user_id(request)
    
    if not org_id or not user_id:
        raise HTTPException(status_code=400, detail="Organization and user required")
    
    success = await AgentOnboardingService.update_agent_soul(
        db, org_id, user_id, soul_update.soul_md
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Agent not found or not active")
    
    return {"updated": True, "soul_updated": True}


# ── Admin Agent Management ───────────────────────────────────────

@router.get("/api/agents/instances", response_model=List[Dict[str, Any]])
async def list_org_agents(
    request: Request,
    db: AsyncSession = Depends(get_tenant_db)
):
    """List all org agents (admin only)."""
    org_id = get_org_id(request)
    user_id = get_user_id(request)
    
    if not org_id:
        raise HTTPException(status_code=400, detail="Organization required")
        
    # Check admin permissions
    await db.execute(text("SET search_path TO crm, public"))
    role_result = await db.execute(
        text("""
            SELECT r.permission_type, r.permissions
            FROM users u
            JOIN roles r ON u.role_id = r.id
            WHERE u.id = :user_id AND u.id IN (SELECT user_id FROM organizations_tenant_users WHERE org_id = :org_id)
        """),
        {"user_id": user_id, "org_id": org_id}
    )
    role = role_result.fetchone()
    
    if not role or (role[0] != 'all' and 'agents.list' not in (role[1] or [])):
        raise HTTPException(status_code=403, detail="Admin permissions required")
    
    agents = await AgentOnboardingService.list_org_agents(db, org_id)
    return agents


# ── Table Setup ──────────────────────────────────────────────────

async def ensure_tables(db: AsyncSession):
    """Ensure agent provisioning tables exist."""
    await db.execute(text("SET search_path TO crm, public"))
    
    # Read and execute migration
    try:
        from pathlib import Path
        migration_path = Path(__file__).parent.parent / "db" / "agent_provisioning_migration.sql"
        
        if migration_path.exists():
            with open(migration_path, "r") as f:
                migration_sql = f.read()
            
            # Execute migration (will be idempotent due to IF NOT EXISTS)
            await db.execute(text(migration_sql))
            await db.commit()
            
            logger.info("Agent provisioning tables ensured")
        else:
            logger.warning("Agent provisioning migration file not found")
            
    except Exception as e:
        logger.error("Failed to ensure agent provisioning tables: %s", e)
        await db.rollback()
        raise


async def seed_default_template(db: AsyncSession, org_id: int = 1):
    """Seed default template for organization."""
    await db.execute(text("SET search_path TO crm, public"))
    
    # Check if default template already exists
    existing = await db.execute(
        text("SELECT id FROM agent_templates WHERE org_id = :org_id AND is_default = true"),
        {"org_id": org_id}
    )
    
    if existing.fetchone():
        logger.info("Default agent template already exists for org %d", org_id)
        return
    
    soul_template = """# {{agent_name}} — Personal Assistant for {{user_name}}

You are {{agent_name}}, a personal AI assistant for {{user_name}} at {{org_name}}.

## Your Role
- Help {{user_name}} with their daily tasks
- Manage their CRM data, emails, and calendar
- Provide insights from their deals and contacts
- Execute tasks assigned to you

## Boundaries
- You can only access data within your organization
- You cannot access other users' private data unless shared
- Follow the organization's policies and guidelines
"""
    
    try:
        await db.execute(
            text("""
                INSERT INTO agent_templates (
                    org_id, name, soul_template, default_skills, default_model, 
                    max_daily_tokens, description, is_default
                ) VALUES (
                    :org_id, 'Default Assistant', :soul_template, CAST('[]' AS jsonb),
                    'anthropic/claude-sonnet-4-20250514', 100000, 
                    'Default template for new employee onboarding', true
                )
            """),
            {
                "org_id": org_id,
                "soul_template": soul_template
            }
        )
        
        await db.commit()
        logger.info("Seeded default agent template for org %d", org_id)
        
    except Exception as e:
        logger.error("Failed to seed default template for org %d: %s", org_id, e)
        await db.rollback()