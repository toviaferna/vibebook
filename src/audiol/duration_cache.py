from __future__ import annotations

import json
import threading
from pathlib import Path

from audiol.storage import write_json_atomic

CACHE_VERSION = 1


class SegmentDurationCache:
    """Per-book cache of measured segment durations.

    ffprobe/mutagen are not cheap when a book has hundreds of segments. This
    sidecar remembers the duration together with the file size and mtime; a
    changed segment invalidates just that entry. Writes are serialized because
    segment synthesis runs in a thread pool.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.Lock()
        self._entries = self._load()
        self._hits = 0
        self._dirty = False

    @property
    def hits(self) -> int:
        with self._lock:
            return self._hits

    def get(self, audio_path: Path) -> int | None:
        try:
            stat = audio_path.stat()
        except OSError:
            return None
        with self._lock:
            entry = self._entries.get(audio_path.name)
            if entry is None or not self._matches(entry, stat.st_size, stat.st_mtime_ns):
                return None
            self._hits += 1
            return int(entry["duration_ms"])

    def put(self, audio_path: Path, duration_ms: int) -> None:
        if duration_ms <= 0:
            return
        try:
            stat = audio_path.stat()
        except OSError:
            return
        with self._lock:
            self._entries[audio_path.name] = {
                "size": stat.st_size,
                "mtime_ns": stat.st_mtime_ns,
                "duration_ms": int(duration_ms),
            }
            self._dirty = True

    def forget(self, audio_path: Path) -> None:
        with self._lock:
            if self._entries.pop(audio_path.name, None) is not None:
                self._dirty = True

    def flush(self) -> None:
        with self._lock:
            if not self._dirty:
                return
            entries = {
                name: entry
                for name, entry in self._entries.items()
                if (self.path.parent / name).is_file()
            }
            payload = {
                "version": CACHE_VERSION,
                "segments": entries,
            }
            self._dirty = False
        write_json_atomic(self.path, payload)

    def _load(self) -> dict[str, dict[str, int]]:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        if not isinstance(raw, dict) or raw.get("version") != CACHE_VERSION:
            return {}
        segments = raw.get("segments")
        if not isinstance(segments, dict):
            return {}
        entries: dict[str, dict[str, int]] = {}
        for name, value in segments.items():
            if not isinstance(name, str) or not isinstance(value, dict):
                continue
            try:
                size = int(value["size"])
                mtime_ns = int(value["mtime_ns"])
                duration_ms = int(value["duration_ms"])
            except (KeyError, TypeError, ValueError):
                continue
            if size > 0 and duration_ms > 0:
                entries[name] = {
                    "size": size,
                    "mtime_ns": mtime_ns,
                    "duration_ms": duration_ms,
                }
        return entries

    @staticmethod
    def _matches(entry: dict[str, int] | None, size: int, mtime_ns: int) -> bool:
        return (
            entry is not None
            and entry.get("size") == size
            and entry.get("mtime_ns") == mtime_ns
            and entry.get("duration_ms", 0) > 0
        )
