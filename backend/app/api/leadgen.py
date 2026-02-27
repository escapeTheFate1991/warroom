"""Lead Gen — proxies to the running leadgen-app service."""
from fastapi import APIRouter, Request, Response
import httpx
import os

router = APIRouter()

LEADGEN_BACKEND = os.getenv("LEADGEN_BACKEND_URL", "http://10.0.0.1:8200")


@router.get("/leads")
async def list_leads(request: Request):
    """Proxy to GET /api/leads/ — supports all filter/sort query params."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{LEADGEN_BACKEND}/api/leads/",
                params=request.query_params,
            )
            return Response(content=resp.content, status_code=resp.status_code, media_type="application/json")
    except httpx.ConnectError:
        return Response(content="[]", status_code=200, media_type="application/json")


@router.get("/leads/stats")
async def leads_stats(request: Request):
    """Proxy to GET /api/leads/stats."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{LEADGEN_BACKEND}/api/leads/stats",
                params=request.query_params,
            )
            return Response(content=resp.content, status_code=resp.status_code, media_type="application/json")
    except httpx.ConnectError:
        return Response(content="{}", status_code=200, media_type="application/json")


@router.post("/search")
async def start_search(request: Request):
    """Proxy to POST /api/search/ — starts a Google Places search job."""
    body = await request.body()
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{LEADGEN_BACKEND}/api/search/",
                content=body,
                headers={"Content-Type": "application/json"},
            )
            return Response(content=resp.content, status_code=resp.status_code, media_type="application/json")
    except httpx.ConnectError:
        return Response(content='{"error":"leadgen service not reachable"}', status_code=503, media_type="application/json")


@router.get("/search")
async def list_searches(request: Request):
    """Proxy to GET /api/search/ — list all search jobs."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{LEADGEN_BACKEND}/api/search/",
                params=request.query_params,
            )
            return Response(content=resp.content, status_code=resp.status_code, media_type="application/json")
    except httpx.ConnectError:
        return Response(content="[]", status_code=200, media_type="application/json")


@router.get("/search/{job_id}")
async def get_search_job(job_id: int):
    """Proxy to GET /api/search/{job_id} — poll a search job's status."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{LEADGEN_BACKEND}/api/search/{job_id}")
            return Response(content=resp.content, status_code=resp.status_code, media_type="application/json")
    except httpx.ConnectError:
        return Response(content='{"error":"leadgen service not reachable"}', status_code=503, media_type="application/json")
