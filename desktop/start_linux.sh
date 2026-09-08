#!/usr/bin/env bash
# VoiceBot OS — Linux Desktop Launcher
# Opens the VoiceBot control center as a standalone Electron-style window
# using the system default browser in app-mode, or launches Chromium/Chrome
# in kiosk-ish app mode for a native-app feel.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# Resolve Python interpreter (prefer project venv, then system python3)
PYTHON="${ROOT_DIR}/.venv/bin/python"
if [ ! -x "$PYTHON" ]; then
  PYTHON="$(command -v python3 || command -v python || true)"
fi
if [ -z "$PYTHON" ]; then
  echo "ERROR: Python 3 not found. Install Python and create a venv."
  exit 1
fi

echo "=========================================="
echo "   VoiceBot OS — Desktop App (Linux)"
echo "=========================================="
echo "  Web console:  http://localhost:5000"
echo "  Press Ctrl+C to stop"
echo "=========================================="
echo ""

# Install deps if missing
if [ ! -f "${ROOT_DIR}/.venv/bin/python" ]; then
  echo "[setup] Creating virtual environment..."
  python3 -m venv "${ROOT_DIR}/.venv"
  ${ROOT_DIR}/.venv/bin/pip install --upgrade pip
  ${ROOT_DIR}/.venv/bin/pip install -r "${ROOT_DIR}/requirements.txt"
fi

# Start the server in the background
"$PYTHON" "${ROOT_DIR}/main.py" &
SERVER_PID=$!

# Wait a moment, then open in app mode
sleep 1.5
URL="http://localhost:5000"

# Try Chromium/Chrome app mode for a native windowed feel
if command -v chromium >/dev/null 2>&1; then
  chromium --app="$URL" --window-size=1400,900 --window-position=0,0 --user-data-dir="/tmp/voicebot-chromium" 2>/dev/null &
elif command -v google-chrome >/dev/null 2>&1; then
  google-chrome --app="$URL" --window-size=1400,900 --user-data-dir="/tmp/voicebot-chrome" 2>/dev/null &
elif command -v firefox >/dev/null 2>&1; then
  firefox --new-window "$URL" 2>/dev/null &
else
  xdg-open "$URL" 2>/dev/null || true
fi

# Wait for server to finish
wait "$SERVER_PID"
