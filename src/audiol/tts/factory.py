from audiol.tts.azure import AzureProvider
from audiol.tts.base import TTSProvider
from audiol.tts.edge import EdgeProvider
from audiol.tts.fake import FakeProvider


def make_provider(engine: str, allow_fake: bool = False) -> TTSProvider:
    if engine == "edge":
        return EdgeProvider()
    if engine == "azure":
        return AzureProvider()
    if engine == "fake" and allow_fake:
        return FakeProvider()
    raise ValueError(f"Unknown or disabled TTS engine: {engine}")
