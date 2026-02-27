"""Chat — WebSocket relay to OpenClaw gateway"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import websockets
import asyncio
import json
import os

router = APIRouter()

OPENCLAW_WS = os.getenv("OPENCLAW_WS_URL", "ws://10.0.0.1:18789")


@router.websocket("/ws")
async def chat_ws(ws: WebSocket):
    """Relay WebSocket messages between WAR ROOM UI and OpenClaw gateway."""
    await ws.accept()

    try:
        async with websockets.connect(OPENCLAW_WS) as openclaw:
            async def forward_to_openclaw():
                try:
                    while True:
                        data = await ws.receive_text()
                        await openclaw.send(data)
                except WebSocketDisconnect:
                    pass

            async def forward_to_client():
                try:
                    async for message in openclaw:
                        await ws.send_text(message if isinstance(message, str) else message.decode())
                except Exception:
                    pass

            await asyncio.gather(forward_to_openclaw(), forward_to_client())
    except Exception as e:
        try:
            await ws.send_text(json.dumps({"error": f"OpenClaw connection failed: {str(e)}"}))
        except Exception:
            pass


@router.get("/sessions")
async def list_sessions():
    """Get active OpenClaw sessions via HTTP."""
    import httpx
    api_url = os.getenv("OPENCLAW_API_URL", "http://10.0.0.1:18789")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{api_url}/api/sessions")
            return resp.json()
    except Exception:
        return {"sessions": [], "note": "openclaw not reachable"}
