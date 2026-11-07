import json
from pathlib import Path

import pytest

from audiol.manifest import book_from_manifest, load_manifest
from audiol.models import Chapter, Segment, make_segment_id
from audiol.timing import ensure_chapter_timing, read_chapter_timing, write_chapter_timing


def _v1_manifest() -> dict:
    return {
        "title": "Libro viejo",
        "author": "Autora",
        "language": "es",
        "voice": "es-MX-JorgeNeural",
        "engine": "edge",
        "style": "neutral",
        "rate": "-10%",
        "chapters": [
            {
                "index": 1,
                "title": "Capítulo 1",
                "segments": [
                    {
                        "id": "c001p0001",
                        "chapter_index": 1,
                        "paragraph_index": 1,
                        "text": "Hola mundo.",
                    },
                    {
                        "id": "c001p0002",
                        "chapter_index": 1,
                        "paragraph_index": 2,
                        "text": "Adiós mundo.",
                    },
                ],
            }
        ],
    }


def test_load_manifest_reads_v1_without_schema_version(tmp_path: Path):
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(_v1_manifest()), encoding="utf-8")

    data = load_manifest(path)
    book = book_from_manifest(data)

    assert data["title"] == "Libro viejo"
    assert book.title == "Libro viejo"
    assert book.author == "Autora"
    assert len(book.chapters) == 1
    assert [segment.text for segment in book.chapters[0].segments] == [
        "Hola mundo.",
        "Adiós mundo.",
    ]
    assert [segment.chunk_index for segment in book.chapters[0].segments] == [0, 0]


def test_book_from_manifest_preserves_v2_segment_fields():
    data = _v1_manifest()
    data["schema_version"] = 2
    data["chapters"][0]["segments"][0].update(
        {
            "chunk_index": 1,
            "source_href": "chapter.xhtml",
            "source_fragment": "inicio",
        }
    )

    book = book_from_manifest(data)
    segment = book.chapters[0].segments[0]

    assert segment.chunk_index == 1
    assert segment.source_href == "chapter.xhtml"
    assert segment.source_fragment == "inicio"


def test_load_manifest_rejects_invalid_json(tmp_path: Path):
    path = tmp_path / "manifest.json"
    path.write_text("{not json", encoding="utf-8")

    with pytest.raises(ValueError):
        load_manifest(path)


def test_load_manifest_rejects_missing_chapters(tmp_path: Path):
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps({"title": "Libro"}), encoding="utf-8")

    with pytest.raises(ValueError):
        load_manifest(path)


def test_ensure_chapter_timing_writes_estimated_file(tmp_path: Path):
    chapter = Chapter(
        index=1,
        title="Capítulo 1",
        segments=[
            Segment(
                id=make_segment_id(1, 1),
                chapter_index=1,
                paragraph_index=1,
                text="Hola mundo.",
            ),
            Segment(
                id=make_segment_id(1, 2),
                chapter_index=1,
                paragraph_index=2,
                text="Adiós mundo.",
            ),
        ],
    )

    timing = ensure_chapter_timing(tmp_path, chapter, 2000)

    path = tmp_path / "timings" / "chapter_001.json"
    loaded = read_chapter_timing(path)
    assert path.exists()
    assert timing == loaded
    assert timing.precision == "estimated"
    assert timing.duration_ms == 2000
    assert timing.segments[0].start_ms == 0
    assert timing.segments[-1].end_ms == 2000
    assert timing.segments[0].words


def test_ensure_chapter_timing_reuses_existing_file(tmp_path: Path):
    chapter = Chapter(
        index=1,
        title="Capítulo 1",
        segments=[
            Segment(
                id=make_segment_id(1, 1),
                chapter_index=1,
                paragraph_index=1,
                text="Hola mundo.",
            )
        ],
    )
    path = tmp_path / "timings" / "chapter_001.json"
    write_chapter_timing(
        path,
        ensure_chapter_timing(tmp_path, chapter, 1000),
    )
    existing = read_chapter_timing(path)

    timing = ensure_chapter_timing(tmp_path, chapter, 9999)

    assert timing == existing
