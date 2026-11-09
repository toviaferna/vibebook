from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from audiol.assemble import (
    build_m4b,
    calibrate_encoder_delay_ms,
    concat_pcm_to_mp3,
)
from audiol.convert import cache_key, measure_duration_ms, synthesize_with_retries
from audiol.ingest.epub import read_epub
from audiol.manifest import (
    DEFAULT_MAX_CHARS,
    SEGMENTATION_VERSION,
    book_from_manifest,
    load_manifest,
    write_manifest,
)
from audiol.models import Book, Segment
from audiol.naming import slugify
from audiol.timing import (
    build_chapter_timing_from_offsets,
    read_word_timings,
    segment_timing_path,
    write_chapter_timing,
    write_word_timings,
)
from audiol.tts.base import TTSProvider
from audiol.tts.factory import make_provider

BACKUP_PREFIX = "segments-"
BACKUP_META = "backup.json"
AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a", ".ogg", ".opus", ".flac"}


class ResegmentError(RuntimeError):
    pass


@dataclass(frozen=True)
class ChapterDiff:
    index: int
    title: str
    changed: bool
    changed_segments: int
    added_segments: int
    removed_segments: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "title": self.title,
            "changed": self.changed,
            "changed_segments": self.changed_segments,
            "added_segments": self.added_segments,
            "removed_segments": self.removed_segments,
        }


@dataclass(frozen=True)
class ResegmentPlan:
    book_id: str
    title: str
    status: str
    can_repair: bool
    needs_repair: bool
    reason: str | None
    current_version: int | None
    target_version: int
    max_chars: int
    source_available: bool
    old_segments: int
    new_segments: int
    changed_segments: int
    chapters: list[ChapterDiff] = field(default_factory=list)

    @property
    def changed_chapters(self) -> list[int]:
        return [chapter.index for chapter in self.chapters if chapter.changed]

    @property
    def changed_chapter_count(self) -> int:
        return len(self.changed_chapters)

    def as_dict(self) -> dict[str, Any]:
        return {
            "book_id": self.book_id,
            "title": self.title,
            "status": self.status,
            "can_repair": self.can_repair,
            "needs_repair": self.needs_repair,
            "reason": self.reason,
            "current_version": self.current_version,
            "target_version": self.target_version,
            "max_chars": self.max_chars,
            "source_available": self.source_available,
            "old_segments": self.old_segments,
            "new_segments": self.new_segments,
            "changed_segments": self.changed_segments,
            "changed_chapters": self.changed_chapters,
            "chapters": [chapter.as_dict() for chapter in self.chapters],
        }


def analyze_resegmentation(book_dir: Path) -> ResegmentPlan:
    plan, _old_book, _new_book = _analyze(book_dir)
    return plan


def repair_segments(
    book_dir: Path,
    *,
    dry_run: bool = False,
    allow_fake: bool = False,
    provider: TTSProvider | None = None,
    max_attempts: int = 5,
    retry_delay: float = 2.0,
) -> dict[str, Any]:
    book_dir = Path(book_dir)
    plan, old_book, new_book = _analyze(book_dir)
    if not plan.can_repair:
        raise ResegmentError(_reason_message(plan.reason))
    if not plan.needs_repair:
        return {
            "changed": False,
            "dry_run": dry_run,
            "backup_id": None,
            **plan.as_dict(),
        }
    if dry_run:
        return {"changed": True, "dry_run": True, "backup_id": None, **plan.as_dict()}

    manifest = load_manifest(book_dir / "manifest.json")
    if plan.status != "ready":
        return _repair_metadata_only(book_dir, manifest, new_book, plan)

    resolved_provider = provider or make_provider(
        str(manifest.get("engine") or "edge"),
        allow_fake=allow_fake,
    )
    backup_id = _create_backup(book_dir, manifest, old_book, new_book, plan)
    try:
        result = _repair_audio(
            book_dir,
            manifest,
            old_book,
            new_book,
            plan,
            resolved_provider,
            max_attempts=max_attempts,
            retry_delay=retry_delay,
        )
    except BaseException:
        restore_resegmentation(book_dir, backup_id)
        raise
    _prune_stale_segments(book_dir, manifest, old_book, new_book, resolved_provider.audio_suffix)
    return {
        "changed": True,
        "dry_run": False,
        "backup_id": backup_id,
        **result,
    }


