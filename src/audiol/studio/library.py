import hashlib
import logging
import os
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import ebooklib
from ebooklib import epub

from audiol.convert import prepare_book, render_markdown
from audiol.ingest.epub import read_epub
from audiol.manifest import load_manifest, write_manifest
from audiol.naming import slugify

logger = logging.getLogger(__name__)

DEFAULT_VOICE = "es-MX-JorgeNeural"
DEFAULT_ENGINE = "edge"
DEFAULT_RATE = "-10%"
COVER_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


class LibraryError(Exception):
    pass


class InvalidEpubError(LibraryError):
    pass


class BookNotFound(LibraryError):
    pass


@dataclass(frozen=True)
class BookRecord:
    id: str
    title: str
    author: str
    language: str
    path: Path
    cover_path: Path | None
    status: str
    voice: str | None
    engine: str | None
    style: str | None
    rate: str | None
    chapter_count: int
    duration_ms: int | None
    created_at: str
    updated_at: str


class Library:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def import_epub(self, source: Path) -> BookRecord:
        source = Path(source)
        if not source.is_file():
            raise FileNotFoundError(source)
        try:
            book = prepare_book(read_epub(source))
        except Exception as exc:
            raise InvalidEpubError(f"Could not read EPUB {source}") from exc
        if not book.chapters:
            raise InvalidEpubError(f"EPUB has no readable chapters: {source}")

        digest = _sha256(source)
        book_id = f"{slugify(book.title)}-{digest[:8]}"
        target = self.root / book_id
        if target.exists():
            if (target / "manifest.json").is_file():
                return self._record_from_dir(target)
            raise LibraryError(f"Library entry exists but is invalid: {target}")

        temporary = self.root / f".import-{uuid4().hex}"
        temporary.mkdir()
        try:
            shutil.copyfile(source, temporary / "source.epub")
            (temporary / "book.md").write_text(render_markdown(book), encoding="utf-8")
            try:
                cover = extract_cover(source, temporary)
            except Exception:
                logger.warning("Could not extract cover from %s", source, exc_info=True)
                cover = None
            write_manifest(
                book,
                temporary,
                DEFAULT_VOICE,
                DEFAULT_ENGINE,
                status="imported",
                book_id=book_id,
                rate=DEFAULT_RATE,
                cover=cover.name if cover is not None else None,
                source_epub="source.epub",
            )
            try:
                os.replace(temporary, target)
            except OSError:
                if (target / "manifest.json").is_file():
                    shutil.rmtree(temporary, ignore_errors=True)
                    return self._record_from_dir(target)
                raise
        except BaseException:
            shutil.rmtree(temporary, ignore_errors=True)
            raise

        return self._record_from_dir(target)

    def scan(self) -> list[BookRecord]:
        records: list[BookRecord] = []
        root = self.root.resolve()
        for child in sorted(self.root.iterdir()):
            if not child.is_dir() or child.name.startswith(".") or child.is_symlink():
                continue
            try:
                resolved = child.resolve()
            except OSError:
                continue
            if not resolved.is_relative_to(root):
                logger.warning("Skipping library entry outside root: %s", child)
                continue
            manifest_path = resolved / "manifest.json"
            if not manifest_path.is_file():
                continue
            try:
                records.append(self._record_from_dir(resolved))
            except (OSError, ValueError, KeyError, TypeError, OverflowError) as exc:
                logger.warning("Skipping invalid library entry %s: %s", child, exc)
        return records

    def get(self, book_id: str) -> BookRecord:
        root = self.root.resolve()
        candidate = self.root / book_id
        if candidate.is_dir() and not candidate.is_symlink():
            try:
                resolved = candidate.resolve()
            except OSError:
                resolved = None
            if (
                resolved is not None
                and resolved.is_relative_to(root)
                and (resolved / "manifest.json").is_file()
            ):
                try:
                    record = self._record_from_dir(resolved)
                except (OSError, ValueError, KeyError, TypeError, OverflowError):
                    record = None
                if record is not None and record.id == book_id:
                    return record
        for record in self.scan():
            if record.id == book_id:
                return record
        raise BookNotFound(book_id)

    def delete(self, book_id: str) -> None:
        record = self.get(book_id)
        target = record.path.resolve()
        root = self.root.resolve()
        if target == root or not target.is_relative_to(root):
            raise LibraryError(f"Refusing to delete outside the library: {target}")
        try:
            shutil.rmtree(target)
        except OSError as exc:
            raise LibraryError(f"Could not delete {target}") from exc

    def asset_path(self, book_id: str, relative: str) -> Path:
        record = self.get(book_id)
        relative_path = Path(relative)
        if relative_path.is_absolute():
            raise LibraryError(f"Asset path must be relative: {relative}")
        library_root = self.root.resolve()
        book_root = record.path.resolve()
        if not book_root.is_relative_to(library_root):
            raise LibraryError(f"Book path escapes the library: {book_root}")
        resolved = (book_root / relative_path).resolve()
        if resolved == book_root or not resolved.is_relative_to(book_root):
            raise LibraryError(f"Asset path escapes the book: {relative}")
        return resolved

    def _record_from_dir(self, book_dir: Path) -> BookRecord:
        manifest_path = book_dir / "manifest.json"
        data = load_manifest(manifest_path)
        chapters = data.get("chapters", [])
        if not isinstance(chapters, list):
            raise ValueError("manifest chapters must be a list")

        created_at = data.get("created_at")
        if not isinstance(created_at, str):
            created_at = _mtime(manifest_path)
        updated_at = data.get("updated_at")
        if not isinstance(updated_at, str):
            updated_at = created_at

        cover_path = _cover_path(book_dir, data.get("cover"))
        status = data.get("status")
        if not isinstance(status, str):
            status = "ready" if _has_audio(book_dir, chapters) else "imported"

        return BookRecord(
            id=str(data.get("id") or book_dir.name),
            title=str(data.get("title", "")),
            author=str(data.get("author", "Desconocido")),
            language=str(data.get("language", "es")),
            path=book_dir,
            cover_path=cover_path,
            status=status,
            voice=_optional_str(data.get("voice")),
            engine=_optional_str(data.get("engine")),
            style=_optional_str(data.get("style")),
            rate=_optional_str(data.get("rate")),
            chapter_count=len(chapters),
            duration_ms=_optional_int(data.get("duration_ms")),
            created_at=created_at,
            updated_at=updated_at,
        )


