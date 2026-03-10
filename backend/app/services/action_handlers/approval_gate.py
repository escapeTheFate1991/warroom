"""Action handler: approval_gate — pauses workflow for human review."""

import logging

from app.services.notify import send_notification

logger = logging.getLogger(__name__)


async def handle(step: dict, context: dict, execution: dict) -> dict:
    """Pause workflow execution and wait for human approval.

    Step config keys:
        required_for (list[str], optional): What needs approval.
        approver (str, optional): Who should approve.
        notes (str, optional): Instructions for the approver.

    The executor checks result["requires_approval"] to pause the execution.
    """
    required_for = step.get("required_for", [])
    approver = step.get("approver", "owner")
    notes = step.get("notes", "")

    # Send a notification about the pending approval
    approval_items = ", ".join(required_for) if required_for else "workflow continuation"
    message = f"Approval needed for: {approval_items}"
    if notes:
        message += f"\n\nNotes: {notes}"
    message += f"\n\nApprover: {approver}"

    try:
        await send_notification(
            type="task",
            title="Workflow Approval Required",
            message=message,
            data={
                "workflow_id": execution.get("workflow_id"),
                "execution_id": execution.get("id"),
                "approver": approver,
                "required_for": required_for,
                "source": "workflow_executor",
                "action": "approval_gate",
            },
        )
    except Exception as exc:
        logger.warning("Failed to send approval notification: %s", exc)

    logger.info("Approval gate: pausing execution %s for %s", execution.get("id"), approver)
    return {
        "success": True,
        "result": {
            "requires_approval": True,
            "approver": approver,
            "required_for": required_for,
            "notes": notes,
        },
        "error": None,
    }
