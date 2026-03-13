"""Chat — WebSocket relay to OpenClaw gateway.

Implements the OpenClaw Gateway WS protocol v3 with device identity auth
for full operator scopes (chat.send, chat.history, chat.abort).
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
import websockets
import asyncio
import json
import os
import uuid
import time
import base64
import logging
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import load_pem_private_key, load_pem_public_key, Encoding, PublicFormat

from app.api.agent_contract import AssignableEntityType, load_agent_assignment_map
from app.db.crm_db import get_crm_db

logger = logging.getLogger("chat")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(levelname)s:%(name)s: %(message)s"))
    logger.addHandler(handler)

router = APIRouter()

OPENCLAW_WS = os.getenv("OPENCLAW_WS_URL", "ws://10.0.0.1:18789")
OPENCLAW_API = os.getenv("OPENCLAW_API_URL", "http://10.0.0.1:18789")
OPENCLAW_TOKEN = os.getenv("OPENCLAW_AUTH_TOKEN", "")
OPENCLAW_PASSWORD = os.getenv("OPENCLAW_AUTH_PASSWORD", "")
DEFAULT_SESSION_KEY = os.getenv("OPENCLAW_SESSION_KEY", "warroom")

# Device identity (Ed25519 keys for scope authorization)
DEVICE_ID = os.getenv("OPENCLAW_DEVICE_ID", "")
DEVICE_PUBLIC_KEY_PEM = os.getenv("OPENCLAW_DEVICE_PUBLIC_KEY", "")
DEVICE_PRIVATE_KEY_PEM = os.getenv("OPENCLAW_DEVICE_PRIVATE_KEY", "")

SCOPES = ["operator.admin", "operator.read", "operator.write", "operator.approvals", "operator.pairing"]
CLIENT_ID = "openclaw-probe"
CLIENT_MODE = "webchat"
PROTOCOL_VERSION = 3


class GroundingFact(BaseModel):
    label: str
    value: Any


class GroundingContext(BaseModel):
    surface: str = "general"
    entity_type: AssignableEntityType | None = None
    entity_id: str | None = None
    title: str | None = None
    summary: str | None = None
    facts: list[GroundingFact] = Field(default_factory=list)


class ChatMessageRequest(BaseModel):
    message: str
    context: GroundingContext | None = None


def base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def build_device_auth(nonce: str) -> dict | None:
    """Build signed device auth payload for the connect frame."""
    if not DEVICE_PRIVATE_KEY_PEM or not DEVICE_ID:
        return None

    signed_at_ms = int(time.time() * 1000)
    scopes_str = ",".join(SCOPES)
    token_str = OPENCLAW_TOKEN or ""

    # v2|deviceId|clientId|clientMode|role|scopes|signedAtMs|token|nonce
    payload = "|".join([
        "v2",
        DEVICE_ID,
        CLIENT_ID,
        CLIENT_MODE,
        "operator",
        scopes_str,
        str(signed_at_ms),
        token_str,
        nonce,
    ])

    # Ed25519 sign
    private_key = load_pem_private_key(DEVICE_PRIVATE_KEY_PEM.encode(), password=None)
    signature = private_key.sign(payload.encode("utf-8"))

    # Extract raw public key bytes (32 bytes)
    public_key = load_pem_public_key(DEVICE_PUBLIC_KEY_PEM.encode())
    raw_public = public_key.public_bytes(Encoding.Raw, PublicFormat.Raw)

    return {
        "id": DEVICE_ID,
        "publicKey": base64url_encode(raw_public),
        "signature": base64url_encode(signature),
        "signedAt": signed_at_ms,
        "nonce": nonce,
    }


def make_req(method: str, params: dict) -> str:
    return json.dumps({"type": "req", "id": str(uuid.uuid4()), "method": method, "params": params})


async def connect_to_gateway(origin: str = "http://10.0.0.11:8300"):
    """Connect to OpenClaw gateway with device identity auth."""
    ws = await websockets.connect(
        OPENCLAW_WS,
        open_timeout=10,
        origin=origin,
        ping_interval=20,
        ping_timeout=20,
    )

    # Wait for connect.challenge
    raw = await asyncio.wait_for(ws.recv(), timeout=10)
    challenge = json.loads(raw)
    nonce = challenge.get("payload", {}).get("nonce", "")
    logger.info("Got challenge, nonce=%s...", nonce[:16])

    # Build connect params with device identity
    auth = {}
    if OPENCLAW_TOKEN:
        auth["token"] = OPENCLAW_TOKEN
    if OPENCLAW_PASSWORD:
        auth["password"] = OPENCLAW_PASSWORD

    params = {
        "client": {
            "id": CLIENT_ID,
            "version": "1.0.0",
            "platform": "linux",
            "mode": CLIENT_MODE,
            "instanceId": str(uuid.uuid4()),
        },
        "auth": auth,
        "role": "operator",
        "scopes": SCOPES,
        "caps": [],
        "minProtocol": PROTOCOL_VERSION,
        "maxProtocol": PROTOCOL_VERSION,
    }

    device = build_device_auth(nonce)
    if device:
        params["device"] = device

    await ws.send(make_req("connect", params))
    resp_raw = await asyncio.wait_for(ws.recv(), timeout=10)
    resp = json.loads(resp_raw)

    if not resp.get("ok"):
        err = resp.get("error", {}).get("message", "unknown error")
        await ws.close()
        raise ConnectionError(f"Gateway connect failed: {err}")

    granted = resp.get("payload", {}).get("scopes", [])
    logger.info("Connected to gateway, scopes=%s", granted)
    return ws


@router.websocket("/ws")
async def chat_ws(ws: WebSocket):
    """Relay WebSocket between WAR ROOM frontend and OpenClaw gateway."""
    await ws.accept()

    session_key = DEFAULT_SESSION_KEY
    openclaw = None
    gateway_alive = asyncio.Event()
    shutdown = asyncio.Event()

    async def ensure_gateway():
        """Connect (or reconnect) to gateway, returns the ws."""
        nonlocal openclaw
        if openclaw:
            try:
                await openclaw.close()
            except Exception:
                pass
        openclaw = await connect_to_gateway()
        gateway_alive.set()
        return openclaw

    try:
        await ensure_gateway()

        await ws.send_text(json.dumps({"type": "connected", "sessionKey": session_key}))

        # Fetch initial history
        await openclaw.send(make_req("chat.history", {"sessionKey": session_key, "limit": 200}))

        async def forward_from_gateway():
            nonlocal openclaw
            while not shutdown.is_set():
                try:
                    async for message in openclaw:
                        raw_str = message if isinstance(message, str) else message.decode()
                        data = json.loads(raw_str)
                        msg_type = data.get("type", "")
                        method = data.get("method", "")
                        logger.info("GW-RAW: type=%s event=%s method=%s keys=%s", msg_type, data.get('event', ''), method, list(data.keys())[:6])

                        # Detect rate limit in response errors and forward as typed alert
                        if msg_type == "res" and not data.get("ok"):
                            err = data.get("error", {})
                            err_code = err.get("code", "")
                            err_msg = err.get("message", "")
                            if "rate" in err_code.lower() or "429" in err_msg or "rate limit" in err_msg.lower():
                                await ws.send_text(json.dumps({
                                    "type": "error",
                                    "code": "rate_limited",
                                    "message": err_msg or "API rate limit reached. Please wait before retrying.",
                                }))

                        # Filter: only forward events for the active session
                        # Gateway returns full key (e.g. "agent:main:warroom") while we send short key ("warroom")
                        if msg_type == "event":
                            payload = data.get("payload", {})
                            event_session = payload.get("sessionKey", "") or payload.get("session", "")
                            if event_session and session_key not in event_session:
                                continue

                            # Detect compaction events from gateway
                            event_stream = payload.get("stream", "")
                            if event_stream == "compaction":
                                phase = payload.get("data", {}).get("phase", "")
                                if phase == "start":
                                    await ws.send_text(json.dumps({
                                        "type": "compaction",
                                        "phase": "start",
                                        "message": "Context compressing — older messages being summarized...",
                                    }))
                                elif phase == "end":
                                    will_retry = payload.get("data", {}).get("willRetry", False)
                                    if not will_retry:
                                        await ws.send_text(json.dumps({
                                            "type": "compaction",
                                            "phase": "end",
                                            "message": "Context compressed — older messages summarized to free up space.",
                                        }))

                            # Detect rate limit in chat events
                            chat_state = payload.get("state", "")
                            if chat_state == "error":
                                err_text = ""
                                msg = payload.get("message", "")
                                if isinstance(msg, str):
                                    err_text = msg
                                elif isinstance(msg, dict):
                                    err_text = msg.get("content", "") or msg.get("text", "")
                                if "rate limit" in err_text.lower() or "429" in err_text:
                                    await ws.send_text(json.dumps({
                                        "type": "error",
                                        "code": "rate_limited",
                                        "message": err_text or "API rate limit reached.",
                                    }))

                        await ws.send_text(json.dumps(data))
                except websockets.exceptions.ConnectionClosed as e:
                    logger.warning("Gateway WS closed: code=%s reason=%s", e.code, e.reason)
                    if shutdown.is_set():
                        break
                    # Auto-reconnect
                    await ws.send_text(json.dumps({"type": "status", "message": "Reconnecting to gateway..."}))
                    for attempt in range(5):
                        try:
                            await asyncio.sleep(1 * (attempt + 1))
                            await ensure_gateway()
                            logger.info("Reconnected to gateway")
                            await ws.send_text(json.dumps({"type": "status", "message": "Reconnected"}))
                            # Re-fetch history after reconnect
                            await openclaw.send(make_req("chat.history", {"sessionKey": session_key, "limit": 50}))
                            break
                        except Exception as re_err:
                            logger.warning("Reconnect attempt %d failed: %s", attempt + 1, re_err)
                    else:
                        await ws.send_text(json.dumps({"type": "error", "message": "Gateway reconnect failed after 5 attempts"}))
                        shutdown.set()
                        break
                except Exception as e:
                    logger.error("Gateway forward error: %s", e)
                    if shutdown.is_set():
                        break

        async def forward_from_client():
            nonlocal session_key, openclaw
            try:
                while not shutdown.is_set():
                    raw = await ws.receive_text()
                    data = json.loads(raw)
                    action = data.get("action", "")

                    if action == "send":
                        message = data.get("message", "")
                        images = data.get("images", [])
                        if not message and not images:
                            continue
                        logger.info("Client→GW: chat.send (%d chars, %d images)", len(message), len(images))
                        send_params = {
                            "sessionKey": session_key,
                            "message": message,
                            "deliver": False,
                            "idempotencyKey": str(uuid.uuid4()),
                        }
                        if images:
                            send_params["attachments"] = [
                                {
                                    "type": "image",
                                    "mimeType": img.split(";")[0].split(":")[1] if ";" in img else "image/png",
                                    "content": img.split(",")[1] if "," in img else img,
                                }
                                for img in images
                            ]
                        await openclaw.send(make_req("chat.send", send_params))

                    elif action == "history":
                        await openclaw.send(make_req("chat.history", {
                            "sessionKey": session_key,
                            "limit": data.get("limit", 200),
                        }))

                    elif action == "abort":
                        params = {"sessionKey": session_key}
                        if data.get("runId"):
                            params["runId"] = data["runId"]
                        await openclaw.send(make_req("chat.abort", params))

                    elif action == "set_session":
                        session_key = data.get("sessionKey", DEFAULT_SESSION_KEY)
                        await ws.send_text(json.dumps({"type": "session_changed", "sessionKey": session_key}))
                        await openclaw.send(make_req("chat.history", {"sessionKey": session_key, "limit": 200}))

                    elif action == "ping":
                        await ws.send_text(json.dumps({"type": "pong"}))

                    else:
                        await openclaw.send(raw)

            except WebSocketDisconnect:
                logger.info("Client disconnected")
                shutdown.set()
            except Exception as e:
                logger.error("Client forward error: %s", e)
                shutdown.set()

        await asyncio.gather(forward_from_gateway(), forward_from_client())

    except Exception as e:
        logger.error("Chat WS error: %s", e)
        try:
            await ws.send_text(json.dumps({"type": "error", "message": f"OpenClaw connection failed: {str(e)}"}))
        except Exception:
            pass
    finally:
        shutdown.set()
        if openclaw:
            try:
                await openclaw.close()
            except Exception:
                pass


@router.get("/session-status")
async def session_status():
    """Return token usage for the active War Room session."""
    import pathlib
    # Mounted read-only from host at /openclaw-sessions
    sessions_path = pathlib.Path("/openclaw-sessions/sessions.json")
    if not sessions_path.exists():
        # Fallback for local dev
        sessions_path = pathlib.Path.home() / ".openclaw" / "agents" / "main" / "sessions" / "sessions.json"
    session_key = f"agent:main:{DEFAULT_SESSION_KEY}"
    try:
        data = json.loads(sessions_path.read_text())
        entry = data.get(session_key, {})
        total = entry.get("totalTokens", 0)
        context_window = entry.get("contextTokens", 200000)
        compaction_count = entry.get("compactionCount", 0)
        return {
            "totalTokens": total,
            "contextWindow": context_window,
            "compactionCount": compaction_count,
            "percentage": round((total / context_window * 100), 1) if context_window else 0,
        }
    except Exception as e:
        logger.warning("Failed to read session status: %s", e)
        return {"totalTokens": 0, "contextWindow": 200000, "compactionCount": 0, "percentage": 0}


@router.get("/sessions")
async def list_sessions():
    import httpx
    api_url = os.getenv("OPENCLAW_API_URL", "http://10.0.0.1:18789")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{api_url}/api/sessions")
            return resp.json()
    except Exception:
        return {"sessions": [], "note": "openclaw not reachable"}


async def _load_grounded_assignments(db, context: GroundingContext | None) -> list[dict[str, Any]]:
    if not context or not context.entity_type or not context.entity_id:
        return []

    assignment_map = await load_agent_assignment_map(
        db,
        entity_type=context.entity_type,
        entity_ids=[str(context.entity_id)],
    )
    return assignment_map.get(str(context.entity_id), [])


def _build_grounding_payload(context: GroundingContext | None, assignments: list[dict[str, Any]]) -> tuple[str, str | None]:
    if not context:
        return "", None

    summary_bits = [context.surface.replace("_", " ").title()]
    if context.title:
        summary_bits.append(context.title)

    grounding_lines = [f"Surface: {context.surface}"]
    if context.entity_type and context.entity_id:
        grounding_lines.append(f"Entity: {context.entity_type} #{context.entity_id}")
    if context.title:
        grounding_lines.append(f"Title: {context.title}")
    if context.summary:
        grounding_lines.append(f"Summary: {context.summary}")

    cleaned_facts = [fact for fact in context.facts if fact.label and fact.value not in (None, "")]
    if cleaned_facts:
        grounding_lines.append("Facts:")
        grounding_lines.extend([f"- {fact.label}: {fact.value}" for fact in cleaned_facts[:8]])

    if assignments:
        grounding_lines.append("Assigned agents:")
        grounding_lines.extend([
            f"- {assignment.get('agent_emoji') or '🤖'} {assignment.get('agent_name') or assignment.get('agent_id')} ({assignment.get('status', 'queued')})"
            for assignment in assignments[:6]
        ])

    grounding_summary = " • ".join(summary_bits)
    return "\n".join(grounding_lines), grounding_summary


@router.post("/message")
async def send_message(body: ChatMessageRequest, db=Depends(get_crm_db)):
    import httpx

    text = body.message.strip()
    if not text:
        raise HTTPException(status_code=400, detail="No message provided")

    assignments = await _load_grounded_assignments(db, body.context)
    grounding_block, grounding_summary = _build_grounding_payload(body.context, assignments)

    auth_token = os.getenv("OPENCLAW_AUTH_TOKEN", OPENCLAW_TOKEN)
    if not auth_token:
        return {
            "response": "AI chat is not configured right now. Add OpenClaw credentials to enable grounded replies.",
            "grounding_summary": grounding_summary,
        }

    system_prompt = (
        "You are the shared WAR ROOM AI assistant. Answer the user's question using the provided business context when it is relevant. "
        "Be specific about the current surface or record, mention assigned agents when helpful, and clearly say when the grounding context is insufficient."
    )
    user_content = text if not grounding_block else f"Grounding context:\n{grounding_block}\n\nUser request:\n{text}"

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{os.getenv('OPENCLAW_API_URL', OPENCLAW_API)}/v1/chat/completions",
                headers={"Authorization": f"Bearer {auth_token}"},
                json={
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content},
                    ],
                    "stream": False,
                    "temperature": 0.3,
                    "max_tokens": 1200,
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                choices = data.get("choices", [])
                if choices:
                    content = choices[0].get("message", {}).get("content", "").strip()
                    if content:
                        return {"response": content, "grounding_summary": grounding_summary}
            logger.warning("Grounded chat failed: %s", resp.status_code)
    except Exception as exc:
        logger.warning("Grounded chat exception: %s", exc)

    raise HTTPException(status_code=502, detail="Failed to get chat response")



@router.post("/polish")
async def polish_prompt(body: dict):
    """Use OpenClaw to clean up and organize a raw text prompt."""
    import httpx

    text = body.get("text", "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="No text provided")

    auth_token = os.getenv("OPENCLAW_AUTH_TOKEN", OPENCLAW_TOKEN)
    if not auth_token:
        return {"polished": text}

    system_prompt = (
        "You are a prompt engineer. Take the user's rough text and rewrite it as a clear, "
        "well-organized prompt. Keep the original intent. Fix grammar, structure it with clear "
        "sections if needed, and make it specific. Return ONLY the polished prompt — no explanation, "
        "no preamble, no quotes around it."
    )

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                f"{os.getenv('OPENCLAW_API_URL', OPENCLAW_API)}/v1/chat/completions",
                headers={"Authorization": f"Bearer {auth_token}"},
                json={
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": text},
                    ],
                    "stream": False,
                    "temperature": 0.3,
                    "max_tokens": 1000,
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                choices = data.get("choices", [])
                if choices:
                    polished = choices[0].get("message", {}).get("content", "").strip()
                    if polished:
                        return {"polished": polished}
                logger.warning("OpenClaw polish response missing choices")
            else:
                logger.warning("OpenClaw polish failed: %s", resp.status_code)
    except Exception as exc:
        logger.warning("Polish failed: %s", exc)

    return {"polished": text}


@router.post("/evaluate-prompt")
async def evaluate_prompt(body: dict):
    """Evaluate prompt clarity and return clarifying questions if vague.

    Inspired by claude-code-prompt-improver: intercepts vague prompts,
    asks grounded clarifying questions, then produces an improved version.

    Request: { text: string, context?: string[] }
    Response: { clear: bool, questions?: string[], improved?: string }
    """
    import httpx

    text = body.get("text", "").strip()
    context = body.get("context", [])  # Recent message summaries for grounding
    if not text:
        raise HTTPException(status_code=400, detail="No text provided")

    auth_token = os.getenv("OPENCLAW_AUTH_TOKEN", OPENCLAW_TOKEN)
    if not auth_token:
        return {"clear": True}

    # Phase 1: Evaluate clarity
    eval_system = (
        "You evaluate prompt clarity for an AI assistant. Given a user prompt and optional "
        "conversation context, determine if the prompt is clear enough to act on.\n\n"
        "A prompt is CLEAR if it has:\n"
        "- A specific action or question\n"
        "- Enough context to proceed without guessing\n"
        "- No critical ambiguity about scope, target, or intent\n\n"
        "A prompt is VAGUE if:\n"
        "- The action is ambiguous (\"fix it\", \"make it better\", \"update things\")\n"
        "- Critical details are missing (which file, which feature, what behavior)\n"
        "- Multiple interpretations are equally valid\n"
        "- Scope is unclear (one page vs entire app, one field vs whole form)\n\n"
        "Respond with EXACTLY this JSON format, nothing else:\n"
        '{"clear": true} or {"clear": false, "questions": ["question 1", "question 2", ...], "context_summary": "brief summary of what you understood"}\n\n'
        "Rules:\n"
        "- Max 6 questions, min 1\n"
        "- Questions must be specific and grounded in what the user said\n"
        "- Include multiple-choice options when possible (e.g., \"Which page? (a) Dashboard (b) Settings (c) Other\")\n"
        "- Don't ask obvious questions the context already answers\n"
        "- Short, direct questions — no fluff"
    )

    context_block = ""
    if context:
        context_block = "\n\nRecent conversation context:\n" + "\n".join(f"- {c}" for c in context[-10:])

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{os.getenv('OPENCLAW_API_URL', OPENCLAW_API)}/v1/chat/completions",
                headers={"Authorization": f"Bearer {auth_token}"},
                json={
                    "messages": [
                        {"role": "system", "content": eval_system},
                        {"role": "user", "content": f"Evaluate this prompt:{context_block}\n\nPrompt: \"{text}\""},
                    ],
                    "stream": False,
                    "temperature": 0.1,
                    "max_tokens": 500,
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                choices = data.get("choices", [])
                if choices:
                    raw = choices[0].get("message", {}).get("content", "").strip()
                    # Parse JSON from response (handle markdown code blocks)
                    json_str = raw
                    if "```" in raw:
                        json_str = raw.split("```")[1]
                        if json_str.startswith("json"):
                            json_str = json_str[4:]
                    try:
                        result = json.loads(json_str.strip())
                        return result
                    except json.JSONDecodeError:
                        logger.warning("Failed to parse evaluation JSON: %s", raw[:200])
                        return {"clear": True}
            else:
                logger.warning("Prompt evaluation failed: %s", resp.status_code)
    except Exception as exc:
        logger.warning("Evaluate prompt failed: %s", exc)

    return {"clear": True}


@router.post("/improve-prompt")
async def improve_prompt(body: dict):
    """Take the original prompt + answers to clarifying questions and produce an improved prompt.

    Request: { original: string, questions: string[], answers: string[] }
    Response: { improved: string }
    """
    import httpx

    original = body.get("original", "").strip()
    questions = body.get("questions", [])
    answers = body.get("answers", [])

    if not original:
        raise HTTPException(status_code=400, detail="No original prompt")

    auth_token = os.getenv("OPENCLAW_AUTH_TOKEN", OPENCLAW_TOKEN)
    if not auth_token:
        return {"improved": original}

    qa_block = ""
    for q, a in zip(questions, answers):
        qa_block += f"\nQ: {q}\nA: {a}"

    improve_system = (
        "You are a prompt engineer. Given the user's original prompt and their answers to "
        "clarifying questions, rewrite the prompt to be clear, specific, and actionable.\n\n"
        "Rules:\n"
        "- Keep the user's intent and voice\n"
        "- Incorporate all answers naturally\n"
        "- Add structure (sections, bullet points) if the prompt is complex\n"
        "- Be specific about scope, targets, and expected behavior\n"
        "- Return ONLY the improved prompt — no explanation, no preamble, no quotes"
    )

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                f"{os.getenv('OPENCLAW_API_URL', OPENCLAW_API)}/v1/chat/completions",
                headers={"Authorization": f"Bearer {auth_token}"},
                json={
                    "messages": [
                        {"role": "system", "content": improve_system},
                        {"role": "user", "content": f"Original prompt: \"{original}\"\n\nClarifying Q&A:{qa_block}\n\nRewrite the prompt:"},
                    ],
                    "stream": False,
                    "temperature": 0.3,
                    "max_tokens": 1500,
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                choices = data.get("choices", [])
                if choices:
                    improved = choices[0].get("message", {}).get("content", "").strip()
                    if improved:
                        return {"improved": improved}
            else:
                logger.warning("Improve prompt failed: %s", resp.status_code)
    except Exception as exc:
        logger.warning("Improve prompt failed: %s", exc)

    return {"improved": original}


# ── Scoped AI Chat (Ask AI panel) ────────────────────────────

class AskAIRequest(BaseModel):
    system: str = ""
    messages: list[dict] = Field(default_factory=list)
    context: dict = Field(default_factory=dict)


@router.post("/ask-ai")
async def ask_ai(body: AskAIRequest):
    """Scoped AI chat for the Command Center help panel."""
    import httpx

    api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="No AI API key configured")

    is_anthropic = bool(os.getenv("ANTHROPIC_API_KEY"))

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            if is_anthropic:
                msgs = [{"role": m.get("role", "user"), "content": m.get("content", "")} for m in body.messages]
                resp = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": os.getenv("ANTHROPIC_API_KEY", ""),
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": "claude-haiku-3-5-20241022",
                        "max_tokens": 1024,
                        "system": body.system,
                        "messages": msgs,
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    text = " ".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
                    return {"response": text.strip() or "No response generated."}
                logger.warning("Ask AI Anthropic: %s", resp.status_code)
                return {"response": f"AI returned {resp.status_code}. Try again."}
            else:
                msgs = [{"role": "system", "content": body.system}]
                msgs.extend({"role": m.get("role", "user"), "content": m.get("content", "")} for m in body.messages)
                resp = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={"model": "gpt-4o-mini", "max_tokens": 1024, "messages": msgs},
                )
                if resp.status_code == 200:
                    choices = resp.json().get("choices", [])
                    if choices:
                        return {"response": choices[0].get("message", {}).get("content", "").strip()}
                return {"response": f"AI returned {resp.status_code}. Try again."}
    except Exception as exc:
        logger.warning("Ask AI failed: %s", exc)
        return {"response": "AI service temporarily unavailable."}
