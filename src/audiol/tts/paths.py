from __future__ import annotations

import ctypes
import os
from pathlib import Path


def to_ascii_path(path: Path) -> Path | None:
    if str(path).isascii() or os.name != "nt":
        return path
    short = _windows_short_path(path)
    if short is not None and str(short).isascii():
        return short
    return None


def _windows_short_path(path: Path) -> Path | None:
    windll = getattr(ctypes, "windll", None)
    if windll is None:
        return None
    try:
        buffer = ctypes.create_unicode_buffer(32768)
        result = windll.kernel32.GetShortPathNameW(str(path), buffer, len(buffer))
    except (AttributeError, OSError):
        return None
    return Path(buffer.value) if result else None
