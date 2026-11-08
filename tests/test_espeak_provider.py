import os
import subprocess
import sys
from pathlib import Path

import pytest

from audiol.tts.espeak import (
    EspeakNotConfigured,
    EspeakProvider,
    _speed,
    resolve_espeak_binary,
    resolve_espeak_path,
)


def _fake_install(tmp_path: Path) -> tuple[Path, Path]:
    binary = tmp_path / "espeak-ng.exe"
    binary.write_bytes(b"binary")
    data = tmp_path / "espeak-ng-data"
    data.mkdir()
    return binary, data


def _write_wav(command: list[str]) -> None:
    output = Path(command[command.index("-w") + 1])
    output.write_bytes(b"RIFF" + b"\x00" * 32)


def test_speed_maps_rate():
    assert _speed("+0%") == 175
    assert _speed("-10%") == 158
    assert _speed("+10%") == 193
    with pytest.raises(ValueError, match="-100%"):
        _speed("-100%")


def test_synthesize_builds_espeak_command(monkeypatch, tmp_path):
    binary, _ = _fake_install(tmp_path)
    provider = EspeakProvider(binary=binary)
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
        "es-419",
        output,
        rate="-10%",
    )

    command = captured["command"]
    kwargs = captured["kwargs"]
    assert isinstance(command, list)
    assert Path(command[0]).is_file()
    assert "espeak" in Path(command[0]).name.lower()
    assert command[command.index("-v") + 1] == "es-419"
    assert command[command.index("-s") + 1] == "158"
    assert Path(command[command.index("--path") + 1]).is_dir()
    assert "--stdin" in command
    assert kwargs["input"] == "Hola mundo\n"
    assert result.path == output
    assert result.words == []
    if os.name == "nt" and not str(output).isascii():
        assert str(Path(command[command.index("-w") + 1])).isascii()


def test_synthesize_reports_process_failure(monkeypatch, tmp_path):
    binary, _ = _fake_install(tmp_path)
    provider = EspeakProvider(binary=binary)
    output = tmp_path / "out.wav"

    def fake_run(command: list[str], **kwargs):
        return subprocess.CompletedProcess(command, 2, "", "espeak exploded")

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(RuntimeError, match="espeak exploded"):
        provider.synthesize("Hola", "es-419", output)
    assert not output.exists()


def test_synthesize_reports_timeout(monkeypatch, tmp_path):
    binary, _ = _fake_install(tmp_path)
    provider = EspeakProvider(binary=binary, timeout=5)
    output = tmp_path / "out.wav"

    def fake_run(command: list[str], **kwargs):
        raise subprocess.TimeoutExpired(command, 5)

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(RuntimeError, match="timed out after 5"):
        provider.synthesize("Hola", "es-419", output)
    assert not output.exists()


def test_synthesize_requires_audio_output(monkeypatch, tmp_path):
    binary, _ = _fake_install(tmp_path)
    provider = EspeakProvider(binary=binary)
    output = tmp_path / "out.wav"

    def fake_run(command: list[str], **kwargs):
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(RuntimeError, match="did not produce"):
        provider.synthesize("Hola", "es-419", output)


def test_resolve_binary_from_environment(monkeypatch, tmp_path):
    binary, _ = _fake_install(tmp_path)
    monkeypatch.setenv("VIBEBOOK_ESPEAK_BIN", str(binary))

    assert resolve_espeak_binary() == binary


def test_resolve_binary_optional_without_install(monkeypatch, tmp_path):
    monkeypatch.setenv("VIBEBOOK_ESPEAK_BIN", str(tmp_path / "missing-espeak"))

    assert resolve_espeak_binary(optional=True) is None
    with pytest.raises(EspeakNotConfigured, match="eSpeak NG binary not found"):
        resolve_espeak_binary()


def test_resolve_bundled_binary(monkeypatch, tmp_path):
    monkeypatch.delenv("VIBEBOOK_ESPEAK_BIN", raising=False)
    bundled = tmp_path / "bundle" / "espeak" / "bin" / "espeak-ng.exe"
    bundled.parent.mkdir(parents=True)
    bundled.write_bytes(b"binary")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path / "bundle"), raising=False)

    assert resolve_espeak_binary(optional=True) == bundled


def test_resolve_path_from_binary_dir(monkeypatch, tmp_path):
    monkeypatch.delenv("VIBEBOOK_ESPEAK_PATH", raising=False)
    binary, _ = _fake_install(tmp_path)

    assert resolve_espeak_path(binary) == tmp_path


def test_resolve_path_honors_environment(monkeypatch, tmp_path):
    data = tmp_path / "custom" / "espeak-ng-data"
    data.mkdir(parents=True)
    monkeypatch.setenv("VIBEBOOK_ESPEAK_PATH", str(data))

    assert resolve_espeak_path(tmp_path / "espeak-ng.exe") == data.parent


def _real_espeak_available() -> bool:
    try:
        return resolve_espeak_binary(optional=True) is not None
    except Exception:
        return False


@pytest.mark.skipif(not _real_espeak_available(), reason="real eSpeak NG not installed")
def test_real_espeak_synthesizes_wav(tmp_path):
    provider = EspeakProvider()
    result = provider.synthesize(
        "Hola. Esta es una prueba real de eSpeak NG: canción, niño, corazón.",
        "es-419",
        tmp_path / "real.wav",
        rate="-10%",
    )

    assert result.path.read_bytes()[:4] == b"RIFF"
    assert result.path.stat().st_size > 1000
