#!/usr/bin/env python3
"""Measure an audio sample against its source text."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from audiol.tools import require_ffmpeg


def probe(path: Path) -> dict:
    _, ffprobe = require_ffmpeg()
    output = subprocess.check_output(
        [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "format=duration,size,bit_rate",
            "-show_entries",
            "stream=codec_name,sample_rate,channels",
            "-of",
            "json",
            str(path),
        ],
        text=True,
    )
    return json.loads(output)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("audio")
    parser.add_argument("text")
    parser.add_argument("--engine", required=True)
    parser.add_argument("--voice", required=True)
    parser.add_argument("--wall-seconds", type=float, required=True)
    args = parser.parse_args()

    text = Path(args.text).read_text(encoding="utf-8")
    chars = len(text)
    data = probe(Path(args.audio))
    duration = float(data["format"]["duration"])
    stream = data["streams"][0]

    result = {
        "engine": args.engine,
        "voice": args.voice,
        "chars": chars,
        "audio_seconds": round(duration, 3),
        "wall_seconds": round(args.wall_seconds, 3),
        "chars_per_wall_second": round(chars / args.wall_seconds, 2),
        "realtime_factor": round(duration / args.wall_seconds, 2),
        "bytes": int(data["format"]["size"]),
        "codec": stream.get("codec_name"),
        "sample_rate": stream.get("sample_rate"),
        "channels": stream.get("channels"),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
