import pytest

from audiol.cli import build_parser, main


def test_cli_default_rate_is_minus_ten_percent():
    args = build_parser().parse_args(["convert", "libro.epub"])
    assert args.rate == "-10%"


def test_cli_version(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert "vibebook" in capsys.readouterr().out


def test_cli_voices(capsys):
    assert main(["voices", "--locale", "es-PY"]) == 0
    output = capsys.readouterr().out
    assert "es-PY-MarioNeural" in output
    assert "es-PY-TaniaNeural" in output
    assert "es-MX-JorgeNeural" not in output


def test_cli_engines(capsys):
    assert main(["engines"]) == 0
    output = capsys.readouterr().out
    assert "piper" in output
    assert "espeak" in output
    assert "edge" in output
    assert "segment" in output


def test_cli_voices_filtered_by_engine(capsys):
    assert main(["voices", "--engine", "piper"]) == 0
    output = capsys.readouterr().out
    assert "es_MX-ald-medium" in output
    assert "es-MX-JorgeNeural" not in output

    assert main(["voices", "--engine", "espeak"]) == 0
    output = capsys.readouterr().out
    assert "es-419" in output
    assert "es_MX-ald-medium" not in output


def test_cli_piper_download(monkeypatch, tmp_path, capsys):
    import audiol.cli as cli

    model = tmp_path / "es_MX-ald-medium.onnx"
    model.write_bytes(b"model")
    calls: dict[str, object] = {}

    def fake_download(voice, destination, force=False, on_progress=None):
        calls.update(voice=voice, destination=destination, force=force)
        if on_progress:
            on_progress("descargando")
        return model

    monkeypatch.setattr(cli, "download_piper_voice", fake_download)

    code = main(
        [
            "piper",
            "download",
            "--voice",
            "es_MX-ald-medium",
            "--dest",
            str(tmp_path / "voices"),
        ]
    )

    assert code == 0
    assert calls["voice"] == "es_MX-ald-medium"
    assert calls["destination"] == tmp_path / "voices"
    output = capsys.readouterr().out
    assert "Voz Piper" in output
    assert "descargando" in output


def test_cli_piper_status_without_install(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("VIBEBOOK_PIPER_BIN", str(tmp_path / "missing-piper"))
    monkeypatch.setenv("VIBEBOOK_PIPER_VOICES", str(tmp_path / "missing-voices"))

    assert main(["piper", "status"]) == 0
    output = capsys.readouterr().out
    assert "no encontrado" in output
    assert "no instalada" in output


def test_cli_convert_requires_a_local_engine_by_default(monkeypatch, tmp_path, tiny_epub):
    monkeypatch.setenv("VIBEBOOK_PIPER_BIN", str(tmp_path / "missing-piper"))
    monkeypatch.setenv("VIBEBOOK_PIPER_VOICES", str(tmp_path / "missing-voices"))
    monkeypatch.setenv("VIBEBOOK_ESPEAK_BIN", str(tmp_path / "missing-espeak"))

    with pytest.raises(SystemExit, match="No local TTS engine"):
        main(["convert", str(tiny_epub), "--dry-run"])


def test_cli_convert_allows_explicit_legacy_engine(monkeypatch, tmp_path, tiny_epub):
    monkeypatch.setenv("VIBEBOOK_PIPER_BIN", str(tmp_path / "missing-piper"))
    monkeypatch.setenv("VIBEBOOK_PIPER_VOICES", str(tmp_path / "missing-voices"))
    monkeypatch.setenv("VIBEBOOK_ESPEAK_BIN", str(tmp_path / "missing-espeak"))

    assert main(["convert", str(tiny_epub), "--engine", "edge", "--dry-run"]) == 0
