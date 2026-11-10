import mimetypes
import re
import threading
import unicodedata
from collections import OrderedDict
from dataclasses import asdict
from pathlib import Path

from fastapi import APIRouter, Query, Request, Response
from fastapi.responses import FileResponse

from audiol.convert import measure_duration_ms
from audiol.manifest import book_from_manifest, load_manifest
from audiol.studio.errors import ApiError
from audiol.studio.library import BookNotFound, BookRecord, LibraryError
from audiol.studio.models import (
    BookmarkCreate,
    BookmarkListResponse,
    BookmarkResponse,
    BookPreferencesResponse,
    BookPreferencesUpdate,
    BookStateResponse,
    BookStateUpdate,
    ChapterResponse,
    ReadingBookmarkCreate,
    ReadingBookmarkListResponse,
    ReadingBookmarkResponse,
    ReadingStateResponse,
    ReadingStateUpdate,
    SearchResponse,
    SearchResult,
)
from audiol.timing import ensure_chapter_timing, read_chapter_timing

router = APIRouter(prefix="/books", tags=["reader"])

_MANIFEST_CACHE: OrderedDict[tuple[str, int, int], dict] = OrderedDict()
_MANIFEST_CACHE_LOCK = threading.Lock()
_MANIFEST_CACHE_MAX = 8


def _load_manifest_cached(path: Path) -> dict:
    try:
        stat = path.stat()
    except OSError:
        return load_manifest(path)
    key = (str(path.resolve()), stat.st_mtime_ns, stat.st_size)
    with _MANIFEST_CACHE_LOCK:
        cached = _MANIFEST_CACHE.get(key)
        if cached is not None:
            _MANIFEST_CACHE.move_to_end(key)
            return cached
    data = load_manifest(path)
    with _MANIFEST_CACHE_LOCK:
        _MANIFEST_CACHE[key] = data
        _MANIFEST_CACHE.move_to_end(key)
        while len(_MANIFEST_CACHE) > _MANIFEST_CACHE_MAX:
            _MANIFEST_CACHE.popitem(last=False)
    return data


def _record(request: Request, book_id: str) -> BookRecord:
    try:
        return request.app.state.library.get(book_id)
    except BookNotFound as exc:
        raise ApiError(404, "book_not_found", "El libro no existe.") from exc


def _manifest(request: Request, record: BookRecord) -> dict:
    try:
        return _load_manifest_cached(record.path / "manifest.json")
    except ValueError as exc:
        raise ApiError(422, "invalid_manifest", str(exc)) from exc


def _chapter_data(manifest: dict, chapter_index: int) -> dict:
    for chapter in manifest.get("chapters", []):
        if int(chapter.get("index", -1)) == chapter_index:
            return chapter
    raise ApiError(404, "chapter_not_found", "El capítulo no existe.")


def _chapter_text_length(chapter: dict) -> int:
    return sum(
        len(str(segment.get("text", "")))
        for segment in chapter.get("segments", [])
        if isinstance(segment, dict)
    )


def _audio_path(request: Request, record: BookRecord, chapter: dict):
    audio = chapter.get("audio")
    if not isinstance(audio, str):
        raise ApiError(409, "audio_not_ready", "El capítulo todavía no tiene audio.")
    try:
        path = request.app.state.library.asset_path(record.id, audio)
    except LibraryError as exc:
        raise ApiError(404, "asset_not_found", "El audio no existe.") from exc
    if not path.is_file():
        raise ApiError(404, "asset_not_found", "El audio no existe.")
    return path


def _optional_audio_path(
    request: Request, record: BookRecord, chapter: dict
) -> tuple[Path | None, int | None]:
    audio = chapter.get("audio")
    if not isinstance(audio, str):
        return None, None
    try:
        path = request.app.state.library.asset_path(record.id, audio)
    except LibraryError:
        return None, None
    if not path.is_file():
        return None, None
    duration = chapter.get("duration_ms")
    if not isinstance(duration, int) or duration <= 0:
        try:
            duration = measure_duration_ms(path)
        except Exception:
            return None, None
    return path, duration


def _fold(text: str) -> tuple[str, list[int]]:
    folded: list[str] = []
    mapping: list[int] = []
    for index, char in enumerate(text):
        for part in unicodedata.normalize("NFKD", char):
            if unicodedata.combining(part):
                continue
            for lower in part.casefold():
                folded.append(lower)
                mapping.append(index)
    return "".join(folded), mapping


def _excerpt(text: str, offset: int, query_length: int) -> str:
    start = max(0, offset - 70)
    end = min(len(text), offset + query_length + 90)
    snippet = re.sub(r"\s+", " ", text[start:end]).strip()
    return f"{'… ' if start else ''}{snippet}{' …' if end < len(text) else ''}"


