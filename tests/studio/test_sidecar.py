import json
from pathlib import Path

from audiol.studio import sidecar
from audiol.tools import find_binary


def test_sidecar_prints_ready_json(tmp_path: Path, monkeypatch, capsys):
    captured = {}

    def fake_run(app, **kwargs):
        captured["app"] = app
        captured["kwargs"] = kwargs

    monkeypatch.setattr(sidecar.uvicorn, "run", fake_run)

    code = sidecar.main(
        [
            "serve",
            "--json-ready",
            "--port",
            "0",
            "--token",
            "test-token",
            "--library",
            str(tmp_path / "library"),
        ]
    )

    assert code == 0
    lines = capsys.readouterr().out.strip().splitlines()
    assert len(lines) == 1
    ready = json.loads(lines[0])
    assert ready["event"] == "ready"
    assert ready["token"] == "test-token"
    assert 0 < ready["port"] < 65536
    assert captured["kwargs"]["host"] == "127.0.0.1"
    assert captured["kwargs"]["access_log"] is False
    assert captured["kwargs"]["log_config"] is None


def test_sidecar_generates_token_when_missing(tmp_path: Path, monkeypatch, capsys):
    monkeypatch.setattr(sidecar.uvicorn, "run", lambda *args, **kwargs: None)

    code = sidecar.main(
        [
            "serve",
            "--json-ready",
            "--library",
            str(tmp_path / "library"),
        ]
    )

    assert code == 0
    ready = json.loads(capsys.readouterr().out.strip())
    assert len(ready["token"]) == 64
    assert int(ready["token"], 16) >= 0


def test_find_binary_prefers_ffmpeg_dir(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("FFMPEG_BINARY", raising=False)
    monkeypatch.delenv("FFPROBE_BINARY", raising=False)
    monkeypatch.setenv("VIBEBOOK_FFMPEG_DIR", str(tmp_path))
    for name in ("ffmpeg", "ffmpeg.exe"):
        (tmp_path / name).write_text("binary", encoding="utf-8")

    found = Path(find_binary("ffmpeg"))

    assert found.parent == tmp_path
    assert found.name.startswith("ffmpeg")


def test_find_web_dist_prefers_environment(tmp_path: Path, monkeypatch):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html></html>", encoding="utf-8")
    monkeypatch.setenv("VIBEBOOK_WEB_DIST", str(dist))

    assert sidecar.find_web_dist() == dist


def test_pyinstaller_spec_lists_assets():
    spec = (
        Path(__file__).resolve().parents[2] / "packaging" / "pyinstaller" / "vibebook-sidecar.spec"
    )
    content = spec.read_text(encoding="utf-8")

    assert "web/dist" in content
    assert "ffmpeg" in content
    assert "ffprobe" in content
    assert "vibebook-sidecar" in content
