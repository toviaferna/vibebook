from pathlib import Path


def _fake_piper(tmp_path: Path) -> tuple[Path, Path]:
    binary = tmp_path / "piper.exe"
    binary.write_bytes(b"binary")
    voices = tmp_path / "piper"
    model_dir = voices / "vits-piper-es_ES-davefx-medium"
    model_dir.mkdir(parents=True)
    (model_dir / "es_ES-davefx-medium.onnx").write_bytes(b"onnx")
    (model_dir / "es_ES-davefx-medium.onnx.json").write_text(
        "{}",
        encoding="utf-8",
    )
    return binary, voices


def test_piper_status_and_update(client, tmp_path: Path):
    binary, voices = _fake_piper(tmp_path)

    response = client.put(
        "/api/piper",
        json={
            "binary": str(binary),
            "voices_dir": str(voices),
            "espeak_data": None,
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["binary_configured"] is True
    assert body["binary"] == str(binary)
    assert body["voices_dir"] == str(voices)
    assert [voice["id"] for voice in body["voices"]] == ["es_ES-davefx-medium"]

    persisted = client.get("/api/piper")
    assert persisted.status_code == 200
    assert persisted.json()["voices"] == body["voices"]

    engines = client.get("/api/engines").json()["items"]
    piper = next(item for item in engines if item["id"] == "piper")
    assert piper["available"] is True

    engine_voices = client.get("/api/engines/piper/voices").json()
    assert any(voice["id"] == "es_ES-davefx-medium" for voice in engine_voices)

    all_voices = client.get("/api/voices?engine=piper").json()
    assert any(voice["id"] == "es_ES-davefx-medium" for voice in all_voices)


def test_piper_update_rejects_missing_paths(client, tmp_path: Path):
    response = client.put(
        "/api/piper",
        json={
            "binary": str(tmp_path / "missing-piper"),
            "voices_dir": str(tmp_path / "missing-voices"),
        },
    )

    assert response.status_code == 422
    message = response.json()["error"]["message"]
    assert "binario" in message
    assert "voces" in message


def test_piper_can_be_cleared(client, tmp_path: Path):
    binary, voices = _fake_piper(tmp_path)
    assert (
        client.put(
            "/api/piper",
            json={"binary": str(binary), "voices_dir": str(voices)},
        ).status_code
        == 200
    )

    response = client.put(
        "/api/piper",
        json={"binary": None, "voices_dir": None, "espeak_data": None},
    )

    assert response.status_code == 200
    assert response.json()["binary_configured"] is False
    assert response.json()["voices"] == []