def _segment_positions(request: Request, record: BookRecord, chapter: dict) -> dict[str, int]:
    timing_rel = chapter.get("timing")
    if not isinstance(timing_rel, str):
        return {}
    try:
        path = request.app.state.library.asset_path(record.id, timing_rel)
    except LibraryError:
        return {}
    if not path.is_file():
        return {}
    try:
        timing = read_chapter_timing(path)
    except (ValueError, OSError):
        return {}
    return {segment.id: segment.start_ms for segment in timing.segments}


def _search_results(
    request: Request,
    record: BookRecord,
    manifest: dict,
    query: str,
    limit: int,
) -> list[SearchResult]:
    folded_query, _ = _fold(query)
    if not folded_query:
        return []

    results: list[SearchResult] = []
    for chapter in manifest.get("chapters", []):
        chapter_index = int(chapter.get("index", 0))
        chapter_title = str(chapter.get("title", ""))
        positions = _segment_positions(request, record, chapter)
        for segment in chapter.get("segments", []):
            text = segment.get("text")
            if not isinstance(text, str):
                continue
            segment_id = str(segment.get("id", ""))
            folded, mapping = _fold(text)
            cursor = 0
            while len(results) < limit:
                index = folded.find(folded_query, cursor)
                if index < 0:
                    break
                offset = mapping[index] if index < len(mapping) else 0
                results.append(
                    SearchResult(
                        chapter_index=chapter_index,
                        chapter_title=chapter_title,
                        segment_id=segment_id,
                        position_ms=positions.get(segment_id, 0),
                        excerpt=_excerpt(text, offset, len(query)),
                        offset=offset,
                    )
                )
                cursor = index + max(1, len(folded_query))
            if len(results) >= limit:
                break
        if len(results) >= limit:
            break
    return results


@router.get("/{book_id}/manifest")
def get_manifest(request: Request, book_id: str) -> dict:
    record = _record(request, book_id)
    return _manifest(request, record)


@router.get("/{book_id}/chapters/{chapter_index}", response_model=ChapterResponse)
def get_chapter(request: Request, book_id: str, chapter_index: int) -> ChapterResponse:
    record = _record(request, book_id)
    manifest = _manifest(request, record)
    chapter = _chapter_data(manifest, chapter_index)
    try:
        book = book_from_manifest(manifest)
    except ValueError as exc:
        raise ApiError(422, "invalid_manifest", str(exc)) from exc
    chapter_model = next((item for item in book.chapters if item.index == chapter_index), None)
    if chapter_model is None:
        raise ApiError(404, "chapter_not_found", "El capítulo no existe.")

    audio_path, duration = _optional_audio_path(request, record, chapter)
    if audio_path is None or duration is None:
        return ChapterResponse(
            chapter=chapter,
            timing=None,
            audio_ready=False,
            duration_ms=chapter.get("duration_ms")
            if isinstance(chapter.get("duration_ms"), int)
            else None,
        )
    try:
        timing = ensure_chapter_timing(record.path, chapter_model, duration)
    except ValueError as exc:
        raise ApiError(422, "invalid_timing", str(exc)) from exc
    return ChapterResponse(
        chapter=chapter,
        timing=asdict(timing),
        audio_ready=True,
        duration_ms=duration,
    )


@router.get("/{book_id}/search", response_model=SearchResponse)
def search_book(
    request: Request,
    book_id: str,
    q: str = Query(min_length=2, max_length=100),
    limit: int = Query(default=30, ge=1, le=100),
) -> SearchResponse:
    record = _record(request, book_id)
    manifest = _manifest(request, record)
    return SearchResponse(items=_search_results(request, record, manifest, q, limit))


@router.get("/{book_id}/bookmarks", response_model=BookmarkListResponse)
def list_bookmarks(request: Request, book_id: str) -> BookmarkListResponse:
    record = _record(request, book_id)
    items = [
        BookmarkResponse(**bookmark) for bookmark in request.app.state.db.list_bookmarks(record.id)
    ]
    return BookmarkListResponse(items=items)


@router.post("/{book_id}/bookmarks", response_model=BookmarkResponse, status_code=201)
def create_bookmark(
    request: Request,
    book_id: str,
    payload: BookmarkCreate,
) -> BookmarkResponse:
    record = _record(request, book_id)
    manifest = _manifest(request, record)
    chapter = _chapter_data(manifest, payload.chapter_index)
    duration = chapter.get("duration_ms")
    if isinstance(duration, int) and payload.position_ms > duration:
        raise ApiError(422, "invalid_bookmark", "La posición supera la duración del capítulo.")
    note = payload.note.strip() if payload.note else None
    bookmark = request.app.state.db.create_bookmark(
        record.id,
        payload.chapter_index,
        payload.position_ms,
        note or None,
    )
    return BookmarkResponse(**bookmark)


