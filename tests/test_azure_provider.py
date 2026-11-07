from pathlib import Path

import pytest

from audiol.tts.azure import AzureProvider


def test_build_ssml_escapes_text_and_adds_style():
    provider = AzureProvider(key="test-key", region="eastus")
    ssml = provider.build_ssml(
        "Hola & adiós",
        "es-MX-JorgeNeural",
        style="cheerful",
        rate="-6%",
    )
    assert 'name="es-MX-JorgeNeural"' in ssml
    assert 'style="cheerful"' in ssml
    assert '<prosody rate="-6%">' in ssml
    assert "Hola &amp; adiós" in ssml
    assert 'xml:lang="es-MX"' in ssml


def test_build_ssml_rejects_invalid_rate():
    provider = AzureProvider(key="test-key", region="eastus")
    with pytest.raises(ValueError):
        provider.build_ssml("Hola", "es-MX-JorgeNeural", rate="fast")


def test_synthesize_writes_audio(monkeypatch, tmp_path: Path):
    class FakeResponse:
        status_code = 200
        content = b"ID3azure"
        text = ""

    captured = {}

    def fake_post(url, headers, data, timeout):
        captured["body"] = data.decode("utf-8")
        return FakeResponse()

    monkeypatch.setattr("audiol.tts.azure.requests.post", fake_post)
    output = tmp_path / "azure.mp3"
    provider = AzureProvider(key="test-key", region="eastus")

    result = provider.synthesize("Hola", "es-MX-JorgeNeural", output, style="cheerful", rate="-6%")

    assert result.path == output
    assert output.read_bytes() == b"ID3azure"
    assert result.words == []
    assert '<prosody rate="-6%">' in captured["body"]


def test_missing_credentials_raise(monkeypatch):
    monkeypatch.delenv("AZURE_SPEECH_KEY", raising=False)
    monkeypatch.delenv("AZURE_SPEECH_REGION", raising=False)
    with pytest.raises(ValueError):
        AzureProvider()
