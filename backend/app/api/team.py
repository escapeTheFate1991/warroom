"""Proxy to Team Dashboard on Brain 2"""

import os

import httpx
from fastapi import APIRouter, Request, Response

router = APIRouter()
BASE = os.getenv("TEAM_DASHBOARD_URL", "http://10.0.0.11:18795")

@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_team(path: str, request: Request):
    headers = {
        "content-type": request.headers.get("content-type", "application/json"),
    }
    authorization = request.headers.get("authorization")
    if authorization:
        headers["authorization"] = authorization

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.request(
            method=request.method,
            url=f"{BASE}/{path}",
            params=request.query_params,
            content=await request.body(),
            headers=headers,
        )
        return Response(content=resp.content, status_code=resp.status_code, media_type=resp.headers.get("content-type"))