def list_backups(book_dir: Path) -> list[dict[str, Any]]:
    backups_dir = Path(book_dir) / "backups"
    if not backups_dir.is_dir():
        return []
    items: list[dict[str, Any]] = []
    for child in sorted(backups_dir.iterdir(), reverse=True):
        if not child.is_dir() or child.is_symlink() or not child.name.startswith(BACKUP_PREFIX):
            continue
        meta = _read_json(child / BACKUP_META)
        items.append(
            {
                "id": child.name,
                "created_at": meta.get("created_at") if meta else None,
                "reason": meta.get("reason") if meta else None,
                "changed_chapters": meta.get("changed_chapters", []) if meta else [],
            }
        )
    return items


def restore_resegmentation(book_dir: Path, backup_id: str | None = None) -> dict[str, Any]:
    book_dir = Path(book_dir)
    backups_dir = book_dir / "backups"
    if backup_id is None:
        backups = list_backups(book_dir)
        if not backups:
            raise ResegmentError("No hay copias de seguridad para restaurar")
        backup_id = backups[0]["id"]
    backup_dir = _safe_backup_dir(backups_dir, backup_id)
    if not backup_dir.is_dir():
        raise ResegmentError(f"No existe la copia de seguridad: {backup_id}")

    restored: list[str] = []
    for source in sorted(backup_dir.rglob("*")):
        if not source.is_file() or source.name == BACKUP_META:
            continue
        relative = source.relative_to(backup_dir)
        target = book_dir / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        restored.append(relative.as_posix())
    return {"backup_id": backup_id, "restored": restored}


def _analyze(book_dir: Path) -> tuple[ResegmentPlan, Book, Book]:
    book_dir = Path(book_dir)
    manifest = load_manifest(book_dir / "manifest.json")
    old_book = book_from_manifest(manifest)
    status = str(manifest.get("status", "imported"))
    current_version = _optional_int(manifest.get("segmentation_version"))
    max_chars = _optional_int(manifest.get("max_chars")) or DEFAULT_MAX_CHARS
    source_name = manifest.get("epub")
    source = book_dir / (source_name if isinstance(source_name, str) else "source.epub")
    source_available = source.is_file()
    base: dict[str, Any] = {
        "book_id": str(manifest.get("id") or book_dir.name),
        "title": str(manifest.get("title", "")),
        "status": status,
        "current_version": current_version,
        "target_version": SEGMENTATION_VERSION,
        "max_chars": max_chars,
        "source_available": source_available,
        "old_segments": sum(len(chapter.segments) for chapter in old_book.chapters),
    }
    if not source_available:
        return (
            ResegmentPlan(
                can_repair=False,
                needs_repair=False,
                reason="source_missing",
                new_segments=0,
                changed_segments=0,
                **base,
            ),
            old_book,
            old_book,
        )
    if status not in {"ready", "imported"}:
        return (
            ResegmentPlan(
                can_repair=False,
                needs_repair=False,
                reason="book_busy",
                new_segments=0,
                changed_segments=0,
                **base,
            ),
            old_book,
            old_book,
        )

    new_book = _prepare_from_source(source, max_chars, old_book)
    chapters = _diff_chapters(old_book, new_book)
    changed_segments = sum(
        chapter.changed_segments + chapter.added_segments for chapter in chapters
    )
    new_segments = sum(len(chapter.segments) for chapter in new_book.chapters)
    needs_repair = (
        current_version is None
        or current_version < SEGMENTATION_VERSION
        or changed_segments > 0
        or any(chapter.removed_segments for chapter in chapters)
        or len(new_book.chapters) != len(old_book.chapters)
    )
    plan = ResegmentPlan(
        can_repair=True,
        needs_repair=needs_repair,
        reason=None,
        new_segments=new_segments,
        changed_segments=changed_segments,
        chapters=chapters,
        **base,
    )
    return plan, old_book, new_book


def _prepare_from_source(source: Path, max_chars: int, old_book: Book) -> Book:
    from audiol.convert import prepare_book

    book = prepare_book(read_epub(source), max_chars=max_chars)
    book.toc = old_book.toc
    book.images = old_book.images
    return book


