import hashlib
import logging
import mimetypes
import os
import re
from uuid import uuid4

from fastapi import APIRouter, Query, Request
from fastapi.responses import FileResponse

from audiol.studio.errors import ApiError
from audiol.studio.models import PreviewRequest, PreviewResponse, VoiceResponse
from audiol.tts.base import validate_rate
from audiol.tts.plugin import PluginVoiceSpec
from audiol.tts.registry import get_engine
from audiol.voices import get_voice, list_voices

router = APIRouter(tags=["voices"])
logger = logging.getLogger(__name__)

PREVIEW_KEY = re.compile(r"^[a-f0-9]{16}\.(mp3|wav)$")


@router.get("/voices", response_model=list[VoiceResponse])
def get_voices(request: Request, engine: str | None = Query(default=None)) -> list[VoiceResponse]:
    plugins = request.app.state.plugins
    if engine is not None:
        if plugins.has(engine):
            record = plugins.get(engine)
            if not record.enabled:
                raise ApiError(422, "invalid_options", "El plugin está deshabilitado.")
            return _plugin_voices(engine, plugins.voices(engine))
        try:
            get_engine(engine)
        except ValueError as exc:
            raise ApiError(422, "invalid_options", str(exc)) from exc

    voices = [
        VoiceResponse(
            id=voice.id,
            locale=voice.locale,
            gender=voice.gender,
            engines=list(voice.engines),
            styles=list(voice.styles),
        )
        for voice in list_voices(engine=engine)
    ]
    if engine is None:
        for record in plugins.records():
            if record.enabled:
                voices.extend(_plugin_voices(record.info.id, record.info.voices))
    return voices


@router.post("/voices/preview", response_model=PreviewResponse)
def create_preview(request: Request, payload: PreviewRequest) -> PreviewResponse:
    settings = request.app.state.settings
    plugins = request.app.state.plugins
    plugin = plugins.get(payload.engine) if plugins.has(payload.engine) else None
    if plugin is not None:
        if not plugin.enabled:
            raise ApiError(422, "invalid_options", "El plugin está deshabilitado.")
        voice = next(
            (item for item in plugin.info.voices if item.id == payload.voice),
            None,
        )
        if voice is None:
            raise ApiError(
                422,
                "invalid_options",
                f"{payload.voice} no es una voz del plugin {payload.engine}.",
            )
        if payload.style != "neutral":
            if payload.style not in plugin.info.capabilities.styles:
                raise ApiError(422, "invalid_options", "El plugin no soporta estilos.")
            if payload.style not in voice.styles:
                raise ApiError(
                    422,
                    "invalid_options",
                    f"{voice.id} no soporta el estilo {payload.style}.",
                )
    else:
        try:
            spec = get_engine(payload.engine)
        except ValueError as exc:
            raise ApiError(422, "invalid_options", str(exc)) from exc
        if not spec.implemented:
            raise ApiError(
                422,
                "invalid_options",
                f"El motor {payload.engine} todavía no está disponible.",
            )
        try:
            voice = get_voice(payload.voice)
        except ValueError as exc:
            raise ApiError(422, "invalid_options", str(exc)) from exc
        if spec.test_only:
            if not settings.allow_fake:
                raise ApiError(422, "invalid_options", "El motor fake está deshabilitado.")
        elif payload.engine not in voice.engines:
            raise ApiError(
                422,
                "invalid_options",
                f"{voice.id} no soporta el motor {payload.engine}.",
            )
        if payload.style != "neutral":
            if not spec.supports_styles:
                raise ApiError(
                    422,
                    "invalid_options",
                    f"El motor {payload.engine} no soporta estilos.",
                )
            if payload.style not in voice.styles:
                raise ApiError(
                    422,
                    "invalid_options",
                    f"{voice.id} no soporta el estilo {payload.style}.",
                )
    try:
        rate = validate_rate(payload.rate)
    except ValueError as exc:
        raise ApiError(422, "invalid_options", str(exc)) from exc
    try:
        provider = request.app.state.provider_factory(payload.engine)
    except ValueError as exc:
        raise ApiError(422, "invalid_options", str(exc)) from exc

    key = hashlib.sha256(
        f"{payload.text}|{payload.voice}|{payload.engine}|{payload.style}|{rate}".encode()
    ).hexdigest()[:16]
    filename = f"{key}{provider.audio_suffix}"
    path = settings.library_dir / ".previews" / filename
    if not path.is_file():
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f"{path.name}.{uuid4().hex}.part")
        try:
            provider.synthesize(
                payload.text,
                payload.voice,
                temporary,
                style=payload.style,
                rate=rate,
            )
            os.replace(temporary, path)
        except ValueError as exc:
            logger.exception("Preview configuration failed")
            temporary.unlink(missing_ok=True)
            raise ApiError(422, "invalid_options", str(exc)) from exc
        except Exception as exc:
            logger.exception("Preview generation failed")
            temporary.unlink(missing_ok=True)
            raise ApiError(502, "tts_error", "No se pudo generar la muestra de voz.") from exc
    return PreviewResponse(url=f"/api/previews/{filename}", key=filename)


@router.get("/previews/{key}")
def get_preview(request: Request, key: str) -> FileResponse:
    if not PREVIEW_KEY.match(key):
        raise ApiError(404, "asset_not_found", "La muestra no existe.")
    path = request.app.state.settings.library_dir / ".previews" / key
    if not path.is_file():
        raise ApiError(404, "asset_not_found", "La muestra no existe.")
    media_type = mimetypes.guess_type(path.name)[0] or "audio/mpeg"
    return FileResponse(path, media_type=media_type)


def _plugin_voices(plugin_id: str, voices: list[PluginVoiceSpec]) -> list[VoiceResponse]:
    return [
        VoiceResponse(
            id=voice.id,
            locale=voice.locale,
            gender=voice.gender,
            engines=[plugin_id],
            styles=list(voice.styles),
        )
        for voice in voices
    ]
