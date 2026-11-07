import json
import os
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from audiol.models import Book, Chapter, Segment, make_segment_id

SCHEMA_VERSION = 2


def load_manifest(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError(f"Invalid manifest at {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"Invalid manifest at {path}: expected a JSON object")
    chapters = data.get("chapters")
    if not isinstance(chapters, list):
        raise ValueError(f"Invalid manifest at {path}: missing chapters")
    return data


def book_from_manifest(data: dict) -> Book:
    chapters: list[Chapter] = []
    for chapter_data in data.get("chapters", []):
        if not isinstance(chapter_data, dict):
            raise ValueError("Invalid manifest: chapter must be an object")
        chapter_index = int(chapter_data.get("index", len(chapters) + 1))
        segments: list[Segment] = []
        for position, segment_data in enumerate(chapter_data.get("segments", []), start=1):
            if not isinstance(segment_data, dict) or "text" not in segment_data:
                raise ValueError("Invalid manifest: segment must have text")
            paragraph_index = int(segment_data.get("paragraph_index", position))
            chunk_index = int(segment_data.get("chunk_index", 0))
            segments.append(
                Segment(
                    id=segment_data.get(
                        "id", make_segment_id(chapter_index, paragraph_index, chunk_index)
                    ),
                    chapter_index=int(segment_data.get("chapter_index", chapter_index)),
                    paragraph_index=paragraph_index,
                    text=str(segment_data["text"]),
                    chunk_index=chunk_index,
                    source_href=segment_data.get("source_href"),
                    source_fragment=segment_data.get("source_fragment"),
                )
            )
        chapters.append(
            Chapter(
                index=chapter_index,
                title=str(chapter_data.get("title", f"Capítulo {chapter_index}")),
                segments=segments,
                source_href=chapter_data.get("source_href"),
                source_fragment=chapter_data.get("source_fragment"),
            )
        )
    return Book(
        title=str(data.get("title", "")),
        author=str(data.get("author", "Desconocido")),
        language=str(data.get("language", "es-419")),
        chapters=chapters,
    )


def write_manifest(
    book: Book,
    out_dir: Path,
    voice: str,
    engine: str,
    *,
    style: str = "neutral",
    rate: str = "+0%",
    status: str = "ready",
    book_id: str | None = None,
    chapter_durations_ms: list[int] | None = None,
    cover: str | None = None,
    source_epub: str | None = None,
    timings_available: bool = True,
) -> Path:
    if chapter_durations_ms is not None and len(chapter_durations_ms) != len(book.chapters):
        raise ValueError("chapter_durations_ms must have one duration per chapter")

    path = out_dir / "manifest.json"
    now = datetime.now(UTC).isoformat()
    total_duration_ms = sum(chapter_durations_ms) if chapter_durations_ms is not None else None
    data = {
        "schema_version": SCHEMA_VERSION,
        "id": book_id or "book",
        "title": book.title,
        "author": book.author,
        "language": book.language,
        "created_at": _existing_created_at(path) or now,
        "updated_at": now,
        "status": status,
        "voice": voice,
        "engine": engine,
        "style": style,
        "rate": rate,
        "duration_ms": total_duration_ms,
        "cover": cover,
        "epub": source_epub,
        "chapters": [
            {
                "index": chapter.index,
                "title": chapter.title,
                "duration_ms": (
                    chapter_durations_ms[position] if chapter_durations_ms is not None else None
                ),
                "audio": (
                    f"audio/chapters/chapter_{chapter.index:03d}.mp3"
                    if chapter_durations_ms is not None
                    else None
                ),
                "timing": (
                    f"timings/chapter_{chapter.index:03d}.json"
                    if chapter_durations_ms is not None and timings_available
                    else None
                ),
                "segments": [asdict(segment) for segment in chapter.segments],
            }
            for position, chapter in enumerate(book.chapters)
        ],
    }
    temporary = path.with_name(f"{path.name}.tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, path)
    return path


def _existing_created_at(path: Path) -> str | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if isinstance(data, dict) and isinstance(data.get("created_at"), str):
        return data["created_at"]
    return None
