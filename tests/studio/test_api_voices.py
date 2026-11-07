from pathlib import Path

from fastapi.testclient import TestClient

from audiol.studio.app import create_app
from audiol.studio.settings import Settings
from audiol.tts.fake import FakeProvider


def test_list_voices(client):
    response = client.get("/api/voices")

    assert response.status_code == 200
    voices = response.json()
    assert any(voice["id"] == "es-MX-JorgeNeural" for voice in voices)
    assert all("engines" in voice and "styles" in voice for voice in voices)


def test_preview_with_fake_is_cached(client):
    payload = {
        "voice": "es-MX-JorgeNeural",
        "engine": "fake",
        "style": "neutral",
        "rate": "-10%",
        "text": "Hola, esta es una muestra.",
    }

    first = client.post("/api/voices/preview", json=payload)
    second = client.post("/api/voices/preview", json=payload)

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert first.json() == second.json()
    audio = client.get(first.json()["url"])
    assert audio.status_code == 200
    assert audio.content


def test_preview_rejects_long_text(client):
    response = client.post(
        "/api/voices/preview",
        json={
            "voice": "es-MX-JorgeNeural",
            "engine": "fake",
            "text": "x" * 121,
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_preview_rejects_invalid_rate(client):
    response = client.post(
        "/api/voices/preview",
        json={
            "voice": "es-MX-JorgeNeural",
            "engine": "fake",
            "rate": "fast",
            "text": "Hola",
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_options"


def test_preview_rejects_unknown_voice(client):
    response = client.post(
        "/api/voices/preview",
        json={"voice": "nope", "engine": "fake", "text": "Hola"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_options"


def test_preview_rejects_fake_when_disabled(tmp_path: Path):
    settings = Settings(
        library_dir=tmp_path / "library",
        token="test-token",
        allow_fake=False,
    )
    app = create_app(settings, provider_factory=lambda engine: FakeProvider())
    with TestClient(app, base_url="http://127.0.0.1") as client:
        client.headers.update({"X-Vibebook-Token": "test-token"})
        response = client.post(
            "/api/voices/preview",
            json={"voice": "es-MX-JorgeNeural", "engine": "fake", "text": "Hola"},
        )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_options"


def test_settings_roundtrip(client):
    initial = client.get("/api/settings")
    assert initial.status_code == 200
    assert initial.json()["reader_theme"] == "light"
    assert initial.json()["azure_configured"] is False

    updated = client.put("/api/settings", json={"reader_theme": "night"})
    assert updated.status_code == 200
    assert updated.json()["reader_theme"] == "night"

    fetched = client.get("/api/settings")
    assert fetched.json()["reader_theme"] == "night"


def test_settings_rejects_unknown_key(client):
    response = client.put("/api/settings", json={"password": "x"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_azure_key_never_returned(client, monkeypatch):
    monkeypatch.setenv("AZURE_SPEECH_KEY", "super-secret")
    monkeypatch.setenv("AZURE_SPEECH_REGION", "eastus")

    payload = client.get("/api/settings").json()

    assert payload["azure_configured"] is True
    assert "super-secret" not in str(payload)


def test_invalid_preview_key_returns_404(client):
    assert client.get("/api/previews/nope.mp3").status_code == 404
    assert client.get("/api/previews/../../etc/passwd").status_code == 404
