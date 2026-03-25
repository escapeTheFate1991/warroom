#!/usr/bin/env python3
"""
Voice Conversation Mode — Always-listening loop.
Listens via Bose mic (VAD), transcribes, sends to OpenClaw chat, 
speaks the response back through the Bose speaker.

Usage: conversation.py [--voice en-US-AriaNeural] [--wake-word friday]
"""

import os
import sys
import json
import wave
import struct
import asyncio
import tempfile
import subprocess
import argparse
import time
from pathlib import Path

import sounddevice as sd
import webrtcvad
import numpy as np

SKILL_DIR = Path(__file__).resolve().parent.parent
WORKSPACE_DIR = SKILL_DIR.parent.parent
VENV_PY = str(SKILL_DIR / ".venv" / "bin" / "python3")
VENV_EDGE_TTS = str(SKILL_DIR / ".venv" / "bin" / "edge-tts")
TRANSCRIBE_SCRIPT = str(SKILL_DIR / "scripts" / "transcribe.py")

# ── Ollama Local LLM ────────────────────────────────────────────────────
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen3:4b")

# Load Friday personality context for local model
_friday_context = ""
_ctx_path = WORKSPACE_DIR / "FRIDAY-CONTEXT.md"
if _ctx_path.is_file():
    _friday_context = _ctx_path.read_text().strip()

# Conversation history for local model (keeps last N turns for context)
_conversation_history = []
MAX_HISTORY_TURNS = 6  # 3 exchanges


def send_to_ollama(text):
    """Send directly to Ollama for sub-second local response."""
    import urllib.request
    global _conversation_history

    messages = []
    # System prompt with Friday personality
    voice_rules = (
        "\n\nVOICE MODE — STRICT RULES:\n"
        "- Reply in 1-3 sentences ONLY\n"
        "- NEVER write your reasoning or thought process\n"
        "- NEVER start with 'Okay, user said' or analyze the question\n"
        "- Just answer directly like a human would in conversation\n"
        "- No markdown, no lists, no formatting — plain speech only"
    )
    if _friday_context:
        messages.append({"role": "system", "content": _friday_context + voice_rules})
    else:
        messages.append({"role": "system", "content":
                         "You are Friday, a sharp and helpful AI assistant." + voice_rules})

    # Add conversation history
    messages.extend(_conversation_history)
    messages.append({"role": "user", "content": text})

    payload = json.dumps({
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
        "think": False,
        "options": {"num_predict": 100, "temperature": 0.7}
    }).encode()

    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"}
    )

    try:
        t0 = time.time()
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
        elapsed = time.time() - t0
        reply = data.get("message", {}).get("content", "").strip()

        # Clean up thinking artifacts from qwen3
        import re as _re
        reply = _re.sub(r'<think>.*?</think>', '', reply, flags=_re.DOTALL).strip()
        # qwen3 often "thinks out loud" — strip lines that are internal monologue
        clean_lines = []
        skip_patterns = [
            r'^(okay|ok|hmm|alright|so|let me|the user|they\'re|as friday|i need to|i should|should i)',
            r'(user (said|asked|wants|is)|checking in|casual greeting|keep it|short and|per instructions)',
            r'^\s*[-—]\s',  # bullet-style reasoning
        ]
        for line in reply.split('\n'):
            line_lower = line.strip().lower()
            if not line_lower:
                continue
            is_thinking = any(_re.search(p, line_lower) for p in skip_patterns)
            if not is_thinking:
                clean_lines.append(line.strip())
        # If we stripped everything, take the last sentence of the original as fallback
        if clean_lines:
            reply = ' '.join(clean_lines)
        else:
            # Grab last complete sentence from original
            sentences = [s.strip() for s in _re.split(r'[.!?]+', reply) if s.strip()]
            reply = (sentences[-1] + '.') if sentences else reply

        print(f"[voice-io] Ollama responded in {elapsed:.2f}s", flush=True)

        # Update history
        _conversation_history.append({"role": "user", "content": text})
        _conversation_history.append({"role": "assistant", "content": reply})
        if len(_conversation_history) > MAX_HISTORY_TURNS * 2:
            _conversation_history = _conversation_history[-MAX_HISTORY_TURNS * 2:]

        return reply
    except Exception as e:
        print(f"[voice-io] Ollama error: {e}", flush=True)
        return None


