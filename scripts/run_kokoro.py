#!/usr/bin/env python3
"""Run the Audiblez/Kokoro pipeline without its broken console wrapper."""

from __future__ import annotations

import argparse

from audiblez.core import main


def cli() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("epub")
    parser.add_argument("--voice", default="em_alex")
    parser.add_argument("--output", default="out/kokoro")
    parser.add_argument("--speed", type=float, default=1.0)
    parser.add_argument("--max-sentences", type=int, default=None)
    args = parser.parse_args()

    main(
        args.epub,
        args.voice,
        False,
        args.speed,
        args.output,
        max_sentences=args.max_sentences,
    )


if __name__ == "__main__":
    cli()
