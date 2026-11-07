from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


def _binary_names(name: str) -> tuple[str, ...]:
    return (name, f"{name}.exe") if os.name == "nt" else (name,)


def _find_in_dir(directory: Path, name: str) -> str | None:
    for relative in ("", "bin", "resources"):
        for filename in _binary_names(name):
            candidate = directory / relative / filename
            if candidate.is_file():
                return str(candidate)
    return None


def _find_bundled(name: str) -> str | None:
    if not getattr(sys, "frozen", False):
        return None
    bundle = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    for directory in (bundle, Path(sys.executable).parent):
        if found := _find_in_dir(directory, name):
            return found
    return None


def find_binary(name: str) -> str:
    """Resolve a native binary from env, bundled resources, PATH, or static-ffmpeg."""
    env_name = f"{name.upper()}_BINARY"
    if configured := os.environ.get(env_name):
        return configured

    if (configured_dir := os.environ.get("VIBEBOOK_FFMPEG_DIR")) and (
        found := _find_in_dir(Path(configured_dir).expanduser(), name)
    ):
        return found

    if found := _find_bundled(name):
        return found

    if found := shutil.which(name):
        return found

    project_root = Path(__file__).resolve().parents[2]
    if found := _find_in_dir(project_root / ".tools" / "bin", name):
        return found

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
