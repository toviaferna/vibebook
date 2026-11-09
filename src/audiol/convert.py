import hashlib
import logging
import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from audiol.assemble import (
    build_m4b,
    calibrate_encoder_delay_ms,
    concat_pcm_to_mp3,
    probe_duration,
    require_ffmpeg,
)
from audiol.chunk import chunk_text
from audiol.clean import clean_paragraph_items
from audiol.manifest import write_manifest
from audiol.models import Book, Chapter, Segment, WordTiming, make_segment_id
from audiol.naming import slugify
from audiol.timing import (
    audio_duration_ms,
    build_chapter_timing_from_offsets,
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
                    level=chapter.level,
                    kind=chapter.kind,
                    number=chapter.number,
                    generated_title=chapter.generated_title,
                )
            )
    return Book(
        title=book.title,
        author=book.author,
        language=book.language,
        chapters=chapters,
        toc=book.toc if len(chapters) == len(book.chapters) else [],
        images=book.images if len(chapters) == len(book.chapters) else [],
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
    max_chars: int = 400,
) -> ConversionResult:
    require_ffmpeg()
    if not book.chapters:
        raise ValueError("No chapters to convert")
    if should_cancel is not None and should_cancel():
        raise ConversionCancelled()

    out_dir.mkdir(parents=True, exist_ok=True)
    resolved_book_id = book_id or slugify(book.title)
    cover, source_epub = _manifest_assets(out_dir)
    had_manifest = (out_dir / "manifest.json").exists()

    try:
        return _convert_core(
            book=book,
            voice=voice,
            engine=engine,
            provider=provider,
            out_dir=out_dir,
            style=style,
            rate=rate,
            force=force,
            max_attempts=max_attempts,
            retry_delay=retry_delay,
            capture_timings=capture_timings,
            on_progress=on_progress,
            should_cancel=should_cancel,
            book_id=resolved_book_id,
            cover=cover,
            source_epub=source_epub,
            max_chars=max_chars,
        )
    except ConversionCancelled:
        _write_terminal_manifest(
            book,
            out_dir,
            voice,
            engine,
            style,
            rate,
            resolved_book_id,
            cover,
            source_epub,
            "interrupted",
            had_manifest,
            max_chars,
        )
        raise
    except KeyboardInterrupt:
        _write_terminal_manifest(
            book,
            out_dir,
            voice,
            engine,
            style,
            rate,
            resolved_book_id,
            cover,
            source_epub,
            "interrupted",
            had_manifest,
            max_chars,
        )
        raise
    except BaseException:
        _write_terminal_manifest(
            book,
            out_dir,
            voice,
            engine,
            style,
            rate,
            resolved_book_id,
            cover,
            source_epub,
            "error",
            had_manifest,
            max_chars,
        )
        raise


def _convert_core(
    *,
    book: Book,
    voice: str,
    engine: str,
    provider: TTSProvider,
    out_dir: Path,
    style: str,
    rate: str,
    force: bool,
    max_attempts: int,
    retry_delay: float,
    capture_timings: bool,
    on_progress: Callable[[ProgressEvent], None] | None,
    should_cancel: Callable[[], bool] | None,
    book_id: str,
    cover: str | None,
    source_epub: str | None,
    max_chars: int,
) -> ConversionResult:
    audio_dir = out_dir / "audio"
    segments_dir = audio_dir / "segments"
    chapters_dir = audio_dir / "chapters"
    timings_dir = out_dir / "timings"
    segments_dir.mkdir(parents=True, exist_ok=True)
    chapters_dir.mkdir(parents=True, exist_ok=True)

    total_segments = sum(len(chapter.segments) for chapter in book.chapters)
    completed_segments = 0
    cached_segments = 0
    chapter_files: list[Path] = []
    chapter_durations: list[int] = []
    timing_offset_ms = calibrate_encoder_delay_ms() if capture_timings else 0

    def emit(event: ProgressEvent) -> None:
        if on_progress is not None:
            on_progress(event)

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
        segment_words: list[list[WordTiming]] = []

        for segment in chapter.segments:
            if should_cancel is not None and should_cancel():
                raise ConversionCancelled()

            key = cache_key(segment, voice, engine, style, rate)
            path = segments_dir / f"{segment.id}_{key}{provider.audio_suffix}"
            cached = False
            if not force:
                if path.exists() and path.stat().st_size > 0:
                    cached = True
                else:
                    fallback = next(segments_dir.glob(f"*_{key}{provider.audio_suffix}"), None)
                    if fallback is not None and fallback.stat().st_size > 0:
                        path = fallback
                        cached = True

            duration_ms: int | None = None
            if cached:
                try:
                    duration_ms = measure_duration_ms(path)
                except Exception:
                    logger.warning(
                        "Cached segment %s is invalid; re-synthesizing",
                        path,
                        exc_info=True,
                    )
                    path.unlink(missing_ok=True)
                    cached = False

            if not cached:
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
                    try:
                        duration_ms = measure_duration_ms(temp_path)
                    except Exception as exc:
                        raise RuntimeError(
                            f"Provider returned invalid audio for segment {segment.id}"
                        ) from exc
                    os.replace(temp_path, path)
                except BaseException:
                    temp_path.unlink(missing_ok=True)
                    raise
                if capture_timings:
                    write_word_timings(segment_timing_path(path), audio.words)

            if duration_ms is None:
                raise RuntimeError(f"Could not determine duration for segment {segment.id}")

            segment_files.append(path)
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
        assembly = concat_pcm_to_mp3(segment_files, chapter_path, audio_dir)
        chapter_duration = measure_duration_ms(chapter_path)
        chapter_files.append(chapter_path)
        chapter_durations.append(chapter_duration)

        if capture_timings:
            timing = build_chapter_timing_from_offsets(
                chapter,
                assembly.offsets_ms,
                assembly.durations_ms,
                segment_words,
                chapter_duration_ms=assembly.total_ms,
                timing_offset_ms=timing_offset_ms,
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
        if should_cancel is not None and should_cancel():
            raise ConversionCancelled()

    if should_cancel is not None and should_cancel():
        raise ConversionCancelled()

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
    if not capture_timings:
        for stale in timings_dir.glob("chapter_*.json"):
            stale.unlink(missing_ok=True)

    duration_ms = sum(chapter_durations)
    write_manifest(
        book,
        out_dir,
        voice,
        engine,
        style=style,
        rate=rate,
        status="ready",
        book_id=book_id,
        chapter_durations_ms=chapter_durations,
        cover=cover,
        source_epub=source_epub,
        timings_available=capture_timings,
        max_chars=max_chars,
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


def _write_terminal_manifest(
    book: Book,
    out_dir: Path,
    voice: str,
    engine: str,
    style: str,
    rate: str,
    book_id: str,
    cover: str | None,
    source_epub: str | None,
    status: str,
    had_manifest: bool,
    max_chars: int,
) -> None:
    if had_manifest:
        return
    try:
        write_manifest(
            book,
            out_dir,
            voice,
            engine,
            style=style,
            rate=rate,
            status=status,
            book_id=book_id,
            cover=cover,
            source_epub=source_epub,
            timings_available=False,
            max_chars=max_chars,
        )
    except Exception:
        logger.exception("Could not write terminal manifest with status %s", status)


def _manifest_assets(out_dir: Path) -> tuple[str | None, str | None]:
    cover = next((path.name for path in out_dir.glob("cover.*") if path.is_file()), None)
    source_epub = "source.epub" if (out_dir / "source.epub").is_file() else None
    return cover, source_epub
