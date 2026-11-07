import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from audiol.models import Book

SCHEMA_VERSION = 2


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
) -> Path:
    if chapter_durations_ms is not None and len(chapter_durations_ms) != len(book.chapters):
        raise ValueError("chapter_durations_ms must have one duration per chapter")

    total_duration_ms = sum(chapter_durations_ms) if chapter_durations_ms is not None else None
    data = {
        "schema_version": SCHEMA_VERSION,
        "id": book_id or "book",
        "title": book.title,
        "author": book.author,
        "language": book.language,
        "created_at": datetime.now(UTC).isoformat(),
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
                    if chapter_durations_ms is not None
                    else None
                ),
                "segments": [asdict(segment) for segment in chapter.segments],
            }
            for position, chapter in enumerate(book.chapters)
        ],
    }
    path = out_dir / "manifest.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
