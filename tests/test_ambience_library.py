import math
import struct
import wave
from pathlib import Path

import pytest

from audiol.ambience.library import AmbienceError, AmbienceLibrary
from audiol.ambience.models import SoundAssetCreate
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


def _wav(path: Path, seconds: float = 0.5, frequency: int = 440) -> None:
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


def _library(tmp_path: Path) -> AmbienceLibrary:
    db = Database(tmp_path / ".vibebook.db")
    db.migrate()
    return AmbienceLibrary(tmp_path / "ambience", db)


def _create(**overrides) -> SoundAssetCreate:
    values = {
        "prompt": "rain soft",
        "kind": "ambience",
        "tags": ["rain", "loop"],
        "license": "CC0-1.0",
        "loopable": True,
    }
    values.update(overrides)
    return SoundAssetCreate(**values)


@requires_ffmpeg
def test_import_probes_and_stores_asset(tmp_path):
    library = _library(tmp_path)
    source = tmp_path / "rain.wav"
    _wav(source)

    asset = library.import_file(source, _create())

    assert asset["id"].startswith("import-rain-soft-")
    assert asset["duration_ms"] >= 400
    assert asset["sample_rate"] == 24_000
    assert asset["channels"] == 1
    assert asset["approved"] is False
    assert library.audio_path(asset["id"]).exists()
    assert (library.assets_dir / f"{asset['id']}.json").exists()


@requires_ffmpeg
def test_import_dedupes_by_checksum(tmp_path):
    library = _library(tmp_path)
    source = tmp_path / "rain.wav"
    _wav(source)

    first = library.import_file(source, _create())
    second = library.import_file(source, _create(prompt="other prompt"))

    assert second["id"] == first["id"]
    items, total = library.db.list_sound_assets()
    assert total == 1
    assert len(items) == 1


def test_import_requires_a_known_license():
    with pytest.raises(ValueError):
        _create(license="unknown")


@requires_ffmpeg
def test_approve_and_rebuild_index(tmp_path):
    library = _library(tmp_path)
    source = tmp_path / "rain.wav"
    _wav(source)
    asset = library.import_file(source, _create())

    approved = library.approve(asset["id"])
    assert approved["approved"] is True

    library.db.delete_sound_asset(asset["id"])
    assert library.db.get_sound_asset(asset["id"]) is None
    assert library.rebuild_index() == 1
    assert library.db.get_sound_asset(asset["id"]) is not None


@requires_ffmpeg
def test_delete_rejects_assets_in_use(tmp_path):
    library = _library(tmp_path)
    source = tmp_path / "rain.wav"
    _wav(source)
    asset = library.import_file(source, _create())
    library.record_use(asset["id"])

    with pytest.raises(AmbienceError):
        library.delete(asset["id"])

    assert library.audio_path(asset["id"]).exists()


@requires_ffmpeg
def test_generate_procedural_bed(tmp_path):
    library = _library(tmp_path)

    asset = library.generate_preset("rain")

    assert asset["provider"] == "procedural"
    assert asset["loopable"] is True
    assert "rain" in asset["tags"]
    assert asset["license"] == "AGPL-3.0"
    assert asset["duration_ms"] >= 29_000
    assert library.audio_path(asset["id"]).exists()
