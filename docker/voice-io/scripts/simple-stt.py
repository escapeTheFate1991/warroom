#!/usr/bin/env python3
"""
Simple Speech-to-Text for OpenClaw webchat.
Just transcribes and writes to /tmp/stt-output.txt for browser injection.
"""

import os
import json
import wave
import struct
import tempfile
import subprocess
from pathlib import Path

import sounddevice as sd
import webrtcvad
import numpy as np

SKILL_DIR = Path(__file__).resolve().parent.parent
TRANSCRIBE_SCRIPT = str(SKILL_DIR / "scripts" / "transcribe.py")
OUTPUT_FILE = "/tmp/stt-output.txt"

# Audio settings
SAMPLE_RATE = 16000
FRAME_DURATION_MS = 30
FRAME_SIZE = int(SAMPLE_RATE * FRAME_DURATION_MS / 1000)
VAD_AGGRESSIVENESS = 3
SILENCE_TIMEOUT_S = 0.8
MIN_SPEECH_FRAMES = 10

def find_bt_source_index():
    """Find any connected BT mic."""
    devices = sd.query_devices()
    for i, d in enumerate(devices):
        name = d["name"].lower()
        if d["max_input_channels"] > 0:
            if any(x in name for x in ["bluez", "bt", "bluetooth", "stargazer", "bose"]):
                return i, d["name"]
    return None, None

def transcribe_audio(audio_data):
    """Transcribe audio using local Whisper."""
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            with wave.open(f.name, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(SAMPLE_RATE)
                wf.writeframes(audio_data)
            
            # Use transcribe.py
            result = subprocess.run([
                str(SKILL_DIR / ".venv" / "bin" / "python3"),
                TRANSCRIBE_SCRIPT, f.name
            ], capture_output=True, text=True, timeout=30)
            
            os.unlink(f.name)
            
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                print(f"Transcription failed: {result.stderr}")
                return None
    except Exception as e:
        print(f"Transcription error: {e}")
        return None

def main():
    mic_index, mic_name = find_bt_source_index()
    if mic_index is None:
        print("❌ No BT mic found. Using default.")
        mic_index = None
        mic_name = "default"
    else:
        print(f"🎤 Using: {mic_name}")

    vad = webrtcvad.Vad(VAD_AGGRESSIVENESS)
    
    print("🎧 Listening... (Ctrl+C to stop)")
    
    # Clear output file
    Path(OUTPUT_FILE).write_text("")
    
    with sd.InputStream(
        device=mic_index,
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype=np.int16,
        blocksize=FRAME_SIZE
    ) as stream:
        
        audio_buffer = []
        speech_frames = 0
        silence_frames = 0
        recording = False
        
        while True:
            try:
                frames, _ = stream.read(FRAME_SIZE)
                frame_bytes = (frames * 32767).astype(np.int16).tobytes()
                
                is_speech = vad.is_speech(frame_bytes, SAMPLE_RATE)
                
                if is_speech:
                    if not recording:
                        print("🗣️  Speech detected...")
                        recording = True
                        audio_buffer = []
                        speech_frames = 0
                    
                    audio_buffer.append(frame_bytes)
                    speech_frames += 1
                    silence_frames = 0
                    
                elif recording:
                    audio_buffer.append(frame_bytes)
                    silence_frames += 1
                    
                    # End on silence
                    if silence_frames > (SILENCE_TIMEOUT_S * 1000 / FRAME_DURATION_MS):
                        if speech_frames >= MIN_SPEECH_FRAMES:
                            print(f"📝 Transcribing {len(audio_buffer)} frames...")
                            
                            audio_data = b''.join(audio_buffer)
                            text = transcribe_audio(audio_data)
                            
                            if text:
                                print(f"👤 You: {text}")
                                # Write to output file for browser injection
                                Path(OUTPUT_FILE).write_text(text)
                            else:
                                print("❌ Transcription failed")
                        
                        recording = False
                        print("🎧 Listening...")

            except KeyboardInterrupt:
                print("\n👋 Stopping...")
                break

if __name__ == "__main__":
    main()