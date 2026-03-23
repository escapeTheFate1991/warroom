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
    from app.api.content_intel import sync_all_competitors

    logger.info("Scheduled competitor sync starting")
    try:
        result = await sync_all_competitors()
        logger.info(
            "Scheduled sync complete: %s",
            result.get("message", "No details available"),
        )
    except Exception as e:
        logger.error("Scheduled competitor sync failed: %s", e)


async def _social_sync_job():
    """Sync all connected social accounts. Called by the scheduler."""
    from app.db.crm_db import crm_session
    from app.api.social_sync import sync_all

    logger.info("Scheduled social sync starting")
    try:
        async with crm_session() as db:
            result = await sync_all(db)
            logger.info(
                "Scheduled social sync complete: %d account results",
                len(result.get("results", [])),
            )
    except Exception as e:
        logger.error("Scheduled social sync failed: %s", e)


async def _audience_refresh_job():
    """Re-run audience intelligence analysis after sync."""
    logger.info("Scheduled audience refresh — placeholder for future implementation")
    # TODO: Wire to audience intelligence re-analysis endpoint


async def _follower_polling_job():
    """Poll all Instagram accounts for new followers."""
    from app.services.follower_polling import poll_all_accounts

    logger.info("Scheduled Instagram follower polling starting")
    try:
        result = await poll_all_accounts()
        new_followers = result.get("total_new_followers", 0)
        accounts_polled = result.get("accounts_polled", 0)
        logger.info(
            "Follower polling complete: %d accounts polled, %d new followers detected",
            accounts_polled,
            new_followers,
        )
    except Exception as e:
        logger.error("Scheduled follower polling failed: %s", e)


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


async def _hourly_loop(job_name: str, job_fn, interval_seconds: int = 3600):
    """Run a job at regular intervals (default: every hour)."""
    while True:
        logger.info("Scheduler: %s starting (next run in %d minutes)", job_name, interval_seconds // 60)
        try:
            await job_fn()
        except Exception as e:
            logger.error("Scheduler %s error: %s", job_name, e)
        await asyncio.sleep(interval_seconds)


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
    social_morning = asyncio.create_task(
        _daily_loop("social-sync-am", _social_sync_job, 8, 12)
    )
    social_afternoon = asyncio.create_task(
        _daily_loop("social-sync-pm", _social_sync_job, 13, 17)
    )
    
    # Follower polling: every hour
    follower_polling = asyncio.create_task(
        _hourly_loop("instagram-follower-polling", _follower_polling_job, 3600)
    )

    _running_tasks.extend([morning, afternoon, social_morning, social_afternoon, follower_polling])
    logger.info(
        "Scheduler started: competitor sync (AM 6-10, PM 4-8 EST), social sync (AM 8-12, PM 1-5 EST), and Instagram follower polling (hourly)"
    )


async def stop_scheduler():
    """Cancel all scheduled tasks."""
    for task in _running_tasks:
        task.cancel()
    _running_tasks.clear()
    logger.info("Scheduler stopped")
