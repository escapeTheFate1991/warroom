"""Mental Library — Qdrant knowledge search + store"""
from fastapi import APIRouter
from pydantic import BaseModel
from qdrant_client import QdrantClient
import httpx
import os

router = APIRouter()

QDRANT_URL = os.getenv("QDRANT_URL", "http://10.0.0.11:6333")
FASTEMBED_URL = os.getenv("FASTEMBED_URL", "http://10.0.0.11:11435")
COLLECTIONS = [
    "friday-memory", "friday-marketing", "friday-knowledge",
    "friday-coding", "friday-projects", "friday-trading", "friday-general",
]


class SearchRequest(BaseModel):
    query: str
    collection: str = "friday-knowledge"
    limit: int = 10


class StoreRequest(BaseModel):
    text: str
    collection: str = "friday-knowledge"
    metadata: dict = {}


async def embed(text: str) -> list[float]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{FASTEMBED_URL}/api/embed",
            json={"model": "nomic-ai/nomic-embed-text-v1.5", "input": text},
        )
        resp.raise_for_status()
        return resp.json()["embeddings"][0]


@router.get("/collections")
async def list_collections():
    client = QdrantClient(url=QDRANT_URL)
    collections = client.get_collections().collections
    results = []
    for c in collections:
        info = client.get_collection(c.name)
        results.append({"name": c.name, "points": info.points_count, "vectors": info.vectors_count})
    return {"collections": results}


@router.post("/search")
async def search(req: SearchRequest):
    vector = await embed(req.query)
    client = QdrantClient(url=QDRANT_URL)
    results = client.query_points(
        collection_name=req.collection,
        query=vector,
        limit=req.limit,
        with_payload=True,
    )
    return {
        "results": [
            {"id": str(r.id), "score": r.score, "payload": r.payload}
            for r in results.points
        ]
    }


@router.post("/store")
async def store(req: StoreRequest):
    vector = await embed(req.text)
    client = QdrantClient(url=QDRANT_URL)
    import uuid
    point_id = str(uuid.uuid4())
    client.upsert(
        collection_name=req.collection,
        points=[{
            "id": point_id,
            "vector": vector,
            "payload": {"text": req.text, **req.metadata},
        }],
    )
    return {"id": point_id, "collection": req.collection}
