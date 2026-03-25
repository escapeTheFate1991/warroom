#!/usr/bin/env python3
"""Voice I/O server — lightweight HTTP wrapper.
Whisper runs as a subprocess per-request so memory is freed after each transcription.
Server itself uses ~15MB RAM."""

import os
import json
import tempfile
import subprocess
import re
import uuid
import time as _time
import threading
from pathlib import Path

from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

SKILL_DIR = Path(__file__).resolve().parent.parent
VENV_PY = str(SKILL_DIR / ".venv" / "bin" / "python3")
TRANSCRIBE_SCRIPT = str(SKILL_DIR / "scripts" / "transcribe.py")
BOSE_MAC_US = os.environ.get("BOSE_MAC", "").replace(":", "_")
VOICE_SESSION = "main"  # Use main session so voice + text are unified
WHISPER_SOCKET = "/tmp/whisper-transcribe.sock"

# Read gateway token once at startup
_gw_token = ""
try:
    with open(os.path.expanduser("~/.openclaw/openclaw.json")) as f:
        m = re.search(r'"token"\s*:\s*"([^"]+)"', f.read())
        if m:
            _gw_token = m.group(1)
except Exception:
    pass


def find_bt_sink():
    """Auto-detect any connected Bluetooth audio sink."""
    sink = os.environ.get("VOICE_IO_SINK")
    if sink:
        return sink
    try:
        env = {**os.environ, "XDG_RUNTIME_DIR": f"/run/user/{os.getuid()}"}
        out = subprocess.check_output(["pactl", "list", "short", "sinks"], text=True, env=env)
        for line in out.strip().split("\n"):
            # Match any bluez sink, or specific MAC if provided
            if BOSE_MAC_US and BOSE_MAC_US in line:
                return line.split("\t")[1]
            if "bluez_output" in line:
                return line.split("\t")[1]
    except Exception:
        pass
    return None


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "bose_sink": find_bt_sink(), "mode": "subprocess"})


@app.route("/transcribe", methods=["POST"])
def transcribe():
    """Receive audio blob, transcribe with whisper subprocess, return text."""
    if "audio" not in request.files and not request.data:
        return jsonify({"error": "No audio provided"}), 400

    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
        if "audio" in request.files:
            request.files["audio"].save(tmp)
        else:
            tmp.write(request.data)
        tmp_path = tmp.name

    wav_path = tmp_path.replace(".webm", ".wav")
    env = {**os.environ, "XDG_RUNTIME_DIR": f"/run/user/{os.getuid()}"}

    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", tmp_path, "-ar", "16000", "-ac", "1", "-f", "wav", wav_path],
            capture_output=True, timeout=15, env=env
        )

        # Try warm Whisper server first, fallback to subprocess
        data = None
        try:
            import socket as _socket
            sock = _socket.socket(_socket.AF_UNIX, _socket.SOCK_STREAM)
            sock.settimeout(15)
            sock.connect(WHISPER_SOCKET)
            sock.sendall(wav_path.encode() + b"\n")
            sock.shutdown(_socket.SHUT_WR)
            resp = b""
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                resp += chunk
            sock.close()
            data = json.loads(resp.decode().strip())
        except (ConnectionRefusedError, FileNotFoundError):
            # Fallback: cold subprocess
            result = subprocess.run(
                [VENV_PY, TRANSCRIBE_SCRIPT, wav_path],
                capture_output=True, text=True, timeout=30, env=env
            )
            if result.returncode != 0:
                return jsonify({"error": result.stderr.strip()}), 500
            data = json.loads(result.stdout.strip())

        return jsonify(data)
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Transcription timed out"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        for p in [tmp_path, wav_path]:
            try:
                os.unlink(p)
            except OSError:
                pass


@app.route("/play", methods=["POST"])
def play():
    data = request.json or {}
    audio_path = data.get("path")
    if not audio_path or not os.path.isfile(audio_path):
        return jsonify({"error": f"File not found: {audio_path}"}), 400

    sink = find_bt_sink()
    env = {**os.environ, "XDG_RUNTIME_DIR": f"/run/user/{os.getuid()}"}

    try:
        wav_tmp = tempfile.mktemp(suffix=".wav")
        subprocess.run(
            ["ffmpeg", "-y", "-i", audio_path, "-ar", "44100", "-ac", "2", "-f", "wav", wav_tmp],
            capture_output=True, timeout=30, env=env
        )
        cmd = ["paplay"]
        if sink:
            cmd.append(f"--device={sink}")
        cmd.append(wav_tmp)
        subprocess.run(cmd, timeout=120, env=env)
        os.unlink(wav_tmp)
        return jsonify({"status": "ok", "sink": sink})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/chat", methods=["POST"])