# ── Config ──────────────────────────────────────────────────────────────
SAMPLE_RATE = 16000
FRAME_DURATION_MS = 30  # 10, 20, or 30 ms for webrtcvad
FRAME_SIZE = int(SAMPLE_RATE * FRAME_DURATION_MS / 1000)
VAD_AGGRESSIVENESS = 3  # 0-3, higher = more aggressive filtering (was 2)
SILENCE_TIMEOUT_S = 0.8  # seconds of silence to end utterance (was 1.5)
MIN_SPEECH_FRAMES = 10  # minimum speech frames to process (avoid tiny blips)
BT_MAC_US = os.environ.get("BOSE_MAC", "").replace(":", "_")

# Gateway WebSocket for sending chat messages
GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://127.0.0.1:18789")
GATEWAY_TOKEN = os.environ.get("GATEWAY_TOKEN", "")


def find_bt_source_index():
    """Find the PipeWire/ALSA device index for any connected BT mic."""
    devices = sd.query_devices()
    for i, d in enumerate(devices):
        name = d["name"].lower()
        if d["max_input_channels"] > 0:
            # Match specific MAC if provided
            if BT_MAC_US and BT_MAC_US.lower().replace("_", ":") in name:
                return i
            # Match any bluez input
            if "bluez" in name:
                return i
    # Fallback: default input
    return None


def find_bt_sink():
    """Find PipeWire sink name for any connected BT speaker."""
    env = {**os.environ, "XDG_RUNTIME_DIR": f"/run/user/{os.getuid()}"}
    try:
        out = subprocess.check_output(["pactl", "list", "short", "sinks"], text=True, env=env)
        for line in out.strip().split("\n"):
            if BT_MAC_US and BT_MAC_US in line:
                return line.split("\t")[1]
            if "bluez_output" in line:
                return line.split("\t")[1]
    except Exception:
        pass
    return None


