from pathlib import Path

import pytest

from audiol.tts.azure import AzureProvider
from audiol.tts.edge import EdgeProvider
from audiol.tts.espeak import EspeakProvider
from audiol.tts.fake import FakeProvider
from audiol.tts.piper import PiperProvider
from audiol.tts.registry import (
    ENGINES,
    default_voice_for_engine,
    engine_available,
    get_engine,
    list_engines,
    make_provider,
    preferred_engine,
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


def _install_fake_espeak(tmp_path: Path, monkeypatch) -> None:
    binary = tmp_path / "espeak-ng.exe"
    binary.write_bytes(b"fake")
    monkeypatch.setenv("VIBEBOOK_ESPEAK_BIN", str(binary))


def test_espeak_is_unavailable_without_binary(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("VIBEBOOK_ESPEAK_BIN", str(tmp_path / "missing-espeak"))

    assert engine_available("espeak") is False


def test_espeak_is_available_with_binary(tmp_path: Path, monkeypatch):
    _install_fake_espeak(tmp_path, monkeypatch)

    assert engine_available("espeak") is True


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


def test_make_provider_returns_espeak(tmp_path: Path, monkeypatch):
    _install_fake_espeak(tmp_path, monkeypatch)

    assert isinstance(make_provider("espeak"), EspeakProvider)


def test_preferred_engine_prefers_piper(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("VIBEBOOK_ESPEAK_BIN", str(tmp_path / "missing-espeak"))
    _install_fake_piper(tmp_path, monkeypatch)

    assert preferred_engine() == "piper"


def test_preferred_engine_falls_back_to_espeak(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("VIBEBOOK_PIPER_BIN", str(tmp_path / "missing-piper"))
    monkeypatch.setenv("VIBEBOOK_PIPER_VOICES", str(tmp_path / "missing-voices"))
    _install_fake_espeak(tmp_path, monkeypatch)

    assert preferred_engine() == "espeak"


def test_preferred_engine_returns_none_without_local_engines(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("VIBEBOOK_PIPER_BIN", str(tmp_path / "missing-piper"))
    monkeypatch.setenv("VIBEBOOK_PIPER_VOICES", str(tmp_path / "missing-voices"))
    monkeypatch.setenv("VIBEBOOK_ESPEAK_BIN", str(tmp_path / "missing-espeak"))

    assert preferred_engine() is None


def test_default_voice_for_engine():
    assert default_voice_for_engine("piper") == "es_MX-ald-medium"
    assert default_voice_for_engine("espeak") == "es-419"
    assert default_voice_for_engine("edge") == "es-MX-JorgeNeural"
    assert default_voice_for_engine("azure") == "es-MX-JorgeNeural"


def test_make_provider_rejects_unknown_engine():
    with pytest.raises(ValueError, match="Unknown TTS engine"):
        make_provider("unknown")
