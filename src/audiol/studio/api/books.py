import contextlib
import logging
import mimetypes
from typing import Annotated, Literal
from uuid import uuid4

from fastapi import APIRouter, File, Request, Response, UploadFile
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool

from audiol.resegment import (
    ResegmentError,
    analyze_resegmentation,
    list_backups,
    repair_segments,
    restore_resegmentation,
)
from audiol.studio.errors import ApiError
from audiol.studio.library import (
    BookNotFound,
    BookRecord,
    InvalidEpubError,
    LibraryError,
)
from audiol.studio.models import (
    BookDetailResponse,
    BookListResponse,
    BookResponse,
    BookStateResponse,
    JobResponse,
    ResegmentBackupResponse,
    ResegmentPlanResponse,
    ResegmentRequest,
    ResegmentRestoreRequest,
)
from audiol.studio.security import save_epub_upload

router = APIRouter(prefix="/books", tags=["books"])
logger = logging.getLogger(__name__)


def _record(request: Request, book_id: str) -> BookRecord:
    try:
        return request.app.state.library.get(book_id)
    except BookNotFound as exc:
        raise ApiError(404, "book_not_found", "El libro no existe.") from exc


def _book_response(row: dict) -> BookResponse:
    duration = row.get("duration_ms")
    position = int(row.get("position_ms") or 0)
    progress = 0.0
    if duration:
        progress = min(1.0, max(0.0, position / int(duration)))
    return BookResponse(
        id=row["id"],
        title=row["title"],
        author=row["author"],
        language=row["language"],
        status=row["status"],
        chapter_count=int(row.get("chapter_count") or 0),
        duration_ms=row.get("duration_ms"),
        voice=row.get("voice"),
        engine=row.get("engine"),
        rate=row.get("rate"),
        cover_url=(f"/api/books/{row['id']}/cover" if row.get("cover_path") else None),
        progress=progress,
        last_position_ms=position,
        last_chapter_index=int(row.get("chapter_index") or 1),
        reading_progress=float(row.get("reading_progress") or 0.0),
        last_read_chapter_index=row.get("reading_chapter_index"),
        last_read_at=row.get("reading_updated_at"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _state_response(request: Request, book_id: str, row: dict) -> BookStateResponse:
    state = request.app.state.db.get_book_state(book_id)
    if state is None:
        return BookStateResponse(
            position_ms=int(row.get("position_ms") or 0),
            chapter_index=int(row.get("chapter_index") or 1),
            playback_rate=float(row.get("playback_rate") or 1.0),
        )
    return BookStateResponse(
        position_ms=int(state["position_ms"]),
        chapter_index=int(state["chapter_index"]),
        playback_rate=float(state["playback_rate"]),
        updated_at=state.get("updated_at"),
    )


@router.get("", response_model=BookListResponse)
def list_books(
    request: Request,
    q: str = "",
    sort: Literal["recent", "title", "duration", "progress"] = "recent",
    limit: int = 50,
    offset: int = 0,
) -> BookListResponse:
    try:
        rows, total = request.app.state.db.list_books(q, sort, limit, offset)
    except ValueError as exc:
        raise ApiError(422, "invalid_request", str(exc)) from exc
    return BookListResponse(
        items=[_book_response(row) for row in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/rescan")
def rescan(request: Request) -> dict:
    records = request.app.state.library.scan()
    request.app.state.db.reconcile(records)
    return {"count": len(records)}


@router.post("/import", status_code=201, response_model=BookResponse)
async def import_book(request: Request, file: Annotated[UploadFile, File()]) -> BookResponse:
    settings = request.app.state.settings
    upload_dir = settings.library_dir / ".uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    temporary = upload_dir / f"{uuid4().hex}.epub"
    try:
        await save_epub_upload(file, temporary, settings)
        try:
            record = await run_in_threadpool(request.app.state.library.import_epub, temporary)
        except InvalidEpubError as exc:
            raise ApiError(422, "invalid_epub", str(exc)) from exc
        except LibraryError as exc:
            raise ApiError(422, "invalid_library_entry", str(exc)) from exc
        request.app.state.db.upsert_book(record)
        row = request.app.state.db.get_book(record.id)
        if row is None:
            raise ApiError(500, "internal_error", "No se pudo indexar el libro.")
        return _book_response(row)
    finally:
        temporary.unlink(missing_ok=True)


@router.get("/{book_id}", response_model=BookDetailResponse)
def get_book(request: Request, book_id: str) -> BookDetailResponse:
    row = request.app.state.db.get_book(book_id)
    if row is None:
        raise ApiError(404, "book_not_found", "El libro no existe.")
    book = _book_response(row)
    last_job = request.app.state.db.get_latest_job(book_id)
    return BookDetailResponse(
        **book.model_dump(),
        state=_state_response(request, book_id, row),
        last_job=JobResponse(**last_job) if last_job is not None else None,
    )


@router.get("/{book_id}/resegment", response_model=ResegmentPlanResponse)
def get_resegment_plan(request: Request, book_id: str) -> ResegmentPlanResponse:
    record = _record(request, book_id)
    try:
        plan = analyze_resegmentation(record.path)
    except (ValueError, ResegmentError) as exc:
        raise ApiError(422, "invalid_manifest", str(exc)) from exc
    return ResegmentPlanResponse(**plan.as_dict())


@router.post("/{book_id}/resegment")
async def run_resegment(
    request: Request,
    book_id: str,
    payload: ResegmentRequest,
) -> dict:
    record = _record(request, book_id)
    if request.app.state.jobs.is_book_active(record.id):
        raise ApiError(
            409,
            "job_in_progress",
            "No se puede reparar un libro mientras se está convirtiendo.",
        )
    try:
        result = await run_in_threadpool(
            repair_segments,
            record.path,
            dry_run=payload.dry_run,
            allow_fake=request.app.state.settings.allow_fake,
        )
    except ResegmentError as exc:
        raise ApiError(422, "resegment_failed", str(exc)) from exc
    except (ValueError, RuntimeError) as exc:
        logger.exception("Could not resegment book %s", record.id)
        raise ApiError(
            500,
            "resegment_failed",
            "No se pudo reparar la segmentación. Revisá los registros del servidor.",
        ) from exc
    if not payload.dry_run:
        refreshed = request.app.state.library.get(record.id)
        request.app.state.db.upsert_book(refreshed)
    return result


@router.get("/{book_id}/resegment/backups", response_model=list[ResegmentBackupResponse])
def get_resegment_backups(request: Request, book_id: str) -> list[ResegmentBackupResponse]:
    record = _record(request, book_id)
    return [ResegmentBackupResponse(**item) for item in list_backups(record.path)]


@router.post("/{book_id}/resegment/restore")
async def restore_resegment(
    request: Request,
    book_id: str,
    payload: ResegmentRestoreRequest,
) -> dict:
    record = _record(request, book_id)
    if request.app.state.jobs.is_book_active(record.id):
        raise ApiError(
            409,
            "job_in_progress",
            "No se puede restaurar un libro mientras se está convirtiendo.",
        )
    try:
        result = await run_in_threadpool(
            restore_resegmentation,
            record.path,
            payload.backup_id,
        )
    except ResegmentError as exc:
        raise ApiError(422, "resegment_failed", str(exc)) from exc
    refreshed = request.app.state.library.get(record.id)
    request.app.state.db.upsert_book(refreshed)
    return result


@router.delete("/{book_id}", status_code=204)
def delete_book(request: Request, book_id: str) -> Response:
    record = _record(request, book_id)
    if request.app.state.jobs.is_book_active(record.id):
        raise ApiError(
            409,
            "job_in_progress",
            "No se puede borrar un libro mientras se está convirtiendo.",
        )
    try:
        request.app.state.library.delete(record.id)
    except LibraryError as exc:
        raise ApiError(422, "invalid_library_entry", str(exc)) from exc
    with contextlib.suppress(KeyError):
        request.app.state.db.delete_book(record.id)
    return Response(status_code=204)


@router.get("/{book_id}/cover")
def get_cover(request: Request, book_id: str) -> FileResponse:
    record = _record(request, book_id)
    if record.cover_path is None or not record.cover_path.is_file():
        raise ApiError(404, "asset_not_found", "El libro no tiene portada.")
    media_type = mimetypes.guess_type(record.cover_path.name)[0] or "image/jpeg"
    return FileResponse(record.cover_path, media_type=media_type)
