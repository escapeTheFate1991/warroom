"""Voice I/O — Speech-to-Text via Whisper + TTS via edge-tts"""
import re
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

# Configurable paths (replace hardcoded /home/eddy/... paths)
VOICE_IO_SCRIPTS_PATH = os.getenv("VOICE_IO_SCRIPTS_PATH", "/home/eddy/.openclaw/workspace/skills/voice-io/scripts")

# TTS text limits
MAX_TTS_TEXT_LENGTH = 5000


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


BT_SCAN_SCRIPT = os.path.join(VOICE_IO_SCRIPTS_PATH, "bt-scan.sh")


def _bt_env():
    return {**os.environ, "XDG_RUNTIME_DIR": os.environ.get("XDG_RUNTIME_DIR", "/run/user/1000")}

@router.get("/bt/status")
async def bt_status():
    """Return current Bluetooth audio device status."""
    try:
        proc = subprocess.run(["bash", BT_SCAN_SCRIPT, "info"], capture_output=True, timeout=5, env=_bt_env())
        return json.loads(proc.stdout.decode().strip())
    except Exception as e:
        return {"connected": False, "error": str(e)}


@router.post("/bt/hfp")
async def bt_switch_hfp():
    """Auto-discover BT device and switch to HFP (mic mode). No disconnect/reconnect."""
    # Use uid 1000 (host user) for PipeWire access — container runs as root
    try:
        # Get current state
        info_proc = subprocess.run(["bash", BT_SCAN_SCRIPT, "info"], capture_output=True, timeout=5, env=_bt_env())
        info = json.loads(info_proc.stdout.decode().strip())

        if not info.get("connected"):
            return {"ok": False, "error": "No Bluetooth audio device connected"}

        # If already in HFP with mic, just return
        if info.get("mic_active") and "headset-head-unit" in info.get("profile", ""):
            return {"ok": True, "device": info.get("name"), "action": "already_hfp"}

        # Switch primary device to HFP, set others to A2DP to avoid conflicts
        # Get all BT cards
        all_cards = subprocess.run(
            ["pactl", "list", "cards", "short"],
            capture_output=True, timeout=5, env=_bt_env(), text=True
        )
        for line in all_cards.stdout.strip().split("\n"):
            if "bluez_card" not in line:
                continue
            card_name = line.split()[1]
            card_mac = card_name.replace("bluez_card.", "").replace("_", ":")
            if card_mac == info.get("mac", ""):
                # This is the primary — switch to HFP
                continue
            # Other devices — force to A2DP so they don't grab the mic
            subprocess.run(
                ["pactl", "set-card-profile", card_name, "a2dp-sink"],
                capture_output=True, timeout=5, env=_bt_env()
            )

        subprocess.run(["bash", BT_SCAN_SCRIPT, "hfp"], capture_output=True, timeout=5, env=_bt_env())
        await asyncio.sleep(0.5)

        # Set mic volume to 100%
        card = info.get("card", "")
        source = card.replace("bluez_card", "bluez_input") + ".0"
        subprocess.run(
            ["pactl", "set-source-volume", source, "100%"],
            capture_output=True, timeout=5,
            env=_bt_env(),
        )

        return {"ok": True, "device": info.get("name"), "action": "switched_to_hfp"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/bt/a2dp")
async def bt_switch_a2dp():
    """Switch back to A2DP (hi-fi audio, no mic)."""
    try:
        proc = subprocess.run(["bash", BT_SCAN_SCRIPT, "a2dp"], capture_output=True, timeout=5, env=_bt_env())
        return {"ok": True, "output": proc.stdout.decode().strip()}
    except Exception as e:
        return {"ok": False, "error": str(e)}


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


def _sanitize_tts_text(text: str) -> str:
    """Strip shell metacharacters from TTS text to prevent injection."""
    # Remove characters that could be interpreted by shell
    return re.sub(r'[;|&`$(){}\\<>!\n\r]', '', text)


def _validate_tts_input(text: str) -> str:
    """Validate and sanitize TTS text input."""
    if not text:
        raise HTTPException(status_code=400, detail="No text provided")
    if len(text) > MAX_TTS_TEXT_LENGTH:
        raise HTTPException(status_code=400, detail=f"Text too long (max {MAX_TTS_TEXT_LENGTH} characters)")
    return _sanitize_tts_text(text)


CHATTERBOX_URL = os.getenv("CHATTERBOX_URL", "http://localhost:8401")


@router.post("/tts")
async def text_to_speech(text: str = "", voice: str = "", engine: str = ""):
    """Generate speech. Tries Chatterbox (GPU) first, falls back to edge-tts."""
    text = _validate_tts_input(text)

    # Try Chatterbox first (better quality, GPU-accelerated)
    if engine != "edge":
        try:
            import httpx
            async with httpx.AsyncClient(timeout=30.0) as client:
                form_data = {"text": text}
                if voice:
                    form_data["speaker_id"] = voice
                resp = await client.post(f"{CHATTERBOX_URL}/tts/generate", data=form_data)
                if resp.status_code == 200:
                    async def stream_chatterbox():
                        yield resp.content
                    return StreamingResponse(stream_chatterbox(), media_type="audio/wav")
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Chatterbox failed, falling back to edge-tts: {e}")

    # Fallback: edge-tts
    edge_voice = voice if voice and not voice.startswith("voice_") else "en-US-AvaNeural"
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp_path = tmp.name

    proc = subprocess.run(
        ["edge-tts", "--voice", edge_voice, "--text", text, "--write-media", tmp_path],
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
    text = _validate_tts_input(text)

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp_path = tmp.name

    proc = subprocess.run(
        ["edge-tts", "--voice", voice, "--text", text, "--write-media", tmp_path],
        capture_output=True, timeout=30,
    )
    if proc.returncode != 0:
        raise HTTPException(status_code=500, detail="TTS failed")

    play_script = os.path.join(VOICE_IO_SCRIPTS_PATH, "play-audio.sh")
    if os.path.exists(play_script):
        subprocess.Popen(["bash", play_script, tmp_path])
        return {"status": "playing", "path": tmp_path}
    else:
        os.unlink(tmp_path)
        return {"status": "error", "detail": "play-audio.sh not found"}