def chat():
    """Send text to OpenClaw via OpenAI-compatible HTTP API."""
    data = request.json or {}
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"error": "No text provided"}), 400

    try:
        import urllib.request

        gateway_url = os.environ.get("GATEWAY_URL", "http://127.0.0.1:18789")
        url = f"{gateway_url}/v1/chat/completions"
        payload = json.dumps({
            "model": "anthropic/claude-haiku-3-5-20241022",  # Fast voice responses
            "messages": [
                {"role": "system", "content": "You are Friday, Eddy's AI assistant. This is a VOICE conversation through Bluetooth headphones (Stargazer). Keep responses concise and conversational — you're being spoken aloud via TTS. No markdown, no emojis, no bullet lists. Talk like a human. You have full context from the main session including all memory, skills, and project knowledge."},
                {"role": "user", "content": text},
            ],
            "stream": False,
            "user": "eddy-voice",
        }).encode()
        headers = {
            "Content-Type": "application/json",
            "x-openclaw-session-key": "voice",
        }
        if _gw_token:
            headers["Authorization"] = f"Bearer {_gw_token}"

        req = urllib.request.Request(url, data=payload, headers=headers)
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode())

        # Extract reply from OpenAI-format response
        choices = result.get("choices", [])
        reply = ""
        if choices:
            msg = choices[0].get("message", {})
            reply = msg.get("content", "")

        # Strip markdown for speech
        reply = reply.replace("**", "").replace("*", "").replace("`", "").replace("#", "")

        return jsonify({"reply": reply})

    except ImportError:
        return jsonify({"error": "websocket-client not installed"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Conversation mode management ────────────────────────────────────────
_convo_pid = None
_convo_proc = None

def _get_convo_pid():
    """Check if conversation process is running."""
    global _convo_pid
    pidfile = "/tmp/voice-io-conversation.pid"
    if os.path.isfile(pidfile):
        try:
            pid = int(open(pidfile).read().strip())
            os.kill(pid, 0)  # Check if alive
            _convo_pid = pid
            return pid
        except (ProcessLookupError, ValueError):
            os.unlink(pidfile)
    _convo_pid = None
    return None


@app.route("/conversation/status", methods=["GET"])
def convo_status():
    pid = _get_convo_pid()
    return jsonify({"running": pid is not None, "pid": pid})


@app.route("/conversation/start", methods=["POST"])
def convo_start():
    pid = _get_convo_pid()
    if pid:
        return jsonify({"status": "already_running", "pid": pid})

    try:
        script = str(SKILL_DIR / "scripts" / "conversation.sh")
        env = {**os.environ, "XDG_RUNTIME_DIR": f"/run/user/{os.getuid()}"}
        subprocess.Popen(["bash", script, "start"], env=env,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        import time as _t
        _t.sleep(2)
        pid = _get_convo_pid()
        if pid:
            return jsonify({"status": "ok", "pid": pid})
        else:
            return jsonify({"status": "error", "error": "Failed to start"}), 500
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route("/conversation/stop", methods=["POST"])
def convo_stop():
    pid = _get_convo_pid()
    if not pid:
        return jsonify({"status": "not_running"})

    try:
        import signal as _sig
        # Send SIGTERM first (triggers our handler which kills children)
        os.kill(pid, _sig.SIGTERM)
        # Give it 1 second to clean up
        import time as _t
        _t.sleep(1)
        # Force kill if still alive
        try:
            os.kill(pid, 0)  # Check if still running
            os.kill(pid, _sig.SIGKILL)
        except ProcessLookupError:
            pass
        # Also kill any lingering audio playback
        subprocess.run(["pkill", "-f", "paplay.*bluez"], capture_output=True)
        subprocess.run(["pkill", "-f", "edge-tts"], capture_output=True)
        # Clean up PID file
        pidfile = SKILL_DIR / "scripts" / ".." / ".." / ".." / ".." / ".." / "tmp" / "voice-io-conversation.pid"
        try:
            os.unlink("/tmp/voice-io-conversation.pid")
        except OSError:
            pass
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("VOICE_IO_PORT", "18793"))
    print(f"[voice-io] Server on port {port} | token={'yes' if _gw_token else 'NO'}", flush=True)
    app.run(host="0.0.0.0", port=port, debug=False)
