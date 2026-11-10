import io
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from audiol.studio.app import create_app
from audiol.studio.settings import Settings
from audiol.tts.fake import FakeProvider


def test_health(client):
    response = client.get("/api/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert "version" in payload
    assert isinstance(payload["ffmpeg"], bool)
    assert "library_dir" in payload


def test_import_and_list_books(client, imported):
    assert imported["status"] == "imported"
    assert imported["chapter_count"] == 2
    assert imported["cover_url"] is None

    response = client.get("/api/books")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["id"] == imported["id"]


def test_book_exposes_reading_progress(client, imported):
    initial = client.get(f"/api/books/{imported['id']}").json()
    assert initial["reading_progress"] == 0
    assert initial["last_read_chapter_index"] is None

    client.put(
        f"/api/books/{imported['id']}/reading-state",
        json={
            "chapter_index": 1,
            "char_offset": 5,
            "page_index": 1,
            "page_count": 4,
            "percent": 0.42,
        },
    )

    detail = client.get(f"/api/books/{imported['id']}").json()
    listed = client.get("/api/books").json()["items"][0]

    assert detail["reading_progress"] == 0.42
    assert detail["last_read_chapter_index"] == 1
    assert listed["reading_progress"] == 0.42
    assert listed["last_read_chapter_index"] == 1


def test_import_requires_token(unauth_client, tiny_epub: Path):
    response = unauth_client.get("/api/books")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_token"


def test_import_rejects_non_epub(client):
    response = client.post(
        "/api/books/import",
        files={"file": ("book.txt", b"not an epub", "text/plain")},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_epub"


def test_import_rejects_oversize(tmp_path: Path, tiny_epub: Path):
    settings = Settings(
        library_dir=tmp_path / "library",
        token="test-token",
        allow_fake=True,
        max_upload_bytes=10,
    )
    app = create_app(settings, provider_factory=lambda engine: FakeProvider())
    with TestClient(app, base_url="http://127.0.0.1") as client:
        client.headers.update({"X-Vibebook-Token": "test-token"})
        response = client.post(
            "/api/books/import",
            files={
                "file": (
                    "tiny.epub",
                    tiny_epub.read_bytes(),
                    "application/epub+zip",
                )
            },
        )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "file_too_large"


def test_import_rejects_zip_bomb(tmp_path: Path):
    settings = Settings(
        library_dir=tmp_path / "library",
        token="test-token",
        allow_fake=True,
        max_archive_entries=10,
        max_uncompressed_bytes=100,
    )
    app = create_app(settings, provider_factory=lambda engine: FakeProvider())
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("META-INF/container.xml", b"<container/>")
        archive.writestr("big.bin", b"0" * 1000)
    with TestClient(app, base_url="http://127.0.0.1") as client:
        client.headers.update({"X-Vibebook-Token": "test-token"})
        response = client.post(
            "/api/books/import",
            files={"file": ("bomb.epub", buffer.getvalue(), "application/epub+zip")},
        )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_epub"


def test_get_book_and_cover(client, cover_epub: Path):
    response = client.post(
        "/api/books/import",
        files={
            "file": (
                "cover.epub",
                cover_epub.read_bytes(),
                "application/epub+zip",
            )
        },
    )
    assert response.status_code == 201, response.text
    book = response.json()
    assert book["cover_url"] == f"/api/books/{book['id']}/cover"

    detail = client.get(f"/api/books/{book['id']}")
    assert detail.status_code == 200
    assert detail.json()["state"]["position_ms"] == 0

    cover = client.get(book["cover_url"])
    assert cover.status_code == 200
    assert cover.headers["content-type"].startswith("image/")


def test_delete_blocked_by_book_activity(client, imported):
    lease = client.app.state.activity.reserve(imported["id"], "convert")

    response = client.delete(f"/api/books/{imported['id']}")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "book_busy"
    client.app.state.activity.release(lease)


def test_delete_book(client, imported):
    response = client.delete(f"/api/books/{imported['id']}")

    assert response.status_code == 204
    assert client.get(f"/api/books/{imported['id']}").status_code == 404
    assert client.get("/api/books").json()["total"] == 0


def test_rescan_picks_up_external_book(client, tmp_path: Path, tiny_epub: Path):
    record = client.app.state.library.import_epub(tiny_epub)

    response = client.post("/api/books/rescan")

    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert client.get(f"/api/books/{record.id}").status_code == 200


def test_non_ascii_token_is_rejected(tmp_path: Path):
    with pytest.raises(ValueError):
        Settings(
            library_dir=tmp_path / "library",
            token="contraseña",
            allow_fake=True,
        )


def test_cors_preflight_is_not_blocked_by_token(tmp_path: Path):
    settings = Settings(
        library_dir=tmp_path / "library",
        token="smoke",
        allow_fake=True,
        dev=True,
    )
    app = create_app(settings, provider_factory=lambda engine: FakeProvider())
    with TestClient(app, base_url="http://127.0.0.1") as client:
        response = client.options(
            "/api/books",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_token_can_be_passed_in_query_for_media(unauth_client):
    assert unauth_client.get("/api/books").status_code == 401

    response = unauth_client.get("/api/books?token=test-token")

    assert response.status_code == 200


def test_tauri_origin_is_allowed_without_dev(tmp_path: Path):
    settings = Settings(
        library_dir=tmp_path / "library",
        token="smoke",
        allow_fake=True,
    )
    app = create_app(settings, provider_factory=lambda engine: FakeProvider())
    with TestClient(app, base_url="http://127.0.0.1") as client:
        response = client.options(
            "/api/books",
            headers={
                "Origin": "http://tauri.localhost",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://tauri.localhost"


def test_error_shape_for_unknown_book(client):
    response = client.get("/api/books/nope")

    assert response.status_code == 404
    error = response.json()["error"]
    assert error["code"] == "book_not_found"
    assert "message" in error


def test_untrusted_host_is_rejected(app):
    with TestClient(app, base_url="http://evil.example") as client:
        client.headers.update({"X-Vibebook-Token": "test-token"})
        response = client.get("/api/health")

    assert response.status_code == 400
