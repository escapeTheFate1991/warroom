"""Action handler: notify_owner — creates an internal notification."""

import logging

from app.services.notify import send_notification

logger = logging.getLogger(__name__)


async def handle(step: dict, context: dict, execution: dict) -> dict:
    """Send an internal notification via the notification system.

    Step config keys:
        channel (str): Notification channel — inbox, alert, etc. Maps to notification type.
        message (str): Notification message body.
        title (str, optional): Notification title. Defaults to "Workflow Notification".
    """
    message = step.get("message", "")
    channel = step.get("channel", "info")
    title = step.get("title", "Workflow Notification")

    if not message:
        return {"success": False, "result": None, "error": "Missing 'message' in step config"}

    # Map channel names to notification types
    type_map = {
        "inbox": "info",
        "alert": "alert",
        "warning": "warning",
        "task": "task",
        "success": "success",
    }
    notif_type = type_map.get(channel, "info")

    try:
        notif_id = await send_notification(
            type=notif_type,
            title=title,
            message=message,
            data={
                "workflow_id": execution.get("workflow_id"),
                "execution_id": execution.get("id"),
                "source": "workflow_executor",
            },
        )
        if notif_id:
            logger.info("Notification sent: [%s] %s (id=%s)", notif_type, title, notif_id)
            return {"success": True, "result": {"notification_id": notif_id}, "error": None}
        else:
            return {"success": False, "result": None, "error": "Notification creation returned None"}
    except Exception as exc:
        logger.error("notify_owner handler failed: %s", exc)
        return {"success": False, "result": None, "error": str(exc)}
