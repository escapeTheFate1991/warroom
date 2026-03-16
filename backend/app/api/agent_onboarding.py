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


class CustomAgentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="", max_length=1000)
    skills: List[str] = Field(default_factory=list)
    model: str = Field(default="anthropic/claude-sonnet-4-20250514")
    avatar_emoji: str = Field(default="🤖", max_length=2)
    soul_template_id: Optional[int] = None


class CustomAgentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    skills: Optional[List[str]] = None
    model: Optional[str] = None
    avatar_emoji: Optional[str] = Field(None, max_length=2)
    soul_md: Optional[str] = Field(None, max_length=50000)


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
            WHERE u.id = :user_id AND u.org_id = :org_id
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
            WHERE u.id = :user_id AND u.org_id = :org_id
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
            WHERE u.id = :user_id AND u.org_id = :org_id
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
            WHERE u.id = :user_id AND u.org_id = :org_id
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


# ── Multiple Agent Management (User's Own Agents) ─────────────────

@router.post("/api/agents/my-agents", response_model=Dict[str, Any])
async def create_my_agent(
    agent: CustomAgentCreate,
    request: Request,
    db: AsyncSession = Depends(get_tenant_db)
):
    """Create a new custom agent (not anchor)."""
    org_id = get_org_id(request)
    user_id = get_user_id(request)
    
    if not org_id or not user_id:
        raise HTTPException(status_code=400, detail="Organization and user required")
    
    await db.execute(text("SET search_path TO crm, public"))
    
    # Get soul template if provided
    soul_md = ""
    if agent.soul_template_id:
        template_result = await db.execute(
            text("""
                SELECT soul_template FROM agent_templates 
                WHERE id = :template_id AND org_id = :org_id
            """),
            {"template_id": agent.soul_template_id, "org_id": org_id}
        )
        template = template_result.fetchone()
        if template:
            soul_md = template[0]
    
    # Generate memory namespace
    memory_namespace = f"org_{org_id}_user_{user_id}_agent_{agent.name.lower().replace(' ', '_')}"
    
    # Create custom agent
    result = await db.execute(
        text("""
            INSERT INTO agent_instances (
                org_id, user_id, agent_name, soul_md, memory_namespace, 
                is_anchor, agent_type, skills, model, description, avatar_emoji
            ) VALUES (
                :org_id, :user_id, :name, :soul_md, :memory_namespace,
                false, 'custom', CAST(:skills AS jsonb), :model, :description, :avatar_emoji
            ) RETURNING id, created_at
        """),
        {
            "org_id": org_id,
            "user_id": user_id,
            "name": agent.name,
            "soul_md": soul_md,
            "memory_namespace": memory_namespace,
            "skills": str(agent.skills).replace("'", '"'),
            "model": agent.model,
            "description": agent.description,
            "avatar_emoji": agent.avatar_emoji
        }
    )
    
    row = result.fetchone()
    await db.commit()
    
    logger.info("Created custom agent %d for user %d in org %d", row[0], user_id, org_id)
    
    return {
        "id": row[0],
        "name": agent.name,
        "type": "custom",
        "memory_namespace": memory_namespace,
        "created_at": row[1]
    }


@router.get("/api/agents/my-agents", response_model=List[Dict[str, Any]])
async def list_my_agents(
    request: Request,
    db: AsyncSession = Depends(get_tenant_db)
):
    """List ALL of current user's agents (anchor + custom)."""
    org_id = get_org_id(request)
    user_id = get_user_id(request)
    
    if not org_id or not user_id:
        raise HTTPException(status_code=400, detail="Organization and user required")
    
    await db.execute(text("SET search_path TO crm, public"))
    result = await db.execute(
        text("""
            SELECT id, agent_name, soul_md, memory_namespace, status, config,
                   last_active, created_at, template_id, is_anchor, agent_type,
                   skills, model, description, avatar_emoji
            FROM agent_instances
            WHERE org_id = :org_id AND user_id = :user_id
            ORDER BY is_anchor DESC, created_at DESC
        """),
        {"org_id": org_id, "user_id": user_id}
    )
    
    agents = []
    for row in result:
        agents.append({
            "id": row[0],
            "name": row[1],
            "soul_md": row[2],
            "memory_namespace": row[3],
            "status": row[4],
            "config": row[5],
            "last_active": row[6],
            "created_at": row[7],
            "template_id": row[8],
            "is_anchor": row[9],
            "type": row[10] or ("anchor" if row[9] else "custom"),
            "skills": row[11] or [],
            "model": row[12] or "anthropic/claude-sonnet-4-20250514",
            "description": row[13] or "",
            "avatar_emoji": row[14] or "🤖"
        })
    
    return agents


