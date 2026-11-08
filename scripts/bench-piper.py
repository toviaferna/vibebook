"""Benchmark local Piper against the >= 2x real-time target.

Usage:
    VIBEBOOK_PIPER_BIN=/path/to/piper \
    VIBEBOOK_PIPER_VOICES=/path/to/voices \
    uv run python scripts/bench-piper.py
"""

from __future__ import annotations

import sys
import time
import wave
from pathlib import Path
from tempfile import TemporaryDirectory

from audiol.tts.piper import PiperProvider, resolve_piper_binary
from audiol.tts.piper_voices import DEFAULT_PIPER_VOICE, resolve_piper_model

TEXT = (
    "En un lugar de la Mancha, de cuyo nombre no quiero acordarme, no ha mucho tiempo "
    "que vivía un hidalgo de los de lanza en astillero, adarga antigua, rocín flaco y "
    "galgo corredor. Una olla de algo más vaca que carnero, salpicón las más noches, "
    "duelos y quebrantos los sábados, lentejas los viernes, algún palomino de añadidura "
    "los domingos, consumían las tres partes de su hacienda."
)
TARGET_X_REAL_TIME = 2.0


def wav_seconds(path: Path) -> float:
    with wave.open(str(path), "rb") as audio:
        return audio.getnframes() / audio.getframerate()


def main() -> int:
    if resolve_piper_binary(optional=True) is None:
        print("Piper binary not found; set VIBEBOOK_PIPER_BIN.", file=sys.stderr)
        return 1
    if resolve_piper_model(DEFAULT_PIPER_VOICE, optional=True) is None:
        print("Piper voice not installed; run `vibebook piper download`.", file=sys.stderr)
        return 1

    provider = PiperProvider()
    with TemporaryDirectory(prefix="vibebook-piper-bench-") as temporary:
        output = Path(temporary) / "bench.wav"
        started = time.perf_counter()
        result = provider.synthesize(TEXT, DEFAULT_PIPER_VOICE, output, rate="-10%")
        elapsed = time.perf_counter() - started
        audio_seconds = wav_seconds(result.path)

    ratio = audio_seconds / elapsed if elapsed else 0.0
    print(
        f"chars={len(TEXT)} elapsed={elapsed:.2f}s audio={audio_seconds:.2f}s "
        f"speed={ratio:.2f}x real-time"
    )
    return 0 if ratio >= TARGET_X_REAL_TIME else 1


if __name__ == "__main__":
    raise SystemExit(main())
