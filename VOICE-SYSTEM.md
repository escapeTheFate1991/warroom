# Voice System — Setup & Troubleshooting Guide

Last updated: 2026-03-01

## Architecture

```
Browser (localhost:3300)
  ├── getUserMedia → captures mic audio from BT headset
  ├── VAD (Voice Activity Detection) → detects speech, records utterance
  ├── POST /api/voice/transcribe → sends audio to backend
  │     └── Backend converts to WAV → sends raw bytes over TCP to Whisper (Brain 1, port 18796)
  ├── WebSocket /api/chat/ws → sends transcribed text to OpenClaw gateway
  └── POST /api/voice/tts → gets audio response, plays through BT headset
        └── Backend runs edge-tts → returns MP3 stream
```

### Key Components

| Component | Location | Runs On |
|-----------|----------|---------|
| ChatPanel (frontend) | `frontend/src/components/chat/ChatPanel.tsx` | Docker container (port 3300) |
| Voice API (backend) | `backend/app/api/voice.py` | Docker container (port 8300, host network) |
| Whisper STT server | `~/.openclaw/workspace/skills/voice-io/scripts/transcribe_server.py` | Brain 1 host (port 18796) |
| BT auto-discover | `~/.openclaw/workspace/skills/voice-io/scripts/bt-scan.sh` | Brain 1 host |

## Prerequisites

1. **Bluetooth headset with mic** (e.g., Stargazer) paired and connected
2. **Whisper server** running on Brain 1 (port 18796)
3. **edge-tts** installed in backend container (included in Dockerfile)
4. **ffmpeg** installed in backend container (included in Dockerfile)

## Bluetooth Setup (CRITICAL)

This desktop has **no built-in microphone**. The only mic is the BT headset. The browser's `getUserMedia` requires the BT headset to be in **HFP (Hands-Free Profile)** mode — A2DP (hi-fi) has no mic.

### Auto-discover & switch profile

```bash
# Check what's connected (no hardcoded MACs)
bash ~/.openclaw/workspace/skills/voice-io/scripts/bt-scan.sh info
# Output: {"connected":true,"name":"Stargazer","mac":"...","profile":"a2dp-sink","mic_active":false,...}

# Switch to HFP (enables mic, lower audio quality)
bash ~/.openclaw/workspace/skills/voice-io/scripts/bt-scan.sh hfp

# Switch back to A2DP (hi-fi audio, no mic)
bash ~/.openclaw/workspace/skills/voice-io/scripts/bt-scan.sh a2dp
```

### If mic captures zero audio (RMS: 0, Peak: 0)

The SCO audio transport didn't establish. This happens when you switch profiles without reconnecting:

```bash
# Full reconnect (discovers MAC automatically)
INFO=$(bash ~/.openclaw/workspace/skills/voice-io/scripts/bt-scan.sh info)
MAC=$(echo $INFO | python3 -c "import sys,json; print(json.load(sys.stdin)['mac'])")
bluetoothctl disconnect $MAC
sleep 2
bluetoothctl connect $MAC
sleep 3
bash ~/.openclaw/workspace/skills/voice-io/scripts/bt-scan.sh hfp
sleep 1
pactl set-source-volume $(pactl list sources short | grep bluez_input | awk '{print $2}') 100%
```

### If mic volume is near zero

After switching to HFP, mic volume may default to 8%. Always set it:

```bash
pactl set-source-volume $(pactl list sources short | grep bluez_input | awk '{print $2}') 100%
```

## Docker Environment Variables

### Backend (`docker-compose.yml`)

These MUST be set or voice endpoints will fail:

```yaml
backend:
  environment:
    WHISPER_HOST: "10.0.0.1"    # Brain 1 IP (where Whisper runs)
    WHISPER_PORT: "18796"        # Whisper TCP port
```

**Why:** The backend runs in a Docker container. `127.0.0.1` inside the container is the container itself, not the host. Whisper runs on the host (Brain 1), so the backend must use the host's actual IP.

This was missing from `docker-compose.yml` (only existed in `docker-compose.brain2.yml`) and caused transcription to silently fail.

### Frontend build args

```yaml
frontend:
  build:
    args:
      NEXT_PUBLIC_API_URL: http://localhost:8300   # Baked at build time
      NEXT_PUBLIC_WS_URL: ws://localhost:18789     # Baked at build time
```

**Critical:** These are baked into the JS bundle at `next build` time. Changing them requires `docker compose build --no-cache frontend`. They are NOT read at runtime.

## Frontend Voice Features

### Two buttons in ChatPanel:

1. **Mic button** (push-to-talk): Hold to record, release to transcribe & send
2. **Waveform button** (conversation mode): Always-listening with VAD, auto-records speech, transcribes, sends, speaks response via TTS

### Conversation mode flow:

