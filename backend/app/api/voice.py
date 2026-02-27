"""Voice I/O — Speech-to-Text via Whisper + TTS via edge-tts"""
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
import tempfile
import socket
import json
import subprocess
import os
import asyncio

router = APIRouter()

WHISPER_SOCKET = "/tmp/whisper-transcribe.sock"


async def transcribe_via_whisper(wav_path: str) -> dict:
    """Send audio file path to the Whisper Unix socket server."""
    loop = asyncio.get_event_loop()

    def _send():
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(30)
        sock.connect(WHISPER_SOCKET)
        sock.sendall((wav_path + "\n").encode())
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
    if not os.path.exists(WHISPER_SOCKET):
        raise HTTPException(status_code=503, detail="Whisper server not running")

    # Save uploaded audio to temp file
    suffix = ".webm" if "webm" in (file.content_type or "") else ".wav"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    # Convert to WAV if needed (Whisper needs WAV/MP3)
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
        result = await transcribe_via_whisper(wav_path)
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

    # Generate audio with edge-tts
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

    # Generate
    proc = subprocess.run(
        ["edge-tts", "--voice", voice, "--text", text, "--write-media", tmp_path],
        capture_output=True, timeout=30,
    )
    if proc.returncode != 0:
        raise HTTPException(status_code=500, detail="TTS failed")

    # Play on Bose speaker
    play_script = "/home/eddy/.openclaw/workspace/skills/voice-io/scripts/play-audio.sh"
    if os.path.exists(play_script):
        subprocess.Popen(["bash", play_script, tmp_path])
        return {"status": "playing", "path": tmp_path}
    else:
        os.unlink(tmp_path)
        return {"status": "error", "detail": "play-audio.sh not found"}
