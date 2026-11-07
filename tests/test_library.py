import json
from pathlib import Path

import pytest

from audiol.manifest import load_manifest
from audiol.studio.library import (
    BookNotFound,
    InvalidEpubError,
    Library,
    LibraryError,
)


@pytest.fixture
def library(tmp_path: Path) -> Library:
    return Library(tmp_path / "library")


def test_import_creates_book_folder_and_imported_manifest(library: Library, tiny_epub: Path):
    record = library.import_epub(tiny_epub)

    assert record.id.startswith("libro-de-prueba-")
    assert record.path.is_dir()
    assert record.status == "imported"
    assert record.chapter_count == 2
    assert record.cover_path is None
    assert (record.path / "source.epub").exists()
    assert (record.path / "book.md").exists()

    manifest = load_manifest(record.path / "manifest.json")
    assert manifest["id"] == record.id
    assert manifest["status"] == "imported"
    assert manifest["epub"] == "source.epub"
    assert len(manifest["chapters"]) == 2


def test_import_same_epub_is_idempotent(library: Library, tiny_epub: Path):
    first = library.import_epub(tiny_epub)
    second = library.import_epub(tiny_epub)

    assert second == first
    assert len([path for path in library.root.iterdir() if path.is_dir()]) == 1


def test_import_extracts_cover(library: Library, cover_epub: Path):
    record = library.import_epub(cover_epub)

    assert record.cover_path is not None
    assert record.cover_path.exists()
    assert record.cover_path.name == "cover.jpg"
    manifest = load_manifest(record.path / "manifest.json")
    assert manifest["cover"] == "cover.jpg"


def test_import_without_cover_returns_none(library: Library, tiny_epub: Path):
    assert library.import_epub(tiny_epub).cover_path is None


def test_import_rejects_invalid_epub(library: Library, tmp_path: Path):
    invalid = tmp_path / "invalid.epub"
    invalid.write_text("not an epub", encoding="utf-8")

    with pytest.raises(InvalidEpubError):
        library.import_epub(invalid)

    assert not list(library.root.glob(".import-*"))


def test_import_rejects_missing_file(library: Library, tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        library.import_epub(tmp_path / "missing.epub")


def test_import_handles_unicode_and_spaces(tmp_path: Path, tiny_epub: Path):
    library = Library(tmp_path / "biblioteca de Tøvia")
    record = library.import_epub(tiny_epub)

    assert record.path.exists()
    assert "biblioteca de Tøvia" in str(record.path)


def test_scan_ignores_invalid_manifests(library: Library, tiny_epub: Path):
    library.import_epub(tiny_epub)
    broken = library.root / "broken"
    broken.mkdir()
    (broken / "manifest.json").write_text("{not json", encoding="utf-8")

    records = library.scan()

    assert [record.id for record in records] == [record.id for record in library.scan()]
    assert len(records) == 1


def test_scan_infers_imported_status_for_legacy_manifest(library: Library, tiny_epub: Path):
    record = library.import_epub(tiny_epub)
    manifest_path = record.path / "manifest.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    del data["status"]
    manifest_path.write_text(json.dumps(data), encoding="utf-8")

    scanned = library.get(record.id)

    assert scanned.status == "imported"


def test_delete_removes_book(library: Library, tiny_epub: Path):
    record = library.import_epub(tiny_epub)

    library.delete(record.id)

    assert not record.path.exists()
    with pytest.raises(BookNotFound):
        library.get(record.id)


def test_get_unknown_book_raises(library: Library):
    with pytest.raises(BookNotFound):
        library.get("does-not-exist")


def test_asset_path_rejects_traversal(library: Library, tiny_epub: Path):
    record = library.import_epub(tiny_epub)

    with pytest.raises(LibraryError):
        library.asset_path(record.id, "../secret")
    with pytest.raises(LibraryError):
        library.asset_path(record.id, str((library.root / "outside").resolve()))


def test_asset_path_resolves_existing_file(library: Library, tiny_epub: Path):
    record = library.import_epub(tiny_epub)

    path = library.asset_path(record.id, "source.epub")

    assert path == (record.path / "source.epub").resolve()
