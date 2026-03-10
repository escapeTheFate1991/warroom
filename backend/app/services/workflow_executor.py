"""Workflow execution engine.

Loads a workflow's action steps and executes them sequentially via action handlers.
Tracks execution state per step, supports retry, pause (approval gates), and delay.
"""

import asyncio
import json
import logging
from copy import deepcopy
from datetime import datetime, timezone

from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.crm_db import crm_session
from app.models.crm.automation import Workflow, WorkflowExecution
from app.services.action_handlers import run_action

logger = logging.getLogger(__name__)

MAX_RETRIES = 3


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _update_execution(db: AsyncSession, execution_id: int, **fields) -> None:
    """Update execution record fields."""
    await db.execute(
        update(WorkflowExecution)
        .where(WorkflowExecution.id == execution_id)
        .values(**fields)
    )
    await db.commit()


async def start_execution(
    workflow_id: int,
    trigger_event: str,
    trigger_entity_type: str | None = None,
    trigger_entity_id: int | None = None,
    trigger_data: dict | None = None,
    initial_context: dict | None = None,
) -> int:
    """Create a new execution record and kick off processing in the background.

    Returns the execution ID.
    """
    async with crm_session() as db:
        await db.execute(text("SET search_path TO crm, public"))

        # Verify workflow exists and is active
        result = await db.execute(select(Workflow).where(Workflow.id == workflow_id))
        workflow = result.scalar_one_or_none()
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")
        if not workflow.is_active:
            raise ValueError(f"Workflow {workflow_id} is not active")

        execution = WorkflowExecution(
            workflow_id=workflow_id,
            trigger_event=trigger_event,
            trigger_entity_type=trigger_entity_type,
            trigger_entity_id=trigger_entity_id,
            trigger_data=trigger_data or {},
            status="pending",
            current_step=0,
            step_results=[],
            context=initial_context or {},
        )
        db.add(execution)
        await db.commit()
        await db.refresh(execution)
        execution_id = execution.id

    # Fire off execution in the background
    asyncio.create_task(_run_execution(execution_id))
    logger.info("Workflow execution %d started for workflow %d", execution_id, workflow_id)
    return execution_id


async def resume_execution(execution_id: int, approval_data: dict | None = None) -> None:
    """Resume a paused execution (after approval gate or delay).

    Optionally merges approval_data into the execution context.
    """
    async with crm_session() as db:
        await db.execute(text("SET search_path TO crm, public"))
        result = await db.execute(
            select(WorkflowExecution).where(WorkflowExecution.id == execution_id)
        )
        execution = result.scalar_one_or_none()
        if not execution:
            raise ValueError(f"Execution {execution_id} not found")
        if execution.status != "paused":
            raise ValueError(f"Execution {execution_id} is not paused (status: {execution.status})")

        # Merge approval data into context
        if approval_data:
            ctx = dict(execution.context or {})
            ctx.update(approval_data)
            execution.context = ctx

        execution.status = "running"
        await db.commit()

    asyncio.create_task(_run_execution(execution_id))
    logger.info("Execution %d resumed", execution_id)


async def retry_execution(execution_id: int) -> None:
    """Retry a failed execution from the step that failed."""
    async with crm_session() as db:
        await db.execute(text("SET search_path TO crm, public"))
        result = await db.execute(
            select(WorkflowExecution).where(WorkflowExecution.id == execution_id)
        )
        execution = result.scalar_one_or_none()
        if not execution:
            raise ValueError(f"Execution {execution_id} not found")
        if execution.status != "failed":
            raise ValueError(f"Execution {execution_id} is not failed (status: {execution.status})")

        execution.status = "running"
        execution.error = None
        await db.commit()

    asyncio.create_task(_run_execution(execution_id))
    logger.info("Execution %d retrying from step %d", execution_id, execution.current_step)


async def cancel_execution(execution_id: int) -> None:
    """Cancel a running or paused execution."""
    async with crm_session() as db:
        await db.execute(text("SET search_path TO crm, public"))
        result = await db.execute(
            select(WorkflowExecution).where(WorkflowExecution.id == execution_id)
        )
        execution = result.scalar_one_or_none()
        if not execution:
            raise ValueError(f"Execution {execution_id} not found")
        if execution.status in ("completed", "failed"):
            raise ValueError(f"Execution {execution_id} already {execution.status}")

        execution.status = "failed"
        execution.error = "Cancelled by user"
        execution.completed_at = datetime.now(timezone.utc)
        await db.commit()

    logger.info("Execution %d cancelled", execution_id)


