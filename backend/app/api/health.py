from fastapi import APIRouter
import httpx
import os

router = APIRouter()

SERVICES = {
    "kanban": os.getenv("KANBAN_API_URL", "http://10.0.0.11:18794"),
    "team": os.getenv("TEAM_DASHBOARD_URL", "http://10.0.0.11:18795"),
    "qdrant": os.getenv("QDRANT_URL", "http://10.0.0.11:6333"),
    "fastembed": os.getenv("FASTEMBED_URL", "http://10.0.0.11:11435"),
}

@router.get("/health")
async def health_check():
    results = {}
    async with httpx.AsyncClient(timeout=5.0) as client:
        for name, url in SERVICES.items():
            try:
                resp = await client.get(f"{url}/health" if name == "fastembed" else url + ("/collections" if name == "qdrant" else "/tasks" if name == "kanban" else "/events"))
                results[name] = "ok" if resp.status_code == 200 else f"error:{resp.status_code}"
            except Exception as e:
                results[name] = f"down:{type(e).__name__}"
    return {"status": "ok", "services": results}
