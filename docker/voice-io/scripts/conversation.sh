#!/usr/bin/env bash
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VENV_PY="$SKILL_DIR/.venv/bin/python3"
PIDFILE="/tmp/voice-io-conversation.pid"
LOGFILE="/tmp/voice-io-conversation.log"

export XDG_RUNTIME_DIR="/run/user/$(id -u)"

case "${1:-start}" in
  start)
    if [[ -f "$PIDFILE" ]] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
      echo "[voice-io] Conversation mode already running (PID $(cat "$PIDFILE"))"
      exit 0
    fi
    echo "[voice-io] Starting conversation mode (always listening)..."
    nohup "$VENV_PY" "$SKILL_DIR/scripts/conversation.py" > "$LOGFILE" 2>&1 &
    echo $! > "$PIDFILE"
    echo "[voice-io] Listening (PID $!) — say 'Friday' to talk"
    echo "[voice-io] Log: $LOGFILE"
    ;;
  stop)
    if [[ -f "$PIDFILE" ]]; then
      kill "$(cat "$PIDFILE")" 2>/dev/null && echo "[voice-io] Conversation stopped." || echo "[voice-io] Not running."
      rm -f "$PIDFILE"
    else
      echo "[voice-io] Not running."
    fi
    ;;
  restart)
    "$0" stop
    sleep 1
    "$0" start
    ;;
  status)
    if [[ -f "$PIDFILE" ]] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
      echo "[voice-io] Conversation mode running (PID $(cat "$PIDFILE"))"
    else
      echo "[voice-io] Not running."
    fi
    ;;
  log)
    tail -f "$LOGFILE"
    ;;
  *)
    echo "Usage: $0 {start|stop|restart|status|log}"
    exit 1
    ;;
esac
