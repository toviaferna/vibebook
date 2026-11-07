import json
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal, cast

from mutagen import File as MutagenFile
from mutagen import MutagenError

from audiol.models import Chapter, WordTiming

Precision = Literal["exact", "estimated"]

_WORD = re.compile(r"\S+")
_COMMA_PAUSE = re.compile(r"[,;:]$")
_SENTENCE_PAUSE = re.compile(r"[.!?…][\"'»”’)]*$")


@dataclass(frozen=True)
class SegmentTiming:
    id: str
    start_ms: int
    end_ms: int
    precision: Precision
    words: list[WordTiming]


@dataclass(frozen=True)
class ChapterTiming:
    chapter_index: int
    duration_ms: int
    precision: Precision
    segments: list[SegmentTiming]


def estimate_word_timings(text: str, duration_ms: int) -> list[WordTiming]:
    if duration_ms <= 0:
        raise ValueError("duration_ms must be positive")
    words = [match.group(0) for match in _WORD.finditer(text)]
    if not words:
        return []

    weights = [_word_weight(word) for word in words]
    total_weight = sum(weights)
    timings: list[WordTiming] = []
    cursor = 0
    for index, word in enumerate(words):
        if index == len(words) - 1:
            end = duration_ms
        else:
            end = round(duration_ms * (sum(weights[: index + 1]) / total_weight))
            end = min(duration_ms, max(cursor + 1, end))
        timings.append(WordTiming(text=word, start_ms=cursor, end_ms=end))
        cursor = end
    return timings


def scale_words(words: list[WordTiming], duration_ms: int) -> list[WordTiming]:
    if not words:
        return []
    if duration_ms <= 0:
        raise ValueError("duration_ms must be positive")
    if len(words) == 1:
        return [WordTiming(text=words[0].text, start_ms=0, end_ms=duration_ms)]

    old_duration = max(1, words[-1].end_ms)
    factor = duration_ms / old_duration
    scaled: list[WordTiming] = []
    cursor = 0
    for index, word in enumerate(words):
        start = min(duration_ms - 1, max(cursor, round(word.start_ms * factor)))
        if index == len(words) - 1:
            end = duration_ms
        else:
            end = min(duration_ms, max(start + 1, round(word.end_ms * factor)))
        scaled.append(WordTiming(text=word.text, start_ms=start, end_ms=end))
        cursor = end
    return scaled


def build_chapter_timing(
    chapter: Chapter,
    segment_durations_ms: list[int],
    segment_words: list[list[WordTiming]],
    chapter_duration_ms: int | None = None,
) -> ChapterTiming:
    if not (len(segment_durations_ms) == len(segment_words) == len(chapter.segments)):
        raise ValueError("segment durations, words and segments must have the same length")
    if chapter_duration_ms is not None and chapter_duration_ms <= 0:
        raise ValueError("chapter_duration_ms must be positive")

    segments: list[SegmentTiming] = []
    cursor = 0
    for segment, duration_ms, words in zip(
        chapter.segments, segment_durations_ms, segment_words, strict=True
    ):
        if duration_ms <= 0:
            raise ValueError(f"segment {segment.id} must have a positive duration")
        exact = bool(words)
        relative_words = (
            scale_words(words, duration_ms)
            if exact
            else estimate_word_timings(segment.text, duration_ms)
        )
        absolute_words = [
            WordTiming(
                text=word.text,
                start_ms=cursor + word.start_ms,
                end_ms=cursor + word.end_ms,
            )
            for word in relative_words
        ]
        segments.append(
            SegmentTiming(
                id=segment.id,
                start_ms=cursor,
                end_ms=cursor + duration_ms,
                precision="exact" if exact else "estimated",
                words=absolute_words,
            )
        )
        cursor += duration_ms

    total_ms = cursor
    precision: Precision = (
        "exact" if segments and all(item.precision == "exact" for item in segments) else "estimated"
    )
    if chapter_duration_ms is not None and total_ms > 0:
        segments = _scale_segments(segments, chapter_duration_ms)
        total_ms = chapter_duration_ms

    return ChapterTiming(
        chapter_index=chapter.index,
        duration_ms=total_ms,
        precision=precision,
        segments=segments,
    )


