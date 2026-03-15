from fastapi import APIRouter
import httpx
import os

router = APIRouter()

SERVICES = {
    "kanban": os.getenv("KANBAN_API_URL", "http://10.0.0.11:18794"),
    "team": os.getenv("TEAM_DASHBOARD_URL", "http://10.0.0.11:18795"),
    "qdrant": os.getenv("QDRANT_URL", "http://10.0.0.11:6333"),
    "warroom_qdrant": "http://localhost:6334",  # War Room's dedicated Qdrant
    "fastembed": os.getenv("FASTEMBED_URL", "http://10.0.0.11:11435"),
}

@router.get("/health")
async def health_check():
    results = {}
    async with httpx.AsyncClient(timeout=5.0) as client:
        for name, url in SERVICES.items():
            try:
                if name == "fastembed":
                    endpoint = f"{url}/health"
                elif name in ["qdrant", "warroom_qdrant"]:
                    endpoint = f"{url}/collections"
                elif name == "kanban":
                    endpoint = f"{url}/tasks"
                else:  # team
                    endpoint = f"{url}/events"
                    
                resp = await client.get(endpoint)
                results[name] = "ok" if resp.status_code == 200 else f"error:{resp.status_code}"
            except Exception as e:
                results[name] = f"down:{type(e).__name__}"
    return {"status": "ok", "services": results}
