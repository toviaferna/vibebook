import json
import logging
import sqlite3
import threading
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from uuid import uuid4

from audiol.convert import ConversionCancelled, convert
from audiol.manifest import book_from_manifest, load_manifest
from audiol.studio.db import Database
from audiol.studio.library import BookRecord, Library
from audiol.tts.base import TTSProvider, validate_rate
from audiol.voices import get_voice

logger = logging.getLogger(__name__)

TERMINAL_JOB_STATUSES = {"completed", "failed", "cancelled", "interrupted"}


class JobInProgress(Exception):
    pass


class JobNotActive(Exception):
    pass


class JobNotFound(Exception):
    pass


class BookNotReady(Exception):
    pass


@dataclass(frozen=True)
class JobOptions:
    voice: str
    engine: str
    style: str = "neutral"
    rate: str = "-10%"
    force: bool = False


class JobManager:
    def __init__(
        self,
        db: Database,
        library: Library,
        provider_factory: Callable[[str], TTSProvider],
        allow_fake: bool = False,
    ) -> None:
        self.db = db
        self.library = library
        self.provider_factory = provider_factory
        self.allow_fake = allow_fake
        self._active_job_id: str | None = None
        self._cancel_event: threading.Event | None = None
        self._lock = threading.Lock()

    def start(self, book_id: str, options: JobOptions) -> str:
        with self._lock:
            if self._active_job_id is not None:
                raise JobInProgress(self._active_job_id)

            record = self.library.get(book_id)
            manifest = load_manifest(record.path / "manifest.json")
            book = book_from_manifest(manifest)
            if not book.chapters:
                raise BookNotReady("Book has no readable chapters")
            self._validate_options(options)
            provider = self.provider_factory(options.engine)

            job_id = f"job_{uuid4().hex}"
            total_segments = sum(len(chapter.segments) for chapter in book.chapters)
            self.db.create_job(
                {
                    "id": job_id,
                    "book_id": record.id,
                    "status": "queued",
                    "stage": "preparing",
                    "total_segments": total_segments,
                    "options_json": json.dumps(asdict(options)),
                }
            )
            cancel_event = threading.Event()
            self._active_job_id = job_id
            self._cancel_event = cancel_event
            thread = threading.Thread(
                target=self._run,
                args=(job_id, record, book, options, provider, cancel_event),
                name=f"vibebook-{job_id}",
                daemon=True,
            )
            thread.start()
            return job_id

    def cancel(self, job_id: str) -> dict:
        job = self.db.get_job(job_id)
        if job is None:
            raise JobNotFound(job_id)
        if job["status"] in TERMINAL_JOB_STATUSES:
            raise JobNotActive(job_id)
        if job["status"] == "cancelled":
            raise JobNotActive(job_id)
        with self._lock:
            if self._active_job_id != job_id or self._cancel_event is None:
                raise JobNotActive(job_id)
            self._cancel_event.set()
            self.db.update_job(job_id, status="cancelling", message="Cancelando")
        result = self.db.get_job(job_id)
        if result is None:
            raise JobNotFound(job_id)
        return result

    def get(self, job_id: str) -> dict:
        job = self.db.get_job(job_id)
        if job is None:
            raise JobNotFound(job_id)
        return job

    def active_job_id(self) -> str | None:
        with self._lock:
            return self._active_job_id

    def is_book_active(self, book_id: str) -> bool:
        active_id = self.active_job_id()
        if active_id is None:
            return False
        job = self.db.get_job(active_id)
        return job is not None and job["book_id"] == book_id

    def mark_interrupted(self) -> None:
        self.db.mark_interrupted()
        with self._lock:
            self._active_job_id = None
            self._cancel_event = None

    def _validate_options(self, options: JobOptions) -> None:
        voice = get_voice(options.voice)
        if options.engine == "fake":
            if not self.allow_fake:
                raise ValueError("The fake engine is disabled")
        elif options.engine not in voice.engines:
            raise ValueError(f"{options.voice} does not support engine {options.engine}")
        if options.style != "neutral":
            if options.engine != "azure":
                raise ValueError("Styles require the azure engine")
            if options.style not in voice.styles:
                raise ValueError(f"{options.voice} does not support style {options.style}")
        validate_rate(options.rate)

    def _run(
        self,
        job_id: str,
        record: BookRecord,
        book,
        options: JobOptions,
        provider: TTSProvider,
        cancel_event: threading.Event,
    ) -> None:
        started_at = _now()
        try:
            self.db.update_job(
                job_id,
                status="running",
                stage="preparing",
                started_at=started_at,
            )
            self.db.set_book_status(record.id, "converting")

            def on_progress(event) -> None:
                try:
                    self.db.update_job(
                        job_id,
                        stage=event.stage,
                        completed_segments=event.completed_segments,
                        total_segments=event.total_segments,
                        chapter_index=event.chapter_index or None,
                        chapter_title=event.chapter_title or None,
                        current_text=event.text,
                        message=event.message,
                    )
                except (KeyError, sqlite3.Error):
                    logger.exception("Could not persist progress for job %s", job_id)
                    cancel_event.set()

            result = convert(
                book,
                options.voice,
                options.engine,
                provider,
                record.path,
                style=options.style,
                rate=options.rate,
                force=options.force,
                on_progress=on_progress,
                should_cancel=cancel_event.is_set,
                book_id=record.id,
            )
        except ConversionCancelled:
            self._safe_set_book_status(record.id, "interrupted")
            self._safe_update_job(
                job_id,
                status="cancelled",
                stage="cancelled",
                message="Cancelado",
                finished_at=_now(),
            )
        except Exception as exc:
            logger.exception("Job %s failed", job_id)
            self._safe_set_book_status(record.id, "error")
            self._safe_update_job(
                job_id,
                status="failed",
                stage="error",
                error=str(exc)[:2000],
                finished_at=_now(),
            )
        else:
            self._safe_set_book_status(
                record.id,
                "ready",
                duration_ms=result.duration_ms,
                chapter_count=len(book.chapters),
                voice=options.voice,
                engine=options.engine,
                style=options.style,
                rate=options.rate,
            )
            self._safe_update_job(
                job_id,
                status="completed",
                stage="done",
                completed_segments=result.total_segments,
                total_segments=result.total_segments,
                message="Listo",
                finished_at=_now(),
            )
        finally:
            with self._lock:
                if self._active_job_id == job_id:
                    self._active_job_id = None
                    self._cancel_event = None

    def _safe_set_book_status(self, book_id: str, status: str, **fields: object) -> None:
        for attempt in range(3):
            try:
                self.db.set_book_status(book_id, status, **fields)
                return
            except KeyError:
                logger.warning("Book %s disappeared during conversion", book_id)
                return
            except sqlite3.Error:
                if attempt == 2:
                    logger.exception("Could not update book %s status", book_id)
                    return
                time.sleep(0.1)

    def _safe_update_job(self, job_id: str, **fields: object) -> None:
        for attempt in range(3):
            try:
                self.db.update_job(job_id, **fields)
                return
            except KeyError:
                logger.warning("Job %s disappeared during terminal update", job_id)
                return
            except sqlite3.Error:
                if attempt == 2:
                    logger.exception("Could not update job %s terminal state", job_id)
                    return
                time.sleep(0.1)


def _now() -> str:
    return datetime.now(UTC).isoformat()
