import json
from dataclasses import asdict
from pathlib import Path

from audiol.models import Book


def write_manifest(
    book: Book,
    out_dir: Path,
    voice: str,
    engine: str,
) -> Path:
    data = {
        "title": book.title,
        "author": book.author,
        "language": book.language,
        "voice": voice,
        "engine": engine,
        "chapters": [
            {
                "index": chapter.index,
                "title": chapter.title,
                "segments": [asdict(segment) for segment in chapter.segments],
            }
            for chapter in book.chapters
        ],
    }
    path = out_dir / "manifest.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
