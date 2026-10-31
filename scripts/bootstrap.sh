#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV="${AUDIOL_VENV:-$HOME/.venvs/audiol}"

python3 -m venv "$VENV"
"$VENV/bin/python" -m pip install --upgrade pip
"$VENV/bin/python" -m pip install torch --index-url https://download.pytorch.org/whl/cpu
"$VENV/bin/python" -m pip install audiblez edge-tts

echo "Venv: $VENV"
echo "Siguiente: source $ROOT/scripts/env.sh"