def record_utterance(device_index=None):
    """Record until speech ends (VAD-based). Returns WAV bytes or None."""
    vad = webrtcvad.Vad(VAD_AGGRESSIVENESS)

    speech_frames = []
    silence_count = 0
    speech_started = False
    max_silence_frames = int(SILENCE_TIMEOUT_S * 1000 / FRAME_DURATION_MS)

    print("🎧 Listening...", flush=True)

    def callback(indata, frames, time_info, status):
        nonlocal silence_count, speech_started
        if status:
            pass  # ignore overflows

        # Convert float32 to int16 for webrtcvad
        audio_int16 = (indata[:, 0] * 32767).astype(np.int16)
        frame_bytes = audio_int16.tobytes()

        # webrtcvad needs exact frame sizes
        chunk_size = FRAME_SIZE * 2  # 2 bytes per sample (int16)
        for offset in range(0, len(frame_bytes) - chunk_size + 1, chunk_size):
            chunk = frame_bytes[offset:offset + chunk_size]
            if len(chunk) < chunk_size:
                break

            is_speech = vad.is_speech(chunk, SAMPLE_RATE)

            if is_speech:
                speech_frames.append(chunk)
                silence_count = 0
                if not speech_started:
                    speech_started = True
                    print("🗣️  Speech detected...", flush=True)
            elif speech_started:
                speech_frames.append(chunk)  # keep some silence for natural endings
                silence_count += 1

    try:
        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="float32",
            blocksize=FRAME_SIZE,
            device=device_index,
            callback=callback,
        ):
            while True:
                time.sleep(0.05)
                if speech_started and silence_count >= max_silence_frames:
                    break
                if speech_started and len(speech_frames) > 3000:  # ~90s max
                    break

    except Exception as e:
        print(f"[voice-io] Recording error: {e}", flush=True)
        return None

    if len(speech_frames) < MIN_SPEECH_FRAMES:
        return None

    print(f"📝 Got {len(speech_frames)} frames, transcribing...", flush=True)

    # Write WAV
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        wav_path = f.name
        with wave.open(f, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(b"".join(speech_frames))

    return wav_path


WHISPER_SOCKET = "/tmp/whisper-transcribe.sock"


def transcribe(wav_path):
    """Transcribe via persistent Whisper server (fast), fallback to subprocess (slow)."""
    try:
        # Try warm server first
        import socket as _socket
        sock = _socket.socket(_socket.AF_UNIX, _socket.SOCK_STREAM)
        sock.settimeout(15)
        sock.connect(WHISPER_SOCKET)
        sock.sendall(wav_path.encode() + b"\n")
        sock.shutdown(_socket.SHUT_WR)
        data = b""
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            data += chunk
        sock.close()
        os.unlink(wav_path)
        result = json.loads(data.decode().strip())
        if "error" in result:
            print(f"[voice-io] Whisper server error: {result['error']}", flush=True)
            return None
        return result.get("text", "").strip()
    except (ConnectionRefusedError, FileNotFoundError):
        # Fallback: subprocess (cold start)
        print("[voice-io] Whisper server not running, using subprocess fallback...", flush=True)
        try:
            result = subprocess.run(
                [VENV_PY, TRANSCRIBE_SCRIPT, wav_path],
                capture_output=True, text=True, timeout=30,
            )
            os.unlink(wav_path)
            if result.returncode != 0:
                print(f"[voice-io] Transcription error: {result.stderr}", flush=True)
                return None
            data = json.loads(result.stdout.strip())
            return data.get("text", "").strip()
        except Exception as e:
            print(f"[voice-io] Transcription failed: {e}", flush=True)
            return None
    except Exception as e:
        print(f"[voice-io] Transcription failed: {e}", flush=True)
        try:
            os.unlink(wav_path)
        except:
            pass
        return None


def send_to_chat(text):
    """Send text to OpenClaw gateway via HTTP hook and get the response."""
    import urllib.request
    import urllib.error

    # Use the webchat WS API via HTTP — send chat message and poll for response
    url = f"{GATEWAY_URL}/hooks/voice-io"
    headers = {"Content-Type": "application/json"}
    if GATEWAY_TOKEN:
        headers["Authorization"] = f"Bearer {GATEWAY_TOKEN}"

    payload = json.dumps({"text": text}).encode()
    req = urllib.request.Request(url, data=payload, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
            return data.get("reply", data.get("text", ""))
    except Exception as e:
        print(f"[voice-io] Chat send failed: {e}", flush=True)
        # Fallback: use the voice-io server to relay
        return None


def send_to_chat_ws(text):
    """Inject text into OpenClaw webchat textarea via browser automation."""
    try:
        import subprocess
        
        # JavaScript to inject text into the textarea
        js_code = f'''
        const textarea = document.querySelector('textarea[placeholder*="message"], textarea');
        if (textarea) {{
            textarea.value = {repr(text)};
            textarea.dispatchEvent(new Event('input', {{ bubbles: true }}));
            textarea.focus();
            console.log("Voice text injected:", {repr(text)});
        }} else {{
            console.error("Textarea not found");
        }}
        '''
        
        # Use OpenClaw browser tool to inject text
        result = subprocess.run([
            "openclaw", "browser", "act", "evaluate", 
            "--fn", js_code
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print(f"[voice-io] ✅ Text injected: {text}", flush=True)
            return "injected"
        else:
            print(f"[voice-io] ❌ Injection failed: {result.stderr}", flush=True)
            return None
            
    except Exception as e:
        print(f"[voice-io] Browser automation failed: {e}", flush=True)
        return None


async def speak(text, voice, sink=None):
    """Convert text to speech with edge-tts and play through Bose."""
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        mp3_path = f.name

    try:
        # Generate TTS
        proc = await asyncio.create_subprocess_exec(
            VENV_EDGE_TTS, "--voice", voice, "--text", text, "--write-media", mp3_path,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        await proc.wait()

        if not os.path.isfile(mp3_path) or os.path.getsize(mp3_path) == 0:
            print("[voice-io] TTS produced no audio", flush=True)
            return

        # Play through Bose
        env = {**os.environ, "XDG_RUNTIME_DIR": f"/run/user/{os.getuid()}"}
        wav_tmp = tempfile.mktemp(suffix=".wav")

        subprocess.run(
            ["ffmpeg", "-y", "-i", mp3_path, "-ar", "44100", "-ac", "2", "-f", "wav", wav_tmp],
            capture_output=True, timeout=15, env=env,
        )

        cmd = ["paplay"]
        if sink:
            cmd.append(f"--device={sink}")
        cmd.append(wav_tmp)

        print("🔊 Speaking...", flush=True)
        subprocess.run(cmd, timeout=120, env=env)

        for p in [mp3_path, wav_tmp]:
            try:
                os.unlink(p)
            except OSError:
                pass

    except Exception as e:
        print(f"[voice-io] TTS/play error: {e}", flush=True)


def _kill_children():
    """Kill all child processes (paplay, ffmpeg, edge-tts) immediately."""
    import signal as _sig
    pid = os.getpid()
    try:
        # Kill entire process group
        os.killpg(os.getpgid(pid), _sig.SIGKILL)
    except ProcessLookupError:
        pass
    except PermissionError:
        # Fallback: kill known child process names
        subprocess.run(["pkill", "-P", str(pid)], capture_output=True)


def _signal_handler(signum, frame):
    """Handle SIGTERM/SIGINT — kill children and exit immediately."""
    print("\n👋 Conversation mode ended (signal).", flush=True)
    # Kill any playing audio
    subprocess.run(["pkill", "-f", "paplay.*bluez"], capture_output=True)
    subprocess.run(["pkill", "-f", "edge-tts"], capture_output=True)
    os._exit(0)


def main():
    import signal as _sig
    _sig.signal(_sig.SIGTERM, _signal_handler)
    _sig.signal(_sig.SIGINT, _signal_handler)

    parser = argparse.ArgumentParser(description="Voice Conversation Mode")
    parser.add_argument("--voice", default="en-US-AvaNeural",
                        help="Edge TTS voice (default: en-US-AriaNeural)")
    parser.add_argument("--wake-word", default=None,
                        help="Optional wake word filter (e.g. 'friday')")
    parser.add_argument("--auto-send", action="store_true", default=True,
                        help="Auto-send to chat (default: true)")
    parser.add_argument("--local", action="store_true", default=False,
                        help="Use local Ollama LLM instead of OpenClaw (faster)")
    parser.add_argument("--model", default=None,
                        help="Ollama model to use with --local (default: qwen3:4b)")
    args = parser.parse_args()

    if args.model:
        global OLLAMA_MODEL
        OLLAMA_MODEL = args.model

    device_idx = find_bt_source_index()
    sink = find_bt_sink()

    print(f"🎙️  Voice Conversation Mode", flush=True)
    print(f"   Voice: {args.voice}", flush=True)
    print(f"   Mic device: {device_idx or 'default'}", flush=True)
    print(f"   Speaker sink: {sink or 'default'}", flush=True)
    print(f"   Wake word: {args.wake_word or 'none (always listening)'}", flush=True)
    print(f"   LLM mode: {'LOCAL (' + OLLAMA_MODEL + ')' if args.local else 'OpenClaw (cloud)'}", flush=True)
    print(f"   Press Ctrl+C to stop\n", flush=True)

    # Conversation window: after Friday speaks, stay active for this many seconds
    # without requiring the wake word (natural back-and-forth)
    CONVERSATION_WINDOW_S = 30
    last_interaction = 0  # timestamp of last spoken response
    in_conversation = False

    while True:
        try:
            # 1. Listen for speech
            wav_path = record_utterance(device_idx)
            if not wav_path:
                # Check if conversation window expired
                if in_conversation and (time.time() - last_interaction) > CONVERSATION_WINDOW_S:
                    in_conversation = False
                    print("💤 Conversation window closed (back to wake word mode)", flush=True)
                continue

            # 2. Transcribe
            text = transcribe(wav_path)
            if not text:
                continue

            # Filter noise/artifacts
            if len(text) < 2 or text.lower() in ["you", ".", "the", "thank you.", "thanks."]:
                continue

            # 3. Check wake word — skip if we're in an active conversation
            if args.wake_word and not in_conversation:
                if args.wake_word.lower() not in text.lower():
                    print(f"   (ignored, no wake word: '{text}')", flush=True)
                    continue
                # Strip wake word from the text
                import re
                text = re.sub(rf'\b{re.escape(args.wake_word)}\b[,.]?\s*', '', text, flags=re.IGNORECASE).strip()
                if not text:
                    # Just the wake word by itself — acknowledge and open conversation
                    in_conversation = True
                    last_interaction = time.time()
                    asyncio.run(speak("Yes?", args.voice, sink))
                    last_interaction = time.time()
                    continue

            # We're now in a conversation (either wake word triggered or window still open)
            in_conversation = True

            print(f"👤 You: {text}", flush=True)

            # 4. Send to chat and get response
            if args.local:
                reply = send_to_ollama(text)
            else:
                reply = send_to_chat_ws(text)
            # Filter out non-speech responses
            SKIP_REPLIES = {"HEARTBEAT_OK", "NO_REPLY", ""}
            reply_clean = (reply or "").strip()
            # Also strip [[tts:...]] tags for display but keep inner text
            import re as _re
            reply_clean = _re.sub(r'\[\[tts:[^\]]*\]\]', '', reply_clean).strip()
            reply_clean = _re.sub(r'\[\[/tts:[^\]]*\]\]', '', reply_clean).strip()

            if reply_clean and reply_clean not in SKIP_REPLIES:
                print(f"🤖 Friday: {reply_clean}", flush=True)
                # 5. Speak the response
                asyncio.run(speak(reply_clean, args.voice, sink))
                last_interaction = time.time()  # Reset window after speaking
            else:
                print("   (no reply from chat)", flush=True)

        except KeyboardInterrupt:
            print("\n👋 Conversation mode ended.", flush=True)
            break
        except Exception as e:
            print(f"[voice-io] Error: {e}", flush=True)
            time.sleep(1)


if __name__ == "__main__":
    main()