def extract_cover(epub_path: Path, out_dir: Path) -> Path | None:
    raw = epub.read_epub(str(epub_path))
    covers = [item for item in raw.get_items() if item.get_type() == ebooklib.ITEM_COVER]
    if not covers:
        covers = [
            item
            for item in raw.get_items()
            if item.get_type() == ebooklib.ITEM_IMAGE and "cover" in item.get_name().lower()
        ]
    if not covers:
        return None

    item = covers[0]
    suffix = Path(item.get_name()).suffix.lower()
    if suffix not in COVER_SUFFIXES:
        suffix = ".jpg"
    output = out_dir / f"cover{suffix}"
    output.write_bytes(item.get_content())
    return output


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _mtime(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=UTC).isoformat()


def _cover_path(book_dir: Path, value: object) -> Path | None:
    root = book_dir.resolve()

    def allowed(candidate: Path) -> Path | None:
        try:
            resolved = candidate.resolve()
        except OSError:
            return None
        if resolved.is_relative_to(root) and resolved.is_file():
            return resolved
        return None

    if isinstance(value, str):
        candidate = allowed(book_dir / value)
        if candidate is not None:
            return candidate
    for suffix in sorted(COVER_SUFFIXES):
        candidate = allowed(book_dir / f"cover{suffix}")
        if candidate is not None:
            return candidate
    return None


def _has_audio(book_dir: Path, chapters: list) -> bool:
    for chapter in chapters:
        if not isinstance(chapter, dict):
            continue
        audio = chapter.get("audio")
        if isinstance(audio, str) and (book_dir / audio).is_file():
            return True
    return any((book_dir / "audio" / "chapters").glob("*.mp3"))


def _optional_str(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _optional_int(value: object) -> int | None:
    if not isinstance(value, (int, float)):
        return None
    try:
        return int(value)
    except (OverflowError, ValueError):
        return None
