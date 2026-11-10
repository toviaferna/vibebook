import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal, cast

from mutagen import File as MutagenFile
from mutagen import MutagenError

from audiol.models import Chapter, WordTiming
from audiol.storage import write_json_atomic

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
    timing_offset_ms: int = 0
    text_hash: str | None = None
    config_hash: str | None = None


def chapter_text_hash(chapter: Chapter) -> str:
    payload = "\x00".join(f"{segment.id}:{segment.text}" for segment in chapter.segments)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def estimate_word_timings(text: str, duration_ms: int) -> list[WordTiming]:
    if duration_ms <= 0:
        raise ValueError("duration_ms must be positive")
    words = [match.group(0) for match in _WORD.finditer(text)]
    if not words:
        return []
    if duration_ms < len(words):
        raise ValueError("duration_ms is too short for the number of words")

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
    if duration_ms < len(words):
        raise ValueError("duration_ms is too short for the number of words")

    old_duration = max(1, words[-1].end_ms)
    factor = duration_ms / old_duration
    scaled: list[WordTiming] = []
    cursor = 0
    for index, word in enumerate(words):
        remaining = len(words) - index - 1
        max_end = duration_ms - remaining
        start = min(max(cursor, round(word.start_ms * factor)), max_end)
        if index == len(words) - 1:
            end = duration_ms
        else:
            end = min(max_end, max(start, round(word.end_ms * factor)))
        scaled.append(WordTiming(text=word.text, start_ms=start, end_ms=end))
        cursor = end
    return scaled


def build_chapter_timing_from_offsets(
    chapter: Chapter,
    segment_offsets_ms: list[int],
    segment_durations_ms: list[int],
    segment_words: list[list[WordTiming]],
    chapter_duration_ms: int | None = None,
    timing_offset_ms: int = 0,
    config_hash: str | None = None,
) -> ChapterTiming:
    if not (
        len(segment_offsets_ms)
        == len(segment_durations_ms)
        == len(segment_words)
        == len(chapter.segments)
    ):
        raise ValueError("segment offsets, durations, words and segments must have the same length")
    if chapter_duration_ms is not None and chapter_duration_ms <= 0:
        raise ValueError("chapter_duration_ms must be positive")

    segments: list[SegmentTiming] = []
    for segment, offset_ms, duration_ms, words in zip(
        chapter.segments,
        segment_offsets_ms,
        segment_durations_ms,
        segment_words,
        strict=True,
    ):
        if offset_ms < 0:
            raise ValueError(f"segment {segment.id} has a negative offset")
        if duration_ms <= 0:
            raise ValueError(f"segment {segment.id} must have a positive duration")
        exact = bool(words)
        relative_words = (
            _normalize_words(words, duration_ms)
            if exact
            else estimate_word_timings(segment.text, duration_ms)
        )
        segments.append(
            SegmentTiming(
                id=segment.id,
                start_ms=offset_ms,
                end_ms=offset_ms + duration_ms,
                precision="exact" if exact else "estimated",
                words=[
                    WordTiming(
                        text=word.text,
                        start_ms=offset_ms + word.start_ms,
                        end_ms=offset_ms + word.end_ms,
                    )
                    for word in relative_words
                ],
            )
        )

    total_ms = chapter_duration_ms if chapter_duration_ms is not None else 0
    if segments:
        total_ms = max(total_ms, segments[-1].end_ms)
    precision: Precision = (
        "exact" if segments and all(item.precision == "exact" for item in segments) else "estimated"
    )
    return ChapterTiming(
        chapter_index=chapter.index,
        duration_ms=total_ms,
        precision=precision,
        segments=segments,
        timing_offset_ms=timing_offset_ms,
        text_hash=chapter_text_hash(chapter),
        config_hash=config_hash,
    )


def _normalize_words(words: list[WordTiming], duration_ms: int) -> list[WordTiming]:
    if not words:
        return []
    if duration_ms < len(words):
        raise ValueError("duration_ms is too short for the number of words")
    normalized: list[WordTiming] = []
    cursor = 0
    for word in words:
        start = max(cursor, min(duration_ms - 1, max(0, word.start_ms)))
        end = min(duration_ms, max(start + 1, word.end_ms))
        normalized.append(WordTiming(text=word.text, start_ms=start, end_ms=end))
        cursor = end
    return normalized


