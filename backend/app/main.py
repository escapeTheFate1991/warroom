"""WAR ROOM — Unified API Gateway"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import kanban, team, library, leadgen, chat, health, mental_library, voice
from app.db.leadgen_db import leadgen_engine
from app.models.lead import Base

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database tables on startup."""
    try:
        # Create leadgen tables if they don't exist
        async with leadgen_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("LeadGen database initialized")
    except Exception as e:
        logger.error("Failed to initialize LeadGen database: %s", e)
    
    yield


app = FastAPI(title="WAR ROOM", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["health"])
app.include_router(kanban.router, prefix="/api/kanban", tags=["kanban"])
app.include_router(team.router, prefix="/api/team", tags=["team"])
app.include_router(library.router, prefix="/api/library", tags=["library"])
app.include_router(leadgen.router, prefix="/api/leadgen", tags=["leadgen"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(mental_library.router, prefix="/api/ml", tags=["mental-library"])
app.include_router(voice.router, prefix="/api/voice", tags=["voice"])
