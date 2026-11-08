from dataclasses import dataclass, field
from typing import Literal

EngineKind = Literal["builtin", "plugin"]
EngineTransport = Literal["local", "http", "command"]
TimingQuality = Literal["native_word", "estimated_word", "segment"]


@dataclass(frozen=True)
class EngineSpec:
    id: str
    label: str
    kind: EngineKind
    transport: EngineTransport
    requires_network: bool
    requires_key: bool
    supports_styles: bool
    timing: TimingQuality
    audio_suffix: str
    license: str
    source_url: str
    description: str
    max_chars: int = 400
    config_schema: dict[str, str] = field(default_factory=dict)
    legacy: bool = False
    implemented: bool = True
    test_only: bool = False


EDGE = EngineSpec(
    id="edge",
    label="Edge TTS",
    kind="builtin",
    transport="http",
    requires_network=True,
    requires_key=False,
    supports_styles=False,
    timing="native_word",
    audio_suffix=".mp3",
    license="Servicio externo no oficial",
    source_url="https://github.com/rany2/edge-tts",
    description="Voz gratuita de Microsoft Edge; requiere internet.",
    legacy=True,
)

AZURE = EngineSpec(
    id="azure",
    label="Azure Speech",
    kind="builtin",
    transport="http",
    requires_network=True,
    requires_key=True,
    supports_styles=True,
    timing="native_word",
    audio_suffix=".mp3",
    license="Servicio comercial",
    source_url="https://azure.microsoft.com/products/ai-services/text-to-speech",
    description="Estilos y word boundaries; requiere clave y cuota.",
    config_schema={
        "key_env": "AZURE_SPEECH_KEY",
        "region_env": "AZURE_SPEECH_REGION",
    },
    legacy=True,
)

FAKE = EngineSpec(
    id="fake",
    label="Motor de prueba",
    kind="builtin",
    transport="local",
    requires_network=False,
    requires_key=False,
    supports_styles=False,
    timing="segment",
    audio_suffix=".wav",
    license="AGPL-3.0-only",
    source_url="",
    description="Genera WAV sintético para tests; no usar en producción.",
    test_only=True,
)

PIPER = EngineSpec(
    id="piper",
    label="Piper",
    kind="builtin",
    transport="local",
    requires_network=False,
    requires_key=False,
    supports_styles=False,
    timing="segment",
    audio_suffix=".wav",
    license="GPL-3.0",
    source_url="https://github.com/OHF-Voice/piper1-gpl",
    description="TTS local en CPU; requiere binario, voz Piper y espeak-ng-data.",
    config_schema={
        "binary_env": "VIBEBOOK_PIPER_BIN",
        "model_env": "VIBEBOOK_PIPER_MODEL",
        "config_env": "VIBEBOOK_PIPER_CONFIG",
        "voices_env": "VIBEBOOK_PIPER_VOICES",
        "espeak_env": "VIBEBOOK_PIPER_ESPEAK_DATA",
    },
)

ESPEAK = EngineSpec(
    id="espeak",
    label="eSpeak NG",
    kind="builtin",
    transport="local",
    requires_network=False,
    requires_key=False,
    supports_styles=False,
    timing="segment",
    audio_suffix=".wav",
    license="GPL-3.0",
    source_url="https://github.com/espeak-ng/espeak-ng",
    description="Fallback local pequeño y robótico; requiere espeak-ng.",
    config_schema={
        "binary_env": "VIBEBOOK_ESPEAK_BIN",
        "path_env": "VIBEBOOK_ESPEAK_PATH",
    },
)
