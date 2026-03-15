"""Agent Onboarding Service — Auto-provision Anchor Agents for employees.

When a new employee joins an org, they get their own personal AI agent
("Anchor Agent") auto-provisioned from a role-based template.
"""

import logging
import re
from typing import Optional, Dict, Any, List
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class AgentOnboardingService:
    """Handle agent provisioning, customization, and lifecycle management."""

    @staticmethod
    async def provision_agent(
        db: AsyncSession, 
        org_id: int, 
        user_id: int, 
        template_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Create agent instance from template.
        
        Args:
            db: Database session
            org_id: Organization ID
            user_id: Employee user ID 
            template_id: Template to use (None = default template)
            
        Returns:
            Dict with agent instance details
            
        Raises:
            ValueError: If user already has agent or template not found
        """
        await db.execute(text("SET search_path TO crm, public"))
        
        # Check if user already has an agent
        existing = await db.execute(
            text("SELECT id FROM agent_instances WHERE org_id = :org_id AND user_id = :user_id"),
            {"org_id": org_id, "user_id": user_id}
        )
        if existing.fetchone():
            raise ValueError(f"User {user_id} already has an anchor agent")
            
        # Get template (default if none specified)
        if template_id:
            template_query = text("""
                SELECT id, name, soul_template, default_skills, default_model, max_daily_tokens
                FROM agent_templates 
                WHERE id = :template_id AND org_id = :org_id
            """)
            template_params = {"template_id": template_id, "org_id": org_id}
        else:
            template_query = text("""
                SELECT id, name, soul_template, default_skills, default_model, max_daily_tokens
                FROM agent_templates 
                WHERE org_id = :org_id AND is_default = true
                ORDER BY created_at DESC LIMIT 1
            """)
            template_params = {"org_id": org_id}
            
        template_result = await db.execute(template_query, template_params)
        template = template_result.fetchone()
        
        if not template:
            raise ValueError("No template found for provisioning")
            
        # Get user and org details for template substitution
        user_result = await db.execute(
            text("SELECT name, email FROM users WHERE id = :user_id"),
            {"user_id": user_id}
        )
        user = user_result.fetchone()
        
        org_result = await db.execute(
            text("SELECT name FROM organizations_tenant WHERE id = :org_id"),
            {"org_id": org_id}
        )
        org = org_result.fetchone()
        
        if not user or not org:
            raise ValueError("User or organization not found")
            
        # Get user's role name if available
        role_result = await db.execute(
            text("""
                SELECT r.name 
                FROM roles r 
                JOIN users u ON u.role_id = r.id 
                WHERE u.id = :user_id
            """),
            {"user_id": user_id}
        )
        role = role_result.fetchone()
        role_name = role[0] if role else "team member"
        
        # Generate agent name and memory namespace
        agent_name = f"{user[0]}'s Assistant"
        memory_namespace = f"org_{org_id}_user_{user_id}"
        
        # Substitute variables in soul template
        soul_md = template[2]  # soul_template
        substitutions = {
            "{{agent_name}}": agent_name,
            "{{user_name}}": user[0],
            "{{org_name}}": org[0],
            "{{role}}": role_name,
            "{{user_email}}": user[1]
        }
        
        for placeholder, value in substitutions.items():
            soul_md = soul_md.replace(placeholder, value)
            
        # Create agent instance
        insert_result = await db.execute(
            text("""
                INSERT INTO agent_instances (
                    org_id, user_id, template_id, agent_name, soul_md, memory_namespace, config
                ) VALUES (
                    :org_id, :user_id, :template_id, :agent_name, :soul_md, :memory_namespace, 
                    CAST(:config AS jsonb)
                ) RETURNING id
            """),
            {
                "org_id": org_id,
                "user_id": user_id,
                "template_id": template[0],
                "agent_name": agent_name,
                "soul_md": soul_md,
                "memory_namespace": memory_namespace,
                "config": '{"model": "' + template[4] + '", "max_daily_tokens": ' + str(template[5]) + '}'
            }
        )
        
        agent_id = insert_result.fetchone()[0]
        await db.commit()
        
        logger.info("Provisioned anchor agent %d for user %d in org %d", agent_id, user_id, org_id)
        
        return {
            "id": agent_id,
            "agent_name": agent_name,
            "memory_namespace": memory_namespace,
            "template_id": template[0],
            "soul_md": soul_md,
            "config": {"model": template[4], "max_daily_tokens": template[5]}
        }
    
    @staticmethod
    async def deprovision_agent(db: AsyncSession, org_id: int, user_id: int) -> bool:
        """Archive agent but preserve memory.
        
        Args:
            db: Database session
            org_id: Organization ID
            user_id: Employee user ID
            
        Returns:
            True if agent was archived, False if not found
        """
        await db.execute(text("SET search_path TO crm, public"))
        
        result = await db.execute(
            text("""
                UPDATE agent_instances 
                SET status = 'archived', updated_at = NOW()
                WHERE org_id = :org_id AND user_id = :user_id AND status != 'archived'
            """),
            {"org_id": org_id, "user_id": user_id}
        )
        
        if result.rowcount > 0:
            await db.commit()
            logger.info("Archived anchor agent for user %d in org %d", user_id, org_id)
            return True
        
        return False
    
    @staticmethod
    async def get_user_agent(db: AsyncSession, org_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """Get the user's anchor agent.
        
        Args:
            db: Database session
            org_id: Organization ID
            user_id: Employee user ID
            
        Returns:
            Agent instance dict or None if not found
        """
        await db.execute(text("SET search_path TO crm, public"))
        
        result = await db.execute(
            text("""
                SELECT ai.id, ai.agent_name, ai.soul_md, ai.memory_namespace, ai.status,
                       ai.config, ai.last_active, ai.created_at, ai.template_id,
                       at.name as template_name
                FROM agent_instances ai
                LEFT JOIN agent_templates at ON ai.template_id = at.id
                WHERE ai.org_id = :org_id AND ai.user_id = :user_id
            """),
            {"org_id": org_id, "user_id": user_id}
        )
        
        row = result.fetchone()
        if not row:
            return None
            
        return {
            "id": row[0],
            "agent_name": row[1],
            "soul_md": row[2],
            "memory_namespace": row[3],
            "status": row[4],
            "config": row[5],
            "last_active": row[6],
            "created_at": row[7],
            "template_id": row[8],
            "template_name": row[9]
        }
    
    @staticmethod
    async def list_org_agents(db: AsyncSession, org_id: int) -> List[Dict[str, Any]]:
        """List all provisioned agents in organization.
        
        Args:
            db: Database session
            org_id: Organization ID
            
        Returns:
            List of agent instance dicts
        """
        await db.execute(text("SET search_path TO crm, public"))
        
        result = await db.execute(
            text("""
                SELECT ai.id, ai.user_id, ai.agent_name, ai.memory_namespace, ai.status,
                       ai.last_active, ai.created_at, u.name as user_name, u.email,
                       at.name as template_name
                FROM agent_instances ai
                JOIN users u ON ai.user_id = u.id
                LEFT JOIN agent_templates at ON ai.template_id = at.id
                WHERE ai.org_id = :org_id
                ORDER BY ai.created_at DESC
            """),
            {"org_id": org_id}
        )
        
        agents = []
        for row in result:
            agents.append({
                "id": row[0],
                "user_id": row[1],
                "agent_name": row[2],
                "memory_namespace": row[3],
                "status": row[4],
                "last_active": row[5],
                "created_at": row[6],
                "user_name": row[7],
                "user_email": row[8],
                "template_name": row[9]
            })
            
        return agents
    
    @staticmethod
    async def update_agent_soul(
        db: AsyncSession, 
        org_id: int, 
        user_id: int, 
        soul_md: str
    ) -> bool:
        """Update user's agent SOUL.md (user customization).
        
        Args:
            db: Database session
            org_id: Organization ID
            user_id: Employee user ID
            soul_md: New SOUL.md content
            
        Returns:
            True if updated, False if agent not found
        """
        await db.execute(text("SET search_path TO crm, public"))
        
        result = await db.execute(
            text("""
                UPDATE agent_instances 
                SET soul_md = :soul_md, updated_at = NOW()
                WHERE org_id = :org_id AND user_id = :user_id AND status = 'active'
            """),
            {"org_id": org_id, "user_id": user_id, "soul_md": soul_md}
        )
        
        if result.rowcount > 0:
            await db.commit()
            logger.info("Updated SOUL.md for user %d anchor agent", user_id)
            return True
            
        return False