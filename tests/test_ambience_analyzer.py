import json

from audiol.ambience.analyzer import analyze_book
from audiol.ambience.plan import validate_plan
from audiol.studio.library import BookRecord
from audiol.timing import ChapterTiming, SegmentTiming, WordTiming, write_chapter_timing


def _record(tmp_path) -> BookRecord:
    book_dir = tmp_path / "book"
    (book_dir / "timings").mkdir(parents=True)
    (book_dir / "manifest.json").write_text(
        json.dumps(
            {
                "schema_version": 2,
                "id": "book-1",
                "title": "La casa del faro",
                "author": "Autora",
                "language": "es",
                "status": "ready",
                "chapters": [
                    {
                        "index": 1,
                        "title": "La lluvia",
                        "duration_ms": 20_000,
                        "timing": "timings/chapter_001.json",
                        "segments": [
                            {
                                "id": "s1",
                                "chapter_index": 1,
                                "paragraph_index": 1,
                                "text": "La lluvia golpeaba la puerta de la casa.",
                            },
                            {
                                "id": "s2",
                                "chapter_index": 1,
                                "paragraph_index": 2,
                                "text": "El mar seguía oscuro detrás del faro.",
                            },
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    write_chapter_timing(
        book_dir / "timings" / "chapter_001.json",
        ChapterTiming(
            chapter_index=1,
            duration_ms=20_000,
            precision="estimated",
            segments=[
                SegmentTiming("s1", 5_000, 6_000, "estimated", [WordTiming("La", 5_000, 5_200)]),
                SegmentTiming(
                    "s2", 15_000, 16_000, "estimated", [WordTiming("El", 15_000, 15_200)]
                ),
            ],
        ),
    )
    return BookRecord(
        id="book-1",
        title="La casa del faro",
        author="Autora",
        language="es",
        path=book_dir,
        cover_path=None,
        status="ready",
        voice=None,
        engine=None,
        style=None,
        rate=None,
        chapter_count=1,
        duration_ms=20_000,
        created_at="2026-11-08T00:00:00+00:00",
        updated_at="2026-11-08T00:00:00+00:00",
    )


def _assets() -> list[dict]:
    return [
        {
            "id": "rain-1",
            "kind": "ambience",
            "prompt": "rain soft",
            "tags": ["rain"],
            "duration_ms": 30_000,
        },
        {
            "id": "door-1",
            "kind": "effect",
            "prompt": "door bell",
            "tags": ["door"],
            "duration_ms": 1_800,
        },
    ]


def test_analyze_detects_rain_and_door(tmp_path):
    record = _record(tmp_path)

    settings, plan = analyze_book(record.path, _assets())

    assert settings.enabled is False
    chapter = plan.chapters[0]
    assert chapter.bed is not None
    assert chapter.bed.asset_id == "rain-1"
    assert chapter.bed.reason == "escena detectada: rain"
    assert [effect.asset_id for effect in chapter.effects] == ["door-1"]
    validate_plan(plan, record, {"rain-1", "door-1"})


def test_analyze_without_assets_returns_empty_plan(tmp_path):
    record = _record(tmp_path)

    _, plan = analyze_book(record.path, [])

    assert plan.chapters == []
