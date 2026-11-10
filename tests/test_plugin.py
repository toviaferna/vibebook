import json
import socket

import pytest

from audiol.studio.plugins import PluginNotFound, PluginRegistry
from audiol.tts.plugin import (
    PluginError,
    PluginInfo,
    PluginProvider,
    fetch_plugin_info,
    fetch_plugin_voices,
    normalize_plugin_url,
)


@pytest.fixture(autouse=True)
def stub_public_dns(monkeypatch):
    original = socket.getaddrinfo

    def fake(host, port, *args, **kwargs):
        if host == "example.com":
            return [
                (
                    socket.AF_INET,
                    socket.SOCK_STREAM,
                    socket.IPPROTO_TCP,
                    "",
                    ("93.184.216.34", port or 443),
                )
            ]
        return original(host, port, *args, **kwargs)

    monkeypatch.setattr(socket, "getaddrinfo", fake)


def test_normalize_plugin_url():
    assert (
        normalize_plugin_url("http://127.0.0.1:9000/", allow_local=True) == "http://127.0.0.1:9000"
    )
    assert (
        normalize_plugin_url("http://localhost:9000/v1", allow_local=True)
        == "http://localhost:9000"
    )
    assert (
        normalize_plugin_url("https://example.com/engine/v1/info") == "https://example.com/engine"
    )


def test_normalize_plugin_url_rejects_local_without_dev_flag():
    with pytest.raises(PluginError, match="private or reserved"):
        normalize_plugin_url("http://127.0.0.1:9000")

    with pytest.raises(PluginError, match="private or reserved"):
        normalize_plugin_url("http://localhost:9000")


def test_normalize_plugin_url_rejects_private_https_hosts():
    for url in (
        "https://10.0.0.5",
        "https://192.168.1.10:8443",
        "https://169.254.169.254/latest/meta-data",
        "https://[::1]",
        "https://[fc00::1]",
    ):
        with pytest.raises(PluginError, match="private or reserved"):
            normalize_plugin_url(url)


def test_normalize_plugin_url_rejects_credentials_and_remote_http():
    with pytest.raises(PluginError, match="credentials"):
        normalize_plugin_url("https://user:pass@example.com")

    with pytest.raises(PluginError, match="HTTPS"):
        normalize_plugin_url("http://example.com", allow_local=True)


def test_normalize_plugin_url_rejects_unresolvable_hosts(monkeypatch):
    def fail(*args, **kwargs):
        raise socket.gaierror("no dns")

    monkeypatch.setattr(socket, "getaddrinfo", fail)

    with pytest.raises(PluginError, match="could not be resolved"):
        normalize_plugin_url("https://no-such-plugin.invalid")


def test_normalize_plugin_url_rejects_insecure_remote():
    with pytest.raises(PluginError, match="HTTPS"):
        normalize_plugin_url("http://example.com")

    with pytest.raises(PluginError, match="absolute"):
        normalize_plugin_url("not-a-url")


def test_invalid_manifest_is_rejected():
    with pytest.raises(ValueError):
        PluginInfo.model_validate(
            {
                "protocol": "vep/2",
                "id": "Bad ID",
                "name": "Bad",
                "voices": [],
            }
        )


def test_registry_rejects_reserved_id(make_plugin_server, tmp_path):
    plugin = make_plugin_server(plugin_id="piper")
    registry = PluginRegistry(tmp_path / "library", allow_local=True)

    with pytest.raises(PluginError, match="reserved"):
        registry.add(plugin.url)


def test_fetch_info_and_voices(plugin_server):
    info = fetch_plugin_info(plugin_server.url, allow_local=True)

    assert info.protocol == "vep/1"
    assert info.id == "fake-plugin"
    assert info.voices[0].id == "fake-es"
    assert [voice.id for voice in fetch_plugin_voices(plugin_server.url, allow_local=True)] == [
        "fake-es"
    ]


def test_registry_add_remove(plugin_server, tmp_path):
    registry = PluginRegistry(tmp_path / "library", allow_local=True)

    record = registry.add(plugin_server.url)

    assert record.info.id == "fake-plugin"
    assert registry.has("fake-plugin")
    assert registry.get("fake-plugin").url == plugin_server.url
    assert registry.records()[0].info.name == "Fake VEP"
    assert json.loads((tmp_path / "library" / "plugins.json").read_text())["items"]

    registry.remove("fake-plugin")

    assert not registry.has("fake-plugin")
    with pytest.raises(PluginNotFound):
        registry.get("fake-plugin")


