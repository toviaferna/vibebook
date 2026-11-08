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


def test_filter_voices_by_engine(client):
    response = client.get("/api/voices", params={"engine": "azure"})

    assert response.status_code == 200
    ids = [voice["id"] for voice in response.json()]
    assert ids == ["es-MX-DaliaNeural", "es-MX-JorgeNeural"]


def test_filter_voices_by_piper(client):
    response = client.get("/api/voices", params={"engine": "piper"})

    assert response.status_code == 200
    assert [voice["id"] for voice in response.json()] == ["es_MX-ald-medium"]


def test_filter_voices_by_espeak(client):
    response = client.get("/api/voices", params={"engine": "espeak"})

    assert response.status_code == 200
    assert [voice["id"] for voice in response.json()] == ["es-419"]


def test_filter_voices_by_fake_keeps_catalog(client):
    response = client.get("/api/voices", params={"engine": "fake"})

    assert response.status_code == 200
    assert len(response.json()) == len(client.get("/api/voices").json())


def test_filter_voices_rejects_unknown_engine(client):
    response = client.get("/api/voices", params={"engine": "nope"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_options"


def test_preview_rejects_uninstalled_espeak(client, monkeypatch, tmp_path):
    from audiol.tts.registry import make_provider

    monkeypatch.setenv("VIBEBOOK_ESPEAK_BIN", str(tmp_path / "missing-espeak"))
    client.app.state.provider_factory = lambda engine: make_provider(engine, allow_fake=True)

    response = client.post(
        "/api/voices/preview",
        json={
            "voice": "es-419",
            "engine": "espeak",
            "text": "Hola",
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_options"
    assert "eSpeak NG" in response.json()["error"]["message"]


def test_preview_rejects_uninstalled_piper(client, monkeypatch, tmp_path):
    from audiol.tts.registry import make_provider

    monkeypatch.setenv("VIBEBOOK_PIPER_BIN", str(tmp_path / "missing-piper"))
    monkeypatch.setenv("VIBEBOOK_PIPER_VOICES", str(tmp_path / "missing-voices"))
    client.app.state.provider_factory = lambda engine: make_provider(engine, allow_fake=True)

    response = client.post(
        "/api/voices/preview",
        json={
            "voice": "es_MX-ald-medium",
            "engine": "piper",
            "text": "Hola",
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_options"
    assert "Piper" in response.json()["error"]["message"]


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
    assert initial.json()["theme_mode"] == "system"
    assert initial.json()["reader_palette"] == "paper"
    assert initial.json()["reader_theme"] == "light"
    assert initial.json()["default_engine"] == "edge"
    assert initial.json()["default_voice"] == "es-MX-JorgeNeural"
    assert initial.json()["azure_configured"] is False

    updated = client.put(
        "/api/settings",
        json={"theme_mode": "dark", "reader_palette": "night"},
    )
    assert updated.status_code == 200
    assert updated.json()["theme_mode"] == "dark"
    assert updated.json()["reader_palette"] == "night"
    assert updated.json()["reader_theme"] == "night"

    fetched = client.get("/api/settings")
    assert fetched.json()["theme_mode"] == "dark"
    assert fetched.json()["reader_palette"] == "night"
    assert fetched.json()["reader_theme"] == "night"


def test_settings_migrates_legacy_reader_theme(client):
    client.app.state.db.set_setting("reader_theme", "sepia")

    payload = client.get("/api/settings").json()

    assert payload["theme_mode"] == "system"
    assert payload["reader_palette"] == "sepia"
    assert payload["reader_theme"] == "sepia"


def test_settings_accepts_legacy_reader_theme(client):
    updated = client.put("/api/settings", json={"reader_theme": "night"})

    assert updated.status_code == 200
    assert updated.json()["reader_palette"] == "night"
    assert updated.json()["reader_theme"] == "night"


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


def _install_fake_piper(tmp_path: Path, monkeypatch) -> None:
    binary = tmp_path / "piper.exe"
    binary.write_bytes(b"fake")
    voices = tmp_path / "voices"
    voices.mkdir()
    (voices / "es_MX-ald-medium.onnx").write_bytes(b"model")
    (voices / "es_MX-ald-medium.onnx.json").write_text("{}", encoding="utf-8")
    monkeypatch.setenv("VIBEBOOK_PIPER_BIN", str(binary))
    monkeypatch.setenv("VIBEBOOK_PIPER_VOICES", str(voices))


def _install_fake_espeak(tmp_path: Path, monkeypatch) -> None:
    binary = tmp_path / "espeak-ng.exe"
    binary.write_bytes(b"fake")
    monkeypatch.setenv("VIBEBOOK_ESPEAK_BIN", str(binary))


def test_settings_defaults_to_piper_when_available(client, monkeypatch, tmp_path):
    _install_fake_piper(tmp_path, monkeypatch)

    payload = client.get("/api/settings").json()

    assert payload["default_engine"] == "piper"
    assert payload["default_voice"] == "es_MX-ald-medium"


def test_settings_defaults_to_espeak_when_piper_is_missing(client, monkeypatch, tmp_path):
    _install_fake_espeak(tmp_path, monkeypatch)

    payload = client.get("/api/settings").json()

    assert payload["default_engine"] == "espeak"
    assert payload["default_voice"] == "es-419"


def test_settings_update_default_engine(client, monkeypatch, tmp_path):
    _install_fake_piper(tmp_path, monkeypatch)

    response = client.put("/api/settings", json={"default_engine": "piper"})

    assert response.status_code == 200, response.text
    assert response.json()["default_engine"] == "piper"
    assert response.json()["default_voice"] == "es_MX-ald-medium"
    assert client.get("/api/settings").json()["default_engine"] == "piper"


def test_settings_rejects_unavailable_engine(client, monkeypatch, tmp_path):
    monkeypatch.setenv("VIBEBOOK_PIPER_BIN", str(tmp_path / "missing-piper"))
    monkeypatch.setenv("VIBEBOOK_PIPER_VOICES", str(tmp_path / "missing-voices"))

    response = client.put("/api/settings", json={"default_engine": "piper"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_options"


def test_settings_rejects_incompatible_voice(client, monkeypatch, tmp_path):
    _install_fake_espeak(tmp_path, monkeypatch)

    response = client.put(
        "/api/settings",
        json={"default_engine": "espeak", "default_voice": "es-MX-JorgeNeural"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_options"
