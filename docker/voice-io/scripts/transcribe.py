#!/usr/bin/env python3
"""Lightweight transcription — loads model, transcribes one file, exits.
No persistent server. Memory freed on exit."""

import sys
import json
import os

def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: transcribe.py <audio-file>"}))
        sys.exit(1)

    audio_path = sys.argv[1]
    if not os.path.isfile(audio_path):
        print(json.dumps({"error": f"File not found: {audio_path}"}))
        sys.exit(1)

    model_size = os.environ.get("WHISPER_MODEL", "tiny.en")  # tiny.en = ~75MB RAM
    device = os.environ.get("WHISPER_DEVICE", "cpu")

    from faster_whisper import WhisperModel
    model = WhisperModel(model_size, device=device, compute_type="int8")
    segments, info = model.transcribe(audio_path, beam_size=3, language="en")
    text = " ".join(seg.text.strip() for seg in segments).strip()

    print(json.dumps({"text": text, "language": info.language, "duration": round(info.duration, 2)}))

if __name__ == "__main__":
    main()
