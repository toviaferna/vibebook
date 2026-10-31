import argparse
import json
import sys
from pathlib import Path

from audiol.convert import convert, prepare_book, render_markdown
from audiol.ingest.epub import read_epub
from audiol.tts.azure import AzureProvider
from audiol.tts.base import validate_rate
from audiol.tts.edge import EdgeProvider
from audiol.tts.fake import FakeProvider
from audiol.voices import get_voice, list_voices


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="audiol")
    subparsers = parser.add_subparsers(dest="command", required=True)

    voices = subparsers.add_parser("voices", help="List available voices")
    voices.add_argument("--locale", default=None, help="Filter by locale, e.g. es-MX")

    convert_parser = subparsers.add_parser("convert", help="Convert an EPUB to M4B")
    convert_parser.add_argument("epub")
    convert_parser.add_argument("--voice", default="es-MX-JorgeNeural")
    convert_parser.add_argument(
        "--engine", choices=["edge", "azure", "fake"], default="edge"
    )
    convert_parser.add_argument("--style", default="neutral")
    convert_parser.add_argument(
        "--rate",
        default="-6%",
        help="Speech rate percentage, e.g. '-6%%' or '+0%%'",
    )
    convert_parser.add_argument("--out", default=None)
    convert_parser.add_argument("--max-chars", type=int, default=400)
    convert_parser.add_argument("--dry-run", action="store_true")
    convert_parser.add_argument("--force", action="store_true")

    return parser


def _normalize_rate_args(argv: list[str]) -> list[str]:
    """Allow `--rate -6%`; argparse otherwise reads the value as an option."""
    normalized: list[str] = []
    index = 0
    while index < len(argv):
        if argv[index] == "--rate" and index + 1 < len(argv):
            normalized.append(f"--rate={argv[index + 1]}")
            index += 2
        else:
            normalized.append(argv[index])
            index += 1
    return normalized


def main(argv: list[str] | None = None) -> int:
    raw_argv = sys.argv[1:] if argv is None else list(argv)
    args = build_parser().parse_args(_normalize_rate_args(raw_argv))

    if args.command == "voices":
        for voice in list_voices(args.locale):
            styles = ",".join(voice.styles) if voice.styles else "-"
            engines = ",".join(voice.engines)
            print(f"{voice.id}\t{voice.locale}\t{voice.gender}\t{engines}\t{styles}")
        return 0

    if args.command == "convert":
        try:
            return _convert(args)
        except (ValueError, RuntimeError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1

    return 1


def _convert(args: argparse.Namespace) -> int:
    voice = get_voice(args.voice)
    if args.engine != "fake" and args.engine not in voice.engines:
        raise SystemExit(f"{args.voice} does not support engine {args.engine}")
    if args.style != "neutral":
        if args.engine != "azure":
            raise SystemExit("Styles require --engine azure")
        if args.style not in voice.styles:
            raise SystemExit(
                f"{args.voice} does not support style {args.style}; "
                f"available: {', '.join(voice.styles) or '-'}"
            )

    rate = validate_rate(args.rate)
    book = prepare_book(read_epub(Path(args.epub)), max_chars=args.max_chars)
    if not book.chapters:
        raise SystemExit("No chapters found in the EPUB")
    out_dir = Path(args.out) if args.out else Path("out") / Path(args.epub).stem

    if args.dry_run:
        stats = {
            "title": book.title,
            "chapters": len(book.chapters),
            "segments": sum(len(chapter.segments) for chapter in book.chapters),
            "chars": sum(
                len(segment.text)
                for chapter in book.chapters
                for segment in chapter.segments
            ),
            "rate": rate,
            "out": str(out_dir),
        }
        print(json.dumps(stats, ensure_ascii=False, indent=2))
        return 0

    provider = _make_provider(args.engine)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "book.md").write_text(render_markdown(book), encoding="utf-8")
    m4b = convert(
        book,
        args.voice,
        args.engine,
        provider,
        out_dir,
        style=args.style,
        rate=rate,
        force=args.force,
    )
    print(f"M4B: {m4b}")
    return 0


def _make_provider(engine: str):
    if engine == "edge":
        return EdgeProvider()
    if engine == "azure":
        return AzureProvider()
    if engine == "fake":
        return FakeProvider()
    raise ValueError(f"Unknown engine: {engine}")
