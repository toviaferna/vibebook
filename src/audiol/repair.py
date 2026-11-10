from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from audiol.assemble import (
    PCM_SAMPLE_RATE,
    calibrate_encoder_delay_ms,
    concat_pcm_to_mp3,
)
from audiol.manifest import book_from_manifest, load_manifest
from audiol.storage import (
    backup_book_state,
    cleanup_staging,
    commit_staged_book,
    new_staging_dir,
)
from audiol.timing import (
    audio_duration_ms,
    build_chapter_timing_from_offsets,
    read_word_timings,
    segment_timing_path,
    write_chapter_timing,
)

AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a", ".ogg", ".opus", ".flac"}


class RepairError(RuntimeError):
    pass


def repair_book(book_dir: Path) -> dict[str, Any]:
    manifest = load_manifest(book_dir / "manifest.json")
    book = book_from_manifest(manifest)
    chapters = manifest.get("chapters", [])
    if not isinstance(chapters, list) or not chapters:
        raise RepairError("The manifest has no chapters")

    timing_offset_ms = calibrate_encoder_delay_ms(PCM_SAMPLE_RATE)
    rebuilt: list[int] = []
    skipped: list[int] = []
    durations: list[int] = []
    updates: list[dict[str, Any]] = []
    job_id = f"repair-{uuid4().hex}"
    staging = new_staging_dir(book_dir, job_id)
    chapters_dir = staging / "chapters"
    timings_dir = staging / "timings"

    try:
        for chapter, chapter_data in zip(book.chapters, chapters, strict=False):
            if not isinstance(chapter_data, dict):
                skipped.append(chapter.index)
                durations.append(0)
                continue
            files = _chapter_segment_files(book_dir, chapter)
            if files is None:
                skipped.append(chapter.index)
                durations.append(int(chapter_data.get("duration_ms") or 0))
                continue

            audio_rel = chapter_data.get("audio")
            if not isinstance(audio_rel, str):
                audio_rel = f"audio/chapters/chapter_{chapter.index:03d}.mp3"
            timing_rel = chapter_data.get("timing")
            if not isinstance(timing_rel, str):
                timing_rel = f"timings/chapter_{chapter.index:03d}.json"
            staged_audio = chapters_dir / Path(audio_rel).name
            staged_timing = timings_dir / Path(timing_rel).name

            assembly = concat_pcm_to_mp3(files, staged_audio, book_dir / "audio")
            words = [read_word_timings(segment_timing_path(path)) for path in files]
            timing = build_chapter_timing_from_offsets(
                chapter,
                assembly.offsets_ms,
                assembly.durations_ms,
                words,
                chapter_duration_ms=assembly.total_ms,
                timing_offset_ms=timing_offset_ms,
            )
            write_chapter_timing(staged_timing, timing)
            try:
                duration_ms = audio_duration_ms(staged_audio)
            except (OSError, ValueError):
                duration_ms = assembly.total_ms
            durations.append(duration_ms)
            rebuilt.append(chapter.index)
            updates.append(
                {
                    "index": chapter.index,
                    "audio": audio_rel,
                    "timing": timing_rel,
                    "duration_ms": duration_ms,
                }
            )

        if not rebuilt:
            raise RepairError("No chapter had segment audio to rebuild")

        for chapter_data in chapters:
            if not isinstance(chapter_data, dict):
                continue
            index = int(chapter_data.get("index", 0))
            update = next((item for item in updates if item["index"] == index), None)
            if update is None:
                continue
            chapter_data["audio"] = update["audio"]
            chapter_data["timing"] = update["timing"]
            chapter_data["duration_ms"] = update["duration_ms"]
        manifest["duration_ms"] = sum(durations)
        manifest["updated_at"] = datetime.now(UTC).isoformat()
        _write_json(staging / "manifest.json", manifest)
        backup = backup_book_state(book_dir, job_id)
        commit_staged_book(staging, book_dir, backup)
        cleanup_staging(book_dir)
    except BaseException:
        cleanup_staging(book_dir)
        raise
    return {
        "rebuilt": rebuilt,
        "skipped": skipped,
        "timing_offset_ms": timing_offset_ms,
        "duration_ms": manifest["duration_ms"],
    }


def _chapter_segment_files(book_dir: Path, chapter) -> list[Path] | None:
    if not chapter.segments:
        return None
    folder = book_dir / "audio" / "segments"
    files: list[Path] = []
    for segment in chapter.segments:
        candidates = [
            path
            for path in sorted(folder.glob(f"{segment.id}_*"))
            if path.suffix.lower() in AUDIO_EXTENSIONS
        ]
        if not candidates:
            return None
        files.append(candidates[0])
    return files


def _write_json(path: Path, payload: dict) -> None:
    temporary = path.with_name(f"{path.name}.{os.getpid()}.part")
    try:
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
