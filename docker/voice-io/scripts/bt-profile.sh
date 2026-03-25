#!/usr/bin/env bash
# bt-profile.sh — Wrapper around bt-scan.sh for backward compatibility
# No hardcoded MACs — delegates to bt-scan.sh which auto-discovers
DIR="$(cd "$(dirname "$0")" && pwd)"
exec "$DIR/bt-scan.sh" "${1:-status}"
