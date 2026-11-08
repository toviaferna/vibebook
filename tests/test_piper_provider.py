import os
import subprocess
from pathlib import Path

import pytest

from audiol.tts.piper import (
    PiperProvider,
    _length_scale,
    resolve_espeak_data,
    resolve_piper_binary,
)
from audiol.tts.piper_voices import (
    DEFAULT_PIPER_VOICE,
    PiperNotConfigured,
    resolve_piper_model,
)


def _fake_install(tmp_path: Path) -> tuple[Path, Path]:
    binary = tmp_path / "piper.exe"
    binary.write_bytes(b"binary")
    model = tmp_path / "es_MX-ald-medium.onnx"
    model.write_bytes(b"model")
    model.with_name(f"{model.name}.json").write_text("{}", encoding="utf-8")
    return binary, model


def _write_wav(command: list[str]) -> None:
    output = Path(command[command.index("-f") + 1])
    output.write_bytes(b"RIFF" + b"\x00" * 32)


def test_length_scale_maps_rate():
    assert _length_scale("+0%") == pytest.approx(1.0)
    assert _length_scale("-10%") == pytest.approx(1.111, abs=0.001)
    assert _length_scale("+10%") == pytest.approx(0.909, abs=0.001)
    with pytest.raises(ValueError, match="-100%"):
        _length_scale("-100%")


def test_synthesize_builds_piper_command(monkeypatch, tmp_path):
    binary, model = _fake_install(tmp_path)
    provider = PiperProvider(binary=binary, model=model)
    output = tmp_path / "out.wav"
    captured: dict[str, object] = {}

    def fake_run(command: list[str], **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        _write_wav(command)
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = provider.synthesize(
        "Hola mundo",
        "es_MX-ald-medium",
        output,
        rate="-10%",
    )

    command = captured["command"]
    kwargs = captured["kwargs"]
    assert isinstance(command, list)
    assert Path(command[0]).name == "piper.exe"
    assert "-m" in command
    assert "-c" in command
    assert "-f" in command
    assert command[command.index("--length_scale") + 1] == "1.111"
    assert kwargs["input"] == "Hola mundo\n"
    assert result.path == output
    assert result.words == []
    if os.name == "nt" and not str(output).isascii():
        assert str(Path(command[command.index("-f") + 1])).isascii()


def test_synthesize_reports_process_failure(monkeypatch, tmp_path):
    binary, model = _fake_install(tmp_path)
    provider = PiperProvider(binary=binary, model=model)
    output = tmp_path / "out.wav"

    def fake_run(command: list[str], **kwargs):
        return subprocess.CompletedProcess(command, 2, "", "model exploded")

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(RuntimeError, match="model exploded"):
        provider.synthesize("Hola", DEFAULT_PIPER_VOICE, output)
    assert not output.exists()


def test_synthesize_reports_timeout(monkeypatch, tmp_path):
    binary, model = _fake_install(tmp_path)
    provider = PiperProvider(binary=binary, model=model, timeout=5)
    output = tmp_path / "out.wav"

    def fake_run(command: list[str], **kwargs):
        raise subprocess.TimeoutExpired(command, 5)

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(RuntimeError, match="timed out after 5"):
        provider.synthesize("Hola", DEFAULT_PIPER_VOICE, output)
    assert not output.exists()


def test_synthesize_requires_audio_output(monkeypatch, tmp_path):
    binary, model = _fake_install(tmp_path)
    provider = PiperProvider(binary=binary, model=model)
    output = tmp_path / "out.wav"

    def fake_run(command: list[str], **kwargs):
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(RuntimeError, match="did not produce"):
        provider.synthesize("Hola", DEFAULT_PIPER_VOICE, output)


def test_resolve_binary_from_environment(monkeypatch, tmp_path):
    binary, _ = _fake_install(tmp_path)
    monkeypatch.setenv("VIBEBOOK_PIPER_BIN", str(binary))

    assert resolve_piper_binary() == binary


def test_resolve_binary_optional_without_install(monkeypatch, tmp_path):
    monkeypatch.setenv("VIBEBOOK_PIPER_BIN", str(tmp_path / "missing-piper"))

    assert resolve_piper_binary(optional=True) is None
    with pytest.raises(PiperNotConfigured, match="Piper binary not found"):
        resolve_piper_binary()


def test_resolve_espeak_data_from_binary_dir(monkeypatch, tmp_path):
    monkeypatch.delenv("VIBEBOOK_PIPER_ESPEAK_DATA", raising=False)
    binary, _ = _fake_install(tmp_path)
    data = tmp_path / "espeak-ng-data"
    data.mkdir()

    assert resolve_espeak_data(binary) == data


def test_resolve_espeak_data_missing(monkeypatch, tmp_path):
    binary, _ = _fake_install(tmp_path)
    monkeypatch.setenv("VIBEBOOK_PIPER_ESPEAK_DATA", str(tmp_path / "missing"))

    with pytest.raises(PiperNotConfigured, match="does not exist"):
        resolve_espeak_data(binary)


def _real_piper_available() -> bool:
    try:
        return (
            resolve_piper_binary(optional=True) is not None
            and resolve_piper_model(DEFAULT_PIPER_VOICE, optional=True) is not None
        )
    except Exception:
        return False


@pytest.mark.skipif(not _real_piper_available(), reason="real Piper binary/voice not installed")
def test_real_piper_synthesizes_wav(tmp_path):
    provider = PiperProvider()
    result = provider.synthesize(
        "Hola. Esta es una prueba real de Piper.",
        DEFAULT_PIPER_VOICE,
        tmp_path / "real.wav",
        rate="-10%",
    )

    assert result.path.read_bytes()[:4] == b"RIFF"
    assert result.path.stat().st_size > 1000
