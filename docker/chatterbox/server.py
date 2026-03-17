"""Chatterbox TTS Docker Service - Voice cloning and text-to-speech API."""

import os
import uuid
import logging
import tempfile
import shutil
import io
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse, StreamingResponse
import uvicorn

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Chatterbox TTS Service", version="2.0.0")

VOICES_DIR = Path("/app/voices")
CACHE_DIR = Path("/app/cache")
TEMP_DIR = Path("/tmp/chatterbox")

for d in [VOICES_DIR, CACHE_DIR, TEMP_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Global model (lazy loaded)
_model = None
_device = "cpu"


def get_model():
    global _model
    if _model is None:
        try:
            import torch
            from chatterbox import ChatterboxTTS
            device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"Loading ChatterboxTTS on {device}...")
            _model = ChatterboxTTS.from_pretrained(device)
            logger.info("ChatterboxTTS loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load ChatterboxTTS: {e}")
            raise HTTPException(status_code=503, detail=f"Model not ready: {e}")
    return _model


@app.get("/health")
async def health():
    try:
        import torch
        has_cuda = torch.cuda.is_available()
    except:
        has_cuda = False
    model_loaded = _model is not None
    return {
        "status": "ok" if model_loaded else "model_not_loaded",
        "model": "chatterbox-tts",
        "device": "cuda" if has_cuda else "cpu",
        "loaded": model_loaded,
        "service": "chatterbox-tts"
    }


@app.post("/tts/generate")
async def generate_speech(
    text: str = Form(...),
    voice_reference: UploadFile = File(None),
    speaker_id: str = Form(None),
    exaggeration: float = Form(0.5),
    pace: float = Form(1.0),
    cfg_weight: float = Form(0.5),
):
    """Generate speech from text, optionally cloning a reference voice."""
    if not text or len(text.strip()) == 0:
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    if len(text) > 2000:
        raise HTTPException(status_code=400, detail="Text too long (max 2000 chars)")

    model = get_model()

    # Handle voice reference
    audio_prompt_path = None
    tmp_ref = None
    try:
        if voice_reference:
            tmp_ref = TEMP_DIR / f"ref_{uuid.uuid4().hex[:8]}.wav"
            with open(tmp_ref, "wb") as f:
                f.write(await voice_reference.read())
            audio_prompt_path = str(tmp_ref)
        elif speaker_id:
            saved = VOICES_DIR / f"{speaker_id}.wav"
            if saved.exists():
                audio_prompt_path = str(saved)
            else:
                raise HTTPException(status_code=404, detail=f"Voice {speaker_id} not found")

        # Generate
        import torchaudio
        wav = model.generate(
            text=text,
            audio_prompt_path=audio_prompt_path,
            exaggeration=exaggeration,
            cfg_weight=cfg_weight,
        )

        # Save to temp WAV
        output_path = TEMP_DIR / f"out_{uuid.uuid4().hex[:8]}.wav"
        torchaudio.save(str(output_path), wav.cpu(), model.sr)

        from starlette.background import BackgroundTask
        return FileResponse(
            path=str(output_path),
            media_type="audio/wav",
            filename="tts_output.wav",
            background=BackgroundTask(lambda: output_path.unlink(missing_ok=True)),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"TTS generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if tmp_ref and tmp_ref.exists():
            tmp_ref.unlink(missing_ok=True)


@app.post("/tts/clone-voice")
async def clone_voice(
    name: str = Form(...),
    audio_reference: UploadFile = File(...),
):
    """Save a voice reference for reuse."""
    speaker_id = f"voice_{uuid.uuid4().hex[:12]}"
    voice_path = VOICES_DIR / f"{speaker_id}.wav"
    content = await audio_reference.read()
    with open(voice_path, "wb") as f:
        f.write(content)

    import json
    meta = {"speaker_id": speaker_id, "name": name, "file_size": len(content)}
    with open(VOICES_DIR / f"{speaker_id}_meta.json", "w") as f:
        json.dump(meta, f)

    return {"speaker_id": speaker_id, "name": name, "status": "saved"}


@app.get("/tts/voices")
async def list_voices():
    import json
    voices = []
    for mf in VOICES_DIR.glob("*_meta.json"):
        try:
            with open(mf) as f:
                voices.append(json.load(f))
        except:
            pass
    return {"voices": voices, "count": len(voices)}


@app.delete("/tts/voices/{speaker_id}")
async def delete_voice(speaker_id: str):
    vp = VOICES_DIR / f"{speaker_id}.wav"
    mp = VOICES_DIR / f"{speaker_id}_meta.json"
    if not vp.exists():
        raise HTTPException(status_code=404, detail="Voice not found")
    vp.unlink(missing_ok=True)
    mp.unlink(missing_ok=True)
    return {"speaker_id": speaker_id, "status": "deleted"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8400)
