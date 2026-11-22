import os
from pathlib import Path

from audiol.tts.piper import piper_ready
from audiol.tts.piper_settings import (
    PiperSettings,
    apply_piper_settings,
    load_piper_settings,
    save_piper_settings,
    suggested_voices_dirs,
    validate_piper_settings,
)
from audiol.tts.piper_voices import (
    discover_piper_voices,
    piper_voice_available,
    resolve_piper_model,
)


def _fake_voice(root: Path, voice_id: str) -> Path:
    directory = root / f"vits-piper-{voice_id}"
    directory.mkdir(parents=True)
    model = directory / f"{voice_id}.onnx"
    model.write_bytes(b"onnx")
    (directory / f"{voice_id}.onnx.json").write_text("{}", encoding="utf-8")
    return model


def _fake_binary(root: Path) -> Path:
    binary = root / "piper.exe"
    binary.write_bytes(b"binary")
    return binary


def test_discover_piper_voices_finds_nested_models(tmp_path, monkeypatch):
    voices = tmp_path / "piper"
    _fake_voice(voices, "es_MX-ald-medium")
    _fake_voice(voices, "es_ES-davefx-medium")
    _fake_voice(voices, "es-glados-medium")
    monkeypatch.setenv("VIBEBOOK_PIPER_VOICES", str(voices))

    found = discover_piper_voices()

    by_id = {voice.id: voice for voice in found}
    assert set(by_id) == {
        "es_MX-ald-medium",
        "es_ES-davefx-medium",
        "es-glados-medium",
    }
    assert by_id["es_MX-ald-medium"].locale == "es-MX"
    assert by_id["es_MX-ald-medium"].gender == "male"
    assert by_id["es_ES-davefx-medium"].locale == "es-ES"
    assert by_id["es-glados-medium"].locale == "es"


def test_resolve_custom_nested_model(tmp_path, monkeypatch):
    voices = tmp_path / "piper"
    model = _fake_voice(voices, "es_AR-daniela-high")
    monkeypatch.setenv("VIBEBOOK_PIPER_VOICES", str(voices))

    assert resolve_piper_model("es_AR-daniela-high") == model
    assert piper_voice_available("es_AR-daniela-high") is True
    assert piper_voice_available("missing-voice") is False


def test_piper_ready_with_binary_and_custom_voice(tmp_path, monkeypatch):
    voices = tmp_path / "piper"
    _fake_voice(voices, "es_MX-claude-high")
    monkeypatch.setenv("VIBEBOOK_PIPER_VOICES", str(voices))
    assert piper_ready() is False

    binary = _fake_binary(tmp_path)
    monkeypatch.setenv("VIBEBOOK_PIPER_BIN", str(binary))
    assert piper_ready() is True


def test_settings_round_trip_and_apply(tmp_path, monkeypatch):
    config = tmp_path / "piper.json"
    monkeypatch.setenv("VIBEBOOK_PIPER_SETTINGS", str(config))
    settings = PiperSettings(
        binary=str(tmp_path / "piper"),
        voices_dir=str(tmp_path / "voices"),
        espeak_data=str(tmp_path / "espeak"),
    )

    save_piper_settings(settings)
    assert load_piper_settings() == settings

    apply_piper_settings(settings)
    assert os.environ["VIBEBOOK_PIPER_BIN"] == settings.binary
    assert os.environ["VIBEBOOK_PIPER_VOICES"] == settings.voices_dir
    assert os.environ["VIBEBOOK_PIPER_ESPEAK_DATA"] == settings.espeak_data

    apply_piper_settings(PiperSettings())
    assert "VIBEBOOK_PIPER_BIN" not in os.environ
    assert "VIBEBOOK_PIPER_VOICES" not in os.environ
    assert "VIBEBOOK_PIPER_ESPEAK_DATA" not in os.environ


def test_settings_load_ignores_corrupt_json(tmp_path, monkeypatch):
    config = tmp_path / "piper.json"
    config.write_text("{ not json", encoding="utf-8")
    monkeypatch.setenv("VIBEBOOK_PIPER_SETTINGS", str(config))

    assert load_piper_settings() == PiperSettings()


def test_validate_piper_settings(tmp_path):
    errors = validate_piper_settings(
        PiperSettings(
            binary=str(tmp_path / "missing-piper"),
            voices_dir=str(tmp_path / "missing-voices"),
            espeak_data=str(tmp_path / "missing-espeak"),
        )
    )
    assert any("binario" in error for error in errors)
    assert any("voces" in error for error in errors)
    assert any("espeak-ng-data" in error for error in errors)

    binary = _fake_binary(tmp_path)
    voices = tmp_path / "voices"
    voices.mkdir()
    espeak = tmp_path / "espeak"
    espeak.mkdir()
    assert (
        validate_piper_settings(
            PiperSettings(
                binary=str(binary),
                voices_dir=str(voices),
                espeak_data=str(espeak),
            )
        )
        == []
    )


def test_suggested_dirs_include_the_flutter_folder(tmp_path, monkeypatch):
    appdata = tmp_path / "Roaming"
    flutter = appdata / "com.vibebook" / "vibebook_app" / "models" / "piper"
    flutter.mkdir(parents=True)
    _fake_voice(flutter, "es_MX-ald-medium")
    monkeypatch.setenv("APPDATA", str(appdata))

    suggestions = suggested_voices_dirs(platform="windows")

    assert any(item["path"] == str(flutter) for item in suggestions)