def _diff_chapters(old_book: Book, new_book: Book) -> list[ChapterDiff]:
    old_by_index = {chapter.index: chapter for chapter in old_book.chapters}
    diffs: list[ChapterDiff] = []
    for chapter in new_book.chapters:
        old = old_by_index.get(chapter.index)
        if old is None:
            diffs.append(
                ChapterDiff(
                    index=chapter.index,
                    title=chapter.title,
                    changed=True,
                    changed_segments=0,
                    added_segments=len(chapter.segments),
                    removed_segments=0,
                )
            )
            continue
        old_segments = {segment.id: segment for segment in old.segments}
        new_segments = {segment.id: segment for segment in chapter.segments}
        changed = sum(
            1
            for segment_id, segment in new_segments.items()
            if segment_id in old_segments and old_segments[segment_id].text != segment.text
        )
        added = sum(1 for segment_id in new_segments if segment_id not in old_segments)
        removed = sum(1 for segment_id in old_segments if segment_id not in new_segments)
        diffs.append(
            ChapterDiff(
                index=chapter.index,
                title=chapter.title,
                changed=bool(changed or added or removed),
                changed_segments=changed,
                added_segments=added,
                removed_segments=removed,
            )
        )
    known = {chapter.index for chapter in new_book.chapters}
    for chapter in old_book.chapters:
        if chapter.index not in known:
            diffs.append(
                ChapterDiff(
                    index=chapter.index,
                    title=chapter.title,
                    changed=True,
                    changed_segments=0,
                    added_segments=0,
                    removed_segments=len(chapter.segments),
                )
            )
    return sorted(diffs, key=lambda item: item.index)


def _repair_metadata_only(
    book_dir: Path,
    manifest: dict[str, Any],
    new_book: Book,
    plan: ResegmentPlan,
) -> dict[str, Any]:
    _write_repaired_manifest(
        book_dir,
        manifest,
        new_book,
        plan,
        chapter_durations_ms=None,
        timings_available=False,
    )
    return {
        "changed": True,
        "dry_run": False,
        "backup_id": None,
        "synthesized_segments": 0,
        "reused_segments": plan.new_segments,
        "rebuilt_chapters": [],
        "duration_ms": None,
        **plan.as_dict(),
    }


def _repair_audio(
    book_dir: Path,
    manifest: dict[str, Any],
    old_book: Book,
    new_book: Book,
    plan: ResegmentPlan,
    provider: TTSProvider,
    *,
    max_attempts: int,
    retry_delay: float,
) -> dict[str, Any]:
    audio_dir = book_dir / "audio"
    segments_dir = audio_dir / "segments"
    chapters_dir = audio_dir / "chapters"
    timings_dir = book_dir / "timings"
    segments_dir.mkdir(parents=True, exist_ok=True)
    chapters_dir.mkdir(parents=True, exist_ok=True)

    voice = str(manifest.get("voice") or "es-MX-JorgeNeural")
    engine = str(manifest.get("engine") or "edge")
    style = str(manifest.get("style") or "neutral")
    rate = str(manifest.get("rate") or "-10%")
    timings_available = any(
        isinstance(chapter, dict) and chapter.get("timing")
        for chapter in manifest.get("chapters", [])
    )
    timing_offset_ms = calibrate_encoder_delay_ms() if timings_available else 0

    changed = set(plan.changed_chapters)
    old_by_index = {
        int(chapter["index"]): chapter
        for chapter in manifest.get("chapters", [])
        if isinstance(chapter, dict) and "index" in chapter
    }
    chapter_files: list[Path] = []
    chapter_durations: list[int] = []
    rebuilt: list[int] = []
    synthesized = 0
    reused = 0

    for chapter in new_book.chapters:
        old_data = old_by_index.get(chapter.index)
        if chapter.index not in changed and old_data is not None:
            audio_path = _manifest_path(book_dir, old_data.get("audio"))
            if audio_path is not None and audio_path.is_file():
                chapter_files.append(audio_path)
                duration = _optional_int(old_data.get("duration_ms"))
                chapter_durations.append(duration or measure_duration_ms(audio_path))
                reused += len(chapter.segments)
                continue

        segment_files: list[Path] = []
        segment_words: list[list] = []
        for segment in chapter.segments:
            key = cache_key(segment, voice, engine, style, rate)
            path, duration, was_cached = _ensure_segment_audio(
                segments_dir,
                segment,
                key,
                provider,
                voice=voice,
                style=style,
                rate=rate,
                max_attempts=max_attempts,
                retry_delay=retry_delay,
            )
            if was_cached:
                reused += 1
            else:
                synthesized += 1
            segment_files.append(path)
            segment_words.append(
                read_word_timings(segment_timing_path(path)) if timings_available else []
            )

        chapter_path = chapters_dir / f"chapter_{chapter.index:03d}.mp3"
        assembly = concat_pcm_to_mp3(segment_files, chapter_path, audio_dir)
        chapter_files.append(chapter_path)
        duration = measure_duration_ms(chapter_path)
        chapter_durations.append(duration)
        if timings_available:
            timing = build_chapter_timing_from_offsets(
                chapter,
                assembly.offsets_ms,
                assembly.durations_ms,
                segment_words,
                chapter_duration_ms=assembly.total_ms,
                timing_offset_ms=timing_offset_ms,
            )
            write_chapter_timing(timings_dir / f"chapter_{chapter.index:03d}.json", timing)
        rebuilt.append(chapter.index)

    m4b_path = book_dir / f"{slugify(new_book.title)}.m4b"
    build_m4b(
        chapter_files,
        [chapter.title for chapter in new_book.chapters],
        {"title": new_book.title, "author": new_book.author},
        m4b_path,
        audio_dir,
    )
    _write_repaired_manifest(
        book_dir,
        manifest,
        new_book,
        plan,
        chapter_durations_ms=chapter_durations,
        timings_available=timings_available,
    )
    return {
        "synthesized_segments": synthesized,
        "reused_segments": reused,
        "rebuilt_chapters": rebuilt,
        "duration_ms": sum(chapter_durations),
        **plan.as_dict(),
    }


