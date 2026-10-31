#!/usr/bin/env python3
"""Minimal Kokoro runner for the bake-off.

This bypasses Audiblez's EPUB/chapter layer and synthesizes a plain text file.
It is the fastest way to hear the Kokoro voice on the same excerpt as Edge TTS.
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import numpy as np
import soundfile as sf
from kokoro import KPipeline


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("text")
    parser.add_argument("--voice", default="em_alex")
    parser.add_argument("--output", default="out/kokoro_direct.wav")
    parser.add_argument("--speed", type=float, default=1.0)
    args = parser.parse_args()

    text = Path(args.text).read_text(encoding="utf-8")
    pipeline = KPipeline(lang_code=args.voice[0])

    segments = []
    started = time.time()
    for _, _, audio in pipeline(
        text, voice=args.voice, speed=args.speed, split_pattern=r"\n\n"
    ):
        if audio is None or len(audio) == 0:
            continue
        if hasattr(audio, "detach"):
            audio = audio.detach().cpu().numpy()
        segments.append(audio)

    elapsed = time.time() - started
    if not segments:
        raise SystemExit("No audio generated")

    audio = np.concatenate(segments)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    sf.write(output, audio, 24000)
    print(
        f"Wrote {output} in {elapsed:.2f}s; "
        f"samples={len(audio)}; seconds={len(audio) / 24000:.2f}"
    )


if __name__ == "__main__":
    main()
