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
from audiol.tts.registry import get_engine
from audiol.voices import get_voice, list_voices

router = APIRouter(tags=["voices"])
logger = logging.getLogger(__name__)

PREVIEW_KEY = re.compile(r"^[a-f0-9]{16}\.(mp3|wav)$")


@router.get("/voices", response_model=list[VoiceResponse])
def get_voices(engine: str | None = Query(default=None)) -> list[VoiceResponse]:
    if engine is not None:
        try:
            get_engine(engine)
        except ValueError as exc:
            raise ApiError(422, "invalid_options", str(exc)) from exc
    return [
        VoiceResponse(
            id=voice.id,
            locale=voice.locale,
            gender=voice.gender,
            engines=list(voice.engines),
            styles=list(voice.styles),
        )
        for voice in list_voices(engine=engine)
    ]


@router.post("/voices/preview", response_model=PreviewResponse)
def create_preview(request: Request, payload: PreviewRequest) -> PreviewResponse:
    settings = request.app.state.settings
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
