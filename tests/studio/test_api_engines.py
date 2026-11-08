def test_list_engines(client, monkeypatch):
    monkeypatch.delenv("AZURE_SPEECH_KEY", raising=False)
    monkeypatch.delenv("AZURE_SPEECH_REGION", raising=False)

    response = client.get("/api/engines")

    assert response.status_code == 200
    items = response.json()["items"]
    assert [item["id"] for item in items] == ["piper", "espeak", "edge", "azure", "fake"]

    by_id = {item["id"]: item for item in items}
    assert by_id["edge"]["available"] is True
    assert by_id["edge"]["legacy"] is True
    assert by_id["edge"]["timing"] == "native_word"
    assert by_id["piper"]["implemented"] is False
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
            "engine": "piper",
            "style": "neutral",
            "rate": "-10%",
            "force": False,
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_options"
    assert "not implemented yet" in response.json()["error"]["message"]
