import json
import time

import pytest

from audiol.studio.api.reader import _MANIFEST_CACHE, _load_manifest_cached
from audiol.tools import find_binary


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


def wait_for_job(client, job_id: str, timeout: float = 30.0) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] in {"completed", "failed", "cancelled"}:
            return job
        time.sleep(0.05)
    raise AssertionError(f"job {job_id} did not finish")


def test_partial_book_preferences_update(client, imported):
    book_id = imported["id"]
    first = client.put(
        f"/api/books/{book_id}/preferences",
        json={"reader_palette": "sepia"},
    )
    assert first.status_code == 200

    second = client.put(
        f"/api/books/{book_id}/preferences",
        json={"reader_size": 22},
    )

    assert second.status_code == 200
    data = second.json()
    assert data["reader_palette"] == "sepia"
    assert data["reader_size"] == 22


def test_m4b_endpoint_uses_manifest_file(client, imported):
    book_dir = client.app.state.library.get(imported["id"]).path
    (book_dir / "old.m4b").write_bytes(b"old")
    (book_dir / "new.m4b").write_bytes(b"new")
    path = book_dir / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["m4b"] = "new.m4b"
    path.write_text(json.dumps(manifest), encoding="utf-8")

    response = client.get(f"/api/books/{imported['id']}/m4b")

    assert response.status_code == 200
    assert response.content == b"new"


def test_manifest_cache_reuses_until_the_file_changes(client, imported):
    _MANIFEST_CACHE.clear()
    path = client.app.state.library.get(imported["id"]).path / "manifest.json"

    first = _load_manifest_cached(path)
    second = _load_manifest_cached(path)

    assert first is second
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["title"] = "Un título mucho más largo"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    third = _load_manifest_cached(path)
    assert third["title"] == "Un título mucho más largo"
    assert third is not first


@pytest.fixture
def converted(client, imported):
    response = client.post(
        f"/api/books/{imported['id']}/convert",
        json={
            "voice": "es-MX-JorgeNeural",
            "engine": "fake",
            "style": "neutral",
            "rate": "-10%",
            "force": False,
        },
    )
    assert response.status_code == 202, response.text
    job = wait_for_job(client, response.json()["job_id"])
    assert job["status"] == "completed", job
    return imported


@requires_ffmpeg
def test_manifest_returns_chapters(client, converted):
    response = client.get(f"/api/books/{converted['id']}/manifest")

    assert response.status_code == 200
    payload = response.json()
    assert payload["schema_version"] == 2
    assert len(payload["chapters"]) == 2


