import hashlib

import pytest
import requests

from audiol.tts.piper_voices import (
    PIPER_VOICES,
    PiperNotConfigured,
    PiperVoiceFile,
    PiperVoiceSpec,
    download_piper_voice,
    get_piper_voice,
    piper_voice_dir,
    resolve_piper_config,
    resolve_piper_model,
    verify_file,
    verify_piper_voice,
)


def test_default_piper_voice_metadata():
    spec = get_piper_voice("es_MX-ald-medium")

    assert spec.locale == "es-MX"
    assert spec.gender == "male"
    assert spec.quality == "medium"
    assert any(item.path.endswith(".onnx") for item in spec.files)


def test_unknown_piper_voice_raises():
    with pytest.raises(ValueError, match="Unknown Piper voice"):
        get_piper_voice("nope")


def test_piper_voice_dir_honors_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("VIBEBOOK_PIPER_VOICES", str(tmp_path))

    assert piper_voice_dir() == tmp_path


def test_resolve_model_from_voices_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("VIBEBOOK_PIPER_VOICES", str(tmp_path))
    model = tmp_path / "es_MX-ald-medium.onnx"
    model.write_bytes(b"model")
    model.with_name(f"{model.name}.json").write_text("{}", encoding="utf-8")

    assert resolve_piper_model("es_MX-ald-medium") == model


def test_resolve_model_honors_explicit_model(monkeypatch, tmp_path):
    model = tmp_path / "custom.onnx"
    model.write_bytes(b"model")
    model.with_name(f"{model.name}.json").write_text("{}", encoding="utf-8")
    monkeypatch.setenv("VIBEBOOK_PIPER_MODEL", str(model))

    assert resolve_piper_model("es_MX-ald-medium") == model


def test_resolve_model_optional_returns_none(monkeypatch, tmp_path):
    monkeypatch.setenv("VIBEBOOK_PIPER_VOICES", str(tmp_path / "missing"))

    assert resolve_piper_model("es_MX-ald-medium", optional=True) is None


def test_resolve_model_requires_config(monkeypatch, tmp_path):
    monkeypatch.setenv("VIBEBOOK_PIPER_MODEL", str(tmp_path / "custom.onnx"))
    (tmp_path / "custom.onnx").write_bytes(b"model")

    with pytest.raises(PiperNotConfigured, match="incomplete"):
        resolve_piper_model("es_MX-ald-medium")


def test_resolve_config_honors_environment(monkeypatch, tmp_path):
    config = tmp_path / "voice.config.json"
    config.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("VIBEBOOK_PIPER_CONFIG", str(config))

    assert resolve_piper_config(tmp_path / "voice.onnx") == config


def test_verify_file_detects_size_and_digest(tmp_path):
    content = b"piper voice"
    target = tmp_path / "voice.onnx"
    target.write_bytes(content)
    expected = PiperVoiceFile(
        path="voice.onnx",
        size=len(content),
        md5=hashlib.md5(content).hexdigest(),  # noqa: S324 - test fixture
    )

    assert verify_file(target, expected)
    assert not verify_file(target, PiperVoiceFile(path="voice.onnx", size=1, md5=expected.md5))


def test_download_piper_voice_verifies_files(monkeypatch, tmp_path):
    model_content = b"model bytes"
    config_content = b"{}"
    spec = PiperVoiceSpec(
        id="test-voice",
        locale="es-MX",
        gender="male",
        quality="test",
        license="test",
        source_url="",
        files=(
            PiperVoiceFile(
                path="test/test-voice.onnx",
                size=len(model_content),
                md5=hashlib.md5(model_content).hexdigest(),  # noqa: S324 - test fixture
            ),
            PiperVoiceFile(
                path="test/test-voice.onnx.json",
                size=len(config_content),
                md5=hashlib.md5(config_content).hexdigest(),  # noqa: S324 - test fixture
            ),
        ),
    )
    monkeypatch.setitem(PIPER_VOICES, "test-voice", spec)

    class Response:
        def __init__(self, content: bytes) -> None:
            self.content = content

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def raise_for_status(self) -> None:
            return None

        def iter_content(self, chunk_size: int):
            yield self.content

    payloads = {
        "test-voice.onnx": model_content,
        "test-voice.onnx.json": config_content,
    }

    def fake_get(url: str, **kwargs):
        return Response(payloads[url.rsplit("/", 1)[-1]])

    monkeypatch.setattr("audiol.tts.piper_voices.requests.get", fake_get)

    model = download_piper_voice("test-voice", tmp_path)

    assert model.read_bytes() == model_content
    assert model.with_name(f"{model.name}.json").read_bytes() == config_content
    assert verify_piper_voice("test-voice", tmp_path)


def test_download_piper_voice_rejects_bad_digest(monkeypatch, tmp_path):
    spec = PiperVoiceSpec(
        id="test-voice",
        locale="es-MX",
        gender="male",
        quality="test",
        license="test",
        source_url="",
        files=(
            PiperVoiceFile(path="test/test-voice.onnx", size=4, md5="0" * 32),
            PiperVoiceFile(path="test/test-voice.onnx.json", size=2, md5="1" * 32),
        ),
    )
    monkeypatch.setitem(PIPER_VOICES, "test-voice", spec)

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def raise_for_status(self) -> None:
            return None

        def iter_content(self, chunk_size: int):
            yield b"nope"

    monkeypatch.setattr("audiol.tts.piper_voices.requests.get", lambda url, **kwargs: Response())

    with pytest.raises(PiperNotConfigured, match="does not match"):
        download_piper_voice("test-voice", tmp_path)

    assert not (tmp_path / "test-voice.onnx").exists()
    assert not list(tmp_path.glob("*.part"))


def test_download_piper_voice_reports_network_error(monkeypatch, tmp_path):
    spec = PiperVoiceSpec(
        id="test-voice",
        locale="es-MX",
        gender="male",
        quality="test",
        license="test",
        source_url="",
        files=(PiperVoiceFile(path="test/test-voice.onnx", size=4, md5="0" * 32),),
    )
    monkeypatch.setitem(PIPER_VOICES, "test-voice", spec)

    def fake_get(url: str, **kwargs):
        raise requests.RequestException("network down")

    monkeypatch.setattr("audiol.tts.piper_voices.requests.get", fake_get)

    with pytest.raises(PiperNotConfigured, match="Could not download.*network down"):
        download_piper_voice("test-voice", tmp_path)


def test_missing_voice_error_mentions_download(monkeypatch, tmp_path):
    monkeypatch.setenv("VIBEBOOK_PIPER_VOICES", str(tmp_path / "missing"))

    with pytest.raises(PiperNotConfigured, match="vibebook piper download"):
        resolve_piper_model("es_MX-ald-medium")
