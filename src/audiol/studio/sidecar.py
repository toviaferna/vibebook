from __future__ import annotations

import argparse
import json
import logging
import os
import secrets
import sys
from pathlib import Path

import uvicorn

from audiol.studio.app import create_app
from audiol.studio.server import find_free_port
from audiol.studio.settings import Settings, default_library_dir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="vibebook-sidecar")
    subparsers = parser.add_subparsers(dest="command", required=True)

    serve = subparsers.add_parser("serve", help="Run the studio backend for the desktop shell")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=0)
    serve.add_argument("--library", default=None)
    serve.add_argument("--token", default=None)
    serve.add_argument("--allow-fake", action="store_true")
    serve.add_argument("--log-level", default="info")
    serve.add_argument(
        "--json-ready",
        action="store_true",
        help="Print a single ready JSON line on stdout; logs go to stderr",
    )
    return parser


def find_web_dist() -> Path | None:
    configured = os.environ.get("VIBEBOOK_WEB_DIST")
    if configured:
        candidate = Path(configured).expanduser()
        return candidate if (candidate / "index.html").is_file() else None

    candidates: list[Path] = []
    if getattr(sys, "frozen", False):
        bundle = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        executable_dir = Path(sys.executable).parent
        candidates.extend(
            [
                bundle / "web" / "dist",
                executable_dir / "web" / "dist",
                executable_dir / "_internal" / "web" / "dist",
            ]
        )
    else:
        project_root = Path(__file__).resolve().parents[3]
        candidates.extend([Path.cwd() / "web" / "dist", project_root / "web" / "dist"])

    for candidate in candidates:
        if (candidate / "index.html").is_file():
            return candidate
    return None


def _configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        stream=sys.stderr,
        format="%(levelname)s %(name)s: %(message)s",
    )


def _serve(args: argparse.Namespace) -> int:
    _configure_logging(args.log_level)
    port = args.port or find_free_port(args.host)
    token = args.token or secrets.token_hex(32)
    library_dir = Path(args.library).expanduser() if args.library else default_library_dir()
    settings = Settings(
        library_dir=library_dir,
        host=args.host,
        port=port,
        token=token,
        allow_fake=args.allow_fake,
        web_dist=find_web_dist(),
    )
    app = create_app(settings)
    if args.json_ready:
        print(
            json.dumps({"event": "ready", "port": port, "token": token}),
            flush=True,
        )
    uvicorn.run(
        app,
        host=args.host,
        port=port,
        log_level=args.log_level,
        access_log=not args.json_ready,
        log_config=None,
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "serve":
            return _serve(args)
    except (ValueError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
