"""Proxy to Team Dashboard on Brain 2"""
from fastapi import APIRouter, Request, Response
import httpx
import os

router = APIRouter()
BASE = os.getenv("TEAM_DASHBOARD_URL", "http://10.0.0.11:18795")

@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_team(path: str, request: Request):
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.request(
            method=request.method,
            url=f"{BASE}/{path}",
            params=request.query_params,
            content=await request.body(),
            headers={"content-type": request.headers.get("content-type", "application/json")},
        )
        return Response(content=resp.content, status_code=resp.status_code, media_type=resp.headers.get("content-type"))
