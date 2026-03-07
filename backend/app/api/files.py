"""Files — write temp files and return their path."""

import os
import re
import logging
from fastapi import APIRouter, HTTPException

logger = logging.getLogger("files")
router = APIRouter()

# Fixed safe directory for artifacts
ARTIFACTS_DIR = os.getenv("WARROOM_ARTIFACTS_DIR", "/tmp/warroom-artifacts")

# Max content size: 10 MB
MAX_CONTENT_SIZE = 10 * 1024 * 1024


@router.post("/open")
async def open_file(body: dict):
    """Write content to a temp file and return its path."""
    content = body.get("content", "")
    filename = body.get("filename", "artifact.txt")

    # ── Input validation ──
    # Enforce content size limit
    if len(content) > MAX_CONTENT_SIZE:
        raise HTTPException(status_code=413, detail=f"Content too large (max {MAX_CONTENT_SIZE // (1024*1024)}MB)")

    # Sanitize filename: strip path components, reject traversal attempts
    filename = os.path.basename(filename)
    if not filename or filename.startswith(".") or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    # Only allow safe characters in filename
    if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9._\-]{0,254}$', filename):
        raise HTTPException(status_code=400, detail="Filename contains invalid characters")

    # ── Write file ──
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    filepath = os.path.join(ARTIFACTS_DIR, filename)

    # Verify resolved path is still within ARTIFACTS_DIR
    real_path = os.path.realpath(filepath)
    if not real_path.startswith(os.path.realpath(ARTIFACTS_DIR)):
        raise HTTPException(status_code=400, detail="Invalid filename")

    with open(filepath, "w") as f:
        f.write(content)

    return {"ok": True, "path": filepath}
