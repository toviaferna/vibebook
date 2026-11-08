from audiol.tts.base import TTSProvider
from audiol.tts.registry import make_provider as _make_provider


def make_provider(engine: str, allow_fake: bool = False) -> TTSProvider:
    return _make_provider(engine, allow_fake=allow_fake)