def build_chapter_timing(
    chapter: Chapter,
    segment_durations_ms: list[int],
    segment_words: list[list[WordTiming]],
    chapter_duration_ms: int | None = None,
    config_hash: str | None = None,
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
        text_hash=chapter_text_hash(chapter),
        config_hash=config_hash,
    )


def ensure_chapter_timing(
    book_dir: Path,
    chapter: Chapter,
    chapter_duration_ms: int,
) -> ChapterTiming:
    if chapter_duration_ms <= 0:
        raise ValueError("chapter_duration_ms must be positive")
    if not chapter.segments:
        raise ValueError("chapter has no segments")
    path = book_dir / "timings" / f"chapter_{chapter.index:03d}.json"
    if path.exists():
        try:
            existing = read_chapter_timing(path)
        except (OSError, ValueError, KeyError, TypeError):
            existing = None
        if existing is not None and _timing_matches(existing, chapter, chapter_duration_ms):
            return existing

    durations = _distribute_duration(chapter, chapter_duration_ms)
    timing = build_chapter_timing(
        chapter,
        durations,
        [[] for _ in chapter.segments],
        chapter_duration_ms=chapter_duration_ms,
    )
    write_chapter_timing(path, timing)
    return timing


def write_chapter_timing(path: Path, timing: ChapterTiming) -> None:
    payload = {
        "schema_version": 2,
        "chapter_index": timing.chapter_index,
        "duration_ms": timing.duration_ms,
        "precision": timing.precision,
        "timing_offset_ms": timing.timing_offset_ms,
        "text_hash": timing.text_hash,
        "config_hash": timing.config_hash,
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
        if not isinstance(payload, dict):
            return []
        words = payload.get("words", [])
        if not isinstance(words, list):
            return []
        return [
            WordTiming(
                text=word["text"],
                start_ms=int(word["start_ms"]),
                end_ms=int(word["end_ms"]),
            )
            for word in words
        ]
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
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
    if not isinstance(payload, dict) or not isinstance(payload.get("segments", []), list):
        raise ValueError(f"Invalid chapter timing at {path}")
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
        timing_offset_ms=int(payload.get("timing_offset_ms", 0)),
        text_hash=payload.get("text_hash"),
        config_hash=payload.get("config_hash"),
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


def _timing_matches(timing: ChapterTiming, chapter: Chapter, chapter_duration_ms: int) -> bool:
    if len(timing.segments) != len(chapter.segments):
        return False
    if [segment.id for segment in timing.segments] != [segment.id for segment in chapter.segments]:
        return False
    if timing.text_hash is not None and timing.text_hash != chapter_text_hash(chapter):
        return False
    tolerance = max(250, chapter_duration_ms // 100)
    return abs(timing.duration_ms - chapter_duration_ms) <= tolerance


def _distribute_duration(chapter: Chapter, duration_ms: int) -> list[int]:
    count = len(chapter.segments)
    if duration_ms < count:
        raise ValueError("chapter duration is too short for its segments")
    total_chars = sum(max(1, len(segment.text)) for segment in chapter.segments)
    durations: list[int] = []
    previous = 0
    elapsed_chars = 0
    for index, segment in enumerate(chapter.segments):
        remaining = count - index - 1
        elapsed_chars += max(1, len(segment.text))
        if remaining == 0:
            end = duration_ms
        else:
            proportional = round(duration_ms * elapsed_chars / total_chars)
            end = min(duration_ms - remaining, max(previous + 1, proportional))
        durations.append(end - previous)
        previous = end
    return durations


def _write_json_atomic(path: Path, payload: dict) -> None:
    write_json_atomic(path, payload)


def _word_weight(word: str) -> float:
    weight = float(max(1, len(word)))
    if _COMMA_PAUSE.search(word):
        return weight * 1.3
    if _SENTENCE_PAUSE.search(word):
        return weight * 2.2
    return weight
