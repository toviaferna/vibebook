import json
import threading
import time
from pathlib import Path

import pytest

from audiol.manifest import SEGMENTATION_VERSION
from audiol.studio.db import Database
from audiol.studio.jobs import (
    JobInProgress,
    JobManager,
    JobNotFound,
    JobOptions,
)
from audiol.studio.library import Library
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

OPTIONS = JobOptions(
    voice="es-MX-JorgeNeural",
    engine="fake",
    rate="-10%",
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


class FailingProvider(FakeProvider):
    def synthesize(self, text, voice, out_path, style="neutral", rate="+0%"):
        raise ValueError("provider exploded")


@pytest.fixture
def library(tmp_path: Path) -> Library:
    return Library(tmp_path / "library")


@pytest.fixture
def db(tmp_path: Path) -> Database:
    database = Database(tmp_path / "library" / ".vibebook.db")
    database.migrate()
    return database


@pytest.fixture
def book(library: Library, db: Database, tiny_epub: Path):
    record = library.import_epub(tiny_epub)
    db.upsert_book(record)
    return record


def wait_for_status(
    manager: JobManager, job_id: str, statuses: set[str], timeout: float = 30.0
) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        job = manager.get(job_id)
        if job["status"] in statuses:
            return job
        time.sleep(0.05)
    raise AssertionError(f"job {job_id} did not reach {statuses}: {manager.get(job_id)}")


@requires_ffmpeg
def test_start_refreshes_old_imports_before_converting(book, db: Database, library: Library):
    manifest_path = book.path / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.pop("segmentation_version", None)
    manifest["chapters"][0]["segments"][0]["text"] = "Viejo texto roto"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    manager = JobManager(
        db,
        library,
        provider_factory=lambda engine: FakeProvider(),
        allow_fake=True,
    )

    job_id = manager.start(book.id, OPTIONS)
    job = wait_for_status(manager, job_id, {"completed", "failed", "cancelled"})

    assert job["status"] == "completed"
    refreshed = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert refreshed["segmentation_version"] == SEGMENTATION_VERSION
    assert refreshed["chapters"][0]["segments"][0]["text"] != "Viejo texto roto"


@requires_ffmpeg
def test_start_runs_conversion_and_updates_db(book, db: Database, library: Library):
    manager = JobManager(
        db,
        library,
        provider_factory=lambda engine: FakeProvider(),
        allow_fake=True,
    )

    job_id = manager.start(book.id, OPTIONS)
    job = wait_for_status(manager, job_id, {"completed", "failed", "cancelled"})

    assert job["status"] == "completed"
    assert job["completed_segments"] == 2
    assert job["total_segments"] == 2
    assert job["started_at"]
    assert job["finished_at"]
    assert db.get_book(book.id)["status"] == "ready"
    assert (book.path / "manifest.json").exists()
    deadline = time.monotonic() + 5
    while manager.active_job_id() is not None and time.monotonic() < deadline:
        time.sleep(0.01)
    assert manager.active_job_id() is None


@requires_ffmpeg
def test_second_job_is_rejected_while_first_is_active(book, db: Database, library: Library):
    started = threading.Event()
    release = threading.Event()
    manager = JobManager(
        db,
        library,
        provider_factory=lambda engine: BlockingProvider(started, release),
        allow_fake=True,
    )

    job_id = manager.start(book.id, OPTIONS)
    assert started.wait(timeout=5)

    with pytest.raises(JobInProgress):
        manager.start(book.id, OPTIONS)

    release.set()
    assert wait_for_status(manager, job_id, {"completed"})["status"] == "completed"


@requires_ffmpeg
def test_cancel_marks_job_and_book(book, db: Database, library: Library):
    started = threading.Event()
    release = threading.Event()
    manager = JobManager(
        db,
        library,
        provider_factory=lambda engine: BlockingProvider(started, release),
        allow_fake=True,
    )
    job_id = manager.start(book.id, OPTIONS)
    assert started.wait(timeout=5)

    manager.cancel(job_id)
    release.set()
    job = wait_for_status(manager, job_id, {"cancelled"})

    assert job["status"] == "cancelled"
    assert db.get_book(book.id)["status"] == "interrupted"


@requires_ffmpeg
def test_worker_error_marks_failed(book, db: Database, library: Library):
    manager = JobManager(
        db,
        library,
        provider_factory=lambda engine: FailingProvider(),
        allow_fake=True,
    )
    job_id = manager.start(book.id, OPTIONS)
    job = wait_for_status(manager, job_id, {"failed"})

    assert "provider exploded" in job["error"]
    assert db.get_book(book.id)["status"] == "error"


def test_start_rejects_unknown_voice(book, db: Database, library: Library):
    manager = JobManager(
        db,
        library,
        provider_factory=lambda engine: FakeProvider(),
        allow_fake=True,
    )

    with pytest.raises(ValueError):
        manager.start(book.id, JobOptions(voice="nope", engine="fake"))


def test_start_rejects_fake_when_not_allowed(book, db: Database, library: Library):
    manager = JobManager(
        db,
        library,
        provider_factory=lambda engine: FakeProvider(),
        allow_fake=False,
    )

    with pytest.raises(ValueError):
        manager.start(book.id, OPTIONS)


def test_get_unknown_job_raises(db: Database, library: Library):
    manager = JobManager(db, library, provider_factory=lambda engine: FakeProvider())

    with pytest.raises(JobNotFound):
        manager.get("job_nope")


def test_mark_interrupted(book, db: Database, library: Library):
    db.set_book_status(book.id, "converting")
    db.create_job(
        {
            "id": "job_1",
            "book_id": book.id,
            "status": "running",
            "stage": "synthesizing",
            "options_json": "{}",
        }
    )
    manager = JobManager(db, library, provider_factory=lambda engine: FakeProvider())

    manager.mark_interrupted()

    assert db.get_job("job_1")["status"] == "interrupted"
    assert db.get_book(book.id)["status"] == "interrupted"
