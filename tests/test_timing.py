import json
from pathlib import Path

import pytest

from audiol.models import Chapter, Segment, WordTiming, make_segment_id
from audiol.timing import (
    build_chapter_timing,
    estimate_word_timings,
    read_chapter_timing,
    scale_words,
    write_chapter_timing,
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
    words = estimate_word_timings("Hola, mundo.", 1000)

    first_duration = words[0].end_ms - words[0].start_ms
    second_duration = words[1].end_ms - words[1].start_ms
    assert second_duration > first_duration


def test_scale_words_to_duration():
    words = [
        WordTiming(text="Hola", start_ms=0, end_ms=100),
        WordTiming(text="mundo", start_ms=100, end_ms=200),
    ]

    scaled = scale_words(words, 1000)

    assert [(word.start_ms, word.end_ms) for word in scaled] == [(0, 500), (500, 1000)]
    assert [word.text for word in scaled] == ["Hola", "mundo"]


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