@router.get("/api/agents/my-agents/{agent_id}", response_model=Dict[str, Any])
async def get_my_agent(
    agent_id: int,
    request: Request,
    db: AsyncSession = Depends(get_tenant_db)
):
    """Get specific agent (user can only access their own)."""
    org_id = get_org_id(request)
    user_id = get_user_id(request)
    
    if not org_id or not user_id:
        raise HTTPException(status_code=400, detail="Organization and user required")
    
    await db.execute(text("SET search_path TO crm, public"))
    result = await db.execute(
        text("""
            SELECT id, agent_name, soul_md, memory_namespace, status, config,
                   last_active, created_at, template_id, is_anchor, agent_type,
                   skills, model, description, avatar_emoji
            FROM agent_instances
            WHERE id = :agent_id AND org_id = :org_id AND user_id = :user_id
        """),
        {"agent_id": agent_id, "org_id": org_id, "user_id": user_id}
    )
    
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return {
        "id": row[0],
        "name": row[1],
        "soul_md": row[2],
        "memory_namespace": row[3],
        "status": row[4],
        "config": row[5],
        "last_active": row[6],
        "created_at": row[7],
        "template_id": row[8],
        "is_anchor": row[9],
        "type": row[10] or ("anchor" if row[9] else "custom"),
        "skills": row[11] or [],
        "model": row[12] or "anthropic/claude-sonnet-4-20250514",
        "description": row[13] or "",
        "avatar_emoji": row[14] or "🤖"
    }


@router.put("/api/agents/my-agents/{agent_id}", response_model=Dict[str, Any])
async def update_my_agent(
    agent_id: int,
    updates: CustomAgentUpdate,
    request: Request,
    db: AsyncSession = Depends(get_tenant_db)
):
    """Update agent (name, skills, model, soul)."""
    org_id = get_org_id(request)
    user_id = get_user_id(request)
    
    if not org_id or not user_id:
        raise HTTPException(status_code=400, detail="Organization and user required")
    
    await db.execute(text("SET search_path TO crm, public"))
    
    # Build update query dynamically
    update_fields = []
    params = {"agent_id": agent_id, "org_id": org_id, "user_id": user_id}
    
    for field, value in updates.dict(exclude_unset=True).items():
        if field == "skills":
            update_fields.append("skills = CAST(:skills AS jsonb)")
            params["skills"] = str(value).replace("'", '"')
        elif field == "name":
            update_fields.append("agent_name = :agent_name")
            params["agent_name"] = value
        else:
            update_fields.append(f"{field} = :{field}")
            params[field] = value
    
    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    update_query = f"""
        UPDATE agent_instances
        SET {', '.join(update_fields)}, updated_at = NOW()
        WHERE id = :agent_id AND org_id = :org_id AND user_id = :user_id
    """
    
    result = await db.execute(text(update_query), params)
    
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    await db.commit()
    
    logger.info("Updated agent %d for user %d in org %d", agent_id, user_id, org_id)
    
    return {"id": agent_id, "updated": True}


@router.delete("/api/agents/my-agents/{agent_id}")
async def delete_my_agent(
    agent_id: int,
    request: Request,
    db: AsyncSession = Depends(get_tenant_db)
):
    """Delete custom agent (cannot delete anchor)."""
    org_id = get_org_id(request)
    user_id = get_user_id(request)
    
    if not org_id or not user_id:
        raise HTTPException(status_code=400, detail="Organization and user required")
    
    await db.execute(text("SET search_path TO crm, public"))
    
    # Check if it's an anchor agent (cannot delete)
    check_result = await db.execute(
        text("""
            SELECT is_anchor FROM agent_instances
            WHERE id = :agent_id AND org_id = :org_id AND user_id = :user_id
        """),
        {"agent_id": agent_id, "org_id": org_id, "user_id": user_id}
    )
    
    agent = check_result.fetchone()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    if agent[0]:  # is_anchor
        raise HTTPException(status_code=400, detail="Cannot delete anchor agent")
    
    # Delete the custom agent
    result = await db.execute(
        text("""
            DELETE FROM agent_instances
            WHERE id = :agent_id AND org_id = :org_id AND user_id = :user_id
        """),
        {"agent_id": agent_id, "org_id": org_id, "user_id": user_id}
    )
    
    await db.commit()
    
    logger.info("Deleted custom agent %d for user %d in org %d", agent_id, user_id, org_id)
    
    return {"deleted": True, "agent_id": agent_id}


