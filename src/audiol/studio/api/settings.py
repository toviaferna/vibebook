import os

from fastapi import APIRouter, Request

from audiol.studio.errors import ApiError
from audiol.studio.models import SettingsResponse, SettingsUpdate
from audiol.tts.base import validate_rate
from audiol.voices import get_voice

router = APIRouter(tags=["settings"])

DEFAULTS = {
    "default_voice": "es-MX-JorgeNeural",
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
        if "default_voice" in updates:
            get_voice(updates["default_voice"])
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
    values = {**DEFAULTS, **{key: value for key, value in stored.items() if key in DEFAULTS}}
    azure_configured = bool(
        os.environ.get("AZURE_SPEECH_KEY") and os.environ.get("AZURE_SPEECH_REGION")
    )
    return SettingsResponse(
        library_dir=str(request.app.state.settings.library_dir),
        azure_configured=azure_configured,
        **values,
    )
