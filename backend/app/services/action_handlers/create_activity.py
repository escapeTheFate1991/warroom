"""Action handler: create_activity — creates a CRM activity/task."""

import logging

from sqlalchemy import text

from app.db.crm_db import crm_session

logger = logging.getLogger(__name__)


async def handle(step: dict, context: dict, execution: dict) -> dict:
    """Create a CRM activity record.

    Step config keys:
        activity_type (str): Type of activity — task, call, meeting, note, email.
        title (str): Activity title/description.
    """
    activity_type = step.get("activity_type", "task")
    title = step.get("title", "")

    if not title:
        return {"success": False, "result": None, "error": "Missing 'title' in step config"}

    try:
        async with crm_session() as db:
            await db.execute(text("SET search_path TO crm, public"))
            result = await db.execute(
                text("""
                    INSERT INTO crm.activities (title, type, comment, additional, created_at)
                    VALUES (:title, :type, :comment, CAST(:additional AS jsonb), now())
                    RETURNING id
                """),
                {
                    "title": title,
                    "type": activity_type,
                    "comment": step.get("comment", ""),
                    "additional": "{}",
                },
            )
            row = result.fetchone()
            await db.commit()
            activity_id = row[0] if row else None

        logger.info("Activity created: [%s] %s (id=%s)", activity_type, title, activity_id)
        return {
            "success": True,
            "result": {"activity_id": activity_id, "type": activity_type, "title": title},
            "error": None,
        }
    except Exception as exc:
        logger.error("create_activity handler failed: %s", exc)
        return {"success": False, "result": None, "error": str(exc)}
