#!/usr/bin/env bash
set -euo pipefail

# Patches the OpenClaw Control UI to include the voice-io mic button.
# Safe to run multiple times (idempotent).

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
JS_SOURCE="$SKILL_DIR/assets/voice-io.js"

# Find the control-ui index.html
UI_HTML=""
for candidate in \
  "$HOME/.npm-global/lib/node_modules/openclaw/dist/control-ui/index.html" \
  "/usr/local/lib/node_modules/openclaw/dist/control-ui/index.html" \
  "/usr/lib/node_modules/openclaw/dist/control-ui/index.html"; do
  if [[ -f "$candidate" ]]; then
    UI_HTML="$candidate"
    break
  fi
done

if [[ -z "$UI_HTML" ]]; then
  echo "[voice-io] ERROR: Could not find control-ui/index.html" >&2
  echo "[voice-io] Searched: ~/.npm-global, /usr/local/lib, /usr/lib" >&2
  exit 1
fi

UI_DIR="$(dirname "$UI_HTML")"
JS_DEST="$UI_DIR/assets/voice-io.js"
MARKER="voice-io.js"

# Copy JS file
cp "$JS_SOURCE" "$JS_DEST"
echo "[voice-io] Copied voice-io.js → $JS_DEST"

# Check if already patched
if grep -q "$MARKER" "$UI_HTML"; then
  echo "[voice-io] Already patched. Updating JS only."
  exit 0
fi

# Inject script tag before </body>
sed -i 's|</body>|<script src="./assets/voice-io.js"></script>\n</body>|' "$UI_HTML"
echo "[voice-io] Patched $UI_HTML ✓"
echo "[voice-io] Reload the Control UI in your browser to see the mic button."
