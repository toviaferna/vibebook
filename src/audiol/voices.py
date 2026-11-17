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
    Voice(
        id="ef_dora",
        locale="es-ES",
        gender="female",
        engines=("kokoro",),
    ),
    Voice(
        id="em_alex",
        locale="es-ES",
        gender="male",
        engines=("kokoro",),
    ),
    Voice(
        id="em_santa",
        locale="es-ES",
        gender="male",
        engines=("kokoro",),
    ),
    Voice(
        id="Kore",
        locale="es-419",
        gender="female",
        engines=("gemini",),
        styles=("chat", "cheerful", "excited", "sad", "whispering"),
    ),
    Voice(
        id="Orus",
        locale="es-419",
        gender="male",
        engines=("gemini",),
        styles=("chat", "cheerful", "excited", "sad", "whispering"),
    ),
    Voice(
        id="Puck",
        locale="es-419",
        gender="male",
        engines=("gemini",),
        styles=("chat", "cheerful", "excited", "sad", "whispering"),
    ),
    Voice(
        id="Charon",
        locale="es-419",
        gender="male",
        engines=("gemini",),
        styles=("chat", "cheerful", "excited", "sad", "whispering"),
    ),
    Voice(
        id="Aoede",
        locale="es-419",
        gender="female",
        engines=("gemini",),
        styles=("chat", "cheerful", "excited", "sad", "whispering"),
    ),
    Voice(
        id="Sulafat",
        locale="es-419",
        gender="female",
        engines=("gemini",),
        styles=("chat", "cheerful", "excited", "sad", "whispering"),
    ),
    Voice(
        id="pNInz6obpgDQGcFmaJgB",
        locale="en-US",
        gender="male",
        engines=("elevenlabs",),
        styles=("chat", "cheerful", "excited", "sad", "whispering"),
    ),
    Voice(
        id="ErXwobaYiN019PkySvjV",
        locale="en-US",
        gender="male",
        engines=("elevenlabs",),
        styles=("chat", "cheerful", "excited", "sad", "whispering"),
    ),
    Voice(
        id="VR6AewLTigWG4xSOukaG",
        locale="en-US",
        gender="male",
        engines=("elevenlabs",),
        styles=("chat", "cheerful", "excited", "sad", "whispering"),
    ),
    Voice(
        id="EXAVITQu4vr4xnSDxMaL",
        locale="en-US",
        gender="female",
        engines=("elevenlabs",),
        styles=("chat", "cheerful", "excited", "sad", "whispering"),
    ),
    Voice(
        id="dlGxemPxFMTY7iXagmOj",
        locale="es-419",
        gender="male",
        engines=("elevenlabs",),
        styles=("chat", "cheerful", "excited", "sad", "whispering"),
    ),
    Voice(
        id="CaJslL1xziwefCeTNzHv",
        locale="es-419",
        gender="female",
        engines=("elevenlabs",),
        styles=("chat", "cheerful", "excited", "sad", "whispering"),
    ),
    Voice(
        id="l1zE9xgNpUTaQCZzpNJa",
        locale="es-419",
        gender="male",
        engines=("elevenlabs",),
        styles=("chat", "cheerful", "excited", "sad", "whispering"),
    ),
    Voice(
        id="UOIqAnmS11Reiei1Ytkc",
        locale="es-ES",
        gender="female",
        engines=("elevenlabs",),
        styles=("chat", "cheerful", "excited", "sad", "whispering"),
    ),
    Voice(
        id="dF1Qg3iMRirscWEMtEKb",
        locale="es-419",
        gender="male",
        engines=("elevenlabs",),
        styles=("chat", "cheerful", "excited", "sad", "whispering"),
    ),
    Voice(
        id="9oPKasc15pfAbMr7N6Gs",
        locale="es-419",
        gender="female",
        engines=("elevenlabs",),
        styles=("chat", "cheerful", "excited", "sad", "whispering"),
    ),
    Voice(
        id="es_MX-ald-medium",
        locale="es-MX",
        gender="male",
        engines=("piper",),
    ),
    Voice(
        id="es-419",
        locale="es-419",
        gender="neutral",
        engines=("espeak",),
    ),
)

VOICES: dict[str, Voice] = {voice.id: voice for voice in _VOICE_LIST}


def list_voices(locale: str | None = None, engine: str | None = None) -> list[Voice]:
    voices = sorted(VOICES.values(), key=lambda voice: (voice.locale, voice.id))
    if locale:
        voices = [voice for voice in voices if voice.locale == locale]
    if engine and engine != "fake":
        voices = [voice for voice in voices if engine in voice.engines]
    return voices


def get_voice(voice_id: str) -> Voice:
    try:
        return VOICES[voice_id]
    except KeyError as exc:
        raise ValueError(f"Unknown voice: {voice_id}") from exc
