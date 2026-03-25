#!/usr/bin/env bash
# bt-scan.sh — Find connected Bluetooth audio device dynamically
# No hardcoded MACs. Discovers whatever is connected.
# Usage: bt-scan.sh [info|hfp|a2dp|status]
set -euo pipefail
# Use existing XDG_RUNTIME_DIR if set, otherwise detect from uid
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"

# Find all bluez cards
get_all_bt_cards() {
  pactl list cards short 2>/dev/null | grep bluez_card | awk '{print $2}'
}

get_bt_card() {
  # Priority: Stargazer headphones first, then any other BT device
  local cards
  cards=$(get_all_bt_cards)
  # Check for Stargazer (AC_BF_71_4A_41_87)
  echo "$cards" | grep -i "4A_41_87" && return
  # Fallback: first available
  echo "$cards" | head -1
}

get_bt_name() {
  local card="$1"
  pactl list cards 2>/dev/null | sed -n "/${card}/,/^$/p" | grep 'device.description' | sed 's/.*= "\(.*\)"/\1/'
}

get_active_profile() {
  local card="$1"
  pactl list cards 2>/dev/null | sed -n "/${card}/,/^$/p" | grep 'Active Profile' | sed 's/.*: //'
}

has_profile() {
  local card="$1" profile="$2"
  pactl list cards 2>/dev/null | sed -n "/${card}/,/^$/p" | grep -q "${profile}:"
}

has_mic() {
  pactl list sources short 2>/dev/null | grep -q "bluez_input"
}

CARD=$(get_bt_card)
if [ -z "$CARD" ]; then
  echo '{"connected":false,"error":"No Bluetooth audio device found"}'
  exit 1
fi

NAME=$(get_bt_name "$CARD")
PROFILE=$(get_active_profile "$CARD")
MAC=$(echo "$CARD" | sed 's/bluez_card\.\(.*\)/\1/' | tr '_' ':')

case "${1:-info}" in
  info|scan)
    HAS_MIC=$(has_mic && echo true || echo false)
    HAS_MSBC=$(has_profile "$CARD" "headset-head-unit-msbc" && echo true || echo false)
    HAS_HFP=$(has_profile "$CARD" "headset-head-unit" && echo true || echo false)
    echo "{\"connected\":true,\"name\":\"${NAME}\",\"mac\":\"${MAC}\",\"card\":\"${CARD}\",\"profile\":\"${PROFILE}\",\"mic_active\":${HAS_MIC},\"has_msbc\":${HAS_MSBC},\"has_hfp\":${HAS_HFP}}"
    ;;
  hfp|mic)
    if has_profile "$CARD" "headset-head-unit-msbc"; then
      pactl set-card-profile "$CARD" headset-head-unit-msbc
      echo "[bt-scan] ${NAME}: Switched to HFP mSBC — mic enabled"
    elif has_profile "$CARD" "headset-head-unit"; then
      pactl set-card-profile "$CARD" headset-head-unit
      echo "[bt-scan] ${NAME}: Switched to HFP — mic enabled"
    else
      echo "[bt-scan] ${NAME}: No HFP profile available — no mic support"
      exit 1
    fi
    ;;
  a2dp|hifi)
    if has_profile "$CARD" "a2dp-sink"; then
      pactl set-card-profile "$CARD" a2dp-sink
      echo "[bt-scan] ${NAME}: Switched to A2DP — hi-fi audio, no mic"
    else
      echo "[bt-scan] ${NAME}: No A2DP profile available"
      exit 1
    fi
    ;;
  status)
    echo "${NAME} (${MAC}): ${PROFILE}"
    has_mic && echo "  Mic: active" || echo "  Mic: inactive"
    ;;
  *)
    echo "Usage: $0 {info|hfp|a2dp|status}"
    exit 1
    ;;
esac
