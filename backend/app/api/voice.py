"""Voice I/O — Speech-to-Text via Whisper + TTS via edge-tts"""
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
import tempfile
import socket
import struct
import json
import subprocess
import os
import asyncio

router = APIRouter()

WHISPER_TCP_HOST = os.getenv("WHISPER_HOST", "127.0.0.1")
WHISPER_TCP_PORT = int(os.getenv("WHISPER_PORT", "18796"))


async def transcribe_via_tcp(wav_data: bytes) -> dict:
    """Send raw WAV bytes to Whisper TCP server, get JSON result back."""
    loop = asyncio.get_event_loop()

    def _send():
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(30)
        sock.connect((WHISPER_TCP_HOST, WHISPER_TCP_PORT))
        # Protocol: 4-byte big-endian length prefix + wav data
        sock.sendall(struct.pack(">I", len(wav_data)) + wav_data)
        data = b""
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            data += chunk
            if b"\n" in data:
                break
        sock.close()
        return json.loads(data.decode().strip())

    return await loop.run_in_executor(None, _send)


@router.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    """Receive audio from browser, convert to WAV, transcribe via Whisper."""
    # Save uploaded audio to temp file
    suffix = ".webm" if "webm" in (file.content_type or "") else ".wav"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    # Convert to WAV if needed
    wav_path = tmp_path
    if suffix != ".wav":
        wav_path = tmp_path.replace(suffix, ".wav")
        proc = subprocess.run(
            ["ffmpeg", "-y", "-i", tmp_path, "-ar", "16000", "-ac", "1", "-f", "wav", wav_path],
            capture_output=True, timeout=15,
        )
        os.unlink(tmp_path)
        if proc.returncode != 0:
            raise HTTPException(status_code=500, detail=f"ffmpeg failed: {proc.stderr.decode()[:200]}")

    try:
        with open(wav_path, "rb") as f:
            wav_data = f.read()
        result = await transcribe_via_tcp(wav_data)
    except ConnectionRefusedError:
        raise HTTPException(status_code=503, detail="Whisper server not running (TCP port 18796)")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)[:200]}")
    finally:
        if os.path.exists(wav_path):
            os.unlink(wav_path)

    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])

    return {"text": result.get("text", ""), "language": result.get("language", "en")}


@router.post("/tts")
async def text_to_speech(text: str = "", voice: str = "en-US-AvaNeural"):
    """Generate speech from text using edge-tts, return audio stream."""
    if not text:
        raise HTTPException(status_code=400, detail="No text provided")

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp_path = tmp.name

    proc = subprocess.run(
        ["edge-tts", "--voice", voice, "--text", text, "--write-media", tmp_path],
        capture_output=True, timeout=30,
    )

    if proc.returncode != 0 or not os.path.exists(tmp_path):
        raise HTTPException(status_code=500, detail="TTS generation failed")

    def stream():
        with open(tmp_path, "rb") as f:
            yield from iter(lambda: f.read(8192), b"")
        os.unlink(tmp_path)

    return StreamingResponse(stream(), media_type="audio/mpeg")


@router.post("/tts/play")
async def tts_play_on_speaker(text: str = "", voice: str = "en-US-AvaNeural"):
    """Generate speech and play on the Bose speaker."""
    if not text:
        raise HTTPException(status_code=400, detail="No text provided")

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp_path = tmp.name

    proc = subprocess.run(
        ["edge-tts", "--voice", voice, "--text", text, "--write-media", tmp_path],
        capture_output=True, timeout=30,
    )
    if proc.returncode != 0:
        raise HTTPException(status_code=500, detail="TTS failed")

    play_script = "/home/eddy/.openclaw/workspace/skills/voice-io/scripts/play-audio.sh"
    if os.path.exists(play_script):
        subprocess.Popen(["bash", play_script, tmp_path])
        return {"status": "playing", "path": tmp_path}
    else:
        os.unlink(tmp_path)
        return {"status": "error", "detail": "play-audio.sh not found"}
