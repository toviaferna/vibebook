#!/usr/bin/env bash
set -euo pipefail

mkdir -p "$(dirname "$0")/../samples"
curl -sL --max-time 60 \
  -o "$(dirname "$0")/../samples/lazarillo.epub" \
  "https://www.gutenberg.org/ebooks/320.epub.noimages"