@requires_ffmpeg
def test_chapter_returns_text_and_timing(client, converted):
    response = client.get(f"/api/books/{converted['id']}/chapters/1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["chapter"]["index"] == 1
    assert payload["chapter"]["segments"][0]["text"].startswith("Pues sepa")
    assert payload["timing"]["chapter_index"] == 1
    assert payload["timing"]["segments"][0]["words"]
    assert payload["timing"]["precision"] == "exact"
    assert payload["audio_ready"] is True
    assert payload["duration_ms"] > 0


@requires_ffmpeg
def test_audio_range_returns_206(client, converted):
    response = client.get(
        f"/api/books/{converted['id']}/audio/1",
        headers={"Range": "bytes=0-99"},
    )

    assert response.status_code == 206
    assert len(response.content) <= 100
    assert response.headers["content-type"].startswith("audio/mpeg")


def test_missing_audio_still_allows_reading(client, imported):
    assert client.get(f"/api/books/{imported['id']}/audio/1").status_code == 409

    response = client.get(f"/api/books/{imported['id']}/chapters/1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["timing"] is None
    assert payload["audio_ready"] is False
    assert payload["chapter"]["segments"][0]["text"].startswith("Pues sepa")


def test_reading_state_defaults_and_roundtrip(client, imported):
    initial = client.get(f"/api/books/{imported['id']}/reading-state")

    assert initial.status_code == 200
    assert initial.json()["chapter_index"] == 1
    assert initial.json()["char_offset"] == 0
    assert initial.json()["percent"] == 0

    updated = client.put(
        f"/api/books/{imported['id']}/reading-state",
        json={
            "chapter_index": 1,
            "char_offset": 12,
            "page_index": 2,
            "page_count": 8,
            "percent": 0.25,
            "cfi": None,
        },
    )

    assert updated.status_code == 200
    assert updated.json()["char_offset"] == 12
    assert updated.json()["page_index"] == 2

    fetched = client.get(f"/api/books/{imported['id']}/reading-state")
    assert fetched.json()["char_offset"] == 12
    assert fetched.json()["percent"] == 0.25


def test_reading_state_rejects_unknown_chapter_and_offset(client, imported):
    chapter = client.get(f"/api/books/{imported['id']}/chapters/1").json()["chapter"]
    text_length = sum(len(segment["text"]) for segment in chapter["segments"])

    unknown = client.put(
        f"/api/books/{imported['id']}/reading-state",
        json={"chapter_index": 99, "char_offset": 0, "percent": 0},
    )
    too_far = client.put(
        f"/api/books/{imported['id']}/reading-state",
        json={"chapter_index": 1, "char_offset": text_length + 1, "percent": 0},
    )

    assert unknown.status_code == 404
    assert too_far.status_code == 422


def test_reading_bookmarks_crud(client, imported):
    created = client.post(
        f"/api/books/{imported['id']}/reading-bookmarks",
        json={"chapter_index": 1, "char_offset": 5, "page_index": 1, "note": "Volver"},
    )

    assert created.status_code == 201
    bookmark = created.json()
    assert bookmark["note"] == "Volver"

    listed = client.get(f"/api/books/{imported['id']}/reading-bookmarks")
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()["items"]] == [bookmark["id"]]

    deleted = client.delete(f"/api/books/{imported['id']}/reading-bookmarks/{bookmark['id']}")
    assert deleted.status_code == 204
    assert client.get(f"/api/books/{imported['id']}/reading-bookmarks").json()["items"] == []


def test_book_preferences_defaults_and_roundtrip(client, imported):
    initial = client.get(f"/api/books/{imported['id']}/preferences")

    assert initial.status_code == 200
    assert initial.json()["reader_mode"] is None

    updated = client.put(
        f"/api/books/{imported['id']}/preferences",
        json={
            "reader_mode": "book",
            "reader_palette": "sepia",
            "reader_font": "hyperlegible",
            "reader_size": 21,
            "page_turn": True,
            "ambience_enabled": False,
        },
    )

    assert updated.status_code == 200
    assert updated.json()["reader_mode"] == "book"
    assert updated.json()["reader_palette"] == "sepia"
    assert updated.json()["page_turn"] is True

    fetched = client.get(f"/api/books/{imported['id']}/preferences")
    assert fetched.json()["reader_font"] == "hyperlegible"
    assert fetched.json()["reader_size"] == 21


def test_original_epub_download(client, imported):
    response = client.get(f"/api/books/{imported['id']}/epub")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/epub+zip")
    assert response.content.startswith(b"PK")


def test_original_epub_missing_returns_404(client, imported):
    path = client.app.state.library.root / imported["id"] / "source.epub"
    path.unlink()

    response = client.get(f"/api/books/{imported['id']}/epub")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "epub_not_found"


def test_audio_key_with_missing_file_returns_404(client, imported):
    import json

    path = client.app.state.library.root / imported["id"] / "manifest.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["chapters"][0]["audio"] = "audio/chapters/missing.mp3"
    path.write_text(json.dumps(data), encoding="utf-8")

    assert client.get(f"/api/books/{imported['id']}/audio/1").status_code == 404


@requires_ffmpeg
def test_state_defaults_and_roundtrip(client, converted):
    initial = client.get(f"/api/books/{converted['id']}/state")
    assert initial.status_code == 200
    assert initial.json()["position_ms"] == 0
    assert initial.json()["chapter_index"] == 1

    updated = client.put(
        f"/api/books/{converted['id']}/state",
        json={"position_ms": 1200, "chapter_index": 1, "playback_rate": 1.25},
    )
    assert updated.status_code == 200
    assert updated.json()["position_ms"] == 1200
    assert updated.json()["playback_rate"] == 1.25

    fetched = client.get(f"/api/books/{converted['id']}/state")
    assert fetched.json()["position_ms"] == 1200


@requires_ffmpeg
def test_state_rejects_unknown_chapter(client, converted):
    response = client.put(
        f"/api/books/{converted['id']}/state",
        json={"position_ms": 0, "chapter_index": 99, "playback_rate": 1.0},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_state"


@requires_ffmpeg
def test_m4b_download(client, converted):
    response = client.get(f"/api/books/{converted['id']}/m4b")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("audio/")


def test_unknown_book_returns_404(client):
    assert client.get("/api/books/nope/manifest").status_code == 404
    assert client.get("/api/books/nope/chapters/1").status_code == 404
    assert client.get("/api/books/nope/state").status_code == 404


def test_imported_book_exposes_and_serves_images(client, image_epub):
    response = client.post(
        "/api/books/import",
        files={
            "file": (
                "illustrated.epub",
                image_epub.read_bytes(),
                "application/epub+zip",
            )
        },
    )
    assert response.status_code == 201, response.text
    book = response.json()

    manifest = client.get(f"/api/books/{book['id']}/manifest").json()
    assert len(manifest["images"]) == 1
    image = manifest["images"][0]
    assert image["alt"] == "Una casa verde"
    assert image["caption"] == "La casa del bosque"
    assert image["chapter_index"] == 1
    assert image["paragraph_index"] == 1

    served = client.get(f"/api/books/{book['id']}/images/{image['id']}")
    assert served.status_code == 200
    assert served.headers["content-type"].startswith("image/")
    assert served.content

    path = client.app.state.library.root / book["id"] / image["path"]
    path.unlink()
    missing = client.get(f"/api/books/{book['id']}/images/{image['id']}")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "image_not_found"
