from dataclasses import asdict

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse

from audiol.convert import measure_duration_ms
from audiol.manifest import book_from_manifest, load_manifest
from audiol.studio.errors import ApiError
from audiol.studio.library import BookNotFound, BookRecord, LibraryError
from audiol.studio.models import BookStateResponse, BookStateUpdate, ChapterResponse
from audiol.timing import ensure_chapter_timing

router = APIRouter(prefix="/books", tags=["reader"])


def _record(request: Request, book_id: str) -> BookRecord:
    try:
        return request.app.state.library.get(book_id)
    except BookNotFound as exc:
        raise ApiError(404, "book_not_found", "El libro no existe.") from exc


def _manifest(request: Request, record: BookRecord) -> dict:
    try:
        return load_manifest(record.path / "manifest.json")
    except ValueError as exc:
        raise ApiError(422, "invalid_manifest", str(exc)) from exc


def _chapter_data(manifest: dict, chapter_index: int) -> dict:
    for chapter in manifest.get("chapters", []):
        if int(chapter.get("index", -1)) == chapter_index:
            return chapter
    raise ApiError(404, "chapter_not_found", "El capítulo no existe.")


def _audio_path(request: Request, record: BookRecord, chapter: dict):
    audio = chapter.get("audio")
    if not isinstance(audio, str):
        raise ApiError(409, "audio_not_ready", "El capítulo todavía no tiene audio.")
    try:
        path = request.app.state.library.asset_path(record.id, audio)
    except LibraryError as exc:
        raise ApiError(404, "asset_not_found", "El audio no existe.") from exc
    if not path.is_file():
        raise ApiError(409, "audio_not_ready", "El capítulo todavía no tiene audio.")
    return path


@router.get("/{book_id}/manifest")
def get_manifest(request: Request, book_id: str) -> dict:
    record = _record(request, book_id)
    return _manifest(request, record)


@router.get("/{book_id}/chapters/{chapter_index}", response_model=ChapterResponse)
def get_chapter(request: Request, book_id: str, chapter_index: int) -> ChapterResponse:
    record = _record(request, book_id)
    manifest = _manifest(request, record)
    chapter = _chapter_data(manifest, chapter_index)
    audio_path = _audio_path(request, record, chapter)
    try:
        book = book_from_manifest(manifest)
    except ValueError as exc:
        raise ApiError(422, "invalid_manifest", str(exc)) from exc
    chapter_model = next((item for item in book.chapters if item.index == chapter_index), None)
    if chapter_model is None:
        raise ApiError(404, "chapter_not_found", "El capítulo no existe.")
    duration = chapter.get("duration_ms")
    if not isinstance(duration, int) or duration <= 0:
        duration = measure_duration_ms(audio_path)
    try:
        timing = ensure_chapter_timing(record.path, chapter_model, duration)
    except ValueError as exc:
        raise ApiError(422, "invalid_timing", str(exc)) from exc
    return ChapterResponse(chapter=chapter, timing=asdict(timing))


@router.get("/{book_id}/audio/{chapter_index}")
def get_audio(request: Request, book_id: str, chapter_index: int) -> FileResponse:
    record = _record(request, book_id)
    manifest = _manifest(request, record)
    chapter = _chapter_data(manifest, chapter_index)
    path = _audio_path(request, record, chapter)
    return FileResponse(path, media_type="audio/mpeg", filename=path.name)


@router.get("/{book_id}/m4b")
def get_m4b(request: Request, book_id: str) -> FileResponse:
    record = _record(request, book_id)
    files = sorted(record.path.glob("*.m4b"))
    if not files:
        raise ApiError(404, "asset_not_found", "El libro todavía no tiene M4B.")
    return FileResponse(files[0], media_type="audio/mp4", filename=files[0].name)


@router.get("/{book_id}/state", response_model=BookStateResponse)
def get_state(request: Request, book_id: str) -> BookStateResponse:
    record = _record(request, book_id)
    state = request.app.state.db.get_book_state(record.id)
    if state is None:
        return BookStateResponse(position_ms=0, chapter_index=1, playback_rate=1.0)
    return BookStateResponse(
        position_ms=int(state["position_ms"]),
        chapter_index=int(state["chapter_index"]),
        playback_rate=float(state["playback_rate"]),
        updated_at=state.get("updated_at"),
    )


@router.put("/{book_id}/state", response_model=BookStateResponse)
def set_state(request: Request, book_id: str, payload: BookStateUpdate) -> BookStateResponse:
    record = _record(request, book_id)
    manifest = _manifest(request, record)
    chapters = manifest.get("chapters", [])
    chapter = next(
        (item for item in chapters if int(item.get("index", -1)) == payload.chapter_index),
        None,
    )
    if chapter is None:
        raise ApiError(422, "invalid_state", "El capítulo no existe.")
    duration = chapter.get("duration_ms")
    if isinstance(duration, int) and payload.position_ms > duration:
        raise ApiError(422, "invalid_state", "La posición supera la duración del capítulo.")
    request.app.state.db.set_book_state(
        record.id,
        payload.position_ms,
        payload.chapter_index,
        payload.playback_rate,
    )
    state = request.app.state.db.get_book_state(record.id)
    if state is None:
        raise ApiError(500, "internal_error", "No se pudo guardar el estado.")
    return BookStateResponse(
        position_ms=int(state["position_ms"]),
        chapter_index=int(state["chapter_index"]),
        playback_rate=float(state["playback_rate"]),
        updated_at=state.get("updated_at"),
    )
