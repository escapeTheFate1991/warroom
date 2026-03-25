"""Minimal Arq worker settings for workflow queue.

This is a stub to prevent the worker container from crashing.
The original workflow_queue.py was removed during socialRecycle cleanup.

This minimal implementation:
1. Provides WorkerSettings for arq worker startup
2. Configures Redis connection using existing redis_pool settings
3. Registers no background tasks (empty worker that stays alive)
4. Provides hooks for future task registration if needed
"""

import logging
from typing import Optional, List, Callable, Any

from app.services.redis_pool import get_redis_settings

logger = logging.getLogger(__name__)

# Import Redis settings from existing redis_pool configuration
REDIS_SETTINGS = get_redis_settings()

# Background task functions (currently empty)
# Future tasks can be added here and registered in FUNCTIONS below
async def placeholder_task() -> str:
    """Placeholder task to demonstrate arq task structure."""
    logger.info("Placeholder task executed")
    return "placeholder complete"

# Task registry - arq requires at least one function
FUNCTIONS: List[Callable[..., Any]] = [placeholder_task]

class WorkerSettings:
    """Arq worker configuration."""
    
    # Redis connection settings
    redis_settings = REDIS_SETTINGS
    
    # Task functions to register (currently empty)
    functions = FUNCTIONS
    
    # Worker configuration
    queue_name = "workflow_queue"
    max_jobs = 10
    job_timeout = 300  # 5 minutes
    keep_result = 3600  # Keep results for 1 hour
    
    # Logging
    log_results = True
    
    @classmethod
    def get_worker_settings(cls) -> dict:
        """Get worker configuration as dict."""
        return {
            "redis_settings": cls.redis_settings,
            "functions": cls.functions,
            "queue_name": cls.queue_name,
            "max_jobs": cls.max_jobs,
            "job_timeout": cls.job_timeout,
            "keep_result": cls.keep_result,
            "log_results": cls.log_results,
        }


# For future use: helper function to enqueue tasks
async def enqueue_task(task_name: str, *args, **kwargs) -> Optional[str]:
    """Enqueue a background task (future use)."""
    from app.services.redis_pool import get_redis_pool
    
    try:
        redis = await get_redis_pool()
        if redis is None:
            logger.warning("Redis unavailable, cannot enqueue task %s", task_name)
            return None
        
        # Task enqueueing would be implemented here when needed
        logger.info("Task enqueueing not implemented: %s", task_name)
        return None
        
    except Exception as e:
        logger.error("Failed to enqueue task %s: %s", task_name, e)
        return None


# Module-level worker settings for arq command line
# This is what gets imported by: arq app.services.workflow_queue.WorkerSettings
WorkerSettings = WorkerSettings