from __future__ import annotations

import os
import shutil
from pathlib import Path


def find_binary(name: str) -> str:
    """Resolve a native binary from env, PATH, .tools/bin, or static-ffmpeg."""
    env_name = f"{name.upper()}_BINARY"
    if configured := os.environ.get(env_name):
        return configured

    if found := shutil.which(name):
        return found

    project_root = Path(__file__).resolve().parents[2]
    local = project_root / ".tools" / "bin" / name
    if local.exists():
        return str(local)

    try:
        import static_ffmpeg

        static_ffmpeg.add_paths()
        if found := shutil.which(name):
            return found
    except Exception as exc:
        raise RuntimeError(
            f"{name} not found. Install ffmpeg/ffprobe or run `uv sync` to use static-ffmpeg."
        ) from exc

    raise RuntimeError(f"{name} not found after static-ffmpeg setup")


def require_ffmpeg() -> tuple[str, str]:
    return find_binary("ffmpeg"), find_binary("ffprobe")
