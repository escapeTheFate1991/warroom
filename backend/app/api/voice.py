"""Voice API endpoints for War Room - Unified voice system."""

import subprocess
import tempfile
import os
import json
from fastapi import APIRouter, HTTPException, UploadFile, File, Request, Response, Depends
from fastapi.responses import StreamingResponse
from pathlib import Path
from app.api.auth import get_current_user
from app.models.crm.user import User

router = APIRouter()

@router.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user)
):
    """Transcription service is unavailable — Whisper requires GPU."""
    return {"text": "", "error": "Transcription service unavailable — GPU required"}


@router.post("/tts")
async def text_to_speech(
    request: Request,
    user: User = Depends(get_current_user)
):
    """Convert text to speech using edge-tts (same as OpenClaw config)."""
    try:
        data = await request.json()
        text = data.get("text", "")
        voice = data.get("voice", "en-US-AvaNeural")  # Same as OpenClaw config
        
        if not text:
            raise HTTPException(status_code=400, detail="No text provided")
        
        # Use edge-tts to generate audio
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
            mp3_path = tmp_file.name
        
        try:
            result = subprocess.run([
                "edge-tts", 
                "--text", text,
                "--voice", voice,
                "--write-media", mp3_path
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0 and os.path.exists(mp3_path):
                # Return audio file
                def iter_file():
                    with open(mp3_path, 'rb') as audio_file:
                        while True:
                            chunk = audio_file.read(8192)
                            if not chunk:
                                break
                            yield chunk
                    os.unlink(mp3_path)  # Clean up after streaming
                
                return StreamingResponse(
                    iter_file(), 
                    media_type="audio/mpeg",
                    headers={"Content-Disposition": "attachment; filename=speech.mp3"}
                )
            else:
                raise HTTPException(status_code=500, detail=f"TTS error: {result.stderr}")
                
        except Exception as e:
            if os.path.exists(mp3_path):
                os.unlink(mp3_path)
            raise e
                
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=500, detail="TTS timeout")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS error: {str(e)}")