import threading
import time

import pytest

from audiol.tools import find_binary
from audiol.tts.fake import FakeProvider


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


class BlockingProvider(FakeProvider):
    def __init__(self, started: threading.Event, release: threading.Event) -> None:
        super().__init__()
        self.started = started
        self.release = release

    def synthesize(self, text, voice, out_path, style="neutral", rate="+0%"):
        self.started.set()
        if not self.release.wait(timeout=10):
            raise RuntimeError("release timeout")
        return super().synthesize(text, voice, out_path, style, rate)


def wait_for_job(client, job_id: str, statuses: set[str], timeout: float = 30.0) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        response = client.get(f"/api/jobs/{job_id}")
        assert response.status_code == 200
        job = response.json()
        if job["status"] in statuses:
            return job
        time.sleep(0.05)
    raise AssertionError(f"job {job_id} did not reach {statuses}")


def convert(client, book_id: str, **overrides) -> dict:
    payload = {
        "voice": "es-MX-JorgeNeural",
        "engine": "fake",
        "style": "neutral",
        "rate": "-10%",
        "force": False,
    }
    payload.update(overrides)
    response = client.post(f"/api/books/{book_id}/convert", json=payload)
    return response


@requires_ffmpeg
def test_start_job_and_get_it(client, imported):
    response = convert(client, imported["id"])
    assert response.status_code == 202, response.text
    job_id = response.json()["job_id"]

    job = wait_for_job(client, job_id, {"completed", "failed"})

    assert job["status"] == "completed"
    assert job["book_id"] == imported["id"]
    assert job["completed_segments"] == 2
    assert client.get(f"/api/books/{imported['id']}").json()["status"] == "ready"


@requires_ffmpeg
def test_sse_emits_job_event_and_closes(client, imported):
    response = convert(client, imported["id"])
    job_id = response.json()["job_id"]
    wait_for_job(client, job_id, {"completed", "failed"})

    stream = client.get(f"/api/jobs/{job_id}/events")

    assert stream.status_code == 200
    assert "event: job" in stream.text
    assert '"status": "completed"' in stream.text


@requires_ffmpeg
def test_second_convert_returns_409_while_active(client, imported):
    started = threading.Event()
    release = threading.Event()
    client.app.state.jobs.provider_factory = lambda engine: BlockingProvider(started, release)
    first = convert(client, imported["id"])
    assert first.status_code == 202
    assert started.wait(timeout=5)

    second = convert(client, imported["id"])
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "job_in_progress"

    release.set()
    wait_for_job(client, first.json()["job_id"], {"completed"})


@requires_ffmpeg
def test_cancel_job_and_resume(client, imported):
    started = threading.Event()
    release = threading.Event()
    client.app.state.jobs.provider_factory = lambda engine: BlockingProvider(started, release)
    job_id = convert(client, imported["id"]).json()["job_id"]
    assert started.wait(timeout=5)

    cancelled = client.post(f"/api/jobs/{job_id}/cancel")
    assert cancelled.status_code == 202
    release.set()
    job = wait_for_job(client, job_id, {"cancelled"})
    assert job["status"] == "cancelled"

    client.app.state.jobs.provider_factory = lambda engine: FakeProvider()
    resumed = client.post(f"/api/jobs/{job_id}/resume")
    assert resumed.status_code == 202, resumed.text
    new_job = wait_for_job(client, resumed.json()["job_id"], {"completed"})
    assert new_job["status"] == "completed"


def test_invalid_voice_returns_422(client, imported):
    response = convert(client, imported["id"], voice="nope")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_options"


def test_invalid_style_returns_422(client, imported):
    response = convert(client, imported["id"], style="cheerful")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_options"


def test_unknown_job_returns_404(client):
    assert client.get("/api/jobs/nope").status_code == 404
    assert client.get("/api/jobs/nope/events").status_code == 404
    assert client.post("/api/jobs/nope/cancel").status_code == 404


def test_convert_unknown_book_returns_404(client):
    assert convert(client, "nope").status_code == 404
