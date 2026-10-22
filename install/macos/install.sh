#!/bin/bash
# Install the Apple TV bridge on macOS: Python environment, pairing, and a LaunchAgent
# so the bridge starts at login.  Run from anywhere:  bash install/macos/install.sh
set -euo pipefail

REPO="$(cd "$(dirname "$0")/../.." && pwd)"
VENV="$REPO/.venv"
LABEL="com.companion.appletv-bridge"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

command -v python3 >/dev/null || { echo "python3 not found. Install it from https://www.python.org/downloads/macos/"; exit 1; }

echo "==> Creating Python environment in $VENV"
python3 -m venv "$VENV"
"$VENV/bin/pip" install --quiet --upgrade pip
"$VENV/bin/pip" install --quiet -r "$REPO/requirements.txt"

if [ ! -f "$REPO/config.json" ]; then
  echo "==> Pairing with your Apple TV"
  "$VENV/bin/python" "$REPO/pair.py"
else
  echo "==> config.json found, skipping pairing (delete it and re-run to pair again)"
fi

echo "==> Installing LaunchAgent $PLIST"
mkdir -p "$HOME/Library/LaunchAgents"
cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>$LABEL</string>
    <key>ProgramArguments</key>
    <array>
        <string>$VENV/bin/python</string>
        <string>$REPO/bridge.py</string>
    </array>
    <key>WorkingDirectory</key><string>$REPO</string>
    <key>RunAtLoad</key><true/>
    <key>KeepAlive</key><true/>
    <key>StandardOutPath</key><string>$REPO/bridge.log</string>
    <key>StandardErrorPath</key><string>$REPO/bridge.log</string>
</dict>
</plist>
EOF
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"

echo "==> Checking the bridge"
for _ in $(seq 1 20); do
  curl -s http://127.0.0.1:8765/ >/dev/null 2>&1 && break
  sleep 0.5
done
if curl -s http://127.0.0.1:8765/ >/dev/null 2>&1; then
  echo "Bridge is running at http://127.0.0.1:8765  (log: $REPO/bridge.log)"
  echo "If macOS asks to allow Python to find devices on your local network, click Allow."
else
  echo "The bridge didn't answer yet. Check $REPO/bridge.log"
fi
