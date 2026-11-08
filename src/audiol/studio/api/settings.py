import os

from fastapi import APIRouter, Request

from audiol.studio.errors import ApiError
from audiol.studio.models import SettingsResponse, SettingsUpdate
from audiol.tts.base import validate_rate
from audiol.tts.registry import (
    default_voice_for_engine,
    engine_available,
    preferred_engine,
)
from audiol.voices import get_voice

router = APIRouter(tags=["settings"])

DEFAULTS = {
    "default_rate": "-10%",
    "reader_theme": "light",
    "reader_font": "serif",
    "reader_size": 19,
    "auto_scroll": True,
    "skip_seconds": 15,
}


@router.get("/settings", response_model=SettingsResponse)
def get_settings(request: Request) -> SettingsResponse:
    return _settings_response(request)


@router.put("/settings", response_model=SettingsResponse)
def update_settings(request: Request, payload: SettingsUpdate) -> SettingsResponse:
    updates = payload.model_dump(exclude_none=True)
    try:
        stored = request.app.state.db.get_settings()
        engine = _current_engine(request, stored)
        if "default_engine" in updates:
            engine = updates["default_engine"]
            if not _engine_is_available(request, engine):
                raise ValueError(f"El motor {engine} no está configurado.")
            if "default_voice" not in updates:
                updates["default_voice"] = _default_voice(request, engine)
        if "default_voice" in updates:
            voice_id = updates["default_voice"]
            if not _voice_supports(request, voice_id, engine):
                raise ValueError(f"{voice_id} no soporta el motor {engine}.")
        if "default_rate" in updates:
            validate_rate(updates["default_rate"])
    except ValueError as exc:
        raise ApiError(422, "invalid_options", str(exc)) from exc
    try:
        for key, value in updates.items():
            request.app.state.db.set_setting(key, value)
    except ValueError as exc:
        raise ApiError(422, "invalid_options", str(exc)) from exc
    return _settings_response(request)


def _settings_response(request: Request) -> SettingsResponse:
    stored = request.app.state.db.get_settings()
    engine = _current_engine(request, stored)
    voice_id = stored.get("default_voice")
    if not voice_id or not _voice_supports(request, voice_id, engine):
        voice_id = _default_voice(request, engine)
    values = {**DEFAULTS, **{key: value for key, value in stored.items() if key in DEFAULTS}}
    azure_configured = bool(
        os.environ.get("AZURE_SPEECH_KEY") and os.environ.get("AZURE_SPEECH_REGION")
    )
    return SettingsResponse(
        library_dir=str(request.app.state.settings.library_dir),
        default_engine=engine,
        default_voice=voice_id,
        azure_configured=azure_configured,
        **values,
    )


def _current_engine(request: Request, stored: dict) -> str:
    stored_engine = stored.get("default_engine")
    if stored_engine and _engine_is_available(request, stored_engine):
        return stored_engine
    return preferred_engine(allow_fake=request.app.state.settings.allow_fake) or "edge"


def _engine_is_available(request: Request, engine: str) -> bool:
    plugins = request.app.state.plugins
    if plugins.has(engine):
        return plugins.get(engine).enabled
    try:
        return engine_available(engine, allow_fake=request.app.state.settings.allow_fake)
    except ValueError:
        return False


def _default_voice(request: Request, engine: str) -> str:
    plugins = request.app.state.plugins
    if plugins.has(engine):
        voices = plugins.get(engine).info.voices
        if voices:
            return voices[0].id
        raise ValueError(f"El plugin {engine} no tiene voces.")
    return default_voice_for_engine(engine)


def _voice_supports(request: Request, voice_id: str, engine: str) -> bool:
    plugins = request.app.state.plugins
    if plugins.has(engine):
        return any(voice.id == voice_id for voice in plugins.voices(engine))
    try:
        voice = get_voice(voice_id)
    except ValueError:
        return False
    return engine == "fake" or engine in voice.engines
