"""Voice API endpoints for War Room - Unified voice system."""

import subprocess
import tempfile
import os
import json
import httpx
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
    """Forward to OpenClaw voice server for transcription."""
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file.flush()
            
            # Forward to OpenClaw voice server
            async with httpx.AsyncClient() as client:
                with open(tmp_file.name, 'rb') as audio_file:
                    files = {"audio": ("recording.webm", audio_file, "audio/webm")}
                    response = await client.post(
                        "http://localhost:18793/transcribe",
                        files=files,
                        timeout=30.0
                    )
                    
            # Clean up temp file
            os.unlink(tmp_file.name)
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"text": "", "error": f"Transcription failed: {response.status_code}"}
                
    except Exception as e:
        return {"text": "", "error": f"Transcription error: {str(e)}"}





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