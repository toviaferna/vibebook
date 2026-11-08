from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal, cast
from uuid import uuid4

from fastapi import APIRouter, File, Form, Query, Request, Response, UploadFile
from fastapi.responses import FileResponse

from audiol.ambience.library import MAX_ASSET_BYTES, AmbienceError, AmbienceLibrary
from audiol.ambience.models import (
    AmbienceAnalyzeRequest,
    AmbienceGenerateRequest,
    AmbiencePlanUpdate,
    AmbienceResponse,
    SoundAssetCreate,
    SoundAssetList,
    SoundAssetResponse,
    SoundKind,
)
from audiol.ambience.plan import AmbiencePlanError, load_ambience, save_ambience, validate_plan
from audiol.studio.errors import ApiError

router = APIRouter(tags=["ambience"])

MEDIA_TYPES = {
    ".ogg": "audio/ogg",
    ".opus": "audio/ogg",
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".flac": "audio/flac",
    ".m4a": "audio/mp4",
}


def _library(request: Request) -> AmbienceLibrary:
    return request.app.state.ambience


def _asset_response(asset: dict) -> SoundAssetResponse:
    return SoundAssetResponse(
        **asset,
        audio_url=f"/api/ambience/assets/{asset['id']}/audio",
    )


@router.get("/ambience/assets", response_model=SoundAssetList)
def list_assets(
    request: Request,
    query: str = Query(default="", max_length=200),
    kind: Literal["ambience", "effect", "music"] | None = None,
    license_name: Annotated[str | None, Query(alias="license", max_length=120)] = None,
    approved: bool | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> SoundAssetList:
    items, total = request.app.state.db.list_sound_assets(
        query=query,
        kind=kind,
        license_name=license_name,
        approved=approved,
        limit=limit,
        offset=offset,
    )
    return SoundAssetList(
        items=[_asset_response(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/ambience/assets/{asset_id}", response_model=SoundAssetResponse)
def get_asset(request: Request, asset_id: str) -> SoundAssetResponse:
    asset = request.app.state.db.get_sound_asset(asset_id)
    if asset is None:
        raise ApiError(404, "asset_not_found", "El sonido no existe.")
    return _asset_response(asset)


@router.post("/ambience/assets/import", response_model=SoundAssetResponse, status_code=201)
async def import_asset(
    request: Request,
    file: Annotated[UploadFile, File()],
    prompt: Annotated[str, Form(min_length=1, max_length=240)],
    license_name: Annotated[str, Form(alias="license", min_length=1, max_length=120)],
    kind: Annotated[str, Form()] = "ambience",
    tags: Annotated[str, Form()] = "",
    attribution: Annotated[str | None, Form()] = None,
    source_url: Annotated[str | None, Form()] = None,
    loopable: Annotated[bool, Form()] = False,
) -> SoundAssetResponse:
    try:
        create = SoundAssetCreate(
            prompt=prompt,
            kind=cast("SoundKind", kind),
            tags=[tag.strip() for tag in tags.split(",") if tag.strip()],
            provider="import",
            loopable=loopable,
            license=license_name,
            attribution=attribution,
            source_url=source_url,
        )
    except ValueError as exc:
        raise ApiError(422, "invalid_asset", str(exc)) from exc
    suffix = Path(file.filename or "").suffix.lower()
    temporary = _library(request).root / f".upload-{uuid4().hex}{suffix}"
    try:
        total = 0
        with temporary.open("wb") as handle:
            while chunk := await file.read(1024 * 1024):
                total += len(chunk)
                if total > MAX_ASSET_BYTES:
                    raise ApiError(413, "asset_too_large", "El sonido supera el límite.")
                handle.write(chunk)
        asset = _library(request).import_file(temporary, create)
    except AmbienceError as exc:
        raise ApiError(422, "invalid_asset", str(exc)) from exc
    finally:
        temporary.unlink(missing_ok=True)
    return _asset_response(asset)


@router.post("/ambience/assets/generate", response_model=list[SoundAssetResponse])
def generate_assets(
    request: Request,
    payload: AmbienceGenerateRequest,
) -> list[SoundAssetResponse]:
    library = _library(request)
    try:
        if payload.preset is None:
            assets = library.generate_all()
        else:
            assets = [library.generate_preset(payload.preset)]
    except (AmbienceError, RuntimeError, ValueError) as exc:
        raise ApiError(422, "generate_failed", str(exc)) from exc
    return [_asset_response(asset) for asset in assets]


@router.post("/ambience/assets/{asset_id}/approve", response_model=SoundAssetResponse)
def approve_asset(request: Request, asset_id: str) -> SoundAssetResponse:
    try:
        asset = _library(request).approve(asset_id)
    except KeyError as exc:
        raise ApiError(404, "asset_not_found", "El sonido no existe.") from exc
    return _asset_response(asset)


@router.delete("/ambience/assets/{asset_id}", status_code=204, response_model=None)
def delete_asset(request: Request, asset_id: str) -> Response:
    try:
        _library(request).delete(asset_id)
    except KeyError as exc:
        raise ApiError(404, "asset_not_found", "El sonido no existe.") from exc
    except AmbienceError as exc:
        raise ApiError(409, "asset_in_use", str(exc)) from exc
    return Response(status_code=204)


@router.get("/ambience/assets/{asset_id}/audio")
def get_asset_audio(request: Request, asset_id: str) -> FileResponse:
    asset = request.app.state.db.get_sound_asset(asset_id)
    if asset is None:
        raise ApiError(404, "asset_not_found", "El sonido no existe.")
    try:
        path = _library(request).audio_path(asset_id)
    except FileNotFoundError as exc:
        raise ApiError(404, "asset_audio_missing", "El audio no está en la biblioteca.") from exc
    _library(request).record_use(asset_id)
    return FileResponse(path, media_type=MEDIA_TYPES.get(path.suffix.lower(), "audio/ogg"))


@router.get("/books/{book_id}/ambience", response_model=AmbienceResponse)
def get_book_ambience(request: Request, book_id: str) -> AmbienceResponse:
    record = _record(request, book_id)
    settings, plan = load_ambience(record.path)
    return AmbienceResponse(book_id=record.id, settings=settings, plan=plan)


@router.put("/books/{book_id}/ambience", response_model=AmbienceResponse)
def put_book_ambience(
    request: Request,
    book_id: str,
    payload: AmbiencePlanUpdate,
) -> AmbienceResponse:
    record = _record(request, book_id)
    try:
        validate_plan(payload.plan, record, _known_assets(request))
    except AmbiencePlanError as exc:
        raise ApiError(422, "invalid_ambience", str(exc)) from exc
    save_ambience(record.path, payload.settings, payload.plan)
    return AmbienceResponse(book_id=record.id, settings=payload.settings, plan=payload.plan)


@router.post("/books/{book_id}/ambience/analyze", response_model=AmbienceResponse)
def analyze_book_ambience(
    request: Request,
    book_id: str,
    _payload: AmbienceAnalyzeRequest,
) -> AmbienceResponse:
    record = _record(request, book_id)
    from audiol.ambience.analyzer import analyze_book

    assets, _ = request.app.state.db.list_sound_assets(limit=200)
    try:
        settings, plan = analyze_book(record.path, assets)
        validate_plan(plan, record, {str(asset["id"]) for asset in assets})
    except AmbiencePlanError as exc:
        raise ApiError(422, "invalid_ambience", str(exc)) from exc
    save_ambience(record.path, settings, plan)
    return AmbienceResponse(book_id=record.id, settings=settings, plan=plan)


def _known_assets(request: Request) -> set[str]:
    assets, _ = request.app.state.db.list_sound_assets(limit=200)
    return {str(asset["id"]) for asset in assets}


def _record(request: Request, book_id: str):
    try:
        return request.app.state.library.get(book_id)
    except KeyError as exc:
        raise ApiError(404, "book_not_found", "El libro no existe.") from exc
