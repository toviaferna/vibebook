from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from audiol.assemble import probe_duration
from audiol.manifest import load_manifest
from audiol.timing import ChapterTiming, audio_duration_ms, read_chapter_timing

SEGMENT_EXTENSIONS = (".wav", ".mp3", ".m4a", ".ogg", ".opus", ".flac")
DEFAULT_GAP_MS = 250
DEFAULT_MAX_DRIFT_MS = 100


def analyze_chapter(
    timing: ChapterTiming,
    chapter_audio_ms: int | None,
    segment_audio_ms: dict[str, int],
) -> dict[str, Any]:
    gaps: list[dict[str, Any]] = []
    overlaps: list[dict[str, Any]] = []
    invalid_words: list[dict[str, Any]] = []
    out_of_bounds: list[dict[str, Any]] = []
    segments: list[dict[str, Any]] = []

    for segment in timing.segments:
        segment_gaps = 0
        segment_overlaps = 0
        previous_end = segment.start_ms
        for word in segment.words:
            if word.end_ms <= word.start_ms or word.start_ms < 0:
                invalid_words.append(
                    {
                        "segment_id": segment.id,
                        "text": word.text,
                        "start_ms": word.start_ms,
                        "end_ms": word.end_ms,
                    }
                )
                continue
            if word.start_ms < segment.start_ms or word.end_ms > segment.end_ms:
                out_of_bounds.append(
                    {
                        "segment_id": segment.id,
                        "text": word.text,
                        "start_ms": word.start_ms,
                        "end_ms": word.end_ms,
                    }
                )
            if word.start_ms < previous_end:
                overlaps.append(
                    {
                        "segment_id": segment.id,
                        "text": word.text,
                        "gap_ms": word.start_ms - previous_end,
                    }
                )
                segment_overlaps += 1
            elif word.start_ms - previous_end > DEFAULT_GAP_MS:
                gaps.append(
                    {
                        "segment_id": segment.id,
                        "text": word.text,
                        "gap_ms": word.start_ms - previous_end,
                    }
                )
                segment_gaps += 1
            previous_end = max(previous_end, word.end_ms)

        audio_ms = segment_audio_ms.get(segment.id)
        segments.append(
            {
                "id": segment.id,
                "start_ms": segment.start_ms,
                "end_ms": segment.end_ms,
                "duration_ms": segment.end_ms - segment.start_ms,
                "audio_ms": audio_ms,
                "audio_delta_ms": (
                    audio_ms - (segment.end_ms - segment.start_ms) if audio_ms is not None else None
                ),
                "precision": segment.precision,
                "word_count": len(segment.words),
                "first_word_ms": segment.words[0].start_ms if segment.words else None,
                "last_word_end_ms": segment.words[-1].end_ms if segment.words else None,
                "leading_silence_ms": (
                    segment.words[0].start_ms - segment.start_ms if segment.words else None
                ),
                "trailing_silence_ms": (
                    segment.end_ms - segment.words[-1].end_ms if segment.words else None
                ),
                "gaps": segment_gaps,
                "overlaps": segment_overlaps,
            }
        )

    timing_sum_ms = sum(segment.end_ms - segment.start_ms for segment in timing.segments)
    chapter_audio_values = [
        segment_audio_ms[segment.id]
        for segment in timing.segments
        if segment.id in segment_audio_ms
    ]
    audio_sum_ms = sum(chapter_audio_values) if chapter_audio_values else None
    return {
        "chapter_index": timing.chapter_index,
        "precision": timing.precision,
        "timing_offset_ms": timing.timing_offset_ms,
        "timing_duration_ms": timing.duration_ms,
        "timing_segment_sum_ms": timing_sum_ms,
        "segment_audio_sum_ms": audio_sum_ms,
        "chapter_audio_ms": chapter_audio_ms,
        "timing_vs_audio_ms": (
            timing.duration_ms - chapter_audio_ms if chapter_audio_ms is not None else None
        ),
        "segment_sum_vs_audio_ms": (
            audio_sum_ms - chapter_audio_ms
            if audio_sum_ms is not None and chapter_audio_ms is not None
            else None
        ),
        "gaps": gaps,
        "overlaps": overlaps,
        "invalid_words": invalid_words,
        "out_of_bounds": out_of_bounds,
        "segments": segments,
    }


def build_report(book_dir: Path) -> dict[str, Any]:
    manifest = load_manifest(book_dir / "manifest.json")
    chapter_audio = _chapter_audio_paths(book_dir, manifest)
    segment_audio = _segment_audio_durations(book_dir)
    chapters: list[dict[str, Any]] = []

    for chapter in manifest.get("chapters", []):
        if not isinstance(chapter, dict):
            continue
        timing_path = chapter.get("timing")
        if not isinstance(timing_path, str):
            chapters.append(
                {
                    "chapter_index": chapter.get("index"),
                    "title": chapter.get("title"),
                    "missing_timing": True,
                }
            )
            continue
        path = book_dir / timing_path
        if not path.is_file():
            chapters.append(
                {
                    "chapter_index": chapter.get("index"),
                    "title": chapter.get("title"),
                    "missing_timing": True,
                }
            )
            continue
        timing = read_chapter_timing(path)
        audio_path = chapter_audio.get(int(timing.chapter_index))
        chapter_ms = _duration_or_none(audio_path)
        report = analyze_chapter(timing, chapter_ms, segment_audio)
        report["title"] = chapter.get("title")
        chapters.append(report)

    return {
        "book": manifest.get("title"),
        "book_id": manifest.get("id"),
        "chapters": chapters,
        "summary": _summary(chapters),
    }


