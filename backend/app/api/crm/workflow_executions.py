"""CRM workflow execution endpoints — trigger, monitor, resume, retry, cancel."""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.crm_db import get_crm_db
from app.models.crm.automation import WorkflowExecution
from app.services.workflow_executor import (
    cancel_execution,
    resume_execution,
    retry_execution,
    start_execution,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Pydantic schemas ─────────────────────────────────────────────────

class ExecutionTriggerRequest(BaseModel):
    workflow_id: int
    trigger_event: str
    trigger_entity_type: Optional[str] = None
    trigger_entity_id: Optional[int] = None
    trigger_data: Optional[Dict[str, Any]] = None
    initial_context: Optional[Dict[str, Any]] = None


class ExecutionResumeRequest(BaseModel):
    approval_data: Optional[Dict[str, Any]] = None


class ExecutionResponse(BaseModel):
    id: int
    workflow_id: Optional[int] = None
    trigger_event: str
    trigger_entity_type: Optional[str] = None
    trigger_entity_id: Optional[int] = None
    trigger_data: Optional[Dict[str, Any]] = None
    status: str
    current_step: int
    step_results: Optional[List[Dict[str, Any]]] = None
    context: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


def _serialize_execution(ex: WorkflowExecution) -> dict:
    return {
        "id": ex.id,
        "workflow_id": ex.workflow_id,
        "trigger_event": ex.trigger_event,
        "trigger_entity_type": ex.trigger_entity_type,
        "trigger_entity_id": ex.trigger_entity_id,
        "trigger_data": ex.trigger_data,
        "status": ex.status,
        "current_step": ex.current_step or 0,
        "step_results": ex.step_results or [],
        "context": ex.context or {},
        "error": ex.error,
        "started_at": ex.started_at.isoformat() if ex.started_at else None,
        "completed_at": ex.completed_at.isoformat() if ex.completed_at else None,
        "created_at": ex.created_at.isoformat() if ex.created_at else None,
    }


# ── Endpoints ────────────────────────────────────────────────────────

@router.post("/workflow-executions", response_model=ExecutionResponse)
async def trigger_execution(data: ExecutionTriggerRequest):
    """Trigger a new workflow execution."""
    try:
        execution_id = await start_execution(
            workflow_id=data.workflow_id,
            trigger_event=data.trigger_event,
            trigger_entity_type=data.trigger_entity_type,
            trigger_entity_id=data.trigger_entity_id,
            trigger_data=data.trigger_data,
            initial_context=data.initial_context,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # Fetch the created execution to return it
    async with get_crm_db_session() as db:
        result = await db.execute(
            select(WorkflowExecution).where(WorkflowExecution.id == execution_id)
        )
        execution = result.scalar_one_or_none()
        if not execution:
            raise HTTPException(status_code=500, detail="Execution created but not found")
        return _serialize_execution(execution)


@router.get("/workflow-executions", response_model=List[ExecutionResponse])
async def list_executions(
    workflow_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_crm_db),
):
    """List workflow executions with optional filters."""
    query = select(WorkflowExecution)
    if workflow_id is not None:
        query = query.where(WorkflowExecution.workflow_id == workflow_id)
    if status is not None:
        query = query.where(WorkflowExecution.status == status)
    query = query.order_by(WorkflowExecution.created_at.desc()).offset(offset).limit(limit)

    result = await db.execute(query)
    return [_serialize_execution(ex) for ex in result.scalars().all()]


@router.get("/workflow-executions/{execution_id}", response_model=ExecutionResponse)
async def get_execution(execution_id: int, db: AsyncSession = Depends(get_crm_db)):
    """Get execution details including step results."""
    result = await db.execute(
        select(WorkflowExecution).where(WorkflowExecution.id == execution_id)
    )
    execution = result.scalar_one_or_none()
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    return _serialize_execution(execution)


@router.post("/workflow-executions/{execution_id}/resume", response_model=ExecutionResponse)
async def resume_paused_execution(
    execution_id: int,
    data: ExecutionResumeRequest = ExecutionResumeRequest(),
):
    """Resume a paused execution (after approval)."""
    try:
        await resume_execution(execution_id, approval_data=data.approval_data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    async with get_crm_db_session() as db:
        result = await db.execute(
            select(WorkflowExecution).where(WorkflowExecution.id == execution_id)
        )
        execution = result.scalar_one_or_none()
        if not execution:
            raise HTTPException(status_code=404, detail="Execution not found")
        return _serialize_execution(execution)


@router.post("/workflow-executions/{execution_id}/retry", response_model=ExecutionResponse)
async def retry_failed_execution(execution_id: int):
    """Retry a failed execution from the step that failed."""
    try:
        await retry_execution(execution_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    async with get_crm_db_session() as db:
        result = await db.execute(
            select(WorkflowExecution).where(WorkflowExecution.id == execution_id)
        )
        execution = result.scalar_one_or_none()
        if not execution:
            raise HTTPException(status_code=404, detail="Execution not found")
        return _serialize_execution(execution)


@router.post("/workflow-executions/{execution_id}/cancel", response_model=ExecutionResponse)
async def cancel_running_execution(execution_id: int, db: AsyncSession = Depends(get_crm_db)):
    """Cancel a running or paused execution."""
    try:
        await cancel_execution(execution_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    result = await db.execute(
        select(WorkflowExecution).where(WorkflowExecution.id == execution_id)
    )
    execution = result.scalar_one_or_none()
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    return _serialize_execution(execution)


# ── Helper: standalone session for post-mutation reads ────────────────

from contextlib import asynccontextmanager
from app.db.crm_db import crm_session
from sqlalchemy import text


@asynccontextmanager
async def get_crm_db_session():
    """Standalone CRM session for reads after background mutations."""
    async with crm_session() as session:
        await session.execute(text("SET search_path TO crm, public"))
        yield session
