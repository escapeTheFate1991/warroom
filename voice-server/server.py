"""Chatterbox Voice Server — self-hosted TTS with zero-shot voice cloning.

Endpoints:
  POST /tts          — Generate speech from text (returns WAV)
  POST /tts/stream   — Generate speech from text (streaming response)
  GET  /voices       — List available voice reference clips
  POST /voices       — Upload a new voice reference clip
  GET  /health       — Health check + model status
"""

import asyncio
import io
import logging
import os
import time
from pathlib import Path
from typing import Optional

import torch
import torchaudio as ta
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("voice-server")

app = FastAPI(title="Chatterbox Voice Server", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Config ───────────────────────────────────────────────

VOICES_DIR = Path(os.environ.get("VOICES_DIR", "/app/voices"))
VOICES_DIR.mkdir(parents=True, exist_ok=True)

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
MODEL = None
MODEL_LOCK = asyncio.Lock()


# ── Model loading ────────────────────────────────────────

def _load_model():
    """Load Chatterbox Turbo model. Called once on first request."""
    global MODEL
    if MODEL is not None:
        return MODEL

    logger.info("Loading Chatterbox Turbo on %s...", DEVICE)
    start = time.time()

    from chatterbox.tts_turbo import ChatterboxTurboTTS
    MODEL = ChatterboxTurboTTS.from_pretrained(device=DEVICE)

    elapsed = time.time() - start
    logger.info("Model loaded in %.1fs on %s", elapsed, DEVICE)

    if DEVICE == "cuda":
        mem = torch.cuda.memory_allocated() / 1024**2
        logger.info("GPU memory used: %.0f MB", mem)

    return MODEL


async def get_model():
    """Thread-safe model access with lazy loading."""
    async with MODEL_LOCK:
        return await asyncio.get_event_loop().run_in_executor(None, _load_model)


# ── Schemas ──────────────────────────────────────────────

class TTSRequest(BaseModel):
    text: str
    voice: Optional[str] = None  # Voice reference clip filename
    exaggeration: float = 0.5
    cfg_weight: float = 0.5


class VoiceInfo(BaseModel):
    name: str
    filename: str
    size_kb: int


# ── TTS Endpoint ─────────────────────────────────────────

@app.post("/tts")
async def generate_speech(req: TTSRequest):
    """Generate speech audio from text.
    
    Returns WAV audio. Optionally specify a voice reference clip for cloning.
    Supports paralinguistic tags: [laugh], [cough], [chuckle], etc.
    """
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    model = await get_model()

    # Find voice reference clip
    audio_prompt_path = None
    if req.voice:
        voice_path = VOICES_DIR / req.voice
        if not voice_path.exists():
            # Try with common extensions
            for ext in [".wav", ".mp3", ".flac"]:
                candidate = VOICES_DIR / f"{req.voice}{ext}"
                if candidate.exists():
                    voice_path = candidate
                    break
            else:
                raise HTTPException(status_code=404, detail=f"Voice '{req.voice}' not found")
        audio_prompt_path = str(voice_path)

    # Generate speech
    start = time.time()
    try:
        kwargs = {"text": req.text}
        if audio_prompt_path:
            kwargs["audio_prompt_path"] = audio_prompt_path

        wav = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: model.generate(**kwargs),
        )
    except Exception as exc:
        logger.error("TTS generation failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(exc)}")

    elapsed = time.time() - start
    duration = wav.shape[-1] / model.sr
    rtf = elapsed / duration if duration > 0 else 0
    logger.info(
        "Generated %.1fs audio in %.2fs (RTF: %.2f) | voice=%s | text=%s",
        duration, elapsed, rtf, req.voice or "default", req.text[:60],
    )

    # Encode to WAV
    buf = io.BytesIO()
    ta.save(buf, wav, model.sr, format="wav")
    buf.seek(0)

    return Response(
        content=buf.read(),
        media_type="audio/wav",
        headers={
            "X-Audio-Duration": f"{duration:.2f}",
            "X-Generation-Time": f"{elapsed:.3f}",
            "X-RTF": f"{rtf:.3f}",
        },
    )


# ── Voice Management ─────────────────────────────────────

@app.get("/voices", response_model=list[VoiceInfo])
async def list_voices():
    """List available voice reference clips."""
    voices = []
    for f in sorted(VOICES_DIR.iterdir()):
        if f.suffix.lower() in {".wav", ".mp3", ".flac", ".ogg"}:
            voices.append(VoiceInfo(
                name=f.stem,
                filename=f.name,
                size_kb=f.stat().st_size // 1024,
            ))
    return voices


@app.post("/voices")
async def upload_voice(
    file: UploadFile = File(...),
    name: str = Form(None),
):
    """Upload a voice reference clip (10+ seconds recommended).
    
    Supported formats: WAV, MP3, FLAC, OGG.
    For best results, use a clean recording with minimal background noise.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    ext = Path(file.filename).suffix.lower()
    if ext not in {".wav", ".mp3", ".flac", ".ogg"}:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {ext}")

    voice_name = name or Path(file.filename).stem
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in voice_name)
    dest = VOICES_DIR / f"{safe_name}{ext}"

    content = await file.read()
    dest.write_bytes(content)

    logger.info("Voice uploaded: %s (%d KB)", dest.name, len(content) // 1024)
    return {"name": safe_name, "filename": dest.name, "size_kb": len(content) // 1024}


# ── Health ───────────────────────────────────────────────

@app.get("/health")
async def health():
    """Health check with model and GPU status."""
    gpu_info = None
    if torch.cuda.is_available():
        gpu_info = {
            "device": torch.cuda.get_device_name(0),
            "memory_total_mb": torch.cuda.get_device_properties(0).total_mem // (1024 * 1024),
            "memory_allocated_mb": round(torch.cuda.memory_allocated() / (1024 * 1024)),
            "memory_reserved_mb": round(torch.cuda.memory_reserved() / (1024 * 1024)),
        }

    return {
        "status": "ok",
        "model_loaded": MODEL is not None,
        "device": DEVICE,
        "gpu": gpu_info,
        "voices_count": len(list(VOICES_DIR.glob("*.*"))),
    }