def _summary(chapters: list[dict[str, Any]]) -> dict[str, Any]:
    drifts = [
        abs(chapter["timing_vs_audio_ms"])
        for chapter in chapters
        if chapter.get("timing_vs_audio_ms") is not None
    ]
    gaps = sum(len(chapter.get("gaps", [])) for chapter in chapters)
    overlaps = sum(len(chapter.get("overlaps", [])) for chapter in chapters)
    invalid = sum(len(chapter.get("invalid_words", [])) for chapter in chapters)
    out_of_bounds = sum(len(chapter.get("out_of_bounds", [])) for chapter in chapters)
    return {
        "chapters": len(chapters),
        "max_drift_ms": max(drifts) if drifts else None,
        "gaps": gaps,
        "overlaps": overlaps,
        "invalid_words": invalid,
        "out_of_bounds": out_of_bounds,
        "missing_timing": sum(1 for chapter in chapters if chapter.get("missing_timing")),
    }


def _chapter_audio_paths(book_dir: Path, manifest: dict) -> dict[int, Path]:
    result: dict[int, Path] = {}
    for chapter in manifest.get("chapters", []):
        if not isinstance(chapter, dict):
            continue
        audio = chapter.get("audio")
        if isinstance(audio, str):
            result[int(chapter.get("index", 0))] = book_dir / audio
    return result


def _segment_audio_durations(book_dir: Path) -> dict[str, int]:
    folder = book_dir / "audio" / "segments"
    if not folder.is_dir():
        return {}
    durations: dict[str, int] = {}
    for extension in SEGMENT_EXTENSIONS:
        for path in folder.glob(f"*{extension}"):
            segment_id = path.name.split("_", 1)[0]
            duration = _duration_or_none(path)
            if duration is not None:
                durations[segment_id] = duration
    return durations


def _duration_or_none(path: Path | None) -> int | None:
    if path is None or not path.is_file():
        return None
    try:
        return int(round(probe_duration(path) * 1000))
    except (OSError, RuntimeError, ValueError, subprocess.CalledProcessError):
        try:
            return audio_duration_ms(path)
        except (OSError, ValueError):
            return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Report Vibebook karaoke sync health")
    parser.add_argument("book_dir", type=Path)
    parser.add_argument("--json", action="store_true", help="Print JSON")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 when drift, gaps, overlaps or invalid words exceed the thresholds",
    )
    parser.add_argument("--max-drift-ms", type=int, default=DEFAULT_MAX_DRIFT_MS)
    args = parser.parse_args(argv)

    try:
        report = build_report(args.book_dir)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        _print_table(report)

    summary = report["summary"]
    failures = [
        summary["gaps"],
        summary["overlaps"],
        summary["invalid_words"],
        summary["out_of_bounds"],
        summary["missing_timing"],
    ]
    drift = summary["max_drift_ms"]
    if args.strict and (any(failures) or (drift is not None and drift > args.max_drift_ms)):
        return 1
    return 0


def _print_table(report: dict[str, Any]) -> None:
    print(f"Libro: {report.get('book') or '-'}")
    print("Cap  prec     timing   audio   drift  seg->audio  gaps  overlap  bad  oob")
    for chapter in report["chapters"]:
        if chapter.get("missing_timing"):
            print(f"{chapter.get('chapter_index', '-'):>3}  sin timing")
            continue
        print(
            f"{chapter['chapter_index']:>3}  {chapter['precision']:<7} "
            f"{chapter['timing_duration_ms']:>7} "
            f"{_fmt(chapter['chapter_audio_ms']):>7} "
            f"{_fmt(chapter['timing_vs_audio_ms']):>6} "
            f"{_fmt(chapter['segment_sum_vs_audio_ms']):>10} "
            f"{len(chapter['gaps']):>5} "
            f"{len(chapter['overlaps']):>7} "
            f"{len(chapter['invalid_words']):>4} "
            f"{len(chapter['out_of_bounds']):>4}"
        )
    summary = report["summary"]
    print(
        f"Resumen: {summary['chapters']} capítulos · "
        f"drift máx {_fmt(summary['max_drift_ms'])} ms · "
        f"{summary['gaps']} huecos · {summary['overlaps']} solapes · "
        f"{summary['invalid_words']} words inválidas"
    )


def _fmt(value: int | None) -> str:
    return "-" if value is None else str(value)


if __name__ == "__main__":
    raise SystemExit(main())
