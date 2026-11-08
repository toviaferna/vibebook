import os

from audiol.tts.azure import AzureProvider
from audiol.tts.base import TTSProvider
from audiol.tts.edge import EdgeProvider
from audiol.tts.espeak import EspeakProvider, espeak_ready
from audiol.tts.fake import FakeProvider
from audiol.tts.piper import PiperProvider, piper_ready
from audiol.tts.spec import AZURE, EDGE, ESPEAK, FAKE, PIPER, EngineSpec

_ENGINE_ORDER = ("piper", "espeak", "edge", "azure", "fake")
_DEFAULT_VOICES = {
    "piper": "es_MX-ald-medium",
    "espeak": "es-419",
    "edge": "es-MX-JorgeNeural",
    "azure": "es-MX-JorgeNeural",
    "fake": "es-MX-JorgeNeural",
}

ENGINES: dict[str, EngineSpec] = {
    engine.id: engine for engine in (PIPER, ESPEAK, EDGE, AZURE, FAKE)
}


def get_engine(engine_id: str) -> EngineSpec:
    try:
        return ENGINES[engine_id]
    except KeyError as exc:
        raise ValueError(f"Unknown TTS engine: {engine_id}") from exc


def list_engines() -> list[EngineSpec]:
    return [ENGINES[engine_id] for engine_id in _ENGINE_ORDER]


def engine_available(engine_id: str, allow_fake: bool = False) -> bool:
    spec = get_engine(engine_id)
    if not spec.implemented:
        return False
    if spec.test_only:
        return allow_fake
    if spec.id == "piper":
        return piper_ready()
    if spec.id == "espeak":
        return espeak_ready()
    if spec.id == "azure":
        return bool(os.environ.get("AZURE_SPEECH_KEY") and os.environ.get("AZURE_SPEECH_REGION"))
    return True


def make_provider(engine: str, allow_fake: bool = False) -> TTSProvider:
    spec = get_engine(engine)
    if spec.test_only and not allow_fake:
        raise ValueError("The fake TTS engine is disabled")
    if not spec.implemented:
        raise ValueError(f"TTS engine is not implemented yet: {engine}")
    if spec.id == "edge":
        return EdgeProvider()
    if spec.id == "azure":
        return AzureProvider()
    if spec.id == "fake":
        return FakeProvider()
    if spec.id == "piper":
        return PiperProvider()
    if spec.id == "espeak":
        return EspeakProvider()
    raise ValueError(f"TTS engine is not available: {engine}")


def preferred_engine(allow_fake: bool = False) -> str | None:
    for engine_id in ("piper", "espeak"):
        if engine_available(engine_id, allow_fake=allow_fake):
            return engine_id
    return None


def default_voice_for_engine(engine_id: str) -> str:
    get_engine(engine_id)
    return _DEFAULT_VOICES.get(engine_id, "es-MX-JorgeNeural")
