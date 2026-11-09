import math
import struct
import wave
from pathlib import Path

import pytest

from audiol.tools import find_binary


def _has_ffmpeg() -> bool:
    try:
        find_binary("ffmpeg")
        find_binary("ffprobe")
        return True
    except RuntimeError:
        return False


requires_ffmpeg = pytest.mark.skipif(not _has_ffmpeg(), reason="ffmpeg/ffprobe not available")


def _wav(path: Path, seconds: float = 0.4, frequency: int = 440) -> None:
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


def _import(client, tmp_path: Path, name: str = "rain.wav", prompt: str = "rain soft"):
    source = tmp_path / name
    _wav(source)
    return client.post(
        "/api/ambience/assets/import",
        files={"file": (name, source.read_bytes(), "audio/wav")},
        data={
            "prompt": prompt,
            "kind": "ambience",
            "tags": "rain,loop",
            "license": "CC0-1.0",
            "loopable": "true",
        },
    )


@requires_ffmpeg
def test_import_list_approve_and_audio(client, tmp_path):
    created = _import(client, tmp_path)
    assert created.status_code == 201, created.text
    asset = created.json()
    assert asset["id"].startswith("import-rain-soft-")
    assert asset["approved"] is False
    assert asset["audio_url"].endswith("/audio")

    listed = client.get("/api/ambience/assets", params={"query": "rain"})
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["id"] == asset["id"]

    audio = client.get(asset["audio_url"])
    assert audio.status_code == 200
    assert audio.content

    approved = client.post(f"/api/ambience/assets/{asset['id']}/approve")
    assert approved.status_code == 200
    assert approved.json()["approved"] is True

    used = client.get(f"/api/ambience/assets/{asset['id']}")
    assert used.json()["usage_count"] == 1

    blocked = client.delete(f"/api/ambience/assets/{asset['id']}")
    assert blocked.status_code == 409


@requires_ffmpeg
def test_delete_unused_asset(client, tmp_path):
    asset = _import(client, tmp_path, name="wind.wav", prompt="wind soft").json()

    deleted = client.delete(f"/api/ambience/assets/{asset['id']}")

    assert deleted.status_code == 204
    assert client.get(f"/api/ambience/assets/{asset['id']}").status_code == 404


@requires_ffmpeg
def test_import_rejects_unknown_license(client, tmp_path):
    source = tmp_path / "rain.wav"
    _wav(source)

    response = client.post(
        "/api/ambience/assets/import",
        files={"file": ("rain.wav", source.read_bytes(), "audio/wav")},
        data={"prompt": "rain", "license": "unknown"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_asset"


def test_provider_status_and_unconfigured_imports(client, monkeypatch):
    monkeypatch.delenv("FREESOUND_API_KEY", raising=False)
    monkeypatch.delenv("VIBEBOOK_AMBIENCE_PLUGIN_URL", raising=False)

    providers = client.get("/api/ambience/providers")
    assert providers.status_code == 200
    assert {item["id"] for item in providers.json()["items"]} == {"freesound", "plugin"}
    assert all(item["configured"] is False for item in providers.json()["items"])

    freesound = client.post(
        "/api/ambience/providers/freesound/import",
        json={"query": "rain"},
    )
    assert freesound.status_code == 422
    assert freesound.json()["error"]["code"] == "provider_unavailable"

    plugin = client.post(
        "/api/ambience/providers/plugin/import",
        json={"prompt": "rain"},
    )
    assert plugin.status_code == 422
    assert plugin.json()["error"]["code"] == "provider_unavailable"


def test_book_ambience_unknown_book_returns_404(client):
    response = client.get("/api/books/nope/ambience")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "book_not_found"


def test_book_ambience_roundtrip(client, imported):
    book_id = imported["id"]

    initial = client.get(f"/api/books/{book_id}/ambience")
    assert initial.status_code == 200
    assert initial.json()["settings"]["enabled"] is False
    assert initial.json()["plan"]["chapters"] == []

    updated = client.put(
        f"/api/books/{book_id}/ambience",
        json={
            "settings": {"enabled": True, "master_gain_db": -20, "ducking_db": -10},
            "plan": {"version": 1, "chapters": []},
        },
    )
    assert updated.status_code == 200
    assert updated.json()["settings"]["enabled"] is True

    fetched = client.get(f"/api/books/{book_id}/ambience")
    assert fetched.json()["settings"]["master_gain_db"] == -20

    analyzed = client.post(
        f"/api/books/{book_id}/ambience/analyze",
        json={"provider": "heuristic"},
    )
    assert analyzed.status_code == 200
    assert analyzed.json()["plan"] == {"version": 1, "chapters": []}
