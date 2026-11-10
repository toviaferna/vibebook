import time

import pytest

from audiol.studio.jobs import JobManager, JobOptions
from audiol.tools import find_binary


def _use_real_factory(client):
    client.app.state.provider_factory = client.app.state.plugins.make_provider
    client.app.state.jobs.provider_factory = client.app.state.plugins.make_provider


def _add(client, url, token=None):
    payload = {"url": url}
    if token is not None:
        payload["token"] = token
    response = client.post("/api/engines/plugins", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_add_list_engines_and_voices(client, plugin_server):
    plugin = _add(client, plugin_server.url)

    assert plugin["id"] == "fake-plugin"
    assert plugin["voice_count"] == 1
    assert plugin["has_token"] is False
    assert plugin["enabled"] is True

    plugins = client.get("/api/engines/plugins").json()["items"]
    assert [item["id"] for item in plugins] == ["fake-plugin"]

    engines = client.get("/api/engines").json()["items"]
    engine = next(item for item in engines if item["id"] == "fake-plugin")
    assert engine["kind"] == "plugin"
    assert engine["transport"] == "http"
    assert engine["available"] is True
    assert engine["configured"] is True
    assert engine["plugin_url"] == plugin_server.url
    assert engine["license"] == "MIT"

    voices = client.get("/api/voices").json()
    assert any(voice["id"] == "fake-es" for voice in voices)
    assert [voice["id"] for voice in client.get("/api/voices?engine=fake-plugin").json()] == [
        "fake-es"
    ]

    assert client.delete("/api/engines/plugins/fake-plugin").status_code == 204
    assert client.get("/api/engines/plugins").json()["items"] == []
    assert all(voice["id"] != "fake-es" for voice in client.get("/api/voices").json())


def test_token_is_stored_but_never_returned(client, make_plugin_server):
    plugin = make_plugin_server(require_token="super-secret")
    response = client.post(
        "/api/engines/plugins",
        json={"url": plugin.url, "token": "super-secret"},
    )

    assert response.status_code == 201, response.text
    assert "super-secret" not in response.text
    assert response.json()["has_token"] is True
    assert "super-secret" not in client.get("/api/engines/plugins").text
    assert "super-secret" not in client.get("/api/engines").text
    library = client.app.state.settings.library_dir
    assert "super-secret" not in (library / "plugins.json").read_text()
    assert "super-secret" in (library / "secrets.json").read_text()


def test_plugin_test_endpoint(client, plugin_server):
    _add(client, plugin_server.url)

    response = client.post("/api/engines/fake-plugin/test")

    assert response.status_code == 200, response.text
    assert response.json()["ok"] is True
    assert response.json()["voice_count"] == 1


def _has_ffmpeg() -> bool:
    try:
        find_binary("ffmpeg")
        find_binary("ffprobe")
        return True
    except RuntimeError:
        return False


requires_ffmpeg = pytest.mark.skipif(
    not _has_ffmpeg(),
    reason="ffmpeg/ffprobe not available",
)


@requires_ffmpeg
def test_convert_with_plugin(client, imported, plugin_server):
    _add(client, plugin_server.url)
    _use_real_factory(client)

    response = client.post(
        f"/api/books/{imported['id']}/convert",
        json={
            "voice": "fake-es",
            "engine": "fake-plugin",
            "style": "neutral",
            "rate": "-10%",
            "force": False,
        },
    )

    assert response.status_code == 202, response.text
    job_id = response.json()["job_id"]
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] in {"completed", "failed", "cancelled"}:
            break
        time.sleep(0.05)
    assert job["status"] == "completed", job
    assert client.get(f"/api/books/{imported['id']}").json()["engine"] == "fake-plugin"


def test_plugin_preview(client, plugin_server):
    _add(client, plugin_server.url)
    _use_real_factory(client)

    response = client.post(
        "/api/voices/preview",
        json={"voice": "fake-es", "engine": "fake-plugin", "text": "Hola"},
    )

    assert response.status_code == 200, response.text
    audio = client.get(response.json()["url"])
    assert audio.status_code == 200
    assert audio.content[:4] == b"RIFF"


def test_plugin_job_validation(plugin_server, tmp_path):
    from audiol.studio.plugins import PluginRegistry

    registry = PluginRegistry(tmp_path / "library", allow_local=True)
    registry.add(plugin_server.url)
    manager = JobManager(
        object(),
        object(),
        lambda engine: registry.make_provider(engine),
        plugins=registry,
    )

    manager._validate_options(JobOptions(voice="fake-es", engine="fake-plugin"))

    with pytest.raises(ValueError, match="not a voice"):
        manager._validate_options(JobOptions(voice="nope", engine="fake-plugin"))


def test_settings_can_use_plugin_as_default(client, plugin_server):
    _add(client, plugin_server.url)

    response = client.put("/api/settings", json={"default_engine": "fake-plugin"})

    assert response.status_code == 200, response.text
    assert response.json()["default_engine"] == "fake-plugin"
    assert response.json()["default_voice"] == "fake-es"

    client.delete("/api/engines/plugins/fake-plugin")
    settings = client.get("/api/settings").json()
    assert settings["default_engine"] != "fake-plugin"


def test_plugin_disable_and_update(client, plugin_server):
    _add(client, plugin_server.url)

    response = client.put("/api/engines/fake-plugin/config", json={"enabled": False})

    assert response.status_code == 200
    assert response.json()["enabled"] is False
    engine = next(
        item for item in client.get("/api/engines").json()["items"] if item["id"] == "fake-plugin"
    )
    assert engine["available"] is False


def test_remove_unknown_plugin_returns_404(client):
    assert client.delete("/api/engines/plugins/nope").status_code == 404
    assert client.post("/api/engines/nope/test").status_code == 404
    assert client.put("/api/engines/nope/config", json={"enabled": True}).status_code == 404


def test_add_invalid_plugin_returns_422(client, make_plugin_server):
    reserved = make_plugin_server(plugin_id="piper")

    response = client.post("/api/engines/plugins", json={"url": reserved.url})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_plugin"

    bad_url = client.post("/api/engines/plugins", json={"url": "not-a-url"})
    assert bad_url.status_code == 422
