#!/usr/bin/env python3
"""Minimal Kokoro runner for the bake-off.

This bypasses Audiblez's EPUB/chapter layer and synthesizes a plain text file.
It is the fastest way to hear the Kokoro voice on the same excerpt as Edge TTS.
"""

from __future__ import annotations

import argparse
import re
import time
from pathlib import Path

import numpy as np
import soundfile as sf
from kokoro import KPipeline


def split_chunks(text: str, max_chars: int = 400) -> list[str]:
    """Split into chunks small enough for Kokoro's non-English G2P.

    Kokoro warns that its long-text chunking is not implemented for languages
    other than English; paragraphs longer than ~510 phonemes are truncated.
    """
    paragraphs = [re.sub(r"\s+", " ", p).strip() for p in text.split("\n\n")]
    paragraphs = [p for p in paragraphs if p]
    chunks: list[str] = []
    for paragraph in paragraphs:
        for sentence in re.split(r"(?<=[.!?…])\s+", paragraph):
            sentence = sentence.strip()
            if not sentence:
                continue
            if len(sentence) <= max_chars:
                chunks.append(sentence)
                continue
            buffer = ""
            for part in re.split(r"(?<=[,;:])\s+", sentence):
                candidate = f"{buffer} {part}".strip()
                if len(candidate) <= max_chars:
                    buffer = candidate
                else:
                    if buffer:
                        chunks.append(buffer)
                    buffer = part
            if buffer:
                chunks.append(buffer)
    return chunks


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("text")
    parser.add_argument("--voice", default="em_alex")
    parser.add_argument("--output", default="out/kokoro_direct.wav")
    parser.add_argument("--speed", type=float, default=1.0)
    args = parser.parse_args()

    text = Path(args.text).read_text(encoding="utf-8")
    chunks = split_chunks(text)
    pipeline = KPipeline(lang_code=args.voice[0])

    segments = []
    started = time.time()
    for index, chunk in enumerate(chunks, start=1):
        for _, _, audio in pipeline(
            chunk, voice=args.voice, speed=args.speed
        ):
            if audio is None or len(audio) == 0:
                continue
            if hasattr(audio, "detach"):
                audio = audio.detach().cpu().numpy()
            segments.append(audio)
        if index % 10 == 0 or index == len(chunks):
            print(f"chunk {index}/{len(chunks)}", flush=True)

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
