"""
Agent Chat API - User-to-Agent Communication and Task Management

This API provides endpoints for users to:
1. Chat with their agents
2. Assign tasks to agents 
3. View task progress and results
4. Manage conversation history

All endpoints enforce user ownership - users can only interact with their own agents.
"""

import logging
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.crm_db import get_tenant_db
from app.services.tenant import get_org_id, get_user_id
from app.services.agent_chat import AgentChatService

logger = logging.getLogger(__name__)
router = APIRouter()

# ── Models ───────────────────────────────────────────────────────

class SendMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000)

class SendMessageResponse(BaseModel):
    success: bool
    agent_name: str
    message_sent: bool
    timestamp: str

class ChatMessage(BaseModel):
    role: str
    content: str
    metadata: Dict[str, Any] = {}
    task_id: Optional[str] = None
    created_at: Optional[str] = None

class ConversationResponse(BaseModel):
    messages: List[ChatMessage]
    agent_instance_id: int
    total_messages: int

class TaskAssignmentRequest(BaseModel):
    task_title: str = Field(..., min_length=1, max_length=200)
    task_description: str = Field(default="", max_length=2000)
    task_type: str = Field(default="general", max_length=50)
    priority: int = Field(default=5, ge=1, le=10)

class TaskUpdateRequest(BaseModel):
    status: str = Field(..., pattern=r"^(pending|assigned|in_progress|completed|failed|cancelled)$")
    result: Optional[Dict[str, Any]] = None

class TaskItem(BaseModel):
    id: int
    title: str
    description: str
    type: str
    priority: int
    status: str
    result: Optional[Dict[str, Any]] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    created_at: Optional[str] = None

class TaskQueueItem(TaskItem):
    agent_name: str
    agent_instance_id: int

# ── Helper Functions ─────────────────────────────────────────────

async def _init_agent_chat_tables(db: AsyncSession):
    """Initialize agent chat tables if they don't exist."""
    from sqlalchemy import text
    from pathlib import Path
    
    migration_path = Path(__file__).parent.parent / "db" / "agent_chat_migration.sql"
    if migration_path.exists():
        with open(migration_path, 'r') as f:
            migration_sql = f.read()
        await db.execute(text(migration_sql))
        await db.commit()

# ── User-to-Agent Chat Endpoints ────────────────────────────────

@router.post("/agent-chat/{agent_id}/messages", response_model=SendMessageResponse)
async def send_message_to_agent(
    agent_id: int,
    request: Request,
    body: SendMessageRequest,
    db: AsyncSession = Depends(get_tenant_db)
):
    """Send a message to an agent."""
    org_id = get_org_id(request)
    user_id = get_user_id(request)
    
    # Removed: tables created at startup
    #     await _init_agent_chat_tables(db)
    
    try:
        result = await AgentChatService.send_to_agent(
            db, org_id, user_id, agent_id, body.message
        )
        return SendMessageResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error sending message to agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to send message")

@router.get("/agent-chat/{agent_id}/messages", response_model=ConversationResponse)
async def get_conversation_history(
    agent_id: int,
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_tenant_db)
):
    """Get conversation history between user and agent."""
    org_id = get_org_id(request)
    user_id = get_user_id(request)
    
    # Removed: tables created at startup
    #     await _init_agent_chat_tables(db)
    
    try:
        messages = await AgentChatService.get_conversation(
            db, org_id, user_id, agent_id, limit
        )
        
        chat_messages = [ChatMessage(**msg) for msg in messages]
        
        return ConversationResponse(
            messages=chat_messages,
            agent_instance_id=agent_id,
            total_messages=len(chat_messages)
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting conversation for agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get conversation")

@router.delete("/agent-chat/{agent_id}/messages")
async def clear_conversation(
    agent_id: int,
    request: Request,
    db: AsyncSession = Depends(get_tenant_db)
):
    """Clear conversation history with an agent."""
    org_id = get_org_id(request)
    user_id = get_user_id(request)
    
    # Removed: tables created at startup
    #     await _init_agent_chat_tables(db)
    
    try:
        result = await AgentChatService.clear_conversation(
            db, org_id, user_id, agent_id
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error clearing conversation for agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear conversation")

# ── Agent Task Queue Endpoints ──────────────────────────────────

@router.post("/agent-chat/{agent_id}/tasks")
async def assign_task_to_agent(
    agent_id: int,
    request: Request,
    body: TaskAssignmentRequest,
    db: AsyncSession = Depends(get_tenant_db)
):
    """Assign a task to an agent."""
    org_id = get_org_id(request)
    user_id = get_user_id(request)
    
    # Removed: tables created at startup
    #     await _init_agent_chat_tables(db)
    
    try:
        result = await AgentChatService.assign_task(
            db, org_id, user_id, agent_id, 
            body.task_title, body.task_description, body.task_type, body.priority
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error assigning task to agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to assign task")

@router.get("/agent-chat/{agent_id}/tasks", response_model=List[TaskItem])
async def get_agent_tasks(
    agent_id: int,
    request: Request,
    db: AsyncSession = Depends(get_tenant_db)
):
    """Get all tasks assigned to an agent."""
    org_id = get_org_id(request)
    user_id = get_user_id(request)
    
    # Removed: tables created at startup
    #     await _init_agent_chat_tables(db)
    
    try:
        tasks = await AgentChatService.get_agent_tasks(
            db, org_id, user_id, agent_id
        )
        return [TaskItem(**task) for task in tasks]
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting tasks for agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get agent tasks")

@router.put("/agent-chat/{agent_id}/tasks/{task_id}")
async def update_task_status(
    agent_id: int,
    task_id: int,
    request: Request,
    body: TaskUpdateRequest,
    db: AsyncSession = Depends(get_tenant_db)
):
    """Update task status and optionally store result."""
    org_id = get_org_id(request)
    user_id = get_user_id(request)
    
    # Removed: tables created at startup
    #     await _init_agent_chat_tables(db)
    
    try:
        result = await AgentChatService.update_task_status(
            db, org_id, user_id, task_id, body.status, body.result
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating task {task_id} for agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update task")

@router.get("/agent-chat/tasks/queue", response_model=List[TaskQueueItem])
async def get_task_queue(
    request: Request,
    db: AsyncSession = Depends(get_tenant_db)
):
    """Get all pending tasks across user's agents."""
    org_id = get_org_id(request)
    user_id = get_user_id(request)
    
    # Removed: tables created at startup
    #     await _init_agent_chat_tables(db)
    
    try:
        tasks = await AgentChatService.get_task_queue(db, org_id, user_id)
        return [TaskQueueItem(**task) for task in tasks]
    except Exception as e:
        logger.error(f"Error getting task queue for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get task queue")

# ── Agent Response Endpoint (for agents to respond) ─────────────

@router.post("/agent-chat/{agent_id}/respond")
async def agent_respond(
    agent_id: int,
    request: Request,
    message: str,
    task_context: Optional[Dict[str, Any]] = None,
    db: AsyncSession = Depends(get_tenant_db)
):
    """Endpoint for agents to post responses (internal use)."""
    org_id = get_org_id(request)
    
    # Removed: tables created at startup
    #     await _init_agent_chat_tables(db)
    
    try:
        result = await AgentChatService.agent_respond(
            db, org_id, agent_id, message, task_context
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error recording agent response for {agent_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to record agent response")