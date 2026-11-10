from __future__ import annotations

import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

from audiol.ambience.library import AmbienceLibrary
from audiol.ambience.models import AmbiencePlan, AmbienceSettings
from audiol.assemble import build_m4b, probe_duration
from audiol.manifest import load_manifest
from audiol.paths import UnsafePathError, safe_book_path
from audiol.timing import read_chapter_timing
from audiol.tools import require_ffmpeg

SAMPLE_RATE = 48_000


class AmbienceMixError(RuntimeError):
    pass


def mix_chapter(
    voice_path: Path,
    bed_path: Path | None,
    effects: list[tuple[Path, int, int, float]],
    duration_ms: int,
    output_path: Path,
    *,
    bed_gain_db: float = -24,
    fade_in_ms: int = 1_500,
    fade_out_ms: int = 2_000,
    master_gain_db: float = -18,
    bed_start_ms: int = 0,
    bed_end_ms: int | None = None,
    ducking_db: float = -12,
) -> Path:
    if bed_path is None and not effects:
        shutil.copy2(voice_path, output_path)
        return output_path
    ffmpeg, _ = require_ffmpeg()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    duration_s = max(0.1, duration_ms / 1000)
    bed_start_s = max(0.0, bed_start_ms / 1000)
    bed_end_s = duration_s if bed_end_ms is None else min(duration_s, bed_end_ms / 1000)
    bed_end_s = max(bed_start_s + 0.1, bed_end_s)
    command = [
        ffmpeg,
        "-nostdin",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(voice_path),
    ]
    filters = ["[0:a]aformat=sample_rates=48000:channel_layouts=mono,volume=1[voice]"]
    mix_inputs = ["[voice]"]
    index = 1
    if bed_path is not None:
        command.extend(["-stream_loop", "-1", "-i", str(bed_path)])
        bed_duration = bed_end_s - bed_start_s
        fade_out_local = max(0.0, bed_duration - fade_out_ms / 1000)
        filters.append(
            f"[{index}:a]aformat=sample_rates=48000:channel_layouts=mono,"
            f"atrim={bed_start_s:.3f}:{bed_end_s:.3f},asetpts=PTS-STARTPTS,"
            f"volume={_db_to_gain(bed_gain_db):.4f},"
            f"afade=t=in:st=0:d={min(fade_in_ms / 1000, bed_duration):.3f},"
            f"afade=t=out:st={fade_out_local:.3f}:d={fade_out_ms / 1000:.3f}[bed]"
        )
        threshold = min(0.2, max(0.005, 0.03 * (abs(ducking_db) / 12)))
        filters.append(
            f"[bed][voice]sidechaincompress=threshold={threshold:.4f}:ratio=8:"
            "attack=20:release=400[ducked]"
        )
        mix_inputs.append("[ducked]")
        index += 1
    for effect_path, start_ms, effect_duration_ms, gain_db in effects:
        command.extend(["-i", str(effect_path)])
        filters.append(
            f"[{index}:a]aformat=sample_rates=48000:channel_layouts=mono,"
            f"volume={_db_to_gain(gain_db):.4f},"
            f"atrim=0:{max(0.1, effect_duration_ms / 1000):.3f},"
            f"adelay={max(0, start_ms)}|{max(0, start_ms)}[fx{index}]"
        )
        mix_inputs.append(f"[fx{index}]")
        index += 1
    master = _db_to_gain(master_gain_db)
    filters.append(
        f"{''.join(mix_inputs)}amix=inputs={len(mix_inputs)}:duration=first:"
        f"dropout_transition=0,volume={master:.4f},alimiter=limit=0.95[out]"
    )
    codec = "pcm_s16le" if output_path.suffix.lower() == ".wav" else "aac"
    command.extend(
        [
            "-filter_complex",
            ";".join(filters),
            "-map",
            "[out]",
            "-t",
            f"{duration_s:.3f}",
            "-c:a",
            codec,
            "-ar",
            str(SAMPLE_RATE),
            "-ac",
            "1",
        ]
    )
    if codec == "aac":
        command.extend(["-b:a", "96k"])
    command.append(str(output_path))
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0 or not output_path.is_file():
        raise AmbienceMixError(completed.stderr[-800:] or "ffmpeg could not mix the chapter")
    return output_path


