from __future__ import annotations

from fastapi import APIRouter

from audiol.studio.errors import ApiError
from audiol.studio.models import (
    PiperSettingsUpdate,
    PiperStatusResponse,
    PiperSuggestionResponse,
    PiperVoiceResponse,
)
from audiol.tts.piper import resolve_piper_binary
from audiol.tts.piper_settings import (
    PiperSettings,
    apply_piper_settings,
    load_piper_settings,
    save_piper_settings,
    suggested_voices_dirs,
    validate_piper_settings,
)
from audiol.tts.piper_voices import discover_piper_voices

router = APIRouter(tags=["piper"])

_VOICE_NAMES = {
    "es_MX-ald-medium": "Aldo",
    "es_ES-davefx-medium": "Dave",
    "es-glados-medium": "Glados",
    "es_AR-daniela-high": "Daniela",
    "es_MX-claude-high": "Claude",
}


def _voice_name(voice_id: str) -> str:
    if voice_id in _VOICE_NAMES:
        return _VOICE_NAMES[voice_id]
    parts = [part for part in voice_id.replace("_", "-").split("-") if part]
    if len(parts) >= 3:
        return parts[2].capitalize()
    if len(parts) == 2:
        return parts[1].capitalize()
    return voice_id


def _status(settings: PiperSettings | None = None) -> PiperStatusResponse:
    current = settings or load_piper_settings()
    errors = validate_piper_settings(current)
    binary = resolve_piper_binary(optional=True)
    voices = [
        PiperVoiceResponse(
            id=voice.id,
            name=_voice_name(voice.id),
            locale=voice.locale,
            gender=voice.gender,
            path=str(voice.path),
        )
        for voice in discover_piper_voices()
    ]
    suggestions = [
        PiperSuggestionResponse(
            path=str(item["path"]),
            label=str(item["label"]),
        )
        for item in suggested_voices_dirs()
    ]
    return PiperStatusResponse(
        binary=str(binary) if binary is not None else current.binary,
        voices_dir=current.voices_dir,
        espeak_data=current.espeak_data,
        binary_configured=binary is not None,
        voices=voices,
        suggestions=suggestions,
        errors=errors,
    )


@router.get("/piper", response_model=PiperStatusResponse)
def get_piper() -> PiperStatusResponse:
    return _status()


@router.put("/piper", response_model=PiperStatusResponse)
def update_piper(payload: PiperSettingsUpdate) -> PiperStatusResponse:
    settings = PiperSettings(
        binary=payload.binary,
        voices_dir=payload.voices_dir,
        espeak_data=payload.espeak_data,
    )
    errors = validate_piper_settings(settings)
    if errors:
        raise ApiError(422, "invalid_piper_settings", "; ".join(errors))
    try:
        save_piper_settings(settings)
    except OSError as exc:
        raise ApiError(
            500,
            "piper_settings_write_failed",
            f"No se pudo guardar la configuración de Piper: {exc}",
        ) from exc
    apply_piper_settings(settings)
    return _status(settings)
