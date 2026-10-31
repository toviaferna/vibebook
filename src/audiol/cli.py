import argparse

from audiol.voices import list_voices


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="audiol")
    subparsers = parser.add_subparsers(dest="command", required=True)

    voices = subparsers.add_parser("voices", help="List available voices")
    voices.add_argument("--locale", default=None, help="Filter by locale, e.g. es-MX")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "voices":
        for voice in list_voices(args.locale):
            styles = ",".join(voice.styles) if voice.styles else "-"
            engines = ",".join(voice.engines)
            print(f"{voice.id}\t{voice.locale}\t{voice.gender}\t{engines}\t{styles}")

    return 0
