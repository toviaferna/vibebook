import json

import pytest

from audiol.ambience.models import (
    AmbienceAnchor,
    AmbienceBed,
    AmbienceChapter,
    AmbienceEffect,
    AmbiencePlan,
    AmbienceSettings,
)
from audiol.ambience.plan import (
    AmbiencePlanError,
    load_ambience,
    plan_path,
    save_ambience,
    validate_plan,
)
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
                "title": "Libro de prueba",
                "author": "Autora",
                "language": "es",
                "status": "ready",
                "chapters": [
                    {
                        "index": 1,
                        "title": "Uno",
                        "duration_ms": 20_000,
                        "timing": "timings/chapter_001.json",
                        "segments": [
                            {"id": "s1", "chapter_index": 1, "paragraph_index": 1, "text": "Uno"},
                            {"id": "s2", "chapter_index": 1, "paragraph_index": 2, "text": "Dos"},
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    timing = ChapterTiming(
        chapter_index=1,
        duration_ms=20_000,
        precision="estimated",
        segments=[
            SegmentTiming("s1", 5_000, 6_000, "estimated", [WordTiming("Uno", 5_000, 6_000)]),
            SegmentTiming("s2", 15_000, 16_000, "estimated", [WordTiming("Dos", 15_000, 16_000)]),
        ],
    )
    write_chapter_timing(book_dir / "timings" / "chapter_001.json", timing)
    return BookRecord(
        id="book-1",
        title="Libro de prueba",
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


def _plan(effects: list[AmbienceEffect] | None = None) -> AmbiencePlan:
    return AmbiencePlan(
        chapters=[
            AmbienceChapter(
                chapter_index=1,
                bed=AmbienceBed(asset_id="rain", confidence=0.8),
                effects=effects or [],
            )
        ]
    )


def _effect(segment: str, duration: int = 3_000, confidence: float = 0.7) -> AmbienceEffect:
    return AmbienceEffect(
        asset_id="bell",
        anchor=AmbienceAnchor(segment_id=segment),
        duration_ms=duration,
        confidence=confidence,
    )


def test_load_ambience_defaults_without_manifest_field(tmp_path):
    record = _record(tmp_path)

    settings, plan = load_ambience(record.path)

    assert settings.enabled is False
    assert settings.master_gain_db == -18
    assert plan.chapters == []


def test_save_ambience_writes_plan_and_manifest(tmp_path):
    record = _record(tmp_path)
    settings = AmbienceSettings(enabled=True, master_gain_db=-20, ducking_db=-10)
    plan = _plan()

    save_ambience(record.path, settings, plan)

    assert plan_path(record.path).is_file()
    loaded_settings, loaded_plan = load_ambience(record.path)
    assert loaded_settings.enabled is True
    assert loaded_settings.master_gain_db == -20
    assert loaded_plan == plan
    manifest = json.loads((record.path / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["ambience"]["enabled"] is True
    assert manifest["ambience"]["plan"] == "ambience/plan.json"
    assert manifest["title"] == "Libro de prueba"


def test_validate_accepts_valid_plan(tmp_path):
    record = _record(tmp_path)

    validate_plan(_plan([_effect("s1"), _effect("s2")]), record, {"rain", "bell"})


def test_validate_rejects_unknown_anchor(tmp_path):
    record = _record(tmp_path)

    with pytest.raises(AmbiencePlanError, match="anchor"):
        validate_plan(_plan([_effect("missing")]), record, {"rain", "bell"})


def test_validate_rejects_unknown_asset(tmp_path):
    record = _record(tmp_path)

    with pytest.raises(AmbiencePlanError, match="asset"):
        validate_plan(_plan([_effect("s1")]), record, {"rain"})


def test_validate_rejects_low_confidence(tmp_path):
    record = _record(tmp_path)

    with pytest.raises(AmbiencePlanError, match="confidence"):
        validate_plan(_plan([_effect("s1", confidence=0.2)]), record, {"rain", "bell"})


def test_validate_rejects_more_than_three_effects(tmp_path):
    record = _record(tmp_path)

    with pytest.raises(AmbiencePlanError, match="more than"):
        validate_plan(
            _plan([_effect("s1")] * 4),
            record,
            {"rain", "bell"},
        )


def test_validate_rejects_effects_in_edge_guard(tmp_path):
    record = _record(tmp_path)

    with pytest.raises(AmbiencePlanError, match="first/last"):
        validate_plan(_plan([_effect("s1", duration=16_000)]), record, {"rain", "bell"})


def test_validate_rejects_short_separation(tmp_path):
    record = _record(tmp_path)
    effect = _effect("s1")
    second = AmbienceEffect(
        asset_id="bell",
        anchor=AmbienceAnchor(segment_id="s1", offset_ms=1_000),
        duration_ms=2_000,
    )

    with pytest.raises(AmbiencePlanError, match="separation"):
        validate_plan(_plan([effect, second]), record, {"rain", "bell"})