@router.post("/api/agents/my-agents/{agent_id}/chat", response_model=Dict[str, str])
async def chat_with_agent(
    agent_id: int,
    request: Request,
    db: AsyncSession = Depends(get_tenant_db)
):
    """Placeholder for agent chat (explains OpenClaw connection)."""
    org_id = get_org_id(request)
    user_id = get_user_id(request)
    
    if not org_id or not user_id:
        raise HTTPException(status_code=400, detail="Organization and user required")
    
    # Verify user owns this agent
    await db.execute(text("SET search_path TO crm, public"))
    result = await db.execute(
        text("""
            SELECT agent_name FROM agent_instances
            WHERE id = :agent_id AND org_id = :org_id AND user_id = :user_id
        """),
        {"agent_id": agent_id, "org_id": org_id, "user_id": user_id}
    )
    
    agent = result.fetchone()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return {
        "message": f"To chat with {agent[0]}, connect via OpenClaw sessions. "
                  f"Use the agent's memory namespace for context persistence."
    }


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
            WHERE u.id = :user_id AND u.org_id = :org_id
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
            
            # Use raw driver_connection for multi-statement SQL (asyncpg limitation)
            conn = await db.connection()
            raw = await conn.get_raw_connection()
            await raw.driver_connection.execute(migration_sql)
            await db.commit()
            
            logger.info("Agent provisioning tables ensured")
        else:
            logger.warning("Agent provisioning migration file not found")
            
    except Exception as e:
        logger.error("Failed to ensure agent provisioning tables: %s", e)
        await db.rollback()
        raise


