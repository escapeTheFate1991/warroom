"""Action handler: ai_draft_message — uses Claude Haiku to draft a message."""

import logging
import os

import httpx

logger = logging.getLogger(__name__)

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-haiku-3-5-20241022"


async def handle(step: dict, context: dict, execution: dict) -> dict:
    """Draft a message using Claude Haiku.

    Step config keys:
        goal (str): What the draft should accomplish.
        channel (str): Target channel (email, sms, etc.) — influences tone/length.
        inputs (list[str], optional): Context fields to pull from execution context.
        approval_required (bool, optional): If True, pauses execution for human review.

    Returns the drafted message in result["draft"]. If approval_required, also
    sets result["requires_approval"] = True so the executor can pause.
    """
    goal = step.get("goal", "")
    channel = step.get("channel", "email")
    input_fields = step.get("inputs", [])
    approval_required = step.get("approval_required", False)

    if not goal:
        return {"success": False, "result": None, "error": "Missing 'goal' in step config"}

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        # Try loading from settings DB
        try:
            from app.services.twilio_client import get_setting_value
            api_key = await get_setting_value("anthropic_api_key") or ""
        except Exception:
            pass

    if not api_key:
        return {"success": False, "result": None, "error": "No Anthropic API key configured"}

    # Build context summary from available data
    context_parts = []
    for field in input_fields:
        value = context.get(field)
        if value:
            context_parts.append(f"- {field}: {value}")

    # Add common context
    for key in ("contact_name", "contact_email", "contact_phone", "deal_title", "entity_type"):
        if key not in input_fields and key in context:
            context_parts.append(f"- {key}: {context[key]}")

    context_summary = "\n".join(context_parts) if context_parts else "No additional context available."

    # Channel-specific guidelines
    channel_guidelines = {
        "sms": "Keep it under 160 characters. Conversational tone. No HTML.",
        "email": "Professional but warm. Use proper greeting and sign-off. HTML formatting allowed.",
        "inbox": "Internal note — concise, action-oriented.",
    }
    guidelines = channel_guidelines.get(channel, "Clear and professional.")

    prompt = (
        f"You are drafting a {channel} message for a CRM workflow.\n\n"
        f"Goal: {goal}\n\n"
        f"Available context:\n{context_summary}\n\n"
        f"Channel guidelines: {guidelines}\n\n"
        f"Draft the message now. Output ONLY the message text, no preamble."
    )

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                ANTHROPIC_API_URL,
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": MODEL,
                    "max_tokens": 512,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            if resp.status_code not in (200, 201):
                return {"success": False, "result": None, "error": f"Anthropic API error ({resp.status_code}): {resp.text[:200]}"}

            data = resp.json()
            draft = ""
            for block in data.get("content", []):
                if block.get("type") == "text":
                    draft += block.get("text", "")

        logger.info("AI draft created for channel=%s, approval_required=%s", channel, approval_required)
        result = {
            "draft": draft.strip(),
            "channel": channel,
            "goal": goal,
            "requires_approval": approval_required,
        }
        return {"success": True, "result": result, "error": None}
    except Exception as exc:
        logger.error("ai_draft_message handler failed: %s", exc)
        return {"success": False, "result": None, "error": str(exc)}
