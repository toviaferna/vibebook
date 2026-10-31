import json
import math
import shutil
import subprocess
import wave
from pathlib import Path

import pytest

from audiol.assemble import build_m4b, concat_to_mp3, probe_duration

pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
    reason="ffmpeg/ffprobe not installed",
)


def make_wav(path: Path, seconds: float, frequency: int = 440) -> Path:
    sample_rate = 24000
    frame_count = int(seconds * sample_rate)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        frames = bytearray()
        for index in range(frame_count):
            value = int(1000 * math.sin(2 * math.pi * frequency * index / sample_rate))
            frames += value.to_bytes(2, "little", signed=True)
        wav.writeframes(frames)
    return path


def test_probe_duration(tmp_path: Path):
    audio = make_wav(tmp_path / "one.wav", 1.0)
    assert abs(probe_duration(audio) - 1.0) < 0.05


def test_concat_to_mp3(tmp_path: Path):
    first = make_wav(tmp_path / "a.wav", 0.5)
    second = make_wav(tmp_path / "b.wav", 0.5)
    output = tmp_path / "joined.mp3"

    concat_to_mp3([first, second], output, tmp_path)

    assert output.exists()
    assert abs(probe_duration(output) - 1.0) < 0.2


def test_build_m4b_with_chapters(tmp_path: Path):
    first = make_wav(tmp_path / "c1.wav", 0.5)
    second = make_wav(tmp_path / "c2.wav", 0.5)
    output = tmp_path / "book.m4b"

    build_m4b(
        [first, second],
        ["Capítulo 1", "Capítulo 2"],
        {"title": "Libro", "author": "Autora"},
        output,
        tmp_path,
    )

    assert output.exists()
    probe = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_chapters", "-of", "json", str(output)],
        text=True,
    )
    chapters = json.loads(probe)["chapters"]
    assert len(chapters) == 2
    assert chapters[0]["tags"]["title"] == "Capítulo 1"

    streams = json.loads(
        subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_streams",
                "-of",
                "json",
                str(output),
            ],
            text=True,
        )
    )
    assert streams["streams"][0]["codec_name"] == "aac"

    format_probe = json.loads(
        subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_format",
                "-of",
                "json",
                str(output),
            ],
            text=True,
        )
    )
    assert format_probe["format"]["tags"]["title"] == "Libro"
    assert format_probe["format"]["tags"]["artist"] == "Autora"


def test_build_m4b_escapes_ffmetadata_values(tmp_path: Path):
    audio = make_wav(tmp_path / "c1.wav", 0.5)
    output = tmp_path / "book.m4b"

    build_m4b(
        [audio],
        ["Capítulo\n1"],
        {"title": "Libro\ncon\\barra", "author": "Autora"},
        output,
        tmp_path,
    )

    assert output.exists()
    format_probe = json.loads(
        subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_format",
                "-of",
                "json",
                str(output),
            ],
            text=True,
        )
    )
    tags = format_probe["format"]["tags"]
    assert tags["title"] == "Libro con\\barra"
    assert "\n" not in tags["title"]
    assert tags["title"]

    chapters = json.loads(
        subprocess.check_output(
            ["ffprobe", "-v", "error", "-show_chapters", "-of", "json", str(output)],
            text=True,
        )
    )["chapters"]
    assert chapters[0]["tags"]["title"] == "Capítulo 1"
