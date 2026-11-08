def test_list_engines(client, monkeypatch, tmp_path):
    monkeypatch.delenv("AZURE_SPEECH_KEY", raising=False)
    monkeypatch.delenv("AZURE_SPEECH_REGION", raising=False)
    monkeypatch.setenv("VIBEBOOK_PIPER_BIN", str(tmp_path / "missing-piper"))
    monkeypatch.setenv("VIBEBOOK_PIPER_VOICES", str(tmp_path / "missing-voices"))

    response = client.get("/api/engines")

    assert response.status_code == 200
    items = response.json()["items"]
    assert [item["id"] for item in items] == ["piper", "espeak", "edge", "azure", "fake"]

    by_id = {item["id"]: item for item in items}
    assert by_id["edge"]["available"] is True
    assert by_id["edge"]["legacy"] is True
    assert by_id["edge"]["timing"] == "native_word"
    assert by_id["piper"]["implemented"] is True
    assert by_id["piper"]["available"] is False
    assert by_id["espeak"]["available"] is False
    assert by_id["azure"]["available"] is False
    assert by_id["fake"]["available"] is True
    assert by_id["fake"]["test_only"] is True

    for item in items:
        assert {
            "id",
            "label",
            "kind",
            "transport",
            "requires_network",
            "requires_key",
            "supports_styles",
            "timing",
            "max_chars",
            "audio_suffix",
            "license",
            "source_url",
            "description",
            "config_schema",
            "legacy",
            "implemented",
            "test_only",
            "available",
        } <= set(item)


def test_engine_response_never_leaks_secrets(client, monkeypatch):
    monkeypatch.setenv("AZURE_SPEECH_KEY", "super-secret")
    monkeypatch.setenv("AZURE_SPEECH_REGION", "eastus")

    response = client.get("/api/engines")

    assert response.status_code == 200
    assert "super-secret" not in response.text
    azure = next(item for item in response.json()["items"] if item["id"] == "azure")
    assert azure["available"] is True
    assert azure["config_schema"] == {
        "key_env": "AZURE_SPEECH_KEY",
        "region_env": "AZURE_SPEECH_REGION",
    }


def test_convert_rejects_unknown_engine(client, imported):
    response = client.post(
        f"/api/books/{imported['id']}/convert",
        json={
            "voice": "es-MX-JorgeNeural",
            "engine": "nope",
            "style": "neutral",
            "rate": "-10%",
            "force": False,
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_options"
    assert "Unknown TTS engine" in response.json()["error"]["message"]


def test_convert_rejects_unimplemented_engine(client, imported):
    response = client.post(
        f"/api/books/{imported['id']}/convert",
        json={
            "voice": "es-MX-JorgeNeural",
            "engine": "espeak",
            "style": "neutral",
            "rate": "-10%",
            "force": False,
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_options"
    assert "not implemented yet" in response.json()["error"]["message"]


def test_convert_rejects_uninstalled_piper(client, imported, monkeypatch, tmp_path):
    from audiol.tts.registry import make_provider

    monkeypatch.setenv("VIBEBOOK_PIPER_BIN", str(tmp_path / "missing-piper"))
    monkeypatch.setenv("VIBEBOOK_PIPER_VOICES", str(tmp_path / "missing-voices"))
    client.app.state.jobs.provider_factory = lambda engine: make_provider(engine, allow_fake=True)

    response = client.post(
        f"/api/books/{imported['id']}/convert",
        json={
            "voice": "es_MX-ald-medium",
            "engine": "piper",
            "style": "neutral",
            "rate": "-10%",
            "force": False,
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_options"
    assert "Piper" in response.json()["error"]["message"]


def test_engines_reports_installed_piper(client, monkeypatch, tmp_path):
    binary = tmp_path / "piper.exe"
    binary.write_bytes(b"fake")
    voices = tmp_path / "voices"
    voices.mkdir()
    (voices / "es_MX-ald-medium.onnx").write_bytes(b"model")
    (voices / "es_MX-ald-medium.onnx.json").write_text("{}", encoding="utf-8")
    monkeypatch.setenv("VIBEBOOK_PIPER_BIN", str(binary))
    monkeypatch.setenv("VIBEBOOK_PIPER_VOICES", str(voices))

    response = client.get("/api/engines")

    assert response.status_code == 200
    piper = next(item for item in response.json()["items"] if item["id"] == "piper")
    assert piper["available"] is True
