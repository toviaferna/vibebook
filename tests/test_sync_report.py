import json
import wave
from pathlib import Path

from audiol.models import WordTiming
from audiol.sync_report import analyze_chapter, build_report, main
from audiol.timing import ChapterTiming, SegmentTiming, write_chapter_timing


def _wav(path: Path, seconds: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(22_050)
        audio.writeframes(b"\x00\x00" * int(22_050 * seconds))


def test_analyze_chapter_finds_gaps_overlaps_and_invalid_words():
    timing = ChapterTiming(
        chapter_index=1,
        duration_ms=2_000,
        precision="exact",
        segments=[
            SegmentTiming(
                id="s1",
                start_ms=0,
                end_ms=1_000,
                precision="exact",
                words=[
                    WordTiming("uno", 0, 400),
                    WordTiming("dos", 700, 900),
                    WordTiming("tres", 850, 950),
                ],
            ),
            SegmentTiming(
                id="s2",
                start_ms=1_000,
                end_ms=2_000,
                precision="estimated",
                words=[WordTiming("mal", 1_000, 1_000)],
            ),
        ],
    )

    report = analyze_chapter(timing, 2_000, {"s1": 1_000, "s2": 1_000})

    assert len(report["gaps"]) == 1
    assert len(report["overlaps"]) == 1
    assert len(report["invalid_words"]) == 1
    assert report["timing_vs_audio_ms"] == 0
    assert report["segments"][0]["audio_delta_ms"] == 0


def test_build_report_compares_timing_with_chapter_audio(tmp_path):
    book = tmp_path / "book"
    _wav(book / "audio" / "segments" / "s1_hash.wav", 1.0)
    _wav(book / "audio" / "segments" / "s2_other.wav", 3.0)
    _wav(book / "audio" / "chapters" / "chapter_001.wav", 1.1)
    timing = ChapterTiming(
        chapter_index=1,
        duration_ms=1_000,
        precision="estimated",
        segments=[
            SegmentTiming(
                id="s1",
                start_ms=0,
                end_ms=1_000,
                precision="estimated",
                words=[WordTiming("hola", 0, 500)],
            )
        ],
    )
    write_chapter_timing(book / "timings" / "chapter_001.json", timing)
    (book / "manifest.json").write_text(
        json.dumps(
            {
                "id": "book",
                "title": "Libro",
                "chapters": [
                    {
                        "index": 1,
                        "title": "Uno",
                        "timing": "timings/chapter_001.json",
                        "audio": "audio/chapters/chapter_001.wav",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    report = build_report(book)

    chapter = report["chapters"][0]
    assert chapter["timing_vs_audio_ms"] == -100
    assert chapter["segment_sum_vs_audio_ms"] == -100
    assert report["summary"]["max_drift_ms"] == 100
    assert report["summary"]["chapters"] == 1


def test_sync_report_cli_json_and_strict(tmp_path, capsys):
    book = tmp_path / "book"
    _wav(book / "audio" / "chapters" / "chapter_001.wav", 1.2)
    timing = ChapterTiming(
        chapter_index=1,
        duration_ms=1_000,
        precision="estimated",
        segments=[
            SegmentTiming(
                id="s1",
                start_ms=0,
                end_ms=1_000,
                precision="estimated",
                words=[WordTiming("hola", 0, 500)],
            )
        ],
    )
    write_chapter_timing(book / "timings" / "chapter_001.json", timing)
    (book / "manifest.json").write_text(
        json.dumps(
            {
                "title": "Libro",
                "chapters": [
                    {
                        "index": 1,
                        "title": "Uno",
                        "timing": "timings/chapter_001.json",
                        "audio": "audio/chapters/chapter_001.wav",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    assert main([str(book), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["summary"]["max_drift_ms"] == 200
    assert main([str(book), "--strict", "--max-drift-ms", "100"]) == 1


def test_missing_timing_is_reported(tmp_path):
    book = tmp_path / "book"
    book.mkdir()
    (book / "manifest.json").write_text(
        json.dumps({"title": "Libro", "chapters": [{"index": 1, "title": "Uno"}]}),
        encoding="utf-8",
    )

    report = build_report(book)

    assert report["summary"]["missing_timing"] == 1