async def seed_skill_templates(db: AsyncSession, org_id: int = 1):
    """Seed skill-based agent templates for organization."""
    await db.execute(text("SET search_path TO crm, public"))
    
    # Mark existing agents as anchor agents (migration compatibility)
    try:
        await db.execute(
            text("""
                UPDATE agent_instances 
                SET is_anchor = true, agent_type = 'anchor'
                WHERE is_anchor IS NULL AND org_id = :org_id
            """),
            {"org_id": org_id}
        )
        await db.commit()
        logger.info("Marked existing agents as anchor agents for org %d", org_id)
    except Exception as e:
        logger.error("Failed to update existing agents: %s", e)
        await db.rollback()
    
    # Check if templates already exist
    existing = await db.execute(
        text("SELECT COUNT(*) FROM agent_templates WHERE org_id = :org_id"),
        {"org_id": org_id}
    )
    
    if existing.fetchone()[0] > 0:
        logger.info("Agent templates already exist for org %d", org_id)
        return
    
    SKILL_TEMPLATES = {
        "frontend-dev": {
            "name": "Frontend Developer",
            "emoji": "🎨",
            "skills": ["react", "nextjs", "tailwind", "typescript", "css"],
            "model": "anthropic/claude-sonnet-4-20250514",
            "soul_template": "# {{agent_name}} — Frontend Developer for {{user_name}}\n\nYou are {{agent_name}}, a frontend developer specializing in React, Next.js, and modern CSS. You help {{user_name}} build beautiful, responsive user interfaces.\n\n## Your Expertise\n- React & Next.js applications\n- Tailwind CSS & responsive design\n- TypeScript development\n- Component architecture\n- Performance optimization\n\n## Your Style\n- Write clean, maintainable code\n- Focus on user experience\n- Use modern best practices\n- Collaborate effectively with backend teams"
        },
        "backend-dev": {
            "name": "Backend Developer", 
            "emoji": "⚙️",
            "skills": ["python", "fastapi", "postgresql", "docker", "api-design"],
            "model": "anthropic/claude-sonnet-4-20250514",
            "soul_template": "# {{agent_name}} — Backend Developer for {{user_name}}\n\nYou are {{agent_name}}, a backend developer specializing in Python, FastAPI, and PostgreSQL. You help {{user_name}} build robust, scalable server-side applications.\n\n## Your Expertise\n- Python & FastAPI development\n- PostgreSQL database design\n- RESTful API architecture\n- Docker containerization\n- System integration\n\n## Your Style\n- Write secure, efficient code\n- Design scalable architectures\n- Follow API best practices\n- Ensure data integrity"
        },
        "security-analyst": {
            "name": "Security Analyst",
            "emoji": "🔒",
            "skills": ["penetration-testing", "code-audit", "owasp", "compliance"],
            "model": "anthropic/claude-sonnet-4-20250514",
            "soul_template": "# {{agent_name}} — Security Analyst for {{user_name}}\n\nYou are {{agent_name}}, a security analyst specializing in application security, penetration testing, and compliance. You help {{user_name}} identify and mitigate security risks.\n\n## Your Expertise\n- Penetration testing & vulnerability assessment\n- Code security audits\n- OWASP compliance\n- Security best practices\n- Risk assessment\n\n## Your Style\n- Think like an attacker\n- Provide actionable recommendations\n- Explain risks clearly\n- Balance security with usability"
        },
        "content-writer": {
            "name": "Content Writer",
            "emoji": "✍️",
            "skills": ["copywriting", "seo", "social-media", "brand-voice"],
            "model": "anthropic/claude-sonnet-4-20250514",
            "soul_template": "# {{agent_name}} — Content Writer for {{user_name}}\n\nYou are {{agent_name}}, a content writer specializing in compelling copy, SEO optimization, and social media content. You help {{user_name}} create content that engages and converts.\n\n## Your Expertise\n- Persuasive copywriting\n- SEO-optimized content\n- Social media strategy\n- Brand voice development\n- Content marketing\n\n## Your Style\n- Write with personality and purpose\n- Optimize for both humans and search engines\n- Adapt tone to audience\n- Focus on results"
        },
        "data-analyst": {
            "name": "Data Analyst",
            "emoji": "📊",
            "skills": ["sql", "analytics", "reporting", "visualization"],
            "model": "anthropic/claude-sonnet-4-20250514",
            "soul_template": "# {{agent_name}} — Data Analyst for {{user_name}}\n\nYou are {{agent_name}}, a data analyst specializing in SQL, business intelligence, and data visualization. You help {{user_name}} make data-driven decisions.\n\n## Your Expertise\n- SQL query optimization\n- Business intelligence\n- Data visualization\n- Statistical analysis\n- Reporting & dashboards\n\n## Your Style\n- Turn data into insights\n- Ask the right questions\n- Present findings clearly\n- Focus on business impact"
        },
        "research-agent": {
            "name": "Researcher",
            "emoji": "🔍",
            "skills": ["web-research", "competitor-analysis", "market-research"],
            "model": "anthropic/claude-haiku-3-5-20241022",
            "soul_template": "# {{agent_name}} — Research Specialist for {{user_name}}\n\nYou are {{agent_name}}, a research specialist who finds, verifies, and synthesizes information. You help {{user_name}} make informed decisions with quality research.\n\n## Your Expertise\n- Web research & fact-checking\n- Competitive analysis\n- Market research\n- Information synthesis\n- Trend identification\n\n## Your Style\n- Be thorough and accurate\n- Cite reliable sources\n- Provide actionable insights\n- Question assumptions"
        }
    }
    
    try:
        for template_key, template_data in SKILL_TEMPLATES.items():
            await db.execute(
                text("""
                    INSERT INTO agent_templates (
                        org_id, name, soul_template, default_skills, default_model, 
                        max_daily_tokens, description, is_default
                    ) VALUES (
                        :org_id, :name, :soul_template, CAST(:skills AS jsonb),
                        :model, 100000, :description, :is_default
                    )
                """),
                {
                    "org_id": org_id,
                    "name": template_data["name"],
                    "soul_template": template_data["soul_template"],
                    "skills": str(template_data["skills"]).replace("'", '"'),
                    "model": template_data["model"],
                    "description": f"{template_data['name']} template for specialized tasks",
                    "is_default": template_key == "frontend-dev"  # Make frontend-dev the default
                }
            )
        
        await db.commit()
        logger.info("Seeded %d skill templates for org %d", len(SKILL_TEMPLATES), org_id)
        
    except Exception as e:
        logger.error("Failed to seed skill templates for org %d: %s", org_id, e)
        await db.rollback()


async def seed_default_template(db: AsyncSession, org_id: int = 1):
    """Seed default template for organization (legacy function - now calls skill templates)."""
    await seed_skill_templates(db, org_id)