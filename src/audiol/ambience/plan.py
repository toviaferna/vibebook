from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from audiol.ambience.models import AmbienceAnchor, AmbiencePlan, AmbienceSettings
from audiol.manifest import load_manifest
from audiol.studio.library import BookRecord
from audiol.timing import read_chapter_timing

PLAN_DIR = "ambience"
PLAN_FILE = "plan.json"
MAX_EFFECTS = 3
MIN_SEPARATION_MS = 8_000
EDGE_GUARD_MS = 2_000
MIN_CONFIDENCE = 0.5


class AmbiencePlanError(ValueError):
    pass


def plan_path(book_dir: Path) -> Path:
    return book_dir / PLAN_DIR / PLAN_FILE


def load_ambience(book_dir: Path) -> tuple[AmbienceSettings, AmbiencePlan]:
    manifest = load_manifest(book_dir / "manifest.json")
    raw = manifest.get("ambience")
    settings = AmbienceSettings()
    if isinstance(raw, dict):
        try:
            settings = AmbienceSettings.model_validate(
                {
                    "enabled": bool(raw.get("enabled", False)),
                    "master_gain_db": raw.get("master_gain_db", -18),
                    "ducking_db": raw.get("ducking_db", -12),
                }
            )
        except ValueError:
            settings = AmbienceSettings()
    path = plan_path(book_dir)
    if not path.is_file():
        return settings, AmbiencePlan()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return settings, AmbiencePlan.model_validate(payload)
    except (OSError, ValueError) as exc:
        raise AmbiencePlanError(f"Invalid ambience plan: {exc}") from exc


def save_ambience(
    book_dir: Path,
    settings: AmbienceSettings,
    plan: AmbiencePlan,
) -> None:
    path = plan_path(book_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    _write_json(path, plan.model_dump())
    manifest = load_manifest(book_dir / "manifest.json")
    manifest["ambience"] = {
        "version": 1,
        "plan": f"{PLAN_DIR}/{PLAN_FILE}",
        "enabled": settings.enabled,
        "master_gain_db": settings.master_gain_db,
        "ducking_db": settings.ducking_db,
    }
    _write_json(book_dir / "manifest.json", manifest)


def validate_plan(
    plan: AmbiencePlan,
    record: BookRecord,
    known_assets: set[str] | None = None,
) -> None:
    manifest = load_manifest(record.path / "manifest.json")
    chapters = {
        int(chapter.get("index", 0)): chapter
        for chapter in manifest.get("chapters", [])
        if isinstance(chapter, dict)
    }
    seen_chapters: set[int] = set()
    for chapter in plan.chapters:
        if chapter.chapter_index in seen_chapters:
            raise AmbiencePlanError(f"Chapter {chapter.chapter_index} is duplicated")
        seen_chapters.add(chapter.chapter_index)
        data = chapters.get(chapter.chapter_index)
        if data is None:
            raise AmbiencePlanError(f"Chapter {chapter.chapter_index} does not exist")
        if len(chapter.effects) > MAX_EFFECTS:
            raise AmbiencePlanError(
                f"Chapter {chapter.chapter_index} has more than {MAX_EFFECTS} effects"
            )
        if chapter.bed is not None:
            _validate_asset(chapter.bed.asset_id, known_assets)
            if chapter.bed.end_ms is not None and chapter.bed.end_ms <= chapter.bed.start_ms:
                raise AmbiencePlanError("The bed must end after it starts")
        segments = {
            str(segment.get("id")): segment
            for segment in data.get("segments", [])
            if isinstance(segment, dict)
        }
        timing = _chapter_timing(record.path, data)
        starts: list[int] = []
        for effect in chapter.effects:
            _validate_asset(effect.asset_id, known_assets)
            if effect.anchor.segment_id not in segments:
                raise AmbiencePlanError(
                    f"Effect anchor {effect.anchor.segment_id} is not a segment "
                    f"of chapter {chapter.chapter_index}"
                )
            if effect.confidence < MIN_CONFIDENCE:
                raise AmbiencePlanError("Effects need confidence >= 0.5")
            start = _anchor_start_ms(effect.anchor, timing)
            if start is None:
                continue
            duration = _chapter_duration_ms(data, timing)
            if duration and (
                start < EDGE_GUARD_MS or start + effect.duration_ms > duration - EDGE_GUARD_MS
            ):
                raise AmbiencePlanError("Effects cannot start or end inside the first/last 2 s")
            starts.append(start)
        starts.sort()
        for previous, current in zip(starts, starts[1:], strict=False):
            if current - previous < MIN_SEPARATION_MS:
                raise AmbiencePlanError("Effects need at least 8 s of separation")


def _validate_asset(asset_id: str, known_assets: set[str] | None) -> None:
    if known_assets is not None and asset_id not in known_assets:
        raise AmbiencePlanError(f"Unknown sound asset: {asset_id}")


def _chapter_timing(book_dir: Path, chapter: dict[str, Any]):
    timing_rel = chapter.get("timing")
    if not isinstance(timing_rel, str):
        return None
    try:
        return read_chapter_timing(book_dir / timing_rel)
    except (OSError, ValueError):
        return None


def _chapter_duration_ms(chapter: dict[str, Any], timing) -> int:
    if timing is not None:
        return int(timing.duration_ms)
    return int(chapter.get("duration_ms") or 0)


def _anchor_start_ms(anchor: AmbienceAnchor, timing) -> int | None:
    if timing is None:
        return None
    for segment in timing.segments:
        if segment.id == anchor.segment_id:
            return int(segment.start_ms + anchor.offset_ms)
    return None


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_name(f"{path.name}.{os.getpid()}.part")
    try:
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
