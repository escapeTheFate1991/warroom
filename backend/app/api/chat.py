"""Chat — WebSocket relay to OpenClaw gateway.

Implements the OpenClaw Gateway WS protocol v3 with device identity auth
for full operator scopes (chat.send, chat.history, chat.abort).
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
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

logger = logging.getLogger("chat")

router = APIRouter()

OPENCLAW_WS = os.getenv("OPENCLAW_WS_URL", "ws://10.0.0.1:18789")
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
    logger.info(f"Got challenge, nonce={nonce[:16]}...")

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
    logger.info(f"Connected to gateway, scopes={granted}")
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
                        data = json.loads(message) if isinstance(message, str) else json.loads(message.decode())
                        msg_type = data.get("type", "")
                        method = data.get("method", "")
                        logger.debug(f"GW→Client: type={msg_type} method={method}")
                        await ws.send_text(json.dumps(data))
                except websockets.exceptions.ConnectionClosed as e:
                    logger.warning(f"Gateway WS closed: code={e.code} reason={e.reason}")
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
                            logger.warning(f"Reconnect attempt {attempt+1} failed: {re_err}")
                    else:
                        await ws.send_text(json.dumps({"type": "error", "message": "Gateway reconnect failed after 5 attempts"}))
                        shutdown.set()
                        break
                except Exception as e:
                    logger.error(f"Gateway forward error: {e}")
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
                        if not message:
                            continue
                        logger.info(f"Client→GW: chat.send ({len(message)} chars)")
                        await openclaw.send(make_req("chat.send", {
                            "sessionKey": session_key,
                            "message": message,
                            "deliver": False,
                            "idempotencyKey": str(uuid.uuid4()),
                        }))

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
                logger.error(f"Client forward error: {e}")
                shutdown.set()

        await asyncio.gather(forward_from_gateway(), forward_from_client())

    except Exception as e:
        logger.error(f"Chat WS error: {e}")
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
