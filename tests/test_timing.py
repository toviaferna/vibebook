import json
from pathlib import Path

import pytest

from audiol.models import Chapter, Segment, WordTiming, make_segment_id
from audiol.timing import (
    build_chapter_timing,
    build_chapter_timing_from_offsets,
    ensure_chapter_timing,
    estimate_word_timings,
    read_chapter_timing,
    read_word_timings,
    scale_words,
    write_chapter_timing,
    write_word_timings,
)


def _chapter(*texts: str) -> Chapter:
    return Chapter(
        index=1,
        title="Capítulo 1",
        segments=[
            Segment(
                id=make_segment_id(1, index),
                chapter_index=1,
                paragraph_index=index,
                text=text,
            )
            for index, text in enumerate(texts, start=1)
        ],
    )


def test_estimate_word_timings_covers_text_and_duration():
    words = estimate_word_timings("Hola, mundo.", 1000)

    assert [word.text for word in words] == ["Hola,", "mundo."]
    assert words[0].start_ms == 0
    assert words[-1].end_ms == 1000
    assert all(word.end_ms > word.start_ms for word in words)
    assert all(left.end_ms <= right.start_ms for left, right in zip(words, words[1:], strict=False))


def test_estimate_word_timings_handles_empty_text():
    assert estimate_word_timings("   ", 1000) == []


def test_estimate_word_timings_rejects_non_positive_duration():
    with pytest.raises(ValueError):
        estimate_word_timings("Hola", 0)


def test_estimate_word_timings_adds_punctuation_pause():
    words = estimate_word_timings("Hola, mundo", 1000)

    first_duration = words[0].end_ms - words[0].start_ms
    second_duration = words[1].end_ms - words[1].start_ms
    assert first_duration > second_duration


def test_estimate_word_timings_rejects_too_many_words_for_duration():
    with pytest.raises(ValueError):
        estimate_word_timings("una dos tres", 2)


def test_scale_words_to_duration():
    words = [
        WordTiming(text="Hola", start_ms=0, end_ms=100),
        WordTiming(text="mundo", start_ms=100, end_ms=200),
    ]

    scaled = scale_words(words, 1000)

    assert [(word.start_ms, word.end_ms) for word in scaled] == [(0, 500), (500, 1000)]
    assert [word.text for word in scaled] == ["Hola", "mundo"]


def test_scale_words_never_exceeds_duration_and_stays_monotonic():
    words = [
        WordTiming(text="uno", start_ms=0, end_ms=995),
        WordTiming(text="dos", start_ms=995, end_ms=1000),
    ]

    scaled = scale_words(words, 100)

    assert all(0 <= word.start_ms <= word.end_ms <= 100 for word in scaled)
    assert all(
        left.end_ms <= right.start_ms for left, right in zip(scaled, scaled[1:], strict=False)
    )
    assert scaled[-1].end_ms == 100


def test_scale_words_clamps_single_word():
    scaled = scale_words([WordTiming(text="Hola", start_ms=10, end_ms=20)], 300)

    assert len(scaled) == 1
    assert scaled[0].start_ms == 0
    assert scaled[0].end_ms == 300


def test_build_chapter_timing_is_cumulative_and_monotonic():
    chapter = _chapter("Hola mundo", "Adiós")
    timing = build_chapter_timing(
        chapter,
        [500, 700],
        [
            [
                WordTiming(text="Hola", start_ms=0, end_ms=200),
                WordTiming(text="mundo", start_ms=200, end_ms=500),
            ],
            [WordTiming(text="Adiós", start_ms=0, end_ms=700)],
        ],
    )

    assert timing.chapter_index == 1
    assert timing.duration_ms == 1200
    assert timing.precision == "exact"
    assert [(item.start_ms, item.end_ms) for item in timing.segments] == [(0, 500), (500, 1200)]
    assert [item.precision for item in timing.segments] == ["exact", "exact"]
    assert [(word.start_ms, word.end_ms) for word in timing.segments[1].words] == [(500, 1200)]


def test_build_chapter_timing_scales_to_chapter_duration():
    chapter = _chapter("Hola mundo")
    timing = build_chapter_timing(
        chapter,
        [500],
        [
            [
                WordTiming(text="Hola", start_ms=0, end_ms=200),
                WordTiming(text="mundo", start_ms=200, end_ms=500),
            ]
        ],
        chapter_duration_ms=1000,
    )

    assert timing.duration_ms == 1000
    assert [(item.start_ms, item.end_ms) for item in timing.segments] == [(0, 1000)]
    assert [(word.start_ms, word.end_ms) for word in timing.segments[0].words] == [
        (0, 400),
        (400, 1000),
    ]


