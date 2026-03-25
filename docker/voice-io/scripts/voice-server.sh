#!/usr/bin/env bash
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PIDFILE="/tmp/voice-io-server.pid"
LOGFILE="/tmp/voice-io-server.log"

export XDG_RUNTIME_DIR="/run/user/$(id -u)"

case "${1:-start}" in
  start)
    if [[ -f "$PIDFILE" ]] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
      echo "[voice-io] Server already running (PID $(cat "$PIDFILE"))"
      exit 0
    fi
    echo "[voice-io] Starting voice server..."
    VENV_PY="$SKILL_DIR/.venv/bin/python3"
    if [[ ! -f "$VENV_PY" ]]; then
      echo "[voice-io] ERROR: venv not found. Run: python3 -m venv $SKILL_DIR/.venv && $SKILL_DIR/.venv/bin/pip install faster-whisper flask flask-cors" >&2
      exit 1
    fi
    nohup "$VENV_PY" "$SKILL_DIR/scripts/voice_server.py" > "$LOGFILE" 2>&1 &
    echo $! > "$PIDFILE"
    echo "[voice-io] Server started (PID $!) — log: $LOGFILE"
    ;;
  stop)
    if [[ -f "$PIDFILE" ]]; then
      kill "$(cat "$PIDFILE")" 2>/dev/null && echo "[voice-io] Server stopped." || echo "[voice-io] Not running."
      rm -f "$PIDFILE"
    else
      echo "[voice-io] No PID file found."
    fi
    ;;
  restart)
    "$0" stop
    sleep 1
    "$0" start
    ;;
  status)
    if [[ -f "$PIDFILE" ]] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
      echo "[voice-io] Running (PID $(cat "$PIDFILE"))"
      curl -s http://127.0.0.1:18792/health | python3 -m json.tool 2>/dev/null || true
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
