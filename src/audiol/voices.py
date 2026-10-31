from dataclasses import dataclass


@dataclass(frozen=True)
class Voice:
    id: str
    locale: str
    gender: str
    engines: tuple[str, ...]
    styles: tuple[str, ...] = ()


VOICES: dict[str, Voice] = {
    "es-MX-JorgeNeural": Voice(
        id="es-MX-JorgeNeural",
        locale="es-MX",
        gender="male",
        engines=("edge", "azure"),
        styles=("chat", "cheerful", "excited", "sad", "whispering"),
    ),
    "es-MX-DaliaNeural": Voice(
        id="es-MX-DaliaNeural",
        locale="es-MX",
        gender="female",
        engines=("edge", "azure"),
        styles=("cheerful", "sad", "whispering"),
    ),
    "es-PY-MarioNeural": Voice(
        id="es-PY-MarioNeural",
        locale="es-PY",
        gender="male",
        engines=("edge",),
    ),
    "es-PY-TaniaNeural": Voice(
        id="es-PY-TaniaNeural",
        locale="es-PY",
        gender="female",
        engines=("edge",),
    ),
}


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
