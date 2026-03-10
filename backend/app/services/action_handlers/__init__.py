"""Action handler registry — maps action type strings to handler modules."""

from . import (
    send_email,
    send_sms,
    make_call,
    delay,
    create_activity,
    create_calendar_event,
    notify_owner,
    ai_draft_message,
    approval_gate,
)

# Registry: action_type → handler module (each has async handle(step, context, execution))
HANDLER_REGISTRY: dict[str, object] = {
    "send_email": send_email,
    "send_sms": send_sms,
    "make_call": make_call,
    "delay": delay,
    "create_activity": create_activity,
    "create_calendar_event": create_calendar_event,
    "notify_owner": notify_owner,
    "ai_draft_message": ai_draft_message,
    "approval_gate": approval_gate,
}


async def run_action(action_type: str, step: dict, context: dict, execution: dict) -> dict:
    """Look up and execute an action handler by type.

    Returns: {"success": bool, "result": any, "error": str|None}
    """
    handler_module = HANDLER_REGISTRY.get(action_type)
    if not handler_module:
        return {
            "success": False,
            "result": None,
            "error": f"Unknown action type: {action_type}. Available: {', '.join(sorted(HANDLER_REGISTRY.keys()))}",
        }
    return await handler_module.handle(step, context, execution)
