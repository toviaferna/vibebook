import json
import math
import struct
import wave
from pathlib import Path

import pytest

from audiol.ambience.library import AmbienceLibrary
from audiol.ambience.mix import mix_chapter, render_ambient_book
from audiol.ambience.models import (
    AmbienceBed,
    AmbienceChapter,
    AmbiencePlan,
    AmbienceSettings,
    SoundAssetCreate,
)
from audiol.assemble import probe_duration
from audiol.studio.db import Database
from audiol.tools import find_binary


def _has_ffmpeg() -> bool:
    try:
        find_binary("ffmpeg")
        find_binary("ffprobe")
        return True
    except RuntimeError:
        return False


requires_ffmpeg = pytest.mark.skipif(not _has_ffmpeg(), reason="ffmpeg/ffprobe not available")


def _wav(path: Path, seconds: float, frequency: int = 440) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rate = 24_000
    frames = bytearray()
    for index in range(int(seconds * rate)):
        sample = int(8_000 * math.sin(2 * math.pi * frequency * index / rate))
        frames += struct.pack("<h", sample)
    with wave.open(str(path), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(rate)
        audio.writeframes(frames)


@requires_ffmpeg
def test_mix_chapter_keeps_duration(tmp_path):
    voice = tmp_path / "voice.wav"
    bed = tmp_path / "bed.wav"
    _wav(voice, 2.0, 220)
    _wav(bed, 1.0, 110)
    output = tmp_path / "mixed.m4a"

    mix_chapter(voice, bed, [], 2_000, output, bed_gain_db=-24, master_gain_db=-18)

    assert output.is_file()
    assert abs(probe_duration(output) - 2.0) < 0.05


@requires_ffmpeg
def test_mix_chapter_without_bed_copies_voice(tmp_path):
    voice = tmp_path / "voice.wav"
    _wav(voice, 1.0)
    output = tmp_path / "copy.wav"

    mix_chapter(voice, None, [], 1_000, output)

    assert output.is_file()
    assert output.read_bytes() == voice.read_bytes()


@requires_ffmpeg
def test_render_ambient_book_builds_m4b(tmp_path):
    book_dir = tmp_path / "book"
    voice = book_dir / "audio" / "chapters" / "chapter_001.wav"
    _wav(voice, 2.0, 220)
    (book_dir / "manifest.json").write_text(
        json.dumps(
            {
                "schema_version": 2,
                "id": "book-1",
                "title": "Libro ambientado",
                "author": "Autora",
                "language": "es",
                "status": "ready",
                "chapters": [
                    {
                        "index": 1,
                        "title": "Uno",
                        "audio": "audio/chapters/chapter_001.wav",
                        "duration_ms": 2_000,
                        "segments": [],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    db = Database(tmp_path / ".vibebook.db")
    db.migrate()
    library = AmbienceLibrary(tmp_path / "ambience", db)
    bed = tmp_path / "bed.wav"
    _wav(bed, 1.0, 110)
    asset = library.import_file(
        bed,
        SoundAssetCreate(
            prompt="rain bed",
            kind="ambience",
            tags=["rain"],
            license="CC0-1.0",
            loopable=True,
        ),
    )
    plan = AmbiencePlan(
        chapters=[
            AmbienceChapter(
                chapter_index=1,
                bed=AmbienceBed(asset_id=asset["id"], gain_db=-24),
            )
        ]
    )

    output = render_ambient_book(
        book_dir,
        plan,
        AmbienceSettings(enabled=True),
        library,
    )

    assert output.is_file()
    assert output.suffix == ".m4b"
    assert abs(probe_duration(output) - 2.0) < 0.05
