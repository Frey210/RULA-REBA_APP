#!/usr/bin/env bash
set -euo pipefail
bundle_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo="$HOME/RULA-REBA_Detection_HailoAI"
cd "$repo"
test -f "$bundle_dir/ergosight-edge.bundle"
.venv/bin/python - <<'PY'
import json
from pathlib import Path
import httpx
state = json.loads(Path('data/edge_state.json').read_text())
with httpx.Client(trust_env=False, timeout=5) as client:
    response = client.get('http://127.0.0.1:8765/detection/status',
                          headers={'Authorization': 'Bearer ' + state.get('device_token', '')})
    response.raise_for_status()
    if response.json().get('running'):
        raise SystemExit('Stop the active assessment before updating the Pi.')
PY
# Preserve credentials, UUID and the active network configuration.
umask 077
backup="$HOME/ergosight-before-024-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$backup"
cp .env data/edge_state.json "$backup/"
git diff --quiet HEAD || { printf 'Tracked local changes found; update stopped.\n' >&2; exit 1; }
git fetch "$bundle_dir/ergosight-edge.bundle" main
git merge --ff-only FETCH_HEAD
sudo bash systemd/install-network-modes.sh
sudo systemctl restart ergoquipt-edge-agent
systemctl is-active ergoquipt-edge-agent
printf 'Update installed. Active Ethernet mode preserved. Run Scan LAN in desktop 0.2.4.\n'
