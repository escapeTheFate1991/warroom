#!/usr/bin/env python3
"""Persistent Whisper transcription server — keeps model warm in memory.
Eliminates ~1-2s cold-start per transcription request.
Listens on a Unix socket for low-overhead IPC."""

import os
import sys
import json
import socket
import tempfile
import threading
import time
from pathlib import Path

# Add venv packages
SKILL_DIR = Path(__file__).resolve().parent.parent
VENV_SITE = SKILL_DIR / ".venv" / "lib" / "python3.12" / "site-packages"
if str(VENV_SITE) not in sys.path:
    sys.path.insert(0, str(VENV_SITE))

from faster_whisper import WhisperModel

SOCKET_PATH = "/tmp/whisper-transcribe.sock"
TCP_PORT = 18796  # TCP listener for Docker containers
MODEL_SIZE = os.environ.get("WHISPER_MODEL", "base")
DEVICE = os.environ.get("WHISPER_DEVICE", "cpu")
COMPUTE_TYPE = os.environ.get("WHISPER_COMPUTE", "int8")

print(f"[whisper-server] Loading model '{MODEL_SIZE}' on {DEVICE} ({COMPUTE_TYPE})...", flush=True)
t0 = time.time()
model = WhisperModel(MODEL_SIZE, device=DEVICE, compute_type=COMPUTE_TYPE)
print(f"[whisper-server] Model loaded in {time.time()-t0:.1f}s — ready for requests", flush=True)


def transcribe(wav_path):
    """Transcribe a WAV file using the warm model. Returns segments with timestamps."""
    segments, info = model.transcribe(wav_path, beam_size=1, best_of=1,
                                       language="en", vad_filter=True)
    seg_list = []
    for seg in segments:
        if seg.text.strip():
            seg_list.append({
                "start": round(seg.start, 1),
                "end": round(seg.end, 1),
                "text": seg.text.strip(),
            })
    full_text = " ".join(s["text"] for s in seg_list)
    return {
        "text": full_text,
        "segments": seg_list,
        "language": info.language,
        "language_probability": round(info.language_probability, 2),
    }


def handle_client(conn):
    """Read wav path from client (Unix socket), transcribe, return JSON."""
    try:
        conn.settimeout(5)  # Don't hang on recv
        data = b""
        while True:
            chunk = conn.recv(4096)
            if not chunk:
                break
            data += chunk
            if b"\n" in data:
                break

        wav_path = data.decode().strip()
        if not wav_path or not os.path.isfile(wav_path):
            result = json.dumps({"error": f"File not found: {wav_path}"})
        else:
            t0 = time.time()
            result = json.dumps(transcribe(wav_path))
            elapsed = time.time() - t0
            print(f"[whisper-server] Transcribed in {elapsed:.2f}s", flush=True)

        conn.sendall(result.encode() + b"\n")
    except Exception as e:
        try:
            conn.sendall(json.dumps({"error": str(e)}).encode() + b"\n")
        except:
            pass
    finally:
        conn.close()


def handle_tcp_client(conn):
    """Handle TCP client — supports both file paths and length-prefixed binary.
    
    Protocol detection:
    - If first bytes look like a text path (starts with '/'), read as file path
    - Otherwise, treat as 4-byte big-endian length prefix + binary WAV data
    """
    import struct
    try:
        # Read first 4 bytes to detect protocol
        header = b""
        while len(header) < 4:
            chunk = conn.recv(4 - len(header))
            if not chunk:
                return
            header += chunk

        # Detect: if starts with '/' it's a file path, not binary length prefix
        if header[0:1] == b'/':
            # File path mode — read the rest of the line
            data = header
            while b"\n" not in data:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                data += chunk
            file_path = data.decode().strip()
            if not os.path.isfile(file_path):
                conn.sendall(json.dumps({"error": f"File not found: {file_path}"}).encode() + b"\n")
                return
            t0 = time.time()
            result = json.dumps(transcribe(file_path))
            elapsed = time.time() - t0
            print(f"[whisper-server] TCP transcribed file in {elapsed:.2f}s: {file_path}", flush=True)
            conn.sendall(result.encode() + b"\n")
            return

        # Binary mode — original length-prefixed protocol
        length = struct.unpack(">I", header)[0]
        if length > 50_000_000:  # 50MB max
            conn.sendall(json.dumps({"error": "Audio too large"}).encode() + b"\n")
            return

        # Read WAV data
        wav_data = b""
        while len(wav_data) < length:
            chunk = conn.recv(min(65536, length - len(wav_data)))
            if not chunk:
                break
            wav_data += chunk

        # Write to temp file, transcribe, clean up
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(wav_data)
            tmp_path = tmp.name

        try:
            t0 = time.time()
            result = json.dumps(transcribe(tmp_path))
            elapsed = time.time() - t0
            print(f"[whisper-server] TCP transcribed in {elapsed:.2f}s ({len(wav_data)} bytes)", flush=True)
        finally:
            os.unlink(tmp_path)

        conn.sendall(result.encode() + b"\n")
    except Exception as e:
        try:
            conn.sendall(json.dumps({"error": str(e)}).encode() + b"\n")
        except:
            pass
    finally:
        conn.close()


def main():
    # Clean up stale socket
    if os.path.exists(SOCKET_PATH):
        os.unlink(SOCKET_PATH)

    # Unix socket for local processes
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(SOCKET_PATH)
    os.chmod(SOCKET_PATH, 0o666)
    server.listen(4)
    print(f"[whisper-server] Listening on {SOCKET_PATH}", flush=True)

    # TCP socket for Docker containers
    tcp_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    tcp_server.bind(("0.0.0.0", TCP_PORT))
    tcp_server.listen(4)
    print(f"[whisper-server] TCP listening on 0.0.0.0:{TCP_PORT}", flush=True)

    def accept_loop(srv, handler):
        while True:
            conn, _ = srv.accept()
            threading.Thread(target=handler, args=(conn,), daemon=True).start()

    try:
        threading.Thread(target=accept_loop, args=(tcp_server, handle_tcp_client), daemon=True).start()
        accept_loop(server, handle_client)
    except KeyboardInterrupt:
        print("[whisper-server] Shutting down", flush=True)
    finally:
        server.close()
        tcp_server.close()
        os.unlink(SOCKET_PATH)


if __name__ == "__main__":
    main()
