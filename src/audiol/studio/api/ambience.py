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
    AmbiencePlan,
    AmbiencePlanUpdate,
    AmbienceResponse,
    FreesoundImportRequest,
    PluginImportRequest,
    ProviderList,
    ProviderStatus,
    SoundAssetCreate,
    SoundAssetList,
    SoundAssetResponse,
    SoundKind,
)
from audiol.ambience.plan import AmbiencePlanError, load_ambience, save_ambience, validate_plan
from audiol.ambience.providers.freesound import FreesoundError, FreesoundProvider
from audiol.ambience.providers.plugin import PluginSoundError, PluginSoundProvider
from audiol.studio.activity import BookBusy
from audiol.studio.ambience_jobs import AmbienceRenderError
from audiol.studio.errors import ApiError
from audiol.studio.library import BookNotFound

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


@router.get("/ambience/providers", response_model=ProviderList)
def list_providers() -> ProviderList:
    freesound = FreesoundProvider.from_env()
    plugin = PluginSoundProvider.from_env()
    return ProviderList(
        items=[
            ProviderStatus(
                id="freesound",
                label="Freesound",
                configured=freesound.configured,
                description="Búsqueda CC0 opcional; requiere FREESOUND_API_KEY.",
            ),
            ProviderStatus(
                id="plugin",
                label="Plugin local de ambiente",
                configured=plugin.configured,
                description="Protocolo vep-sound/1 opcional; nunca se instala solo.",
            ),
        ]
    )


@router.post(
    "/ambience/providers/freesound/import",
    response_model=SoundAssetResponse,
    status_code=201,
)
def import_from_freesound(
    request: Request,
    payload: FreesoundImportRequest,
) -> SoundAssetResponse:
    provider = FreesoundProvider.from_env()
    if not provider.configured:
        raise ApiError(422, "provider_unavailable", "FREESOUND_API_KEY no está configurada.")
    try:
        results = provider.search(payload.query, payload.limit, payload.license_filter)
        if not results:
            raise ApiError(404, "not_found", "No encontramos sonidos con esa licencia.")
        asset = provider.import_asset(results[0], _library(request), prompt=payload.query)
    except FreesoundError as exc:
        raise ApiError(502, "provider_error", str(exc)) from exc
    return _asset_response(asset)


@router.post(
    "/ambience/providers/plugin/import",
    response_model=SoundAssetResponse,
    status_code=201,
)
def import_from_plugin(
    request: Request,
    payload: PluginImportRequest,
) -> SoundAssetResponse:
    provider = PluginSoundProvider.from_env()
    if not provider.configured:
        raise ApiError(
            422,
            "provider_unavailable",
            "VIBEBOOK_AMBIENCE_PLUGIN_URL no está configurada.",
        )
    try:
        asset = provider.import_asset(
            payload.prompt,
            _library(request),
            kind=payload.kind,
            duration_ms=payload.duration_ms,
        )
    except PluginSoundError as exc:
        raise ApiError(502, "provider_error", str(exc)) from exc
    return _asset_response(asset)


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
    lease = _reserve(request, record.id, "ambience_save")
    try:
        try:
            validate_plan(payload.plan, record, _known_assets(request))
        except AmbiencePlanError as exc:
            raise ApiError(422, "invalid_ambience", str(exc)) from exc
        save_ambience(record.path, payload.settings, payload.plan)
        request.app.state.db.record_sound_asset_uses(_plan_asset_ids(payload.plan))
    finally:
        request.app.state.activity.release(lease)
    return AmbienceResponse(book_id=record.id, settings=payload.settings, plan=payload.plan)


@router.post("/books/{book_id}/ambience/analyze", response_model=AmbienceResponse)
def analyze_book_ambience(
    request: Request,
    book_id: str,
    _payload: AmbienceAnalyzeRequest,
) -> AmbienceResponse:
    record = _record(request, book_id)
    from audiol.ambience.analyzer import analyze_book

    lease = _reserve(request, record.id, "ambience_save")
    try:
        assets, _ = request.app.state.db.list_sound_assets(limit=200)
        try:
            settings, plan = analyze_book(record.path, assets)
            validate_plan(plan, record, {str(asset["id"]) for asset in assets})
        except AmbiencePlanError as exc:
            raise ApiError(422, "invalid_ambience", str(exc)) from exc
        save_ambience(record.path, settings, plan)
        request.app.state.db.record_sound_asset_uses(_plan_asset_ids(plan))
    finally:
        request.app.state.activity.release(lease)
    return AmbienceResponse(book_id=record.id, settings=settings, plan=plan)


@router.post("/books/{book_id}/ambience/render", status_code=202)
def render_book_ambience(request: Request, book_id: str) -> dict:
    record = _record(request, book_id)
    settings, plan = load_ambience(record.path)
    try:
        validate_plan(plan, record, _known_assets(request))
    except AmbiencePlanError as exc:
        raise ApiError(422, "invalid_ambience", str(exc)) from exc
    if not any(chapter.bed is not None or chapter.effects for chapter in plan.chapters):
        raise ApiError(422, "empty_ambience", "El plan no tiene cues para exportar.")
    try:
        job_id = request.app.state.ambience_jobs.start(record.id)
    except AmbienceRenderError as exc:
        raise ApiError(409, "ambience_busy", str(exc)) from exc
    return {"job_id": job_id}


@router.get("/books/{book_id}/ambience/audio")
def get_ambient_audio(request: Request, book_id: str) -> FileResponse:
    record = _record(request, book_id)
    path = record.path / "audio" / "ambientado.m4b"
    if not path.is_file():
        raise ApiError(404, "ambient_audio_missing", "Todavía no hay un M4B ambientado.")
    return FileResponse(path, media_type="audio/mp4", filename="ambientado.m4b")


@router.get("/books/{book_id}/ambience/attribution")
def get_ambient_attribution(request: Request, book_id: str) -> FileResponse:
    record = _record(request, book_id)
    path = record.path / "audio" / "ambientado-attribution.txt"
    if not path.is_file():
        raise ApiError(404, "attribution_missing", "El libro no tiene atribuciones de ambiente.")
    return FileResponse(path, media_type="text/plain", filename="ambientado-attribution.txt")


def _known_assets(request: Request) -> set[str]:
    assets, _ = request.app.state.db.list_sound_assets(limit=200)
    return {str(asset["id"]) for asset in assets}


def _plan_asset_ids(plan: AmbiencePlan) -> list[str]:
    ids: list[str] = []
    for chapter in plan.chapters:
        if chapter.bed is not None:
            ids.append(chapter.bed.asset_id)
        ids.extend(effect.asset_id for effect in chapter.effects)
    return ids


def _record(request: Request, book_id: str):
    try:
        return request.app.state.library.get(book_id)
    except (BookNotFound, KeyError) as exc:
        raise ApiError(404, "book_not_found", "El libro no existe.") from exc


def _reserve(request: Request, book_id: str, kind: str):
    try:
        return request.app.state.activity.reserve(book_id, kind)
    except BookBusy as exc:
        raise ApiError(
            409,
            "book_busy",
            f"El libro está ocupado con otra operación: {exc.kind}.",
        ) from exc
