from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from audiol.ambience.models import (
    AmbienceAnchor,
    AmbienceBed,
    AmbienceChapter,
    AmbienceEffect,
    AmbiencePlan,
    AmbienceSettings,
)
from audiol.manifest import load_manifest
from audiol.paths import UnsafePathError, safe_book_path
from audiol.timing import read_chapter_timing

BED_KEYWORDS: dict[str, tuple[str, ...]] = {
    "rain": ("lluvia", "llueve", "tormenta", "chaparrón", "paraguas"),
    "sea": ("mar", "olas", "playa", "marea", "océano", "puerto"),
    "wind": ("viento", "ráfaga", "vendaval", "brisa", "silbido"),
    "room": ("cuarto", "habitación", "casa", "interior", "sala", "cocina", "biblioteca"),
    "fire": ("fuego", "chimenea", "brasas", "hoguera", "llama"),
    "night": ("noche", "nocturno", "estrellas", "luna", "madrugada"),
}

EFFECT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "door": ("puerta", "portón", "entró", "salió"),
    "bell": ("campana", "timbre", "reloj"),
    "steps": ("pasos", "pisadas", "caminaba", "subió"),
    "thunder": ("trueno", "relámpago", "rayo"),
    "glass": ("copa", "vaso", "brindis", "cristal"),
    "birds": ("pájaros", "gaviotas", "aves", "gorriones"),
}


def analyze_book(
    book_dir: Path,
    assets: list[dict[str, Any]],
) -> tuple[AmbienceSettings, AmbiencePlan]:
    manifest = load_manifest(book_dir / "manifest.json")
    settings = AmbienceSettings()
    chapters: list[AmbienceChapter] = []
    for chapter_data in manifest.get("chapters", []):
        if not isinstance(chapter_data, dict):
            continue
        index = int(chapter_data.get("index", 0))
        if index < 1:
            continue
        text = " ".join(
            str(segment.get("text", ""))
            for segment in chapter_data.get("segments", [])
            if isinstance(segment, dict)
        ).lower()
        bed = _pick_bed(text, assets)
        timing = _timing(book_dir, chapter_data)
        effects = _pick_effects(text, assets, timing, chapter_data)
        if bed is not None or effects:
            chapters.append(AmbienceChapter(chapter_index=index, bed=bed, effects=effects))
    return settings, AmbiencePlan(chapters=chapters)


def _pick_bed(text: str, assets: list[dict[str, Any]]) -> AmbienceBed | None:
    if not text:
        return None
    scores: Counter[str] = Counter()
    for scene, words in BED_KEYWORDS.items():
        scores[scene] = sum(text.count(word) for word in words)
    if not scores or scores.most_common(1)[0][1] == 0:
        return None
    scene, hits = scores.most_common(1)[0]
    asset = _find_asset(assets, scene, "ambience")
    if asset is None:
        return None
    confidence = min(0.9, 0.55 + hits * 0.05)
    return AmbienceBed(
        asset_id=str(asset["id"]),
        gain_db=-24,
        confidence=round(confidence, 2),
        reason=f"escena detectada: {scene}",
    )


def _pick_effects(
    text: str, assets: list[dict[str, Any]], timing, chapter: dict
) -> list[AmbienceEffect]:
    if timing is None or not text:
        return []
    duration = int(timing.duration_ms)
    candidates: list[tuple[int, str, str]] = []
    for segment in timing.segments:
        segment_text = ""
        for raw in chapter.get("segments", []):
            if isinstance(raw, dict) and raw.get("id") == segment.id:
                segment_text = str(raw.get("text", "")).lower()
                break
        if not segment_text:
            continue
        for effect, words in EFFECT_KEYWORDS.items():
            if any(word in segment_text for word in words):
                candidates.append((int(segment.start_ms), effect, segment.id))
                break
    candidates.sort()
    effects: list[AmbienceEffect] = []
    last_start = -MIN_SEPARATION
    for start, effect, segment_id in candidates:
        if len(effects) >= 3:
            break
        if start < 2_000 or start > duration - 2_000 or start - last_start < MIN_SEPARATION:
            continue
        asset = _find_asset(assets, effect, "effect")
        if asset is None:
            continue
        effects.append(
            AmbienceEffect(
                asset_id=str(asset["id"]),
                anchor=AmbienceAnchor(segment_id=segment_id, offset_ms=0),
                duration_ms=min(3_000, int(asset.get("duration_ms") or 1_800)),
                confidence=0.65,
                reason=f"efecto detectado: {effect}",
            )
        )
        last_start = start
    return effects


def _find_asset(assets: list[dict[str, Any]], tag: str, kind: str) -> dict[str, Any] | None:
    for asset in assets:
        if asset.get("kind") != kind:
            continue
        tags = {str(item).lower() for item in asset.get("tags", [])}
        prompt = str(asset.get("prompt", "")).lower()
        if tag in tags or tag in prompt:
            return asset
    return None


def _timing(book_dir: Path, chapter: dict[str, Any]):
    timing_rel = chapter.get("timing")
    if not isinstance(timing_rel, str):
        return None
    try:
        path = safe_book_path(book_dir, timing_rel)
        return read_chapter_timing(path)
    except (OSError, ValueError, UnsafePathError):
        return None


MIN_SEPARATION = 8_000
