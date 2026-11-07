import hashlib
import os
import re
import time
import unicodedata
from pathlib import Path

from audiol.assemble import build_m4b, concat_to_mp3, require_ffmpeg
from audiol.chunk import chunk_text
from audiol.clean import clean_paragraph_items
from audiol.manifest import write_manifest
from audiol.models import Book, Chapter, Segment, make_segment_id
from audiol.tts.base import TTSProvider


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
) -> None:
    if max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")
    for attempt in range(1, max_attempts + 1):
        try:
            provider.synthesize(text, voice, out_path, style=style, rate=rate)
            return
        except ValueError:
            out_path.unlink(missing_ok=True)
            raise
        except Exception:
            out_path.unlink(missing_ok=True)
            if attempt == max_attempts:
                raise
            time.sleep(retry_delay * (2 ** (attempt - 1)))


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
) -> Path:
    require_ffmpeg()
    if not book.chapters:
        raise ValueError("No chapters to convert")
    out_dir.mkdir(parents=True, exist_ok=True)
    audio_dir = out_dir / "audio"
    segments_dir = audio_dir / "segments"
    chapters_dir = audio_dir / "chapters"
    segments_dir.mkdir(parents=True, exist_ok=True)
    chapters_dir.mkdir(parents=True, exist_ok=True)

    write_manifest(book, out_dir, voice, engine, style=style, rate=rate)

    chapter_files: list[Path] = []
    for chapter in book.chapters:
        segment_files: list[Path] = []
        for segment in chapter.segments:
            key = cache_key(segment, voice, engine, style, rate)
            path = segments_dir / f"{segment.id}_{key}{provider.audio_suffix}"
            if not force and not path.exists():
                cached = next(segments_dir.glob(f"*_{key}{provider.audio_suffix}"), None)
                if cached is not None:
                    path = cached
            if force or not path.exists() or path.stat().st_size == 0:
                temp_path = path.with_name(f"{path.name}.part")
                try:
                    synthesize_with_retries(
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
            segment_files.append(path)

        chapter_path = chapters_dir / f"chapter_{chapter.index:03d}.mp3"
        concat_to_mp3(segment_files, chapter_path, audio_dir)
        chapter_files.append(chapter_path)

    m4b_path = out_dir / f"{slugify(book.title)}.m4b"
    build_m4b(
        chapter_files,
        [chapter.title for chapter in book.chapters],
        {"title": book.title, "author": book.author},
        m4b_path,
        audio_dir,
    )
    return m4b_path


def slugify(text: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_text).strip("-").lower()
    return slug or "audiolibro"
