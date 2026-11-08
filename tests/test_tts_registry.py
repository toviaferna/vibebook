from pathlib import Path

import pytest

from audiol.tts.azure import AzureProvider
from audiol.tts.edge import EdgeProvider
from audiol.tts.fake import FakeProvider
from audiol.tts.piper import PiperProvider
from audiol.tts.registry import (
    ENGINES,
    engine_available,
    get_engine,
    list_engines,
    make_provider,
)


def test_engine_ids_are_unique():
    ids = [engine.id for engine in list_engines()]

    assert ids == ["piper", "espeak", "edge", "azure", "fake"]
    assert len(ids) == len(set(ids))
    assert set(ENGINES) == set(ids)


def test_unknown_engine_raises_clear_error():
    with pytest.raises(ValueError, match="Unknown TTS engine: nope"):
        get_engine("nope")


def test_engine_timings_are_declared():
    for engine in list_engines():
        assert engine.timing in {"native_word", "estimated_word", "segment"}


def test_edge_declares_word_timings():
    edge = get_engine("edge")

    assert edge.timing == "native_word"
    assert edge.requires_network is True
    assert edge.legacy is True


def test_fake_is_test_only():
    fake = get_engine("fake")

    assert fake.test_only is True
    assert fake.timing == "segment"


def test_fake_availability_requires_allow_fake():
    assert engine_available("fake") is False
    assert engine_available("fake", allow_fake=True) is True


def test_azure_availability_requires_credentials(monkeypatch):
    monkeypatch.delenv("AZURE_SPEECH_KEY", raising=False)
    monkeypatch.delenv("AZURE_SPEECH_REGION", raising=False)

    assert engine_available("azure") is False

    monkeypatch.setenv("AZURE_SPEECH_KEY", "key")
    monkeypatch.setenv("AZURE_SPEECH_REGION", "eastus")

    assert engine_available("azure") is True


def _install_fake_piper(tmp_path: Path, monkeypatch) -> None:
    binary = tmp_path / "piper.exe"
    binary.write_bytes(b"fake")
    voices = tmp_path / "voices"
    voices.mkdir()
    (voices / "es_MX-ald-medium.onnx").write_bytes(b"model")
    (voices / "es_MX-ald-medium.onnx.json").write_text("{}", encoding="utf-8")
    monkeypatch.setenv("VIBEBOOK_PIPER_BIN", str(binary))
    monkeypatch.setenv("VIBEBOOK_PIPER_VOICES", str(voices))


def test_piper_is_unavailable_without_binary_and_voice(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("VIBEBOOK_PIPER_BIN", str(tmp_path / "missing-piper"))
    monkeypatch.setenv("VIBEBOOK_PIPER_VOICES", str(tmp_path / "missing-voices"))

    assert engine_available("piper") is False


def test_piper_is_available_with_binary_and_voice(tmp_path: Path, monkeypatch):
    _install_fake_piper(tmp_path, monkeypatch)

    assert engine_available("piper") is True


def test_edge_is_available():
    assert engine_available("edge") is True


def test_make_provider_returns_edge():
    assert isinstance(make_provider("edge"), EdgeProvider)


def test_make_provider_returns_azure(monkeypatch):
    monkeypatch.setenv("AZURE_SPEECH_KEY", "key")
    monkeypatch.setenv("AZURE_SPEECH_REGION", "eastus")

    assert isinstance(make_provider("azure"), AzureProvider)


def test_make_provider_returns_fake_when_allowed():
    assert isinstance(make_provider("fake", allow_fake=True), FakeProvider)


def test_make_provider_rejects_fake_unless_allowed():
    with pytest.raises(ValueError, match="disabled"):
        make_provider("fake")


def test_make_provider_returns_piper(tmp_path: Path, monkeypatch):
    _install_fake_piper(tmp_path, monkeypatch)

    assert isinstance(make_provider("piper"), PiperProvider)


def test_make_provider_rejects_unimplemented_engine():
    with pytest.raises(ValueError, match="not implemented yet"):
        make_provider("espeak")


def test_make_provider_rejects_unknown_engine():
    with pytest.raises(ValueError, match="Unknown TTS engine"):
        make_provider("unknown")
