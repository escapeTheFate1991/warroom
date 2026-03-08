"""Background scheduler for periodic tasks.

Uses asyncio tasks instead of APScheduler to avoid extra dependencies.
Runs twice-daily competitor syncs at randomized times within windows.
"""
import asyncio
import logging
import random
from datetime import datetime, time, timedelta, timezone

logger = logging.getLogger("scheduler")

_running_tasks: list[asyncio.Task] = []


async def _competitor_sync_job():
    """Sync all competitors. Called by the scheduler."""
    from app.db.crm_db import crm_session
    from app.api.content_intel import sync_all_competitors

    logger.info("Scheduled competitor sync starting")
    try:
        async with crm_session() as db:
            result = await sync_all_competitors(db)
            logger.info(
                "Scheduled sync complete: %d synced, %d failed",
                result.get("synced", 0),
                result.get("failed", 0),
            )
    except Exception as e:
        logger.error("Scheduled competitor sync failed: %s", e)


async def _audience_refresh_job():
    """Re-run audience intelligence analysis after sync."""
    logger.info("Scheduled audience refresh — placeholder for future implementation")
    # TODO: Wire to audience intelligence re-analysis endpoint


def _random_time_in_window(start_hour: int, end_hour: int) -> time:
    """Generate a random time within the given hour window."""
    hour = random.randint(start_hour, end_hour - 1)
    minute = random.randint(0, 59)
    return time(hour=hour, minute=minute)


def _seconds_until(target: time) -> float:
    """Seconds from now until the next occurrence of target time (EST)."""
    from zoneinfo import ZoneInfo
    est = ZoneInfo("America/New_York")
    now = datetime.now(est)
    target_dt = now.replace(hour=target.hour, minute=target.minute, second=0, microsecond=0)
    if target_dt <= now:
        target_dt += timedelta(days=1)
    return (target_dt - now).total_seconds()


async def _daily_loop(job_name: str, job_fn, start_hour: int, end_hour: int):
    """Run a job once per day at a random time within the window."""
    while True:
        target = _random_time_in_window(start_hour, end_hour)
        wait = _seconds_until(target)
        logger.info(
            "Scheduler: %s next run at %s EST (in %.0f min)",
            job_name,
            target.strftime("%H:%M"),
            wait / 60,
        )
        await asyncio.sleep(wait)
        try:
            await job_fn()
        except Exception as e:
            logger.error("Scheduler %s error: %s", job_name, e)
        # After running, sleep at least 20 hours to prevent double-runs
        await asyncio.sleep(20 * 3600)


async def start_scheduler():
    """Start all scheduled background tasks."""
    logger.info("Starting background scheduler")

    # Morning sync: 6am-10am EST
    morning = asyncio.create_task(
        _daily_loop("competitor-sync-am", _competitor_sync_job, 6, 10)
    )
    # Afternoon sync: 4pm-8pm EST
    afternoon = asyncio.create_task(
        _daily_loop("competitor-sync-pm", _competitor_sync_job, 16, 20)
    )

    _running_tasks.extend([morning, afternoon])
    logger.info("Scheduler started: 2 competitor sync jobs (AM 6-10, PM 4-8 EST)")


async def stop_scheduler():
    """Cancel all scheduled tasks."""
    for task in _running_tasks:
        task.cancel()
    _running_tasks.clear()
    logger.info("Scheduler stopped")
