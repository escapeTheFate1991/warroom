"""
Agent Chat Service

Manages conversations between users and their agents, and coordination between agents.
Integrates with Network-AI for inter-agent communication.
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.agent_comms import AgentComms

logger = logging.getLogger(__name__)

class AgentChatService:
    """Service for managing agent chat messages and task assignments."""
    
    @staticmethod
    async def send_to_agent(db: AsyncSession, org_id: int, user_id: int, agent_instance_id: int, message: str) -> Dict[str, Any]:
        """User sends a message to their agent. Validates ownership first."""
        
        # Verify agent belongs to user
        result = await db.execute(text("""
            SELECT ai.id, ai.agent_name 
            FROM agent_instances ai 
            WHERE ai.id = :agent_id AND ai.user_id = :user_id AND ai.org_id = :org_id
        """), {
            "agent_id": agent_instance_id,
            "user_id": user_id,
            "org_id": org_id
        })
        
        agent = result.mappings().first()
        if not agent:
            raise ValueError(f"Agent {agent_instance_id} not found or not owned by user {user_id}")
        
        # Store message in agent_chat_messages table
        await db.execute(text("""
            INSERT INTO agent_chat_messages (org_id, user_id, agent_instance_id, role, content)
            VALUES (:org_id, :user_id, :agent_id, 'user', :message)
        """), {
            "org_id": org_id,
            "user_id": user_id,
            "agent_id": agent_instance_id,
            "message": message
        })
        
        # Post to blackboard for agent processing via Network-AI
        await AgentComms.post_message(
            from_agent_id=user_id,  # User as agent 
            to_agent_id=agent_instance_id,
            org_id=org_id,
            message=message
        )
        
        await db.commit()
        
        return {
            "success": True,
            "agent_name": agent["agent_name"],
            "message_sent": True,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    @staticmethod
    async def get_conversation(db: AsyncSession, org_id: int, user_id: int, agent_instance_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """Get chat history between user and their agent."""
        
        # Verify agent belongs to user
        result = await db.execute(text("""
            SELECT ai.id 
            FROM agent_instances ai 
            WHERE ai.id = :agent_id AND ai.user_id = :user_id AND ai.org_id = :org_id
        """), {
            "agent_id": agent_instance_id,
            "user_id": user_id,
            "org_id": org_id
        })
        
        if not result.first():
            raise ValueError(f"Agent {agent_instance_id} not found or not owned by user {user_id}")
        
        # Get conversation history
        result = await db.execute(text("""
            SELECT role, content, metadata, task_id, created_at
            FROM agent_chat_messages
            WHERE org_id = :org_id AND user_id = :user_id AND agent_instance_id = :agent_id
            ORDER BY created_at DESC
            LIMIT :limit
        """), {
            "org_id": org_id,
            "user_id": user_id,
            "agent_id": agent_instance_id,
            "limit": limit
        })
        
        messages = []
        for row in result.mappings():
            messages.append({
                "role": row["role"],
                "content": row["content"],
                "metadata": row["metadata"] or {},
                "task_id": row["task_id"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None
            })
        
        # Reverse to get chronological order
        return list(reversed(messages))
    
    @staticmethod
    async def agent_respond(db: AsyncSession, org_id: int, agent_instance_id: int, message: str, task_context: Optional[Dict] = None) -> Dict[str, Any]:
        """Agent posts a response. Can include task results for knowledge pool."""
        
        # Get agent info
        result = await db.execute(text("""
            SELECT ai.user_id, ai.agent_name
            FROM agent_instances ai
            WHERE ai.id = :agent_id AND ai.org_id = :org_id
        """), {
            "agent_id": agent_instance_id,
            "org_id": org_id
        })
        
        agent_info = result.mappings().first()
        if not agent_info:
            raise ValueError(f"Agent {agent_instance_id} not found")
        
        # Store agent response
        task_id = task_context.get("task_id") if task_context else None
        metadata = {"task_context": task_context} if task_context else {}
        
        await db.execute(text("""
            INSERT INTO agent_chat_messages (org_id, user_id, agent_instance_id, role, content, metadata, task_id)
            VALUES (:org_id, :user_id, :agent_id, 'agent', :message, CAST(:metadata AS jsonb), :task_id)
        """), {
            "org_id": org_id,
            "user_id": agent_info["user_id"],
            "agent_id": agent_instance_id,
            "message": message,
            "metadata": json.dumps(metadata),
            "task_id": task_id
        })
        
        # If task_context provided, also contribute to knowledge pool
        if task_context:
            await AgentComms.post_task_result(
                org_id=org_id,
                agent_id=agent_instance_id,
                task_id=task_id,
                result=task_context
            )
        
        await db.commit()
        
        return {
            "success": True,
            "agent_name": agent_info["agent_name"],
            "response_stored": True,
            "task_contributed": bool(task_context),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    @staticmethod
    async def assign_task(db: AsyncSession, org_id: int, user_id: int, agent_instance_id: int, task_title: str, task_description: str = "", task_type: str = "general", priority: int = 5) -> Dict[str, Any]:
        """Assign a task to an agent."""
        
        # Verify agent belongs to user
        result = await db.execute(text("""
            SELECT ai.id, ai.agent_name 
            FROM agent_instances ai 
            WHERE ai.id = :agent_id AND ai.user_id = :user_id AND ai.org_id = :org_id
        """), {
            "agent_id": agent_instance_id,
            "user_id": user_id,
            "org_id": org_id
        })
        
        agent = result.mappings().first()
        if not agent:
            raise ValueError(f"Agent {agent_instance_id} not found or not owned by user {user_id}")
        
        # Create task assignment
        result = await db.execute(text("""
            INSERT INTO agent_task_queue (org_id, agent_instance_id, assigned_by_user_id, task_title, task_description, task_type, priority)
            VALUES (:org_id, :agent_id, :user_id, :title, :description, :type, :priority)
            RETURNING id
        """), {
            "org_id": org_id,
            "agent_id": agent_instance_id,
            "user_id": user_id,
            "title": task_title,
            "description": task_description,
            "type": task_type,
            "priority": priority
        })
        
        task_id = result.scalar()
        await db.commit()
        
        return {
            "success": True,
            "task_id": task_id,
            "agent_name": agent["agent_name"],
            "task_title": task_title,
            "status": "pending"
        }
    
    @staticmethod
    async def get_agent_tasks(db: AsyncSession, org_id: int, user_id: int, agent_instance_id: int) -> List[Dict[str, Any]]:
        """Get tasks assigned to an agent."""
        
        # Verify agent belongs to user
        result = await db.execute(text("""
            SELECT ai.id 
            FROM agent_instances ai 
            WHERE ai.id = :agent_id AND ai.user_id = :user_id AND ai.org_id = :org_id
        """), {
            "agent_id": agent_instance_id,
            "user_id": user_id,
            "org_id": org_id
        })
        
        if not result.first():
            raise ValueError(f"Agent {agent_instance_id} not found or not owned by user {user_id}")
        
        # Get tasks
        result = await db.execute(text("""
            SELECT id, task_title, task_description, task_type, priority, status, result, 
                   started_at, completed_at, created_at
            FROM agent_task_queue
            WHERE org_id = :org_id AND agent_instance_id = :agent_id
            ORDER BY priority DESC, created_at DESC
        """), {
            "org_id": org_id,
            "agent_id": agent_instance_id
        })
        
        tasks = []
        for row in result.mappings():
            tasks.append({
                "id": row["id"],
                "title": row["task_title"],
                "description": row["task_description"],
                "type": row["task_type"],
                "priority": row["priority"],
                "status": row["status"],
                "result": row["result"],
                "started_at": row["started_at"].isoformat() if row["started_at"] else None,
                "completed_at": row["completed_at"].isoformat() if row["completed_at"] else None,
                "created_at": row["created_at"].isoformat() if row["created_at"] else None
            })
        
        return tasks
    
    @staticmethod
    async def update_task_status(db: AsyncSession, org_id: int, user_id: int, task_id: int, status: str, result: Optional[Dict] = None) -> Dict[str, Any]:
        """Update task status and optionally store result."""
        
        # Verify task belongs to user's agent
        check_result = await db.execute(text("""
            SELECT atq.id, atq.agent_instance_id, ai.agent_name
            FROM agent_task_queue atq
            JOIN agent_instances ai ON ai.id = atq.agent_instance_id
            WHERE atq.id = :task_id AND atq.org_id = :org_id AND ai.user_id = :user_id
        """), {
            "task_id": task_id,
            "org_id": org_id,
            "user_id": user_id
        })
        
        task_info = check_result.mappings().first()
        if not task_info:
            raise ValueError(f"Task {task_id} not found or not owned by user {user_id}")
        
        # Update task
        update_fields = ["status = :status", "updated_at = NOW()"]
        params = {
            "task_id": task_id,
            "org_id": org_id,
            "status": status
        }
        
        if status == "in_progress":
            update_fields.append("started_at = NOW()")
        elif status in ["completed", "failed"]:
            update_fields.append("completed_at = NOW()")
        
        if result:
            update_fields.append("result = CAST(:result AS jsonb)")
            params["result"] = json.dumps(result)
        
        await db.execute(text(f"""
            UPDATE agent_task_queue 
            SET {', '.join(update_fields)}
            WHERE id = :task_id AND org_id = :org_id
        """), params)
        
        await db.commit()
        
        return {
            "success": True,
            "task_id": task_id,
            "agent_name": task_info["agent_name"],
            "status": status,
            "result_stored": bool(result)
        }
    
    @staticmethod
    async def get_task_queue(db: AsyncSession, org_id: int, user_id: int) -> List[Dict[str, Any]]:
        """Get all pending tasks across user's agents."""
        
        result = await db.execute(text("""
            SELECT atq.id, atq.task_title, atq.task_description, atq.task_type, 
                   atq.priority, atq.status, atq.created_at,
                   ai.agent_name, ai.id as agent_instance_id
            FROM agent_task_queue atq
            JOIN agent_instances ai ON ai.id = atq.agent_instance_id
            WHERE atq.org_id = :org_id AND ai.user_id = :user_id
            ORDER BY atq.priority DESC, atq.created_at ASC
        """), {
            "org_id": org_id,
            "user_id": user_id
        })
        
        tasks = []
        for row in result.mappings():
            tasks.append({
                "id": row["id"],
                "title": row["task_title"],
                "description": row["task_description"],
                "type": row["task_type"],
                "priority": row["priority"],
                "status": row["status"],
                "agent_name": row["agent_name"],
                "agent_instance_id": row["agent_instance_id"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None
            })
        
        return tasks
    
    @staticmethod
    async def clear_conversation(db: AsyncSession, org_id: int, user_id: int, agent_instance_id: int) -> Dict[str, Any]:
        """Clear conversation history between user and agent."""
        
        # Verify agent belongs to user
        result = await db.execute(text("""
            SELECT ai.id 
            FROM agent_instances ai 
            WHERE ai.id = :agent_id AND ai.user_id = :user_id AND ai.org_id = :org_id
        """), {
            "agent_id": agent_instance_id,
            "user_id": user_id,
            "org_id": org_id
        })
        
        if not result.first():
            raise ValueError(f"Agent {agent_instance_id} not found or not owned by user {user_id}")
        
        # Delete messages
        delete_result = await db.execute(text("""
            DELETE FROM agent_chat_messages
            WHERE org_id = :org_id AND user_id = :user_id AND agent_instance_id = :agent_id
        """), {
            "org_id": org_id,
            "user_id": user_id,
            "agent_id": agent_instance_id
        })
        
        await db.commit()
        
        return {
            "success": True,
            "messages_deleted": delete_result.rowcount
        }