async def _run_execution(execution_id: int) -> None:
    """Core execution loop — runs steps sequentially from current_step."""
    try:
        async with crm_session() as db:
            await db.execute(text("SET search_path TO crm, public"))

            # Load execution
            result = await db.execute(
                select(WorkflowExecution).where(WorkflowExecution.id == execution_id)
            )
            execution = result.scalar_one_or_none()
            if not execution:
                logger.error("Execution %d not found in runner", execution_id)
                return

            # Load workflow actions
            wf_result = await db.execute(
                select(Workflow).where(Workflow.id == execution.workflow_id)
            )
            workflow = wf_result.scalar_one_or_none()
            if not workflow:
                await _update_execution(db, execution_id, status="failed", error="Workflow not found")
                return

            actions = workflow.actions or []
            if not actions:
                await _update_execution(
                    db, execution_id,
                    status="completed",
                    completed_at=datetime.now(timezone.utc),
                )
                return

            # Mark as running
            if execution.status == "pending":
                execution.status = "running"
                execution.started_at = datetime.now(timezone.utc)
                await db.commit()

            context = dict(execution.context or {})
            step_results = list(execution.step_results or [])
            current_step = execution.current_step or 0

            for step_index in range(current_step, len(actions)):
                step = actions[step_index]
                action_type = step.get("type", "unknown")

                step_record = {
                    "step_index": step_index,
                    "action_type": action_type,
                    "status": "running",
                    "result": None,
                    "error": None,
                    "started_at": _now(),
                    "completed_at": None,
                }

                # Update current step
                execution.current_step = step_index
                # Ensure step_results list is long enough
                if len(step_results) <= step_index:
                    step_results.append(step_record)
                else:
                    step_results[step_index] = step_record

                execution.step_results = step_results
                await db.commit()

                # Execute the step with retry
                execution_dict = {
                    "id": execution.id,
                    "workflow_id": execution.workflow_id,
                    "trigger_event": execution.trigger_event,
                }

                handler_result = None
                last_error = None
                for attempt in range(MAX_RETRIES):
                    try:
                        handler_result = await run_action(action_type, step, context, execution_dict)
                        if handler_result.get("success"):
                            break
                        last_error = handler_result.get("error", "Unknown error")
                    except Exception as exc:
                        last_error = str(exc)
                        logger.warning(
                            "Step %d (%s) attempt %d failed: %s",
                            step_index, action_type, attempt + 1, last_error,
                        )
                        if attempt < MAX_RETRIES - 1:
                            await asyncio.sleep(2 ** attempt)  # Exponential backoff

                if not handler_result or not handler_result.get("success"):
                    # Step failed after all retries
                    step_record["status"] = "failed"
                    step_record["error"] = last_error
                    step_record["completed_at"] = _now()
                    step_results[step_index] = step_record

                    execution.step_results = step_results
                    execution.status = "failed"
                    execution.error = f"Step {step_index} ({action_type}) failed: {last_error}"
                    execution.completed_at = datetime.now(timezone.utc)
                    await db.commit()
                    logger.error("Execution %d failed at step %d: %s", execution_id, step_index, last_error)
                    return

                # Step succeeded
                step_result_data = handler_result.get("result", {})
                step_record["status"] = "completed"
                step_record["result"] = step_result_data
                step_record["completed_at"] = _now()
                step_results[step_index] = step_record

                # Merge step result into shared context
                if isinstance(step_result_data, dict):
                    context.update(step_result_data)

                execution.step_results = step_results
                execution.context = context
                await db.commit()

                # Check if this step requires pausing (approval gate or ai_draft with approval)
                if isinstance(step_result_data, dict) and step_result_data.get("requires_approval"):
                    execution.status = "paused"
                    execution.current_step = step_index + 1  # Resume from next step
                    await db.commit()
                    logger.info("Execution %d paused at step %d for approval", execution_id, step_index)
                    return

                # Handle delay steps
                if action_type == "delay" and isinstance(step_result_data, dict):
                    delay_seconds = step_result_data.get("delay_seconds", 0)
                    if delay_seconds > 0:
                        # For short delays (< 5 min), sleep inline
                        # For longer delays, pause and let scheduler resume
                        if delay_seconds <= 300:
                            logger.info("Execution %d: inline delay %ds", execution_id, delay_seconds)
                            await asyncio.sleep(delay_seconds)
                        else:
                            # Pause execution — a scheduler should resume it later
                            execution.status = "paused"
                            execution.current_step = step_index + 1
                            execution.context = {
                                **context,
                                "_resume_after": _now(),
                                "_delay_seconds": delay_seconds,
                            }
                            await db.commit()
                            logger.info(
                                "Execution %d paused for %ds delay at step %d",
                                execution_id, delay_seconds, step_index,
                            )
                            return

            # All steps completed
            execution.status = "completed"
            execution.completed_at = datetime.now(timezone.utc)
            execution.step_results = step_results
            execution.context = context
            await db.commit()
            logger.info("Execution %d completed successfully", execution_id)

    except Exception as exc:
        logger.exception("Execution %d crashed: %s", execution_id, exc)
        try:
            async with crm_session() as db:
                await db.execute(text("SET search_path TO crm, public"))
                await _update_execution(
                    db, execution_id,
                    status="failed",
                    error=f"Executor crash: {exc}",
                    completed_at=datetime.now(timezone.utc),
                )
        except Exception:
            logger.exception("Failed to mark execution %d as failed after crash", execution_id)
