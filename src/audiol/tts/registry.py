from audiol.provider_keys import get_provider_key, get_provider_region, provider_configured
from audiol.tts.azure import AzureProvider
from audiol.tts.base import TTSProvider
from audiol.tts.edge import EdgeProvider
from audiol.tts.elevenlabs import ElevenLabsProvider
from audiol.tts.espeak import EspeakProvider, espeak_ready
from audiol.tts.fake import FakeProvider
from audiol.tts.gemini import GeminiProvider
from audiol.tts.kokoro import KokoroProvider
from audiol.tts.kokoro_assets import kokoro_ready
from audiol.tts.piper import PiperProvider, piper_ready
from audiol.tts.spec import (
    AZURE,
    EDGE,
    ELEVENLABS,
    ESPEAK,
    FAKE,
    GEMINI,
    KOKORO,
    PIPER,
    EngineSpec,
)

_ENGINE_ORDER = (
    "piper",
    "kokoro",
    "espeak",
    "edge",
    "gemini",
    "elevenlabs",
    "azure",
    "fake",
)
_DEFAULT_VOICES = {
    "piper": "es_MX-ald-medium",
    "kokoro": "ef_dora",
    "espeak": "es-419",
    "edge": "es-MX-JorgeNeural",
    "gemini": "Kore",
    "elevenlabs": "pNInz6obpgDQGcFmaJgB",
    "azure": "es-MX-JorgeNeural",
    "fake": "es-MX-JorgeNeural",
}

ENGINES: dict[str, EngineSpec] = {
    engine.id: engine for engine in (PIPER, KOKORO, ESPEAK, EDGE, GEMINI, ELEVENLABS, AZURE, FAKE)
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
    if spec.id == "kokoro":
        return kokoro_ready()
    if spec.id == "espeak":
        return espeak_ready()
    if spec.id in {"gemini", "elevenlabs", "azure"}:
        return provider_configured(spec.id)
    return True


def make_provider(engine: str, allow_fake: bool = False) -> TTSProvider:
    spec = get_engine(engine)
    if spec.test_only and not allow_fake:
        raise ValueError("The fake TTS engine is disabled")
    if not spec.implemented:
        raise ValueError(f"TTS engine is not implemented yet: {engine}")
    if spec.id == "edge":
        return EdgeProvider()
    if spec.id == "gemini":
        return GeminiProvider()
    if spec.id == "elevenlabs":
        return ElevenLabsProvider()
    if spec.id == "azure":
        return AzureProvider(get_provider_key("azure"), get_provider_region("azure"))
    if spec.id == "fake":
        return FakeProvider()
    if spec.id == "piper":
        return PiperProvider()
    if spec.id == "kokoro":
        return KokoroProvider()
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