def test_registry_persists_without_token_in_manifests(make_plugin_server, tmp_path):
    plugin = make_plugin_server(require_token="super-secret")
    registry = PluginRegistry(tmp_path / "library", allow_local=True)

    registry.add(plugin.url, token="super-secret")

    assert registry.has_token("fake-plugin")
    assert registry.token("fake-plugin") == "super-secret"
    assert "super-secret" not in (tmp_path / "library" / "plugins.json").read_text()
    assert "super-secret" in (tmp_path / "library" / "secrets.json").read_text()

    restored = PluginRegistry(tmp_path / "library", allow_local=True)
    assert restored.token("fake-plugin") == "super-secret"


def test_registry_requires_token(make_plugin_server, tmp_path):
    plugin = make_plugin_server(require_token="super-secret")
    registry = PluginRegistry(tmp_path / "library", allow_local=True)

    with pytest.raises(PluginError, match="Could not reach|HTTP 401"):
        registry.add(plugin.url)

    registry.add(plugin.url, token="super-secret")


def test_registry_does_not_overwrite_corrupt_manifests(tmp_path):
    directory = tmp_path / "library"
    directory.mkdir()
    path = directory / "plugins.json"
    path.write_text("{broken", encoding="utf-8")
    registry = PluginRegistry(directory, allow_local=True)

    with pytest.raises(PluginError, match="corrupt"):
        registry._save()

    assert path.read_text(encoding="utf-8") == "{broken"
    backups = list(directory.glob("plugins.json.corrupt-*"))
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == "{broken"


def test_registry_does_not_overwrite_corrupt_secrets(tmp_path):
    directory = tmp_path / "library"
    directory.mkdir()
    path = directory / "secrets.json"
    path.write_text("{broken", encoding="utf-8")
    registry = PluginRegistry(directory, allow_local=True)

    with pytest.raises(PluginError, match="corrupt"):
        registry._save()

    assert path.read_text(encoding="utf-8") == "{broken"
    assert list(directory.glob("secrets.json.corrupt-*"))


def test_provider_synthesizes_wav(plugin_server, tmp_path):
    provider = PluginProvider(plugin_server.url, timeout=5, allow_local=True)
    result = provider.synthesize("Hola mundo", "fake-es", tmp_path / "out.wav")

    assert result.path.read_bytes()[:4] == b"RIFF"
    assert result.words == []


def test_provider_reports_http_error(make_plugin_server, tmp_path):
    plugin = make_plugin_server(fail_synthesis=True)
    provider = PluginProvider(plugin.url, timeout=5, allow_local=True)

    with pytest.raises(RuntimeError, match="Synthesis exploded"):
        provider.synthesize("Hola", "fake-es", tmp_path / "out.wav")


def test_provider_rejects_invalid_audio(make_plugin_server, tmp_path):
    plugin = make_plugin_server(invalid_audio=True)
    provider = PluginProvider(plugin.url, timeout=5, allow_local=True)

    with pytest.raises(RuntimeError, match="invalid WAV"):
        provider.synthesize("Hola", "fake-es", tmp_path / "out.wav")


def test_provider_times_out(make_plugin_server, tmp_path):
    plugin = make_plugin_server(delay=2)
    provider = PluginProvider(plugin.url, timeout=0.2, allow_local=True)

    with pytest.raises(RuntimeError, match="Could not reach"):
        provider.synthesize("Hola", "fake-es", tmp_path / "out.wav")


def test_registry_make_provider(plugin_server, tmp_path):
    registry = PluginRegistry(tmp_path / "library", allow_local=True)
    registry.add(plugin_server.url)

    provider = registry.make_provider("fake-plugin")

    assert isinstance(provider, PluginProvider)
    assert provider.url == plugin_server.url


def test_registry_test_endpoint(plugin_server, tmp_path):
    registry = PluginRegistry(tmp_path / "library", allow_local=True)
    registry.add(plugin_server.url)

    result = registry.test("fake-plugin")

    assert result["ok"] is True
    assert result["voice_count"] == 1
    assert result["latency_ms"] >= 0


def test_plugin_provider_requires_text(plugin_server, tmp_path):
    provider = PluginProvider(plugin_server.url, timeout=5, allow_local=True)

    with pytest.raises(ValueError, match="empty text"):
        provider.synthesize(" ", "fake-es", tmp_path / "out.wav")


def test_plugin_registry_unknown_plugin(tmp_path):
    registry = PluginRegistry(tmp_path / "library", allow_local=True)

    with pytest.raises(PluginNotFound):
        registry.get("nope")
    with pytest.raises(PluginNotFound):
        registry.remove("nope")
    with pytest.raises(PluginNotFound):
        registry.make_provider("nope")
