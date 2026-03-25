#!/usr/bin/env bash
set -euo pipefail

# Installs a systemd path watcher that re-patches the Control UI
# whenever OpenClaw updates overwrite the index.html.

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
UNIT_DIR="$HOME/.config/systemd/user"

mkdir -p "$UNIT_DIR"

# Watch the control-ui directory for changes
cat > "$UNIT_DIR/voice-io-patch.path" <<EOF
[Unit]
Description=Watch OpenClaw Control UI for updates (voice-io)

[Path]
PathChanged=$HOME/.npm-global/lib/node_modules/openclaw/dist/control-ui/index.html
Unit=voice-io-patch.service

[Install]
WantedBy=default.target
EOF

cat > "$UNIT_DIR/voice-io-patch.service" <<EOF
[Unit]
Description=Re-patch OpenClaw Control UI with voice-io mic button

[Service]
Type=oneshot
ExecStartPre=/bin/sleep 2
ExecStart=/bin/bash $SKILL_DIR/scripts/patch-ui.sh
EOF

systemctl --user daemon-reload
systemctl --user enable --now voice-io-patch.path

echo "[voice-io] Watcher installed and active."
echo "[voice-io] The mic button will be auto-restored after OpenClaw updates."
