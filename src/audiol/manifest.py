import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from audiol.models import Book, BookImage, Chapter, Segment, TocNode, make_segment_id
from audiol.storage import write_json_atomic

SCHEMA_VERSION = 2
SEGMENTATION_VERSION = 2
DEFAULT_MAX_CHARS = 400


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
                level=int(chapter_data.get("level", 1)),
                kind=str(chapter_data.get("kind", "chapter")),
                number=(
                    int(chapter_data["number"])
                    if isinstance(chapter_data.get("number"), int)
                    else None
                ),
                generated_title=bool(chapter_data.get("generated_title", False)),
            )
        )
    return Book(
        title=str(data.get("title", "")),
        author=str(data.get("author", "Desconocido")),
        language=str(data.get("language", "es-419")),
        chapters=chapters,
        toc=_toc_from_manifest(data.get("toc")),
        images=_images_from_manifest(data.get("images")),
    )


def _images_from_manifest(value: object) -> list[BookImage]:
    if not isinstance(value, list):
        return []
    result: list[BookImage] = []
    for item in value:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            continue
        result.append(
            BookImage(
                id=str(item["id"]),
                path=str(item["path"]) if isinstance(item.get("path"), str) else None,
                alt=str(item.get("alt", "")),
                caption=str(item["caption"]) if isinstance(item.get("caption"), str) else None,
                role=str(item.get("role", "illustration")),
                chapter_index=(
                    int(item["chapter_index"])
                    if isinstance(item.get("chapter_index"), int)
                    else None
                ),
                paragraph_index=int(item.get("paragraph_index", 0)),
                position=str(item.get("position", "after")),
                width=int(item["width"]) if isinstance(item.get("width"), int) else None,
                height=int(item["height"]) if isinstance(item.get("height"), int) else None,
            )
        )
    return result


def _toc_from_manifest(value: object) -> list[TocNode]:
    if not isinstance(value, list):
        return []
    result: list[TocNode] = []
    for item in value:
        if not isinstance(item, dict) or not isinstance(item.get("title"), str):
            continue
        result.append(
            TocNode(
                title=str(item["title"]),
                level=int(item.get("level", 1)),
                chapter_index=(
                    int(item["chapter_index"])
                    if isinstance(item.get("chapter_index"), int)
                    else None
                ),
                kind=str(item.get("kind", "chapter")),
                children=_toc_from_manifest(item.get("children")),
            )
        )
    return result


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
    max_chars: int = DEFAULT_MAX_CHARS,
    segmentation_version: int = SEGMENTATION_VERSION,
    m4b: str | None = None,
    preserve_from: dict | None = None,
) -> Path:
    if chapter_durations_ms is not None and len(chapter_durations_ms) != len(book.chapters):
        raise ValueError("chapter_durations_ms must have one duration per chapter")

    path = out_dir / "manifest.json"
    previous = preserve_from if preserve_from is not None else _read_manifest_dict(path)
    now = datetime.now(UTC).isoformat()
    total_duration_ms = sum(chapter_durations_ms) if chapter_durations_ms is not None else None
    data = {
        "schema_version": SCHEMA_VERSION,
        "id": book_id or "book",
        "title": book.title,
        "author": book.author,
        "language": book.language,
        "created_at": _created_at_from(previous) or _existing_created_at(path) or now,
        "updated_at": now,
        "status": status,
        "voice": voice,
        "engine": engine,
        "style": style,
        "rate": rate,
        "segmentation_version": segmentation_version,
        "max_chars": max_chars,
        "duration_ms": total_duration_ms,
        "cover": cover,
        "epub": source_epub,
        "m4b": m4b,
        "toc": [asdict(node) for node in book.toc],
        "images": [
            {
                "id": image.id,
                "path": image.path,
                "alt": image.alt,
                "caption": image.caption,
                "role": image.role,
                "chapter_index": image.chapter_index,
                "paragraph_index": image.paragraph_index,
                "position": image.position,
                "width": image.width,
                "height": image.height,
            }
            for image in book.images
            if image.path is not None
        ],
        "chapters": [
            {
                "index": chapter.index,
                "title": chapter.title,
                "level": chapter.level,
                "kind": chapter.kind,
                "number": chapter.number,
                "generated_title": chapter.generated_title,
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
    for key, value in previous.items():
        data.setdefault(key, value)
    write_json_atomic(path, data)
    return path


def _existing_created_at(path: Path) -> str | None:
    data = _read_manifest_dict(path)
    return _created_at_from(data)


def _read_manifest_dict(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _created_at_from(data: dict) -> str | None:
    value = data.get("created_at")
    return value if isinstance(value, str) else None
