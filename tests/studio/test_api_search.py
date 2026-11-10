import time

import pytest

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
def test_search_is_case_and_accent_insensitive(client, converted):
    response = client.get(
        f"/api/books/{converted['id']}/search",
        params={"q": "lazaro"},
    )

    assert response.status_code == 200
    items = response.json()["items"]
    assert items
    first = items[0]
    assert first["chapter_index"] == 1
    assert first["segment_id"]
    assert "Lázaro" in first["excerpt"]
    assert first["position_ms"] >= 0
    assert first["char_offset"] >= 0


@requires_ffmpeg
def test_search_returns_empty_for_unknown_text(client, converted):
    response = client.get(
        f"/api/books/{converted['id']}/search",
        params={"q": "zzzz"},
    )

    assert response.status_code == 200
    assert response.json()["items"] == []


@requires_ffmpeg
def test_search_rejects_too_short_query(client, converted):
    response = client.get(
        f"/api/books/{converted['id']}/search",
        params={"q": "a"},
    )

    assert response.status_code == 422


@requires_ffmpeg
def test_bookmark_lifecycle(client, converted):
    created = client.post(
        f"/api/books/{converted['id']}/bookmarks",
        json={"chapter_index": 1, "position_ms": 500, "note": "  mi nota  "},
    )

    assert created.status_code == 201
    bookmark = created.json()
    assert bookmark["note"] == "mi nota"
    assert bookmark["position_ms"] == 500

    listed = client.get(f"/api/books/{converted['id']}/bookmarks")
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()["items"]] == [bookmark["id"]]

    deleted = client.delete(f"/api/books/{converted['id']}/bookmarks/{bookmark['id']}")
    assert deleted.status_code == 204
    assert client.get(f"/api/books/{converted['id']}/bookmarks").json()["items"] == []
    assert (
        client.delete(f"/api/books/{converted['id']}/bookmarks/{bookmark['id']}").status_code == 404
    )


@requires_ffmpeg
def test_bookmark_accepts_missing_note(client, converted):
    created = client.post(
        f"/api/books/{converted['id']}/bookmarks",
        json={"chapter_index": 1, "position_ms": 0},
    )

    assert created.status_code == 201
    assert created.json()["note"] is None


@requires_ffmpeg
def test_bookmark_rejects_unknown_chapter(client, converted):
    response = client.post(
        f"/api/books/{converted['id']}/bookmarks",
        json={"chapter_index": 99, "position_ms": 0},
    )

    assert response.status_code == 404


@requires_ffmpeg
def test_bookmark_rejects_position_past_duration(client, converted):
    response = client.post(
        f"/api/books/{converted['id']}/bookmarks",
        json={"chapter_index": 1, "position_ms": 10_000_000},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_bookmark"
