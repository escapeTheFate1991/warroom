---
name: voice-io
description: Voice input/output via Bluetooth speaker (Bose Flex SoundLink). Adds a microphone button to the webchat Control UI for push-to-talk, transcribes speech locally with faster-whisper, and plays TTS responses through the Bose speaker. Self-heals UI injection after OpenClaw updates.
metadata:
  openclaw:
    emoji: "🎙️"
    requires:
      bins: ["python3", "ffmpeg"]
---

# Voice I/O Skill

Voice input (STT) and output (TTS playback) through a Bluetooth speaker/mic.

## Components

1. **Mic Button** — Injected into the webchat Control UI (push-to-talk)
2. **Voice Server** — Local Python HTTP server for audio transcription
3. **Audio Playback** — Routes TTS output to the Bluetooth speaker via PipeWire
4. **UI Patcher** — Re-injects mic button after OpenClaw updates

## Setup (one-time)

```bash
# Install system dependencies
sudo apt install -y pulseaudio-utils python3-pip ffmpeg

# Install Python deps
pip3 install faster-whisper flask flask-cors

# Patch the webchat UI to add mic button
bash {baseDir}/scripts/patch-ui.sh

# Start the voice server (runs on port 18793)
bash {baseDir}/scripts/voice-server.sh start
```

## Usage

### Voice Input (browser mic → text)
- Click the 🎙️ button in webchat (above Send)
- Speak — click again to stop
- Audio is sent to the local voice server, transcribed, and inserted as a chat message

### Voice Output (TTS → Bose speaker)
When using the `tts` tool, play the result through the Bose speaker:
```bash
bash {baseDir}/scripts/play-audio.sh /path/to/audio.mp3
```

### After OpenClaw Updates
The UI patch is removed by updates. Re-apply:
```bash
bash {baseDir}/scripts/patch-ui.sh
```
Or set up the systemd path watcher for auto-healing:
```bash
bash {baseDir}/scripts/install-watcher.sh
```

## Audio Device Management
```bash
# List sinks (speakers)
pactl list short sinks

# List sources (mics)
pactl list short sources

# The voice server auto-detects the Bose device. Override with:
export VOICE_IO_SINK="bluez_output.AC_BF_71_FB_DC_8D.1"
export VOICE_IO_SOURCE="bluez_input.AC_BF_71_FB_DC_8D.0"
```

## Architecture

```
Browser (mic button)
  ↓ audio/webm POST
Voice Server (:18793/transcribe)
  ↓ faster-whisper (local, no API key)
  ↓ returns { text: "..." }
Browser inserts text into chat input
  ↓ user clicks Send (or auto-send)

TTS tool → audio file
  ↓ play-audio.sh
PipeWire → Bose Flex SoundLink
```
