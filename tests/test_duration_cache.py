import json
import os
from pathlib import Path

from audiol.duration_cache import SegmentDurationCache


def _audio(path: Path) -> Path:
    path.write_bytes(b"RIFF" + b"\0" * 64)
    return path


def test_duration_cache_round_trips_and_invalidates_on_change(tmp_path: Path):
    audio = _audio(tmp_path / "segment.wav")
    cache = SegmentDurationCache(tmp_path / "durations.json")

    assert cache.get(audio) is None
    cache.put(audio, 1234)
    assert cache.get(audio) == 1234
    assert cache.hits == 1

    cache.flush()
    reloaded = SegmentDurationCache(tmp_path / "durations.json")
    assert reloaded.get(audio) == 1234

    audio.write_bytes(audio.read_bytes() + b"changed")
    assert reloaded.get(audio) is None


def test_duration_cache_invalidates_on_mtime_without_size_change(tmp_path: Path):
    audio = _audio(tmp_path / "segment.wav")
    cache = SegmentDurationCache(tmp_path / "durations.json")
    cache.put(audio, 900)

    stat = audio.stat()
    os.utime(audio, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000))

    assert cache.get(audio) is None


def test_duration_cache_ignores_corrupt_or_old_files(tmp_path: Path):
    cache_path = tmp_path / "durations.json"
    cache_path.write_text("{not json", encoding="utf-8")
    assert SegmentDurationCache(cache_path).get(_audio(tmp_path / "a.wav")) is None

    cache_path.write_text(json.dumps({"version": 0, "segments": {}}), encoding="utf-8")
    assert SegmentDurationCache(cache_path).get(_audio(tmp_path / "b.wav")) is None
