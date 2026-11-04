from dataclasses import dataclass


@dataclass(frozen=True)
class Voice:
    id: str
    locale: str
    gender: str
    engines: tuple[str, ...]
    styles: tuple[str, ...] = ()


_VOICE_LIST = (
    Voice(
        id="es-MX-JorgeNeural",
        locale="es-MX",
        gender="male",
        engines=("edge", "azure"),
        styles=("chat", "cheerful", "excited", "sad", "whispering"),
    ),
    Voice(
        id="es-MX-DaliaNeural",
        locale="es-MX",
        gender="female",
        engines=("edge", "azure"),
        styles=("cheerful", "sad", "whispering"),
    ),
    Voice(
        id="es-PY-MarioNeural",
        locale="es-PY",
        gender="male",
        engines=("edge",),
    ),
    Voice(
        id="es-PY-TaniaNeural",
        locale="es-PY",
        gender="female",
        engines=("edge",),
    ),
)

VOICES: dict[str, Voice] = {voice.id: voice for voice in _VOICE_LIST}


def list_voices(locale: str | None = None) -> list[Voice]:
    voices = sorted(VOICES.values(), key=lambda voice: (voice.locale, voice.id))
    if locale:
        voices = [voice for voice in voices if voice.locale == locale]
    return voices


def get_voice(voice_id: str) -> Voice:
    try:
        return VOICES[voice_id]
    except KeyError as exc:
        raise ValueError(f"Unknown voice: {voice_id}") from exc
