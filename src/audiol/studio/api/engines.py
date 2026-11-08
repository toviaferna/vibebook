from urllib.parse import urlparse

from fastapi import APIRouter, Request

from audiol.studio.errors import ApiError
from audiol.studio.models import (
    EngineListResponse,
    EngineResponse,
    PluginAddRequest,
    PluginConfigUpdate,
    PluginListResponse,
    PluginResponse,
    PluginTestResponse,
    VoiceResponse,
)
from audiol.studio.plugins import PluginNotFound, PluginRecord
from audiol.tts.plugin import PluginError
from audiol.tts.registry import engine_available, get_engine, list_engines
from audiol.voices import list_voices

router = APIRouter(tags=["engines"])


@router.get("/engines", response_model=EngineListResponse)
def get_engines(request: Request) -> EngineListResponse:
    allow_fake = request.app.state.settings.allow_fake
    items = []
    for engine in list_engines():
        available = engine_available(engine.id, allow_fake=allow_fake)
        items.append(
            EngineResponse(
                id=engine.id,
                label=engine.label,
                kind=engine.kind,
                transport=engine.transport,
                requires_network=engine.requires_network,
                requires_key=engine.requires_key,
                supports_styles=engine.supports_styles,
                timing=engine.timing,
                max_chars=engine.max_chars,
                audio_suffix=engine.audio_suffix,
                license=engine.license,
                source_url=engine.source_url,
                description=engine.description,
                config_schema=engine.config_schema,
                legacy=engine.legacy,
                implemented=engine.implemented,
                test_only=engine.test_only,
                available=available,
                configured=available,
            )
        )
    for record in request.app.state.plugins.records():
        items.append(_plugin_engine(request, record))
    return EngineListResponse(items=items)


@router.get("/engines/plugins", response_model=PluginListResponse)
def get_plugins(request: Request) -> PluginListResponse:
    return PluginListResponse(
        items=[_plugin_response(request, record) for record in request.app.state.plugins.records()]
    )


@router.post("/engines/plugins", response_model=PluginResponse, status_code=201)
def add_plugin(request: Request, payload: PluginAddRequest) -> PluginResponse:
    try:
        record = request.app.state.plugins.add(payload.url, token=payload.token)
    except PluginError as exc:
        raise ApiError(422, "invalid_plugin", str(exc)) from exc
    return _plugin_response(request, record)


@router.delete("/engines/plugins/{plugin_id}", status_code=204)
def remove_plugin(request: Request, plugin_id: str) -> None:
    try:
        request.app.state.plugins.remove(plugin_id)
    except PluginNotFound as exc:
        raise ApiError(404, "plugin_not_found", str(exc)) from exc


@router.put("/engines/{plugin_id}/config", response_model=PluginResponse)
def update_plugin(request: Request, plugin_id: str, payload: PluginConfigUpdate) -> PluginResponse:
    try:
        record = request.app.state.plugins.update_config(
            plugin_id,
            token=payload.token,
            enabled=payload.enabled,
        )
    except PluginNotFound as exc:
        raise ApiError(404, "plugin_not_found", str(exc)) from exc
    return _plugin_response(request, record)


@router.post("/engines/{plugin_id}/test", response_model=PluginTestResponse)
def test_plugin(request: Request, plugin_id: str) -> PluginTestResponse:
    try:
        result = request.app.state.plugins.test(plugin_id)
    except PluginNotFound as exc:
        raise ApiError(404, "plugin_not_found", str(exc)) from exc
    except PluginError as exc:
        raise ApiError(422, "invalid_plugin", str(exc)) from exc
    except ValueError as exc:
        raise ApiError(422, "invalid_plugin", str(exc)) from exc
    except RuntimeError as exc:
        raise ApiError(502, "plugin_error", str(exc)) from exc
    return PluginTestResponse(**result)


@router.get("/engines/{plugin_id}/voices", response_model=list[VoiceResponse])
def get_engine_voices(request: Request, plugin_id: str) -> list[VoiceResponse]:
    if request.app.state.plugins.has(plugin_id):
        record = request.app.state.plugins.get(plugin_id)
        if not record.enabled:
            raise ApiError(422, "invalid_options", "El plugin está deshabilitado.")
        return [
            VoiceResponse(
                id=voice.id,
                locale=voice.locale,
                gender=voice.gender,
                engines=[plugin_id],
                styles=list(voice.styles),
            )
            for voice in request.app.state.plugins.voices(plugin_id)
        ]
    try:
        get_engine(plugin_id)
    except ValueError as exc:
        raise ApiError(404, "engine_not_found", str(exc)) from exc
    return [
        VoiceResponse(
            id=voice.id,
            locale=voice.locale,
            gender=voice.gender,
            engines=list(voice.engines),
            styles=list(voice.styles),
        )
        for voice in list_voices(engine=plugin_id)
    ]


def _plugin_response(request: Request, record: PluginRecord) -> PluginResponse:
    info = record.info
    return PluginResponse(
        id=info.id,
        name=info.name,
        version=info.version,
        url=record.url,
        protocol=info.protocol,
        license=info.license,
        source=info.source,
        languages=list(info.capabilities.languages),
        styles=list(info.capabilities.styles),
        timings=info.capabilities.timings,
        max_chars=info.limits.max_chars,
        timeout_seconds=info.limits.timeout_seconds,
        voice_count=len(info.voices),
        has_token=request.app.state.plugins.has_token(info.id),
        enabled=record.enabled,
        added_at=record.added_at,
        updated_at=record.updated_at,
    )


def _plugin_engine(request: Request, record: PluginRecord) -> EngineResponse:
    info = record.info
    host = (urlparse(record.url).hostname or "").lower()
    local = host in {"127.0.0.1", "localhost", "::1"}
    return EngineResponse(
        id=info.id,
        label=info.name,
        kind="plugin",
        transport="http",
        requires_network=not local,
        requires_key=request.app.state.plugins.has_token(info.id),
        supports_styles=bool(info.capabilities.styles),
        timing=info.capabilities.timings,
        max_chars=info.limits.max_chars,
        audio_suffix=".wav",
        license=info.license,
        source_url=info.source,
        description=f"{info.name} {info.version} (plugin VEP)",
        config_schema={"url": "URL del plugin"},
        legacy=False,
        implemented=True,
        test_only=False,
        available=record.enabled,
        configured=record.enabled,
        plugin_url=record.url,
    )