def _ensure_segment_audio(
    segments_dir: Path,
    segment: Segment,
    key: str,
    provider: TTSProvider,
    *,
    voice: str,
    style: str,
    rate: str,
    max_attempts: int,
    retry_delay: float,
) -> tuple[Path, int, bool]:
    path = segments_dir / f"{segment.id}_{key}{provider.audio_suffix}"
    for candidate in (path, next(segments_dir.glob(f"*_{key}{provider.audio_suffix}"), None)):
        if candidate is None or not candidate.is_file() or candidate.stat().st_size <= 0:
            continue
        try:
            return candidate, measure_duration_ms(candidate), True
        except Exception:
            if candidate == path:
                candidate.unlink(missing_ok=True)

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
            duration = measure_duration_ms(temp_path)
        except Exception as exc:
            raise RuntimeError(f"Provider returned invalid audio for segment {segment.id}") from exc
        os.replace(temp_path, path)
        write_word_timings(segment_timing_path(path), audio.words)
    except BaseException:
        temp_path.unlink(missing_ok=True)
        raise
    return path, duration, False


def _write_repaired_manifest(
    book_dir: Path,
    manifest: dict[str, Any],
    new_book: Book,
    plan: ResegmentPlan,
    *,
    chapter_durations_ms: list[int] | None,
    timings_available: bool,
) -> None:
    write_manifest(
        new_book,
        book_dir,
        str(manifest.get("voice") or "es-MX-JorgeNeural"),
        str(manifest.get("engine") or "edge"),
        style=str(manifest.get("style") or "neutral"),
        rate=str(manifest.get("rate") or "-10%"),
        status="ready" if chapter_durations_ms is not None else plan.status,
        book_id=plan.book_id,
        chapter_durations_ms=chapter_durations_ms,
        cover=_optional_str(manifest.get("cover")),
        source_epub=_optional_str(manifest.get("epub")),
        timings_available=timings_available,
        max_chars=plan.max_chars,
        segmentation_version=SEGMENTATION_VERSION,
    )


