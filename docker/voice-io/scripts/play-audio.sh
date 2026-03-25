#!/usr/bin/env bash
set -euo pipefail

# Play audio through any connected Bluetooth speaker via PipeWire/PulseAudio
# Usage: play-audio.sh /path/to/audio.mp3

AUDIO_FILE="${1:?Usage: play-audio.sh <audio-file>}"

export XDG_RUNTIME_DIR="/run/user/$(id -u)"

# Find any connected Bluetooth sink (or use override)
SINK="${VOICE_IO_SINK:-}"
if [[ -z "$SINK" ]]; then
  # Prefer specific MAC if set, otherwise any bluez sink
  BT_MAC_US="${BOSE_MAC:-}"
  BT_MAC_US="${BT_MAC_US//:/\_}"
  if [[ -n "$BT_MAC_US" ]]; then
    SINK=$(pactl list short sinks 2>/dev/null | grep "$BT_MAC_US" | awk '{print $2}' | head -1)
  fi
  if [[ -z "$SINK" ]]; then
    SINK=$(pactl list short sinks 2>/dev/null | grep "bluez_output" | awk '{print $2}' | head -1)
  fi
fi

if [[ -z "$SINK" ]]; then
  echo "[voice-io] Warning: No Bluetooth speaker found, using default sink" >&2
fi

# Convert to WAV and play
TMP_WAV=$(mktemp /tmp/voice-io-XXXX.wav)
trap 'rm -f "$TMP_WAV"' EXIT

ffmpeg -y -i "$AUDIO_FILE" -ar 44100 -ac 2 -f wav "$TMP_WAV" 2>/dev/null

if [[ -n "$SINK" ]]; then
  paplay --device="$SINK" "$TMP_WAV"
else
  paplay "$TMP_WAV"
fi
