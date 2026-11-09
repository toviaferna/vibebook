import base64
import io
import math
import struct
import wave
from pathlib import Path

import httpx
import pytest

from audiol.ambience.library import AmbienceLibrary
from audiol.ambience.providers.freesound import CC0_FILTER, FreesoundProvider
from audiol.ambience.providers.plugin import PluginSoundProvider
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


def _wav_bytes(seconds: float = 0.4, frequency: int = 440) -> bytes:
    rate = 24_000
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(rate)
        frames = bytearray()
        for index in range(int(seconds * rate)):
            sample = int(8_000 * math.sin(2 * math.pi * frequency * index / rate))
            frames += struct.pack("<h", sample)
        audio.writeframes(frames)
    return buffer.getvalue()


def _library(tmp_path: Path) -> AmbienceLibrary:
    db = Database(tmp_path / ".vibebook.db")
    db.migrate()
    return AmbienceLibrary(tmp_path / "ambience", db)


def test_freesound_requires_key():
    provider = FreesoundProvider("")

    with pytest.raises(Exception, match="FREESOUND_API_KEY"):
        provider.search("rain")


def test_freesound_search_maps_results():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/search/text/")
        assert request.url.params["filter"] == CC0_FILTER
        assert request.headers["authorization"] == "Token key"
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "id": 42,
                        "name": "rain soft.wav",
                        "previews": {"preview-hq-mp3": "https://cdn/rain.wav"},
                        "license": "Creative Commons 0",
                        "username": "fieldrecordist",
                        "tags": ["rain", "nature"],
                        "duration": 3.5,
                    }
                ]
            },
        )

    provider = FreesoundProvider("key", client=httpx.Client(transport=httpx.MockTransport(handler)))

    results = provider.search("rain")

    assert len(results) == 1
    result = results[0]
    assert result.id == 42
    assert result.license == "Creative Commons 0"
    assert result.duration_ms == 3500
    assert "fieldrecordist" in result.attribution
    assert result.source_url == "https://freesound.org/s/42/"


@requires_ffmpeg
def test_freesound_imports_preview(tmp_path):
    payload = _wav_bytes()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/search/text/"):
            return httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "id": 42,
                            "name": "rain soft.wav",
                            "previews": {"preview-hq-mp3": "https://cdn/rain.wav"},
                            "license": "Creative Commons 0",
                            "username": "fieldrecordist",
                            "tags": ["rain"],
                            "duration": 0.4,
                        }
                    ]
                },
            )
        return httpx.Response(200, content=payload, headers={"content-type": "audio/wav"})

    library = _library(tmp_path)
    provider = FreesoundProvider("key", client=httpx.Client(transport=httpx.MockTransport(handler)))
    result = provider.search("rain")[0]

    asset = provider.import_asset(result, library, prompt="rain")

    assert asset["provider"] == "freesound"
    assert asset["license"] == "Creative Commons 0"
    assert asset["attribution"]
    assert library.audio_path(asset["id"]).exists()


def test_plugin_requires_url():
    provider = PluginSoundProvider("")

    with pytest.raises(Exception, match="no está configurado"):
        provider.generate("rain")


@requires_ffmpeg
def test_plugin_generates_base64_audio(tmp_path):
    payload = _wav_bytes()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/generate")
        body = request.read().decode()
        assert "rain" in body
        return httpx.Response(
            200,
            json={
                "audio_base64": base64.b64encode(payload).decode(),
                "license": "CC0-1.0",
                "attribution": "Local test plugin",
                "model": "fake-sfx",
                "format": "wav",
                "tags": ["rain"],
            },
        )

    library = _library(tmp_path)
    provider = PluginSoundProvider(
        "http://127.0.0.1:9999",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    asset = provider.import_asset("rain", library)

    assert asset["provider"] == "plugin"
    assert asset["license"] == "CC0-1.0"
    assert asset["model"] == "fake-sfx"
    assert library.audio_path(asset["id"]).exists()


def test_plugin_rejects_missing_license(tmp_path):
    payload = _wav_bytes()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"audio_base64": base64.b64encode(payload).decode()},
        )

    provider = PluginSoundProvider(
        "http://127.0.0.1:9999",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    with pytest.raises(Exception, match="licencia"):
        provider.import_asset("rain", _library(tmp_path))
