#!/usr/bin/env bash
# Source this file before running the audio engines.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export ROOT
export PATH="$ROOT/.tools/bin:$PATH"
export LD_LIBRARY_PATH="$ROOT/.tools/espeak-root/usr/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export ESPEAK_DATA_PATH="$ROOT/.tools/espeak-root/usr/lib/x86_64-linux-gnu/espeak-ng-data"
export ESPEAK_LIBRARY="$ROOT/.tools/espeak-root/usr/lib/x86_64-linux-gnu/libespeak-ng.so.1"
export PULSE_SERVER=unix:/tmp/no-pulse
