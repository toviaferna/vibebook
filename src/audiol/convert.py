import hashlib
import logging
import os
import re
import time
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from audiol.assemble import build_m4b, concat_to_mp3, probe_duration, require_ffmpeg
from audiol.chunk import chunk_text
from audiol.clean import clean_paragraph_items
from audiol.manifest import write_manifest
from audiol.models import Book, Chapter, Segment, WordTiming, make_segment_id
from audiol.timing import (
    audio_duration_ms,
    build_chapter_timing,
    read_word_timings,
    segment_timing_path,
    write_chapter_timing,
    write_word_timings,
)
from audiol.tts.base import AudioResult, TTSProvider

logger = logging.getLogger(__name__)

ProgressStage = Literal["preparing", "synthesizing", "assembling", "finalizing", "done"]


@dataclass(frozen=True)
class ProgressEvent:
    stage: ProgressStage
    completed_segments: int
    total_segments: int
    chapter_index: int
    chapter_title: str
    segment_id: str | None = None
    text: str | None = None
    message: str | None = None


@dataclass(frozen=True)
class ConversionResult:
    m4b_path: Path
    out_dir: Path
    total_segments: int
    cached_segments: int
    duration_ms: int


class ConversionCancelled(Exception):
    pass


def prepare_book(book: Book, max_chars: int = 400) -> Book:
    chapters: list[Chapter] = []
    for chapter in book.chapters:
        paragraphs = clean_paragraph_items((segment.text, segment) for segment in chapter.segments)
        segments: list[Segment] = []
        for paragraph_index, (paragraph, source) in enumerate(paragraphs, start=1):
            for chunk_index, text in enumerate(chunk_text(paragraph, max_chars=max_chars)):
                segments.append(
                    Segment(
                        id=make_segment_id(chapter.index, paragraph_index, chunk_index),
                        chapter_index=chapter.index,
                        paragraph_index=paragraph_index,
                        text=text,
                        chunk_index=chunk_index,
                        source_href=source.source_href,
                        source_fragment=source.source_fragment,
                    )
                )
        if segments:
            chapters.append(
                Chapter(
                    index=chapter.index,
                    title=chapter.title,
                    segments=segments,
                    source_href=chapter.source_href,
                    source_fragment=chapter.source_fragment,
                )
            )
    return Book(
        title=book.title,
        author=book.author,
        language=book.language,
        chapters=chapters,
    )


def render_markdown(book: Book) -> str:
    lines = [f"# {book.title}", "", f"*{book.author}*", ""]
    for chapter in book.chapters:
        lines.extend([f"## {chapter.title}", ""])
        for segment in chapter.segments:
            lines.extend([segment.text, ""])
    return "\n".join(lines).rstrip() + "\n"


def cache_key(segment: Segment, voice: str, engine: str, style: str, rate: str) -> str:
    payload = f"{segment.text}|{voice}|{engine}|{style}|{rate}".encode()
    return hashlib.sha256(payload).hexdigest()[:16]


def synthesize_with_retries(
    provider: TTSProvider,
    text: str,
    voice: str,
    out_path: Path,
    style: str,
    rate: str,
    max_attempts: int = 5,
    retry_delay: float = 2.0,
) -> AudioResult:
    if max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")
    for attempt in range(1, max_attempts + 1):
        try:
            return provider.synthesize(text, voice, out_path, style=style, rate=rate)
        except ValueError:
            out_path.unlink(missing_ok=True)
            raise
        except Exception:
            out_path.unlink(missing_ok=True)
            if attempt == max_attempts:
                raise
            time.sleep(retry_delay * (2 ** (attempt - 1)))
    raise RuntimeError("unreachable")


def measure_duration_ms(path: Path) -> int:
    try:
        return audio_duration_ms(path)
    except Exception:
        logger.debug("mutagen could not read %s; falling back to ffprobe", path, exc_info=True)
        return int(round(probe_duration(path) * 1000))


