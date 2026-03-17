"""Chatterbox TTS Docker Service - Voice cloning and text-to-speech API.

FastAPI server that provides TTS endpoints with voice cloning capabilities
using the chatterbox-tts library.
"""

import os
import uuid
import logging
import tempfile
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Chatterbox TTS Service", version="1.0.0")

# Directories
VOICES_DIR = Path("/app/voices")
CACHE_DIR = Path("/app/cache")
TEMP_DIR = Path("/tmp/chatterbox")

# Ensure directories exist
for dir_path in [VOICES_DIR, CACHE_DIR, TEMP_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# Global TTS model (lazy loaded)
tts_model = None


def get_tts_model():
    """Lazy load the TTS model."""
    global tts_model
    if tts_model is None:
        try:
            # Try to import chatterbox-tts
            from chatterbox_tts import ChatterboxTTS
            tts_model = ChatterboxTTS(model_name="chatterbox-turbo")
            logger.info("Chatterbox TTS model loaded successfully")
        except ImportError:
            logger.error("chatterbox-tts not available - using mock implementation")
            tts_model = MockTTS()
        except Exception as e:
            logger.error(f"Failed to load TTS model: {e}")
            tts_model = MockTTS()
    return tts_model


class MockTTS:
    """Mock TTS implementation for development/testing."""
    
    def __init__(self):
        self.name = "mock-tts"
    
    def generate_speech(self, text: str, voice_reference: str = None, 
                       speaker_id: str = None, **kwargs) -> bytes:
        """Generate mock audio (silence)."""
        # Create 3 seconds of silence as placeholder
        import subprocess
        import tempfile
        
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
            # Generate silence using ffmpeg
            subprocess.run([
                "ffmpeg", "-y", "-f", "lavfi", 
                "-i", "anullsrc=r=22050:cl=mono", 
                "-t", "3", "-c:a", "pcm_s16le", 
                tmp_file.name
            ], capture_output=True)
            
            with open(tmp_file.name, "rb") as f:
                audio_data = f.read()
            
            os.unlink(tmp_file.name)
            return audio_data


@app.get("/health")
async def health():
    """Health check endpoint."""
    model = get_tts_model()
    return {
        "status": "ok",
        "model": getattr(model, 'name', 'unknown'),
        "service": "chatterbox-tts"
    }


@app.post("/tts/generate")
async def generate_speech(
    text: str = Form(...),
    voice_reference: UploadFile = File(None),
    speaker_id: str = Form(None),
    exaggeration: float = Form(0.5),
    pace: float = Form(1.0),
):
    """Generate speech from text, optionally cloning a reference voice.
    
    Args:
        text: Text to convert to speech
        voice_reference: Audio file for zero-shot voice cloning
        speaker_id: ID of previously saved voice
        exaggeration: Voice exaggeration level (0.0-1.0)
        pace: Speech pace (0.5-2.0)
    
    Returns:
        WAV audio file
    """
    if not text or len(text.strip()) == 0:
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    
    if len(text) > 2000:
        raise HTTPException(status_code=400, detail="Text too long (max 2000 characters)")
    
    try:
        model = get_tts_model()
        
        # Handle voice reference
        voice_ref_path = None
        if voice_reference:
            # Save uploaded voice reference
            voice_ref_path = TEMP_DIR / f"ref_{uuid.uuid4().hex[:8]}.wav"
            with open(voice_ref_path, "wb") as f:
                content = await voice_reference.read()
                f.write(content)
        elif speaker_id:
            # Use saved voice
            saved_voice_path = VOICES_DIR / f"{speaker_id}.wav"
            if saved_voice_path.exists():
                voice_ref_path = saved_voice_path
            else:
                raise HTTPException(status_code=404, detail=f"Voice ID {speaker_id} not found")
        
        # Generate speech
        audio_data = model.generate_speech(
            text=text,
            voice_reference=str(voice_ref_path) if voice_ref_path else None,
            speaker_id=speaker_id,
            exaggeration=exaggeration,
            pace=pace
        )
        
        # Save to temporary file for response
        output_path = TEMP_DIR / f"output_{uuid.uuid4().hex[:8]}.wav"
        
        if isinstance(audio_data, bytes):
            with open(output_path, "wb") as f:
                f.write(audio_data)
        else:
            # If model returns file path instead of bytes
            shutil.copy2(audio_data, output_path)
        
        # Clean up temporary voice reference
        if voice_reference and voice_ref_path and voice_ref_path.exists():
            voice_ref_path.unlink()
        
        # Return audio file
        return FileResponse(
            path=str(output_path),
            media_type="audio/wav",
            filename=f"tts_{uuid.uuid4().hex[:8]}.wav",
            background=lambda: output_path.unlink() if output_path.exists() else None
        )
        
    except Exception as e:
        logger.error(f"TTS generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"TTS generation failed: {str(e)}")


@app.post("/tts/clone-voice")
async def clone_voice(
    name: str = Form(...),
    audio_reference: UploadFile = File(...),
):
    """Save a voice reference for reuse.
    
    Args:
        name: Friendly name for the voice
        audio_reference: Audio file containing the voice to clone
    
    Returns:
        speaker_id for future use
    """
    if not name or len(name.strip()) == 0:
        raise HTTPException(status_code=400, detail="Voice name cannot be empty")
    
    if not audio_reference:
        raise HTTPException(status_code=400, detail="Audio reference file is required")
    
    try:
        # Generate speaker ID
        speaker_id = f"voice_{uuid.uuid4().hex[:12]}"
        
        # Save audio reference
        voice_path = VOICES_DIR / f"{speaker_id}.wav"
        with open(voice_path, "wb") as f:
            content = await audio_reference.read()
            f.write(content)
        
        # Save metadata
        metadata = {
            "speaker_id": speaker_id,
            "name": name,
            "created_at": "2025-01-01T00:00:00Z",  # Placeholder
            "file_size": len(content)
        }
        
        metadata_path = VOICES_DIR / f"{speaker_id}_meta.json"
        import json
        with open(metadata_path, "w") as f:
            json.dump(metadata, f)
        
        logger.info(f"Voice cloned successfully: {speaker_id} ({name})")
        
        return {
            "speaker_id": speaker_id,
            "name": name,
            "status": "saved",
            "file_size": len(content)
        }
        
    except Exception as e:
        logger.error(f"Voice cloning failed: {e}")
        raise HTTPException(status_code=500, detail=f"Voice cloning failed: {str(e)}")


@app.get("/tts/voices")
async def list_voices():
    """List available cloned voices."""
    try:
        voices = []
        
        for metadata_file in VOICES_DIR.glob("*_meta.json"):
            try:
                import json
                with open(metadata_file, "r") as f:
                    metadata = json.load(f)
                voices.append(metadata)
            except Exception as e:
                logger.warning(f"Failed to read voice metadata {metadata_file}: {e}")
        
        return {
            "voices": voices,
            "count": len(voices)
        }
        
    except Exception as e:
        logger.error(f"Failed to list voices: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list voices: {str(e)}")


@app.delete("/tts/voices/{speaker_id}")
async def delete_voice(speaker_id: str):
    """Delete a cloned voice."""
    try:
        voice_path = VOICES_DIR / f"{speaker_id}.wav"
        metadata_path = VOICES_DIR / f"{speaker_id}_meta.json"
        
        if not voice_path.exists():
            raise HTTPException(status_code=404, detail="Voice not found")
        
        # Delete files
        voice_path.unlink()
        if metadata_path.exists():
            metadata_path.unlink()
        
        logger.info(f"Voice deleted: {speaker_id}")
        
        return {
            "speaker_id": speaker_id,
            "status": "deleted"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete voice {speaker_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete voice: {str(e)}")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8400)