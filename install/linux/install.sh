#!/bin/bash
# Install the Apple TV bridge on Linux or Raspberry Pi (including CompanionPi):
# Python environment, pairing, and a systemd service so the bridge starts at boot.
# Run as your normal user (it uses sudo for the service):  bash install/linux/install.sh
set -euo pipefail

REPO="$(cd "$(dirname "$0")/../.." && pwd)"
VENV="$REPO/.venv"
SERVICE="appletv-bridge"
RUN_USER="$(id -un)"

if [ "$RUN_USER" = "root" ]; then
  echo "Run this as a normal user, not root (the pairing key is saved in that user's home folder)."
  exit 1
fi

if ! python3 -c "import venv, ensurepip" 2>/dev/null; then
  echo "==> Installing python3-venv"
  sudo apt-get update && sudo apt-get install -y python3-venv python3-pip
fi

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

echo "==> Installing systemd service $SERVICE"
sudo tee "/etc/systemd/system/$SERVICE.service" >/dev/null <<EOF
[Unit]
Description=Apple TV bridge for Bitfocus Companion
Wants=network-online.target
After=network-online.target

[Service]
User=$RUN_USER
WorkingDirectory=$REPO
ExecStart=$VENV/bin/python $REPO/bridge.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable --now "$SERVICE"

echo "==> Checking the bridge"
for _ in $(seq 1 20); do
  curl -s http://127.0.0.1:8765/ >/dev/null 2>&1 && break
  sleep 0.5
done
if curl -s http://127.0.0.1:8765/ >/dev/null 2>&1; then
  echo "Bridge is running at http://127.0.0.1:8765  (log: journalctl -u $SERVICE -f)"
else
  echo "The bridge didn't answer yet. Check: journalctl -u $SERVICE -n 50"
fi
