"""arq worker — processes workflow execution jobs via Redis queue.

Job types:
  1. execute_workflow_job — kicks off a full workflow execution
  2. execute_step_job — runs execution from a specific step (for deferred delays / retries)
  3. resume_workflow_job — resumes a paused execution

Run with: arq app.services.workflow_queue.WorkerSettings
"""

import logging
from datetime import timedelta
from typing import Any

from app.services.redis_pool import REDIS_SETTINGS

logger = logging.getLogger(__name__)


async def execute_workflow_job(
    ctx: dict,
    workflow_id: int,
    trigger_event: str,
    trigger_entity_type: str | None = None,
    trigger_entity_id: int | None = None,
    trigger_data: dict | None = None,
    initial_context: dict | None = None,
) -> dict[str, Any]:
    """Execute a full workflow — called by arq worker.

    This imports and calls the executor's internal _run_execution after creating
    the execution record.
    """
    from app.services.workflow_executor import _create_execution_record, _run_execution

    execution_id = await _create_execution_record(
        workflow_id=workflow_id,
        trigger_event=trigger_event,
        trigger_entity_type=trigger_entity_type,
        trigger_entity_id=trigger_entity_id,
        trigger_data=trigger_data,
        initial_context=initial_context,
    )
    logger.info("arq: executing workflow %d → execution %d", workflow_id, execution_id)
    await _run_execution(execution_id)
    return {"execution_id": execution_id}


async def execute_step_job(
    ctx: dict,
    execution_id: int,
) -> dict[str, Any]:
    """Resume execution from its current_step — used for deferred delays.

    The execution record already has current_step set to the next step.
    """
    from app.services.workflow_executor import _run_execution

    logger.info("arq: resuming execution %d from deferred step", execution_id)
    await _run_execution(execution_id)
    return {"execution_id": execution_id}


async def resume_workflow_job(
    ctx: dict,
    execution_id: int,
    approval_data: dict | None = None,
) -> dict[str, Any]:
    """Resume a paused execution (approval gate) — called by arq worker."""
    from app.services.workflow_executor import _prepare_resume, _run_execution

    await _prepare_resume(execution_id, approval_data)
    logger.info("arq: resumed execution %d", execution_id)
    await _run_execution(execution_id)
    return {"execution_id": execution_id}


async def startup(ctx: dict) -> None:
    """arq worker startup hook."""
    logger.info("Workflow queue worker starting up")


async def shutdown(ctx: dict) -> None:
    """arq worker shutdown hook."""
    logger.info("Workflow queue worker shutting down")


class WorkerSettings:
    """arq worker configuration."""

    functions = [execute_workflow_job, execute_step_job, resume_workflow_job]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = REDIS_SETTINGS
    max_jobs = 10
    job_timeout = 600  # 10 minutes max per job
    retry_jobs = True
    max_tries = 3
    health_check_interval = 30
