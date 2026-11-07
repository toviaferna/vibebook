from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from audiol.studio.app import create_app
from audiol.studio.settings import Settings
from audiol.tts.fake import FakeProvider


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        library_dir=tmp_path / "library",
        token="test-token",
        allow_fake=True,
        max_upload_bytes=2 * 1024 * 1024,
        max_archive_entries=100,
        max_uncompressed_bytes=4 * 1024 * 1024,
    )


@pytest.fixture
def app(settings: Settings):
    return create_app(settings, provider_factory=lambda engine: FakeProvider())


@pytest.fixture
def client(app):
    with TestClient(app, base_url="http://127.0.0.1") as test_client:
        test_client.headers.update({"X-Vibebook-Token": "test-token"})
        yield test_client


@pytest.fixture
def unauth_client(app):
    with TestClient(app, base_url="http://127.0.0.1") as test_client:
        yield test_client


@pytest.fixture
def imported(client, tiny_epub: Path):
    response = client.post(
        "/api/books/import",
        files={"file": ("tiny.epub", tiny_epub.read_bytes(), "application/epub+zip")},
    )
    assert response.status_code == 201, response.text
    return response.json()
