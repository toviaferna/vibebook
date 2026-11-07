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


@requires_ffmpeg
def test_audio_range_returns_206(client, converted):
    response = client.get(
        f"/api/books/{converted['id']}/audio/1",
        headers={"Range": "bytes=0-99"},
    )

    assert response.status_code == 206
    assert len(response.content) <= 100
    assert response.headers["content-type"].startswith("audio/mpeg")


def test_missing_audio_returns_409(client, imported):
    assert client.get(f"/api/books/{imported['id']}/audio/1").status_code == 409
    assert client.get(f"/api/books/{imported['id']}/chapters/1").status_code == 409


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