def render_ambient_book(
    book_dir: Path,
    plan: AmbiencePlan,
    settings: AmbienceSettings,
    library: AmbienceLibrary,
    output_path: Path | None = None,
    progress: Callable[[int, int, str], None] | None = None,
) -> Path:
    manifest = load_manifest(book_dir / "manifest.json")
    chapters = [chapter for chapter in manifest.get("chapters", []) if isinstance(chapter, dict)]
    if not chapters:
        raise AmbienceMixError("The book has no chapters")
    plan_by_index = {chapter.chapter_index: chapter for chapter in plan.chapters}
    work_root = book_dir / "ambience" / "work"
    work_root.mkdir(parents=True, exist_ok=True)
    chapter_files: list[Path] = []
    chapter_titles: list[str] = []
    total = len(chapters)
    for position, chapter in enumerate(chapters, start=1):
        index = int(chapter.get("index", position))
        audio_rel = chapter.get("audio")
        if not isinstance(audio_rel, str):
            raise AmbienceMixError(f"Chapter {index} has no audio")
        try:
            voice_path = safe_book_path(book_dir, audio_rel)
        except UnsafePathError as exc:
            raise AmbienceMixError(f"Chapter {index} audio path is invalid") from exc
        if not voice_path.is_file():
            raise AmbienceMixError(f"Chapter {index} audio is missing")
        chapter_plan = plan_by_index.get(index)
        bed_path = None
        effects: list[tuple[Path, int, int, float]] = []
        if chapter_plan is not None:
            if chapter_plan.bed is not None:
                bed_path = library.audio_path(chapter_plan.bed.asset_id)
            for effect in chapter_plan.effects:
                start_ms = _effect_start_ms(
                    book_dir, chapter, effect.anchor.segment_id, effect.anchor.offset_ms
                )
                if start_ms is None:
                    continue
                effects.append(
                    (
                        library.audio_path(effect.asset_id),
                        start_ms,
                        effect.duration_ms,
                        effect.gain_db,
                    )
                )
        output = work_root / f"chapter_{index:03d}.wav"
        duration_ms = int(chapter.get("duration_ms") or 0)
        if duration_ms <= 0:
            duration_ms = round(probe_duration(voice_path) * 1000)
        bed = chapter_plan.bed if chapter_plan is not None else None
        mix_chapter(
            voice_path,
            bed_path,
            effects,
            duration_ms,
            output,
            bed_gain_db=bed.gain_db if bed else -24,
            fade_in_ms=bed.fade_in_ms if bed else 0,
            fade_out_ms=bed.fade_out_ms if bed else 0,
            master_gain_db=settings.master_gain_db,
            bed_start_ms=bed.start_ms if bed else 0,
            bed_end_ms=bed.end_ms if bed else None,
            ducking_db=settings.ducking_db,
        )
        chapter_files.append(output)
        chapter_titles.append(str(chapter.get("title") or f"Capítulo {index}"))
        if progress is not None:
            progress(position, total, chapter_titles[-1])
    destination = output_path or (book_dir / "audio" / "ambientado.m4b")
    build_m4b(
        chapter_files,
        chapter_titles,
        {
            "title": str(manifest.get("title") or "Vibebook"),
            "author": str(manifest.get("author") or ""),
        },
        destination,
        work_root,
    )
    return destination


def _effect_start_ms(
    book_dir: Path,
    chapter: dict,
    segment_id: str,
    offset_ms: int,
) -> int | None:
    timing_rel = chapter.get("timing")
    if not isinstance(timing_rel, str):
        return None
    try:
        path = safe_book_path(book_dir, timing_rel)
        timing = read_chapter_timing(path)
    except (OSError, ValueError, UnsafePathError):
        return None
    segment = next((item for item in timing.segments if item.id == segment_id), None)
    return int(segment.start_ms + offset_ms) if segment is not None else None


def _db_to_gain(db: float) -> float:
    return 10 ** (db / 20)
