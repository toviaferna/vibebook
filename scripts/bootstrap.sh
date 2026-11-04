#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if ! command -v uv >/dev/null 2>&1; then
  echo "uv no está instalado."
  echo "Instálalo con: curl -LsSf https://astral.sh/uv/install.sh | sh"
  exit 1
fi

uv sync
echo "Listo. Ejecuta: uv run vibebook --help"