def _create_backup(
    book_dir: Path,
    manifest: dict[str, Any],
    old_book: Book,
    new_book: Book,
    plan: ResegmentPlan,
) -> str:
    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    backup_id = f"{BACKUP_PREFIX}{timestamp}-{uuid4().hex[:6]}"
    backup_dir = book_dir / "backups" / backup_id
    backup_dir.mkdir(parents=True, exist_ok=False)

    _copy_file(book_dir / "manifest.json", backup_dir / "manifest.json")
    for m4b in book_dir.glob("*.m4b"):
        _copy_file(m4b, backup_dir / m4b.name)

    changed = set(plan.changed_chapters)
    for chapter in old_book.chapters:
        if chapter.index not in changed:
            continue
        chapter_data = next(
            (
                item
                for item in manifest.get("chapters", [])
                if isinstance(item, dict) and int(item.get("index", -1)) == chapter.index
            ),
            None,
        )
        if chapter_data is None:
            continue
        for key in ("audio", "timing"):
            path = _manifest_path(book_dir, chapter_data.get(key))
            if path is not None and path.is_file():
                _copy_file(path, backup_dir / path.relative_to(book_dir))

    old_by_index = {chapter.index: chapter for chapter in old_book.chapters}
    new_by_index = {chapter.index: chapter for chapter in new_book.chapters}
    voice = str(manifest.get("voice") or "es-MX-JorgeNeural")
    engine = str(manifest.get("engine") or "edge")
    style = str(manifest.get("style") or "neutral")
    rate = str(manifest.get("rate") or "-10%")
    for index, old_chapter in old_by_index.items():
        new_chapter = new_by_index.get(index)
        new_segments = (
            {segment.id: segment for segment in new_chapter.segments} if new_chapter else {}
        )
        for old_segment in old_chapter.segments:
            new_segment = new_segments.get(old_segment.id)
            if new_segment is not None and new_segment.text == old_segment.text:
                continue
            old_key = cache_key(old_segment, voice, engine, style, rate)
            for path in _segment_audio_files(book_dir, old_segment.id, old_key):
                _copy_file(path, backup_dir / path.relative_to(book_dir))
                timing = segment_timing_path(path)
                if timing.is_file():
                    _copy_file(timing, backup_dir / timing.relative_to(book_dir))

    (backup_dir / BACKUP_META).write_text(
        json.dumps(
            {
                "created_at": datetime.now(UTC).isoformat(),
                "reason": "resegment",
                "changed_chapters": plan.changed_chapters,
                "changed_segments": plan.changed_segments,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return backup_id


def _prune_stale_segments(
    book_dir: Path,
    manifest: dict[str, Any],
    old_book: Book,
    new_book: Book,
    suffix: str,
) -> None:
    voice = str(manifest.get("voice") or "es-MX-JorgeNeural")
    engine = str(manifest.get("engine") or "edge")
    style = str(manifest.get("style") or "neutral")
    rate = str(manifest.get("rate") or "-10%")
    new_by_index = {chapter.index: chapter for chapter in new_book.chapters}
    for old_chapter in old_book.chapters:
        new_chapter = new_by_index.get(old_chapter.index)
        new_segments = (
            {segment.id: segment for segment in new_chapter.segments} if new_chapter else {}
        )
        for old_segment in old_chapter.segments:
            new_segment = new_segments.get(old_segment.id)
            if new_segment is not None and new_segment.text == old_segment.text:
                continue
            old_key = cache_key(old_segment, voice, engine, style, rate)
            if new_segment is not None:
                new_key = cache_key(new_segment, voice, engine, style, rate)
                if new_key == old_key:
                    continue
            for path in _segment_audio_files(book_dir, old_segment.id, old_key, suffix=suffix):
                path.unlink(missing_ok=True)
                segment_timing_path(path).unlink(missing_ok=True)


def _segment_audio_files(
    book_dir: Path,
    segment_id: str,
    key: str,
    *,
    suffix: str | None = None,
) -> list[Path]:
    segments_dir = book_dir / "audio" / "segments"
    if not segments_dir.is_dir():
        return []
    paths = sorted(segments_dir.glob(f"{segment_id}_{key}*"))
    return [path for path in paths if path.is_file() and (suffix is None or path.suffix == suffix)]


def _manifest_path(book_dir: Path, value: object) -> Path | None:
    if not isinstance(value, str) or not value:
        return None
    candidate = (book_dir / value).resolve()
    root = book_dir.resolve()
    if candidate == root or not candidate.is_relative_to(root):
        return None
    return candidate


def _safe_backup_dir(backups_dir: Path, backup_id: str) -> Path:
    if Path(backup_id).name != backup_id:
        raise ResegmentError("Identificador de copia inválido")
    candidate = (backups_dir / backup_id).resolve()
    if not candidate.is_relative_to(backups_dir.resolve()):
        raise ResegmentError("Identificador de copia inválido")
    return candidate


def _copy_file(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _optional_int(value: object) -> int | None:
    return int(value) if isinstance(value, int) else None


def _optional_str(value: object) -> str | None:
    return str(value) if isinstance(value, str) else None


def _reason_message(reason: str | None) -> str:
    if reason == "source_missing":
        return "El libro no tiene una copia del EPUB fuente"
    if reason == "book_busy":
        return "El libro no está listo para reparar"
    return "No se puede reparar la segmentación de este libro"
