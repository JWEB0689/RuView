#!/usr/bin/env bash
# RuView ESP32 CSI Sensing Server Launcher
set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BINARY="${REPO_ROOT}/v2/target/release/sensing-server"
DEFAULT_MODEL="${REPO_ROOT}/data/models/huggingface-model.rvf"
if [ ! -f "$DEFAULT_MODEL" ]; then
    DEFAULT_MODEL="${REPO_ROOT}/data/models/wifi-densepose-mmfi-pose.rvf"
fi
MODEL="${RUVIEW_MODEL:-$DEFAULT_MODEL}"

# Stop any existing sensing-server process using ports 8081, 5005, or 8765
if lsof -i :8081 -i :5005 -i :8765 >/dev/null 2>&1; then
    echo "[!] Existing sensing-server process detected on ports 8081/5005/8765. Stopping it..."
    pkill -f "sensing-server" || true
    sleep 1
fi

# Build release binary if missing
if [ ! -f "$BINARY" ]; then
    echo "[*] Building release binary..."
    cargo build --release --manifest-path "${REPO_ROOT}/v2/Cargo.toml" -p wifi-densepose-sensing-server
fi

echo "[*] Starting RuView Sensing Server (Release Mode)..."
echo "[*] Web UI:          http://localhost:8081/ui/index.html"
echo "[*] Observatory HUD: http://localhost:8081/ui/observatory.html"
echo "[*] Vitals API:      http://localhost:8081/api/v1/vital-signs"
echo "[*] UDP Listening:   0.0.0.0:5005 (ESP32 CSI)"
echo ""

exec "$BINARY" \
  --http-port 8081 \
  --udp-port 5005 \
  --udp-bind 0.0.0.0 \
  --udp-insecure-lan \
  --source esp32 \
  --load-rvf "$MODEL" \
  --model "$MODEL" "$@"
