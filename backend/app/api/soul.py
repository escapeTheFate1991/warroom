"""Soul Editor — read/write/backup SOUL.md, IDENTITY.md, USER.md, AGENTS.md, MEMORY.md."""
import json
import shutil
import logging
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()

WORKSPACE = Path("/openclaw-workspace")
HISTORY_DIR = WORKSPACE / ".soul-history"
SOUL_FILES = ["SOUL.md", "IDENTITY.md", "USER.md", "AGENTS.md", "MEMORY.md"]


@router.get("/soul")
async def get_soul():
    result = {}
    for f in SOUL_FILES:
        fp = WORKSPACE / f
        result[f] = fp.read_text(errors="replace") if fp.exists() else ""
    return result


class PutSoulRequest(BaseModel):
    filename: str
    content: str

@router.put("/soul")
async def put_soul(req: PutSoulRequest):
    if req.filename not in SOUL_FILES:
        raise HTTPException(status_code=400, detail=f"Invalid file. Allowed: {SOUL_FILES}")
    fp = WORKSPACE / req.filename
    # Backup before overwrite
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    if fp.exists():
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = HISTORY_DIR / f"{req.filename}.{ts}"
        shutil.copy2(fp, backup)
    fp.write_text(req.content)
    return {"ok": True, "filename": req.filename}


@router.get("/soul/history/{filename}")
async def get_soul_history(filename: str):
    if filename not in SOUL_FILES:
        raise HTTPException(status_code=400, detail="Invalid file")
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    versions = []
    for f in sorted(HISTORY_DIR.glob(f"{filename}.*"), reverse=True):
        ts_str = f.suffix.lstrip(".")
        versions.append({"path": f.name, "timestamp": ts_str, "size": f.stat().st_size})
    return versions[:20]


@router.post("/soul/revert/{filename}")
async def revert_soul(filename: str, body: dict):
    version = body.get("version")
    if not version:
        raise HTTPException(status_code=400, detail="version required")
    backup = HISTORY_DIR / version
    if not backup.exists():
        raise HTTPException(status_code=404, detail="Version not found")
    target = WORKSPACE / filename
    # Backup current before revert
    if target.exists():
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy2(target, HISTORY_DIR / f"{filename}.{ts}")
    shutil.copy2(backup, target)
    return {"ok": True, "reverted_to": version}