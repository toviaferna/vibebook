import os
import subprocess
from pathlib import Path

from audiol.tools import require_ffmpeg


def _ffmetadata_value(value: str) -> str:
    value = value.replace("\\", "\\\\").replace("\n", " ").replace("\r", " ")
    if value.startswith((";", "#")):
        value = "\\" + value
    return value


def _write_concat_list(path: Path, files: list[Path]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    entries = ["file '" + str(file.resolve()).replace("'", "'\\''") + "'" for file in files]
    path.write_text("\n".join(entries) + "\n", encoding="utf-8")


def probe_duration(path: Path) -> float:
    _, ffprobe = require_ffmpeg()
    output = subprocess.check_output(
        [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        encoding="utf-8",
        errors="replace",
    )
    try:
        return float(output.strip())
    except ValueError as exc:
        raise RuntimeError(f"Could not read duration from {path}") from exc


def concat_to_mp3(files: list[Path], out_path: Path, work_dir: Path) -> Path:
    if not files:
        raise ValueError("No audio files to concatenate")
    ffmpeg, _ = require_ffmpeg()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    work_dir.mkdir(parents=True, exist_ok=True)

    list_path = work_dir / f"{out_path.stem}_concat.txt"
    _write_concat_list(list_path, files)
    temporary = out_path.with_name(f"{out_path.name}.part")

    try:
        subprocess.run(
            [
                ffmpeg,
                "-nostdin",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(list_path),
                "-af",
                "loudnorm=I=-19:TP=-3:LRA=7",
                "-c:a",
                "libmp3lame",
                "-b:a",
                "64k",
                "-f",
                "mp3",
                str(temporary),
            ],
            check=True,
        )
        os.replace(temporary, out_path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return out_path


def build_m4b(
    chapter_files: list[Path],
    chapter_titles: list[str],
    metadata: dict[str, str],
    out_path: Path,
    work_dir: Path,
) -> Path:
    if not chapter_files:
        raise ValueError("No chapters to assemble")
    if len(chapter_files) != len(chapter_titles):
        raise ValueError("chapter_files and chapter_titles must have the same length")
    ffmpeg, _ = require_ffmpeg()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    work_dir.mkdir(parents=True, exist_ok=True)

    list_path = work_dir / f"{out_path.stem}_m4b_concat.txt"
    _write_concat_list(list_path, chapter_files)

    durations = [probe_duration(file) for file in chapter_files]
    metadata_lines = [
        ";FFMETADATA1",
        f"title={_ffmetadata_value(metadata.get('title', ''))}",
        f"artist={_ffmetadata_value(metadata.get('author', ''))}",
    ]
    start_ms = 0
    for title, duration in zip(chapter_titles, durations, strict=True):
        end_ms = start_ms + int(round(duration * 1000))
        metadata_lines.extend(
            [
                "[CHAPTER]",
                "TIMEBASE=1/1000",
                f"START={start_ms}",
                f"END={end_ms}",
                f"title={_ffmetadata_value(title)}",
            ]
        )
        start_ms = end_ms

    metadata_path = work_dir / f"{out_path.stem}_ffmetadata.txt"
    metadata_path.write_text("\n".join(metadata_lines) + "\n", encoding="utf-8")
    temporary = out_path.with_name(f"{out_path.stem}.part{out_path.suffix}")

    try:
        subprocess.run(
            [
                ffmpeg,
                "-nostdin",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(list_path),
                "-i",
                str(metadata_path),
                "-map_metadata",
                "1",
                "-map_chapters",
                "1",
                "-c:a",
                "aac",
                "-b:a",
                "64k",
                "-movflags",
                "+faststart",
                str(temporary),
            ],
            check=True,
        )
        os.replace(temporary, out_path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return out_path
