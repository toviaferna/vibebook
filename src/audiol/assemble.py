import math
import os
import shutil
import struct
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from audiol.tools import require_ffmpeg

PCM_SAMPLE_RATE = 24_000
PCM_BYTES_PER_FRAME = 2
_CALIBRATION_CACHE: dict[int, int] = {}


@dataclass(frozen=True)
class ChapterAudio:
    path: Path
    offsets_ms: list[int]
    durations_ms: list[int]
    total_ms: int
    sample_rate: int = PCM_SAMPLE_RATE


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


def calibrate_encoder_delay_ms(sample_rate: int = PCM_SAMPLE_RATE) -> int:
    if sample_rate in _CALIBRATION_CACHE:
        return _CALIBRATION_CACHE[sample_rate]
    ffmpeg, _ = require_ffmpeg()
    burst_samples = int(0.02 * sample_rate)
    impulse_at = int(0.4 * sample_rate)
    total_samples = int(1.0 * sample_rate)
    pcm = bytearray()
    for index in range(total_samples):
        value = 0
        if impulse_at <= index < impulse_at + burst_samples:
            value = int(8_000 * math.cos(2 * math.pi * 1_000 * (index - impulse_at) / sample_rate))
        pcm += struct.pack("<h", value)

    with tempfile.TemporaryDirectory(prefix="vibebook-calibration-") as temp:
        root = Path(temp)
        source = root / "source.pcm"
        encoded = root / "encoded.mp3"
        decoded = root / "decoded.pcm"
        source.write_bytes(pcm)
        _encode_pcm_to_mp3(ffmpeg, source, encoded, sample_rate)
        _decode_pcm(ffmpeg, encoded, decoded, sample_rate)
        decoded_bytes = decoded.read_bytes()

    samples = struct.iter_unpack("<h", decoded_bytes)
    first = next(
        (index for index, (value,) in enumerate(samples) if abs(value) > 1_000),
        None,
    )
    if first is None:
        raise RuntimeError("Could not measure the MP3 encoder delay")
    delay_ms = int(round((first - impulse_at) * 1000 / sample_rate))
    _CALIBRATION_CACHE[sample_rate] = delay_ms
    return delay_ms


def concat_pcm_to_mp3(
    files: list[Path],
    out_path: Path,
    work_dir: Path,
    sample_rate: int = PCM_SAMPLE_RATE,
) -> ChapterAudio:
    if not files:
        raise ValueError("No audio files to concatenate")
    if sample_rate <= 0:
        raise ValueError("sample_rate must be positive")
    ffmpeg, _ = require_ffmpeg()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    work_dir.mkdir(parents=True, exist_ok=True)
    temporary_mp3 = out_path.with_name(f"{out_path.name}.part")

    offsets_ms: list[int] = []
    durations_ms: list[int] = []
    total_frames = 0
    try:
        with tempfile.TemporaryDirectory(prefix=f"{out_path.stem}-", dir=work_dir) as temp:
            pcm_dir = Path(temp)
            chapter_pcm = pcm_dir / "chapter.pcm"
            with chapter_pcm.open("wb") as output:
                for index, source in enumerate(files):
                    segment_pcm = pcm_dir / f"segment_{index:05d}.pcm"
                    _decode_pcm(ffmpeg, source, segment_pcm, sample_rate)
                    frames = segment_pcm.stat().st_size // PCM_BYTES_PER_FRAME
                    if frames <= 0:
                        raise RuntimeError(f"Decoded an empty segment: {source}")
                    offsets_ms.append(_frames_to_ms(total_frames, sample_rate))
                    durations_ms.append(_frames_to_ms(frames, sample_rate))
                    with segment_pcm.open("rb") as input_file:
                        shutil.copyfileobj(input_file, output, length=1024 * 1024)
                    total_frames += frames
                    segment_pcm.unlink(missing_ok=True)
            _encode_pcm_to_mp3(ffmpeg, chapter_pcm, temporary_mp3, sample_rate)
        os.replace(temporary_mp3, out_path)
    except BaseException:
        temporary_mp3.unlink(missing_ok=True)
        raise
    return ChapterAudio(
        path=out_path,
        offsets_ms=offsets_ms,
        durations_ms=durations_ms,
        total_ms=_frames_to_ms(total_frames, sample_rate),
        sample_rate=sample_rate,
    )


def _decode_pcm(ffmpeg: str, source: Path, target: Path, sample_rate: int) -> None:
    subprocess.run(
        [
            ffmpeg,
            "-nostdin",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(source),
            "-vn",
            "-ac",
            "1",
            "-ar",
            str(sample_rate),
            "-f",
            "s16le",
            "-acodec",
            "pcm_s16le",
            str(target),
        ],
        check=True,
    )


def _encode_pcm_to_mp3(
    ffmpeg: str,
    pcm_path: Path,
    out_path: Path,
    sample_rate: int,
) -> None:
    subprocess.run(
        [
            ffmpeg,
            "-nostdin",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "s16le",
            "-ar",
            str(sample_rate),
            "-ac",
            "1",
            "-i",
            str(pcm_path),
            "-af",
            "loudnorm=I=-19:TP=-3:LRA=7",
            "-c:a",
            "libmp3lame",
            "-b:a",
            "64k",
            "-f",
            "mp3",
            str(out_path),
        ],
        check=True,
    )


def _frames_to_ms(frames: int, sample_rate: int) -> int:
    return int(round(frames * 1000 / sample_rate))


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