def convert(
    book: Book,
    voice: str,
    engine: str,
    provider: TTSProvider,
    out_dir: Path,
    style: str = "neutral",
    rate: str = "+0%",
    force: bool = False,
    max_attempts: int = 5,
    retry_delay: float = 2.0,
    capture_timings: bool = True,
    on_progress: Callable[[ProgressEvent], None] | None = None,
    should_cancel: Callable[[], bool] | None = None,
    book_id: str | None = None,
) -> ConversionResult:
    require_ffmpeg()
    if not book.chapters:
        raise ValueError("No chapters to convert")
    if should_cancel is not None and should_cancel():
        raise ConversionCancelled()

    out_dir.mkdir(parents=True, exist_ok=True)
    audio_dir = out_dir / "audio"
    segments_dir = audio_dir / "segments"
    chapters_dir = audio_dir / "chapters"
    timings_dir = out_dir / "timings"
    segments_dir.mkdir(parents=True, exist_ok=True)
    chapters_dir.mkdir(parents=True, exist_ok=True)

    resolved_book_id = book_id or slugify(book.title)
    cover, source_epub = _manifest_assets(out_dir)
    total_segments = sum(len(chapter.segments) for chapter in book.chapters)
    completed_segments = 0
    cached_segments = 0
    chapter_files: list[Path] = []
    chapter_durations: list[int] = []

    def emit(event: ProgressEvent) -> None:
        if on_progress is not None:
            on_progress(event)

    write_manifest(
        book,
        out_dir,
        voice,
        engine,
        style=style,
        rate=rate,
        status="converting",
        book_id=resolved_book_id,
        cover=cover,
        source_epub=source_epub,
    )
    emit(
        ProgressEvent(
            stage="preparing",
            completed_segments=0,
            total_segments=total_segments,
            chapter_index=0,
            chapter_title="",
            message="Preparando el libro",
        )
    )

    for chapter in book.chapters:
        segment_files: list[Path] = []
        segment_durations: list[int] = []
        segment_words: list[list[WordTiming]] = []

        for segment in chapter.segments:
            if should_cancel is not None and should_cancel():
                raise ConversionCancelled()

            key = cache_key(segment, voice, engine, style, rate)
            path = segments_dir / f"{segment.id}_{key}{provider.audio_suffix}"
            cached = False
            if not force and path.exists() and path.stat().st_size > 0:
                cached = True
            elif not force:
                fallback = next(segments_dir.glob(f"*_{key}{provider.audio_suffix}"), None)
                if fallback is not None and fallback.stat().st_size > 0:
                    path = fallback
                    cached = True

            if force or not path.exists() or path.stat().st_size == 0:
                temp_path = path.with_name(f"{path.name}.part")
                try:
                    audio = synthesize_with_retries(
                        provider,
                        segment.text,
                        voice,
                        temp_path,
                        style,
                        rate,
                        max_attempts=max_attempts,
                        retry_delay=retry_delay,
                    )
                    os.replace(temp_path, path)
                except BaseException:
                    temp_path.unlink(missing_ok=True)
                    raise
                if capture_timings:
                    write_word_timings(segment_timing_path(path), audio.words)
                cached = False

            segment_files.append(path)
            segment_durations.append(measure_duration_ms(path))
            segment_words.append(
                read_word_timings(segment_timing_path(path)) if capture_timings else []
            )
            completed_segments += 1
            if cached:
                cached_segments += 1
            emit(
                ProgressEvent(
                    stage="synthesizing",
                    completed_segments=completed_segments,
                    total_segments=total_segments,
                    chapter_index=chapter.index,
                    chapter_title=chapter.title,
                    segment_id=segment.id,
                    text=segment.text,
                    message=f"Sintetizando {completed_segments} de {total_segments}",
                )
            )

        if should_cancel is not None and should_cancel():
            raise ConversionCancelled()

        chapter_path = chapters_dir / f"chapter_{chapter.index:03d}.mp3"
        concat_to_mp3(segment_files, chapter_path, audio_dir)
        chapter_duration = measure_duration_ms(chapter_path)
        chapter_files.append(chapter_path)
        chapter_durations.append(chapter_duration)

        if capture_timings:
            timing = build_chapter_timing(
                chapter,
                segment_durations,
                segment_words,
                chapter_duration_ms=chapter_duration,
            )
            write_chapter_timing(timings_dir / f"chapter_{chapter.index:03d}.json", timing)

        emit(
            ProgressEvent(
                stage="assembling",
                completed_segments=completed_segments,
                total_segments=total_segments,
                chapter_index=chapter.index,
                chapter_title=chapter.title,
                message=f"Ensamblando {chapter.title}",
            )
        )

    emit(
        ProgressEvent(
            stage="finalizing",
            completed_segments=completed_segments,
            total_segments=total_segments,
            chapter_index=0,
            chapter_title="",
            message="Creando el M4B",
        )
    )

    m4b_path = out_dir / f"{slugify(book.title)}.m4b"
    build_m4b(
        chapter_files,
        [chapter.title for chapter in book.chapters],
        {"title": book.title, "author": book.author},
        m4b_path,
        audio_dir,
    )
    duration_ms = sum(chapter_durations)
    write_manifest(
        book,
        out_dir,
        voice,
        engine,
        style=style,
        rate=rate,
        status="ready",
        book_id=resolved_book_id,
        chapter_durations_ms=chapter_durations,
        cover=cover,
        source_epub=source_epub,
    )
    emit(
        ProgressEvent(
            stage="done",
            completed_segments=completed_segments,
            total_segments=total_segments,
            chapter_index=0,
            chapter_title="",
            message="Listo",
        )
    )
    return ConversionResult(
        m4b_path=m4b_path,
        out_dir=out_dir,
        total_segments=total_segments,
        cached_segments=cached_segments,
        duration_ms=duration_ms,
    )


def _manifest_assets(out_dir: Path) -> tuple[str | None, str | None]:
    cover = next((path.name for path in out_dir.glob("cover.*") if path.is_file()), None)
    source_epub = "source.epub" if (out_dir / "source.epub").is_file() else None
    return cover, source_epub


def slugify(text: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_text).strip("-").lower()
    return slug or "audiolibro"
