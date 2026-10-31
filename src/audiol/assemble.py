import shutil
import subprocess
from pathlib import Path


def require_ffmpeg() -> None:
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        raise RuntimeError("ffmpeg and ffprobe must be installed and in PATH")


def _ffmetadata_value(value: str) -> str:
    value = value.replace("\\", "\\\\").replace("\n", " ").replace("\r", " ")
    if value.startswith((";", "#")):
        value = "\\" + value
    return value


def probe_duration(path: Path) -> float:
    require_ffmpeg()
    output = subprocess.check_output(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        text=True,
    )
    return float(output.strip())


def concat_to_mp3(files: list[Path], out_path: Path, work_dir: Path) -> Path:
    if not files:
        raise ValueError("No audio files to concatenate")
    require_ffmpeg()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    work_dir.mkdir(parents=True, exist_ok=True)

    list_path = work_dir / f"{out_path.stem}_concat.txt"
    list_path.write_text(
        "\n".join(f"file '{file.resolve()}'" for file in files) + "\n",
        encoding="utf-8",
    )

    subprocess.run(
        [
            "ffmpeg",
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
            str(out_path),
        ],
        check=True,
    )
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
    require_ffmpeg()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    work_dir.mkdir(parents=True, exist_ok=True)

    list_path = work_dir / "m4b_concat.txt"
    list_path.write_text(
        "\n".join(f"file '{file.resolve()}'" for file in chapter_files) + "\n",
        encoding="utf-8",
    )

    durations = [probe_duration(file) for file in chapter_files]
    metadata_lines = [
        ";FFMETADATA1",
        f"title={_ffmetadata_value(metadata.get('title', ''))}",
        f"artist={_ffmetadata_value(metadata.get('author', ''))}",
    ]
    start_ms = 0
    for title, duration in zip(chapter_titles, durations):
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

    metadata_path = work_dir / "ffmetadata.txt"
    metadata_path.write_text("\n".join(metadata_lines) + "\n", encoding="utf-8")

    subprocess.run(
        [
            "ffmpeg",
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
            str(out_path),
        ],
        check=True,
    )
    return out_path
