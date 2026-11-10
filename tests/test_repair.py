import json
import math
import struct
import wave
from pathlib import Path

import pytest

from audiol.cli import main
from audiol.convert import cache_key
from audiol.models import Segment, WordTiming
from audiol.repair import RepairError, _select_segment_audio, repair_book
from audiol.timing import (
    ChapterTiming,
    SegmentTiming,
    read_chapter_timing,
    segment_timing_path,
    write_chapter_timing,
    write_word_timings,
)
from audiol.tools import find_binary


def _has_ffmpeg() -> bool:
    try:
        find_binary("ffmpeg")
        find_binary("ffprobe")
        return True
    except RuntimeError:
        return False


requires_ffmpeg = pytest.mark.skipif(
    not _has_ffmpeg(),
    reason="ffmpeg/ffprobe not available",
)


def _wav(path: Path, seconds: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rate = 24_000
    frames = bytearray()
    for index in range(int(seconds * rate)):
        sample = int(4_000 * math.sin(2 * math.pi * 440 * index / rate))
        frames += struct.pack("<h", sample)
    with wave.open(str(path), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(rate)
        audio.writeframes(frames)


def _book(tmp_path: Path) -> Path:
    book_dir = tmp_path / "book"
    segments_dir = book_dir / "audio" / "segments"
    first = segments_dir / "s1_oldkey.wav"
    second = segments_dir / "s2_oldkey.wav"
    _wav(first, 0.5)
    _wav(second, 0.25)
    write_word_timings(
        segment_timing_path(first),
        [WordTiming(text="Hola", start_ms=0, end_ms=400)],
    )
    write_word_timings(
        segment_timing_path(second),
        [WordTiming(text="mundo", start_ms=0, end_ms=200)],
    )
    old_timing = ChapterTiming(
        chapter_index=1,
        duration_ms=999,
        precision="estimated",
        segments=[
            SegmentTiming("s1", 0, 500, "estimated", []),
            SegmentTiming("s2", 500, 999, "estimated", []),
        ],
    )
    write_chapter_timing(book_dir / "timings" / "chapter_001.json", old_timing)
    (book_dir / "manifest.json").write_text(
        json.dumps(
            {
                "schema_version": 2,
                "id": "old-book",
                "title": "Viejo",
                "author": "Autora",
                "language": "es",
                "status": "ready",
                "voice": "old",
                "engine": "fake",
                "chapters": [
                    {
                        "index": 1,
                        "title": "Uno",
                        "audio": "audio/chapters/chapter_001.mp3",
                        "timing": "timings/chapter_001.json",
                        "duration_ms": 999,
                        "segments": [
                            {
                                "id": "s1",
                                "chapter_index": 1,
                                "paragraph_index": 1,
                                "text": "Hola",
                            },
                            {
                                "id": "s2",
                                "chapter_index": 1,
                                "paragraph_index": 2,
                                "text": "mundo",
                            },
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return book_dir


@requires_ffmpeg
def test_repair_book_rebuilds_timing_from_offsets(tmp_path):
    book_dir = _book(tmp_path)

    result = repair_book(book_dir)

    assert result["rebuilt"] == [1]
    assert result["skipped"] == []
    assert (book_dir / "audio" / "chapters" / "chapter_001.mp3").exists()
    timing = read_chapter_timing(book_dir / "timings" / "chapter_001.json")
    assert [segment.start_ms for segment in timing.segments] == [0, 500]
    assert [segment.end_ms for segment in timing.segments] == [500, 750]
    assert timing.segments[0].words[0].start_ms == 0
    assert timing.segments[1].words[0].start_ms == 500
    assert timing.timing_offset_ms == result["timing_offset_ms"]
    manifest = json.loads((book_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["chapters"][0]["duration_ms"] > 0
    assert manifest["duration_ms"] == manifest["chapters"][0]["duration_ms"]


@requires_ffmpeg
def test_repair_book_skips_chapters_without_segment_audio(tmp_path):
    book_dir = _book(tmp_path)
    manifest_path = book_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["chapters"].append(
        {
            "index": 2,
            "title": "Dos",
            "audio": "audio/chapters/chapter_002.mp3",
            "timing": "timings/chapter_002.json",
            "duration_ms": 100,
            "segments": [
                {"id": "missing", "chapter_index": 2, "paragraph_index": 1, "text": "Nada"}
            ],
        }
    )
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    result = repair_book(book_dir)

    assert result["rebuilt"] == [1]
    assert result["skipped"] == [2]


def test_repair_prefers_manifest_cache_key(tmp_path):
    book_dir = _book(tmp_path)
    folder = book_dir / "audio" / "segments"
    segment = Segment(
        id="s1",
        chapter_index=1,
        paragraph_index=1,
        text="Hola",
    )
    key = cache_key(segment, "old", "fake", "neutral", "-10%")
    expected = folder / f"s1_{key}.wav"
    expected.write_bytes((folder / "s1_oldkey.wav").read_bytes())
    (folder / "s1_other.wav").write_bytes(b"wrong")

    selected = _select_segment_audio(folder, segment, "old", "fake", "neutral", "-10%")

    assert selected == expected


def test_repair_rejects_ambiguous_segment_audio(tmp_path):
    book_dir = _book(tmp_path)
    folder = book_dir / "audio" / "segments"
    segment = Segment(id="s1", chapter_index=1, paragraph_index=1, text="Hola")
    (folder / "s1_a.wav").write_bytes(b"a")
    (folder / "s1_b.wav").write_bytes(b"b")

    with pytest.raises(RepairError, match="Ambiguous"):
        _select_segment_audio(folder, segment, "old", "fake", "neutral", "-10%")


def test_repair_rejects_audio_path_outside_book(tmp_path):
    book_dir = _book(tmp_path)
    path = book_dir / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["chapters"][0]["audio"] = "../escape.mp3"
    path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(RepairError, match="escapes"):
        repair_book(book_dir)


@requires_ffmpeg
def test_repair_failure_preserves_previous_manifest(tmp_path, monkeypatch):
    book_dir = _book(tmp_path)
    manifest_before = (book_dir / "manifest.json").read_bytes()

    def fail(*args, **kwargs):
        raise RuntimeError("timing failed")

    monkeypatch.setattr("audiol.repair.write_chapter_timing", fail)

    with pytest.raises(RuntimeError, match="timing failed"):
        repair_book(book_dir)

    assert (book_dir / "manifest.json").read_bytes() == manifest_before
    assert not (book_dir / "audio" / "chapters" / "chapter_001.mp3").exists()
    assert not list(book_dir.glob(".staging/*"))


@requires_ffmpeg
def test_repair_sync_cli(tmp_path, capsys):
    book_dir = _book(tmp_path)

    assert main(["repair-sync", str(book_dir)]) == 0
    output = capsys.readouterr().out
    assert "Reparados: 1" in output
    assert "offset" in output