def test_build_chapter_timing_falls_back_when_words_empty():
    chapter = _chapter("Hola mundo")
    timing = build_chapter_timing(chapter, [1000], [[]])

    assert timing.precision == "estimated"
    assert timing.segments[0].precision == "estimated"
    assert [word.text for word in timing.segments[0].words] == ["Hola", "mundo"]
    assert timing.segments[0].words[-1].end_ms == 1000


def test_build_chapter_timing_rejects_mismatched_lengths():
    chapter = _chapter("Hola")

    with pytest.raises(ValueError):
        build_chapter_timing(chapter, [100], [])

    with pytest.raises(ValueError):
        build_chapter_timing(chapter, [], [])


def test_build_chapter_timing_requires_positive_duration():
    chapter = _chapter("Hola")

    with pytest.raises(ValueError):
        build_chapter_timing(chapter, [0], [[]])


def test_short_chapter_still_distributes_one_ms_per_segment(tmp_path: Path):
    chapter = _chapter("Uno", "Dos", "Tres")

    timing = ensure_chapter_timing(tmp_path, chapter, 3)

    assert timing.duration_ms == 3
    assert [(segment.start_ms, segment.end_ms) for segment in timing.segments] == [
        (0, 1),
        (1, 2),
        (2, 3),
    ]


def test_read_word_timings_handles_non_dict_payload(tmp_path: Path):
    path = tmp_path / "broken.timing.json"
    path.write_text("[]", encoding="utf-8")

    assert read_word_timings(path) == []


def test_word_timing_roundtrip(tmp_path: Path):
    path = tmp_path / "sample.timing.json"
    words = [WordTiming(text="Hola", start_ms=0, end_ms=250)]

    write_word_timings(path, words)

    assert read_word_timings(path) == words


def test_timing_from_offsets_preserves_silence_and_absolute_time():
    chapter = _chapter("Hola mundo", "Otra vez")
    timing = build_chapter_timing_from_offsets(
        chapter,
        [0, 1_000],
        [800, 500],
        [
            [WordTiming(text="Hola", start_ms=100, end_ms=400)],
            [WordTiming(text="Otra", start_ms=0, end_ms=200)],
        ],
        chapter_duration_ms=1_500,
    )

    assert timing.segments[0].start_ms == 0
    assert timing.segments[0].end_ms == 800
    assert timing.segments[0].words[0].start_ms == 100
    assert timing.segments[0].words[0].end_ms == 400
    assert timing.segments[1].start_ms == 1_000
    assert timing.segments[1].words[0].start_ms == 1_000
    assert timing.duration_ms == 1_500


def test_timing_from_offsets_normalizes_overlaps_without_drift():
    chapter = _chapter("Uno dos tres")
    timing = build_chapter_timing_from_offsets(
        chapter,
        [0],
        [1_000],
        [
            [
                WordTiming(text="Uno", start_ms=0, end_ms=500),
                WordTiming(text="dos", start_ms=450, end_ms=700),
                WordTiming(text="tres", start_ms=650, end_ms=900),
            ]
        ],
    )

    words = timing.segments[0].words
    assert [word.start_ms for word in words] == [0, 500, 700]
    assert words[-1].end_ms == 900
    assert timing.precision == "exact"


def test_timing_from_offsets_estimates_when_words_are_missing():
    chapter = _chapter("Hola mundo")
    timing = build_chapter_timing_from_offsets(
        chapter,
        [0],
        [1_000],
        [[]],
    )

    assert timing.precision == "estimated"
    assert timing.segments[0].words
    assert timing.segments[0].words[-1].end_ms == 1_000


def test_timing_roundtrip_json(tmp_path: Path):
    chapter = _chapter("Hola mundo")
    timing = build_chapter_timing(
        chapter,
        [500],
        [
            [
                WordTiming(text="Hola", start_ms=0, end_ms=200),
                WordTiming(text="mundo", start_ms=200, end_ms=500),
            ]
        ],
    )
    path = tmp_path / "chapter_001.json"

    write_chapter_timing(path, timing)
    loaded = read_chapter_timing(path)

    assert loaded == timing
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1
    assert payload["duration_ms"] == 500
    assert payload["segments"][0]["words"][0]["text"] == "Hola"
