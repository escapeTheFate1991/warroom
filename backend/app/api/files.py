"""Files — write temp files and open them on the local machine."""

import os
import tempfile
import subprocess
import logging
from fastapi import APIRouter

logger = logging.getLogger("files")
router = APIRouter()


@router.post("/open")
async def open_file(body: dict):
    """Write content to a temp file and open it with the default editor."""
    content = body.get("content", "")
    filename = body.get("filename", "artifact.txt")

    # Write to /tmp with the correct filename
    tmp_dir = os.path.join(tempfile.gettempdir(), "warroom-artifacts")
    os.makedirs(tmp_dir, exist_ok=True)
    filepath = os.path.join(tmp_dir, filename)

    with open(filepath, "w") as f:
        f.write(content)

    # Open with xdg-open (Linux) — non-blocking
    try:
        subprocess.Popen(
            ["xdg-open", filepath],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env={**os.environ, "DISPLAY": ":1"},
        )
    except Exception as e:
        logger.warning(f"Failed to open file: {e}")
        return {"ok": False, "error": str(e), "path": filepath}

    return {"ok": True, "path": filepath}
