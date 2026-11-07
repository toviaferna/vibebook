from pathlib import Path

from fastapi.testclient import TestClient

from audiol.cli import build_parser, main
from audiol.studio.app import create_app
from audiol.studio.server import find_free_port, run_studio
from audiol.studio.settings import Settings


def test_studio_parser_accepts_options():
    args = build_parser().parse_args(
        [
            "studio",
            "--library",
            "out",
            "--port",
            "0",
            "--no-browser",
            "--allow-fake",
            "--token",
            "secret",
            "--dev",
        ]
    )

    assert args.command == "studio"
    assert args.library == "out"
    assert args.port == 0
    assert args.no_browser is True
    assert args.allow_fake is True
    assert args.token == "secret"
    assert args.dev is True


def test_studio_command_builds_settings_and_skips_browser(tmp_path: Path, monkeypatch):
    captured = {}

    def fake_run(settings, open_browser=True):
        captured["settings"] = settings
        captured["open_browser"] = open_browser

    monkeypatch.setattr("audiol.cli.run_studio", fake_run)

    code = main(
        [
            "studio",
            "--library",
            str(tmp_path / "library"),
            "--no-browser",
            "--allow-fake",
        ]
    )

    assert code == 0
    assert captured["open_browser"] is False
    assert captured["settings"].library_dir == tmp_path / "library"
    assert captured["settings"].allow_fake is True


def test_find_free_port_returns_usable_port():
    port = find_free_port()

    assert 0 < port < 65536


def test_run_studio_port_zero_and_browser(tmp_path: Path, monkeypatch):
    captured = {}
    opened = []

    def fake_run(app, host, port, log_level):
        captured["host"] = host
        captured["port"] = port
        captured["log_level"] = log_level

    monkeypatch.setattr("audiol.studio.server.uvicorn.run", fake_run)
    monkeypatch.setattr("audiol.studio.server.webbrowser.open", opened.append)

    settings = Settings(library_dir=tmp_path / "library", port=0)
    run_studio(settings, open_browser=True)

    assert captured["host"] == "127.0.0.1"
    assert captured["port"] > 0
    assert opened
    assert opened[0].startswith("http://127.0.0.1:")


def test_placeholder_page_links_docs(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "/docs" in response.text
    assert "/api/health" in response.text


def test_static_spa_when_web_dist_exists(tmp_path: Path):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html>vibebook spa</html>", encoding="utf-8")
    (dist / "asset.txt").write_text("asset", encoding="utf-8")
    settings = Settings(
        library_dir=tmp_path / "library",
        token=None,
        web_dist=dist,
    )
    app = create_app(settings)
    with TestClient(app, base_url="http://127.0.0.1") as client:
        assert "vibebook spa" in client.get("/").text
        assert client.get("/asset.txt").text == "asset"
        assert client.get("/api/nope").status_code == 404