def write_chapter_timing(path: Path, timing: ChapterTiming) -> None:
    payload = {
        "schema_version": 1,
        "chapter_index": timing.chapter_index,
        "duration_ms": timing.duration_ms,
        "precision": timing.precision,
        "segments": [
            {
                "id": segment.id,
                "start_ms": segment.start_ms,
                "end_ms": segment.end_ms,
                "precision": segment.precision,
                "words": [asdict(word) for word in segment.words],
            }
            for segment in timing.segments
        ],
    }
    _write_json_atomic(path, payload)


def segment_timing_path(audio_path: Path) -> Path:
    return audio_path.with_suffix(".timing.json")


def write_word_timings(path: Path, words: list[WordTiming]) -> None:
    _write_json_atomic(
        path,
        {"schema_version": 1, "words": [asdict(word) for word in words]},
    )


def read_word_timings(path: Path) -> list[WordTiming]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return [
            WordTiming(
                text=word["text"],
                start_ms=int(word["start_ms"]),
                end_ms=int(word["end_ms"]),
            )
            for word in payload.get("words", [])
        ]
    except (OSError, ValueError, KeyError, TypeError):
        return []


def audio_duration_ms(path: Path) -> int:
    try:
        audio = MutagenFile(path)
    except MutagenError as exc:
        raise ValueError(f"Could not read duration from {path}") from exc
    if audio is None or audio.info is None or audio.info.length <= 0:
        raise ValueError(f"Could not read duration from {path}")
    return int(round(audio.info.length * 1000))


def read_chapter_timing(path: Path) -> ChapterTiming:
    payload = json.loads(path.read_text(encoding="utf-8"))
    segments = [
        SegmentTiming(
            id=segment["id"],
            start_ms=int(segment["start_ms"]),
            end_ms=int(segment["end_ms"]),
            precision=cast(Precision, segment["precision"]),
            words=[
                WordTiming(
                    text=word["text"],
                    start_ms=int(word["start_ms"]),
                    end_ms=int(word["end_ms"]),
                )
                for word in segment.get("words", [])
            ],
        )
        for segment in payload.get("segments", [])
    ]
    return ChapterTiming(
        chapter_index=int(payload["chapter_index"]),
        duration_ms=int(payload["duration_ms"]),
        precision=cast(Precision, payload["precision"]),
        segments=segments,
    )


def _scale_segments(segments: list[SegmentTiming], duration_ms: int) -> list[SegmentTiming]:
    total_ms = segments[-1].end_ms
    if total_ms <= 0:
        return segments
    factor = duration_ms / total_ms
    scaled: list[SegmentTiming] = []
    cursor = 0
    for index, segment in enumerate(segments):
        start = cursor
        if index == len(segments) - 1:
            end = duration_ms
        else:
            end = min(duration_ms, max(start + 1, round(segment.end_ms * factor)))
        relative_words = [
            WordTiming(
                text=word.text,
                start_ms=word.start_ms - segment.start_ms,
                end_ms=word.end_ms - segment.start_ms,
            )
            for word in segment.words
        ]
        words = [
            WordTiming(
                text=word.text,
                start_ms=start + word.start_ms,
                end_ms=start + word.end_ms,
            )
            for word in scale_words(relative_words, end - start)
        ]
        scaled.append(
            SegmentTiming(
                id=segment.id,
                start_ms=start,
                end_ms=end,
                precision=segment.precision,
                words=words,
            )
        )
        cursor = end
    return scaled


def _write_json_atomic(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, path)


def _word_weight(word: str) -> float:
    weight = float(max(1, len(word)))
    if _COMMA_PAUSE.search(word):
        return weight * 1.3
    if _SENTENCE_PAUSE.search(word):
        return weight * 2.2
    return weight