@router.delete("/{book_id}/bookmarks/{bookmark_id}", status_code=204, response_model=None)
def delete_bookmark(request: Request, book_id: str, bookmark_id: int) -> Response:
    record = _record(request, book_id)
    if not request.app.state.db.delete_bookmark(record.id, bookmark_id):
        raise ApiError(404, "bookmark_not_found", "El marcador no existe.")
    return Response(status_code=204)


@router.get("/{book_id}/audio/{chapter_index}")
def get_audio(request: Request, book_id: str, chapter_index: int) -> FileResponse:
    record = _record(request, book_id)
    manifest = _manifest(request, record)
    chapter = _chapter_data(manifest, chapter_index)
    path = _audio_path(request, record, chapter)
    return FileResponse(path, media_type="audio/mpeg", filename=path.name)


@router.get("/{book_id}/epub")
def get_epub(request: Request, book_id: str) -> FileResponse:
    record = _record(request, book_id)
    manifest = _manifest(request, record)
    epub = manifest.get("epub")
    if not isinstance(epub, str):
        raise ApiError(404, "epub_not_found", "El EPUB original no está disponible.")
    try:
        path = request.app.state.library.asset_path(record.id, epub)
    except LibraryError as exc:
        raise ApiError(404, "epub_not_found", "El EPUB original no existe.") from exc
    if not path.is_file():
        raise ApiError(404, "epub_not_found", "El EPUB original no existe.")
    return FileResponse(
        path,
        media_type="application/epub+zip",
        filename=f"{record.id}.epub",
        content_disposition_type="inline",
    )


@router.get("/{book_id}/images/{image_id}")
def get_image(request: Request, book_id: str, image_id: str) -> FileResponse:
    record = _record(request, book_id)
    manifest = _manifest(request, record)
    image = next(
        (
            item
            for item in manifest.get("images", [])
            if isinstance(item, dict) and item.get("id") == image_id
        ),
        None,
    )
    if image is None:
        raise ApiError(404, "image_not_found", "La imagen no existe.")
    relative = image.get("path")
    if not isinstance(relative, str):
        raise ApiError(404, "image_not_found", "La imagen no existe.")
    try:
        path = request.app.state.library.asset_path(record.id, relative)
    except LibraryError as exc:
        raise ApiError(404, "image_not_found", "La imagen no existe.") from exc
    if not path.is_file():
        raise ApiError(404, "image_not_found", "La imagen no existe.")
    media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return FileResponse(
        path,
        media_type=media_type,
        filename=path.name,
        content_disposition_type="inline",
        headers={"Cache-Control": "private, max-age=3600"},
    )


@router.get("/{book_id}/m4b")
def get_m4b(request: Request, book_id: str) -> FileResponse:
    record = _record(request, book_id)
    manifest = _manifest(request, record)
    manifest_m4b = manifest.get("m4b")
    if isinstance(manifest_m4b, str):
        try:
            path = request.app.state.library.asset_path(record.id, manifest_m4b)
        except LibraryError:
            path = None
        if path is not None and path.is_file():
            return FileResponse(path, media_type="audio/mp4", filename=path.name)
    for candidate in sorted(record.path.glob("*.m4b")):
        try:
            path = request.app.state.library.asset_path(record.id, candidate.name)
        except LibraryError:
            continue
        if path.is_file():
            return FileResponse(path, media_type="audio/mp4", filename=path.name)
    raise ApiError(404, "asset_not_found", "El libro todavía no tiene M4B.")


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


@router.get("/{book_id}/reading-state", response_model=ReadingStateResponse)
def get_reading_state(request: Request, book_id: str) -> ReadingStateResponse:
    record = _record(request, book_id)
    state = request.app.state.db.get_reading_state(record.id)
    if state is None:
        return ReadingStateResponse(
            book_id=record.id,
            chapter_index=1,
            char_offset=0,
            page_index=0,
            page_count=None,
            percent=0.0,
            cfi=None,
            updated_at=None,
        )
    return ReadingStateResponse(
        book_id=record.id,
        chapter_index=int(state["chapter_index"]),
        char_offset=int(state["char_offset"]),
        page_index=int(state["page_index"]),
        page_count=int(state["page_count"]) if state.get("page_count") is not None else None,
        percent=float(state["percent"]),
        cfi=state.get("cfi"),
        updated_at=state.get("updated_at"),
    )