1. Click waveform → `startConversationMode()` → `getUserMedia` captures BT mic
2. VAD loop (`requestAnimationFrame`) monitors audio levels
3. Speech detected (avg frequency > `SILENCE_THRESHOLD=15`) → starts `MediaRecorder`
4. 1.5s silence → stops recording → sends to `/api/voice/transcribe`
5. Transcribed text sent as chat message via WebSocket
6. Assistant response triggers `speakText()` → fetches TTS audio → plays through headset
7. Audio queue ensures sequential playback (no overlapping)
8. Click End → `stopConversationMode()` → kills VAD, audio, mic, queue immediately

### Key implementation details:

- **`conversationActiveRef` (ref, not state)** — Used in VAD loop and async callbacks so they see the latest value. State would be stale in the closure.
- **Audio queue** — `audioQueueRef` + `audioPlayingRef` + `processAudioQueue` (while loop). Prevents overlapping TTS playback.
- **Triple guard on stop** — `speakText` checks `conversationActiveRef` before fetch, after fetch, and after blob decode. Hitting End bails at any point.
- **`currentAudioRef`** — Tracks the playing `Audio` element so stop can `pause()` + clear it.
- **Stop kills everything** — queue cleared, playing flag reset, VAD cancelled, audio paused, mic tracks stopped, audio context closed.

## Backend Voice Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/voice/transcribe` | POST | Receives audio (webm/wav), converts to WAV via ffmpeg, sends to Whisper over TCP |
| `/api/voice/tts` | POST | Generates speech via edge-tts, returns MP3 stream |
| `/api/voice/tts/play` | POST | Generates speech and plays on host speaker (via play-audio.sh) |
| `/api/voice/bt/status` | GET | Returns BT device info (auto-discover, no hardcoded MAC) |
| `/api/voice/bt/hfp` | POST | Switches BT to HFP mode with full reconnect |
| `/api/voice/bt/a2dp` | POST | Switches BT back to A2DP |

**Note:** BT endpoints (`/bt/*`) call host commands (`bluetoothctl`, `pactl`) via `bt-scan.sh`. These only work when the backend container has access to the host's D-Bus and PulseAudio (host network mode helps but may still need volume mounts for full BT control).

## Whisper TCP Protocol

The Whisper server (`transcribe_server.py`) listens on TCP port 18796:

- **Send:** 4-byte big-endian length prefix + raw WAV bytes
- **Receive:** JSON line: `{"text": "transcribed text", "language": "en"}\n`

## Common Issues & Fixes

### "Buttons don't work" (no response on click)
- **Cause:** No mic available to browser. BT is in A2DP mode (no mic) or disconnected.
- **Fix:** Switch to HFP: `bash bt-scan.sh hfp`

### "Buttons work but no transcription"
- **Cause:** `WHISPER_HOST`/`WHISPER_PORT` not set in docker-compose.yml, or Whisper server not running.
- **Fix:** Add env vars, restart backend. Verify Whisper: `ss -tlnp | grep 18796`

### "Audio plays on top of itself"
- **Cause:** Audio queue not in the Docker image. Frontend needs rebuild after code changes.
- **Fix:** `docker compose up -d --build frontend`

### "Audio tone in headphones, mic not picking up"
- **Cause:** HFP SCO transport not established. Profile was switched without reconnecting BT.
- **Fix:** Full disconnect/reconnect cycle (see BT section above), then set mic volume to 100%.

### "Audio plays 3x / multiple responses spoken at once"
- **Cause:** Gateway broadcasts events for ALL sessions to operator connections. The War Room relay was forwarding everything — so responses from OpenClaw webchat, cron jobs, or other sessions all triggered TTS.
- **Fix:** Session filter in `chat.py` `forward_from_gateway` — checks `payload.sessionKey` and skips events not matching the active War Room session key.

### "Keeps talking after hitting End"
- **Cause:** TTS fetch was in-flight when stop was pressed. Without guards, it plays after completion.
- **Fix:** Triple guard pattern in `speakText` (check ref before fetch, after fetch, after blob).

### "Frontend changes not reflected"
- **Cause:** Docker image is stale. Next.js bakes code at build time.
- **Fix:** `docker compose up -d --build frontend` — always rebuild after code changes.

## Files Modified (2026-03-01 session)

| File | Change |
|------|--------|
| `docker-compose.yml` | Added `WHISPER_HOST` and `WHISPER_PORT` env vars |
| `backend/app/api/voice.py` | Added BT endpoints (`/bt/status`, `/bt/hfp`, `/bt/a2dp`) |
| `frontend/src/components/chat/ChatPanel.tsx` | Fixed audio queue (while loop), triple guard on stop, sequential playback |
| `~/.openclaw/workspace/skills/voice-io/scripts/bt-scan.sh` | NEW — auto-discover BT device, switch profiles, no hardcoded MACs |
| `~/.openclaw/workspace/skills/voice-io/scripts/bt-profile.sh` | Updated to delegate to bt-scan.sh |
