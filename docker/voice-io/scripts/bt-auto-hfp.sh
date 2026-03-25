#!/usr/bin/env bash
# Auto-switch any BT audio device to HFP when it connects
# Run via: bluetoothctl monitor | bash bt-auto-hfp.sh
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"

while read -r line; do
  if echo "$line" | grep -q "Connected: yes"; then
    sleep 3  # Wait for PipeWire to register the card
    CARD=$(pactl list cards short 2>/dev/null | grep bluez_card | tail -1 | awk '{print $2}')
    if [[ -n "$CARD" ]]; then
      # Check if it has HFP
      if pactl list cards 2>/dev/null | sed -n "/${CARD}/,/^$/p" | grep -q "headset-head-unit-msbc"; then
        pactl set-card-profile "$CARD" headset-head-unit-msbc 2>/dev/null
        echo "[bt-auto-hfp] Switched $CARD to HFP mSBC"
      elif pactl list cards 2>/dev/null | sed -n "/${CARD}/,/^$/p" | grep -q "headset-head-unit"; then
        pactl set-card-profile "$CARD" headset-head-unit 2>/dev/null
        echo "[bt-auto-hfp] Switched $CARD to HFP"
      fi
    fi
  fi
done