@router.put("/{book_id}/reading-state", response_model=ReadingStateResponse)
def set_reading_state(
    request: Request, book_id: str, payload: ReadingStateUpdate
) -> ReadingStateResponse:
    record = _record(request, book_id)
    manifest = _manifest(request, record)
    chapter = _chapter_data(manifest, payload.chapter_index)
    if payload.char_offset > _chapter_text_length(chapter):
        raise ApiError(422, "invalid_state", "La posición supera el texto del capítulo.")
    if (
        payload.page_count is not None
        and payload.page_count > 0
        and payload.page_index >= payload.page_count
    ):
        raise ApiError(422, "invalid_state", "La página supera el total de páginas.")
    state = request.app.state.db.set_reading_state(
        record.id,
        payload.chapter_index,
        payload.char_offset,
        payload.page_index,
        payload.page_count,
        payload.percent,
        payload.cfi,
    )
    return ReadingStateResponse(
        book_id=record.id,
        chapter_index=int(state["chapter_index"]),
        char_offset=int(state["char_offset"]),
        page_index=int(state["page_index"]),
        page_count=int(state["page_count"]) if state.get("page_count") is not None else None,
        percent=float(state["percent"]),
        cfi=state.get("cfi"),
        updated_at=state.get("updated_at"),
    )


@router.get("/{book_id}/reading-bookmarks", response_model=ReadingBookmarkListResponse)
def list_reading_bookmarks(request: Request, book_id: str) -> ReadingBookmarkListResponse:
    record = _record(request, book_id)
    items = [
        ReadingBookmarkResponse(**bookmark)
        for bookmark in request.app.state.db.list_reading_bookmarks(record.id)
    ]
    return ReadingBookmarkListResponse(items=items)


@router.post(
    "/{book_id}/reading-bookmarks",
    response_model=ReadingBookmarkResponse,
    status_code=201,
)
def create_reading_bookmark(
    request: Request,
    book_id: str,
    payload: ReadingBookmarkCreate,
) -> ReadingBookmarkResponse:
    record = _record(request, book_id)
    manifest = _manifest(request, record)
    chapter = _chapter_data(manifest, payload.chapter_index)
    if payload.char_offset > _chapter_text_length(chapter):
        raise ApiError(422, "invalid_bookmark", "La posición supera el texto del capítulo.")
    note = payload.note.strip() if payload.note else None
    bookmark = request.app.state.db.create_reading_bookmark(
        record.id,
        payload.chapter_index,
        payload.char_offset,
        payload.page_index,
        note or None,
    )
    return ReadingBookmarkResponse(**bookmark)


@router.delete(
    "/{book_id}/reading-bookmarks/{bookmark_id}",
    status_code=204,
    response_model=None,
)
def delete_reading_bookmark(request: Request, book_id: str, bookmark_id: int) -> Response:
    record = _record(request, book_id)
    if not request.app.state.db.delete_reading_bookmark(record.id, bookmark_id):
        raise ApiError(404, "bookmark_not_found", "El marcador no existe.")
    return Response(status_code=204)


@router.get("/{book_id}/preferences", response_model=BookPreferencesResponse)
def get_book_preferences(request: Request, book_id: str) -> BookPreferencesResponse:
    record = _record(request, book_id)
    preferences = request.app.state.db.get_book_preferences(record.id)
    if preferences is None:
        return BookPreferencesResponse(book_id=record.id)
    return BookPreferencesResponse(
        book_id=record.id,
        reader_mode=preferences.get("reader_mode"),
        reader_palette=preferences.get("reader_palette"),
        reader_font=preferences.get("reader_font"),
        reader_size=preferences.get("reader_size"),
        page_turn=preferences.get("page_turn"),
        ambience_enabled=preferences.get("ambience_enabled"),
        updated_at=preferences.get("updated_at"),
    )


@router.put("/{book_id}/preferences", response_model=BookPreferencesResponse)
def set_book_preferences(
    request: Request,
    book_id: str,
    payload: BookPreferencesUpdate,
) -> BookPreferencesResponse:
    record = _record(request, book_id)
    preferences = request.app.state.db.set_book_preferences(
        record.id,
        payload.model_dump(exclude_unset=True),
    )
    return BookPreferencesResponse(
        book_id=record.id,
        reader_mode=preferences.get("reader_mode"),
        reader_palette=preferences.get("reader_palette"),
        reader_font=preferences.get("reader_font"),
        reader_size=preferences.get("reader_size"),
        page_turn=preferences.get("page_turn"),
        ambience_enabled=preferences.get("ambience_enabled"),
        updated_at=preferences.get("updated_at"),
    )
