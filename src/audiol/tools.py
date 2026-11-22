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


def resolve_shimmed_binary(
    path: str,
    name: str,
    *,
    windows: bool | None = None,
) -> str | None:
    """Resolve a Windows package-manager shim to the real executable.

    Scoop and similar tools put a small launcher in ``shims`` that points at
    ``apps/<name>/<version>/bin/<name>.exe``. Bundling that launcher in the
    PyInstaller sidecar produces a binary that cannot find its target at
    runtime ("Cannot open shim file for read"), so the real executable must be
    resolved before packaging.
    """
    if windows is None:
        windows = os.name == "nt"
    if not windows:
        return None
    candidate = Path(path)
    if candidate.parent.name.lower() != "shims":
        return None
    apps = candidate.parent.parent / "apps" / name
    if not apps.is_dir():
        return None
    for item in sorted(apps.iterdir(), reverse=True):
        binary = item / "bin" / f"{name}.exe"
        if binary.is_file():
            return str(binary)
    return None


def _resolve_binary(
    path: str,
    name: str,
    *,
    windows: bool | None = None,
) -> str | None:
    resolved = resolve_shimmed_binary(path, name, windows=windows)
    if resolved is not None:
        return resolved
    is_windows = os.name == "nt" if windows is None else windows
    if is_windows and Path(path).parent.name.lower() == "shims":
        return None
    return path


def find_optional_binary(name: str, env_names: tuple[str, ...] = ()) -> str | None:
    """Resolve a native binary without raising or falling back to static-ffmpeg."""
    for env_name in (*env_names, f"{name.upper()}_BINARY"):
        if configured := os.environ.get(env_name):
            return configured

    if found := _find_bundled(name):
        return found

    if (found := shutil.which(name)) and (resolved := _resolve_binary(found, name)):
        return resolved

    project_root = Path(__file__).resolve().parents[2]
    return _find_in_dir(project_root / ".tools" / "bin", name)


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

    if (found := shutil.which(name)) and (resolved := _resolve_binary(found, name)):
        return resolved

    project_root = Path(__file__).resolve().parents[2]
    if found := _find_in_dir(project_root / ".tools" / "bin", name):
        return found

    try:
        import static_ffmpeg

        static_ffmpeg.add_paths()
        if (found := shutil.which(name)) and (resolved := _resolve_binary(found, name)):
            return resolved
    except Exception as exc:
        raise RuntimeError(
            f"{name} not found. Install ffmpeg/ffprobe or run `uv sync` to use static-ffmpeg."
        ) from exc

    raise RuntimeError(f"{name} not found after static-ffmpeg setup")


def require_ffmpeg() -> tuple[str, str]:
    return find_binary("ffmpeg"), find_binary("ffprobe")
