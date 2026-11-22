from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

from audiol.tts import kokoro_assets
from audiol.tts.kokoro_assets import (
    KokoroFile,
    KokoroNotConfigured,
    _download,
    ensure_kokoro_assets,
    kokoro_ready,
)


class FakeStream:
    def __init__(self, data: bytes) -> None:
        self.data = data

    def __enter__(self) -> FakeStream:
        return self

    def __exit__(self, *args) -> None:
        return None

    def raise_for_status(self) -> None:
        return None

    def iter_content(self, chunk_size: int):
        yield self.data


def _spec(name: str, data: bytes) -> KokoroFile:
    return KokoroFile(
        name=name,
        url=f"https://example.test/{name}",
        size=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
    )


def _install_tiny_assets(tmp_path: Path) -> tuple[KokoroFile, KokoroFile]:
    model = _spec("tiny-model.onnx", b"model-bytes")
    voices = _spec("tiny-voices.bin", b"voices-bytes")
    (tmp_path / model.name).write_bytes(b"model-bytes")
    (tmp_path / voices.name).write_bytes(b"voices-bytes")
    espeak = tmp_path / kokoro_assets.ESPEAK_DIR
    espeak.mkdir()
    (espeak / "phontab").write_text("data", encoding="ascii")
    return model, voices


def test_kokoro_download_verifies_size_and_hash(tmp_path: Path, monkeypatch):
    data = b"small asset"
    spec = _spec("asset.bin", data)
    monkeypatch.setattr(
        kokoro_assets.requests,
        "get",
        lambda *args, **kwargs: FakeStream(data),
    )
    target = tmp_path / "asset.bin"

    _download(spec, target)

    assert target.read_bytes() == data
    assert not list(tmp_path.glob("asset.bin.*.part"))


def test_kokoro_download_cleans_up_a_mismatched_file(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(
        kokoro_assets.requests,
        "get",
        lambda *args, **kwargs: FakeStream(b"tampered"),
    )
    spec = _spec("asset.bin", b"expected")
    target = tmp_path / "asset.bin"

    with pytest.raises(KokoroNotConfigured, match="does not match the manifest"):
        _download(spec, target)

    assert not target.exists()
    assert not list(tmp_path.glob("asset.bin.*.part"))


def test_kokoro_download_reports_network_errors(tmp_path: Path, monkeypatch):
    import requests

    def fail(*args, **kwargs):
        raise requests.RequestException("offline")

    monkeypatch.setattr(kokoro_assets.requests, "get", fail)

    with pytest.raises(KokoroNotConfigured, match="Could not download"):
        _download(_spec("asset.bin", b"data"), tmp_path / "asset.bin")


def test_kokoro_ready_checks_sizes_and_espeak_data(tmp_path: Path, monkeypatch):
    model, voices = _install_tiny_assets(tmp_path)
    monkeypatch.setattr(kokoro_assets, "KOKORO_MODEL", model)
    monkeypatch.setattr(kokoro_assets, "KOKORO_VOICES", voices)

    assert kokoro_ready(tmp_path) is True

    (tmp_path / model.name).write_bytes(b"short")
    assert kokoro_ready(tmp_path) is False

    (tmp_path / model.name).write_bytes(b"model-bytes")
    (tmp_path / kokoro_assets.ESPEAK_DIR / "phontab").unlink()
    assert kokoro_ready(tmp_path) is False


def test_ensure_kokoro_assets_skips_valid_files(tmp_path: Path, monkeypatch):
    model, voices = _install_tiny_assets(tmp_path)
    monkeypatch.setattr(kokoro_assets, "KOKORO_MODEL", model)
    monkeypatch.setattr(kokoro_assets, "KOKORO_VOICES", voices)
    monkeypatch.setattr(kokoro_assets, "KOKORO_FILES", (model, voices))
    monkeypatch.setattr(
        kokoro_assets,
        "_download",
        lambda spec, target: pytest.fail("should not download valid files"),
    )
    progress: list[str] = []

    result = ensure_kokoro_assets(tmp_path, on_progress=progress.append)

    assert result == tmp_path
    assert progress == [f"{model.name}: listo", f"{voices.name}: listo"]


def test_ensure_kokoro_assets_downloads_missing_files(tmp_path: Path, monkeypatch):
    model, voices = _install_tiny_assets(tmp_path)
    (tmp_path / voices.name).unlink()
    monkeypatch.setattr(kokoro_assets, "KOKORO_MODEL", model)
    monkeypatch.setattr(kokoro_assets, "KOKORO_VOICES", voices)
    monkeypatch.setattr(kokoro_assets, "KOKORO_FILES", (model, voices))
    downloaded: list[str] = []

    def fake_download(spec, target):
        downloaded.append(spec.name)
        target.write_bytes(b"voices-bytes")

    monkeypatch.setattr(kokoro_assets, "_download", fake_download)
    progress: list[str] = []

    ensure_kokoro_assets(tmp_path, on_progress=progress.append)

    assert downloaded == [voices.name]
    assert f"{voices.name}: descargando" in " ".join(progress)
    assert f"{voices.name}: verificado" in progress


@pytest.mark.skipif(os.name != "nt", reason="Windows path validation")
def test_kokoro_root_rejects_non_ascii_paths(tmp_path: Path, monkeypatch):
    configured = tmp_path / "voces-ñ"
    monkeypatch.setenv("VIBEBOOK_KOKORO_DIR", str(configured))

    with pytest.raises(KokoroNotConfigured, match="ASCII"):
        kokoro_assets.kokoro_root()


def test_kokoro_root_uses_configured_directory(tmp_path: Path, monkeypatch):
    configured = tmp_path / "kokoro"
    monkeypatch.setenv("VIBEBOOK_KOKORO_DIR", str(configured))
    # tmp_path itself contains the non-ASCII Windows profile name.
    monkeypatch.setattr(kokoro_assets, "_is_ascii", lambda path: True)

    assert kokoro_assets.kokoro_root() == configured
