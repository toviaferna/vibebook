import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from audiol.models import WordTiming

RATE_PATTERN = re.compile(r"^[+-]?(100|\d{1,2})%$")
MAX_PROVIDER_CONCURRENCY = 16


def validate_rate(rate: str) -> str:
    if not RATE_PATTERN.match(rate):
        raise ValueError(f"Invalid rate: {rate!r}; expected a percentage such as '-10%' or '+0%'")
    return rate


def provider_concurrency(provider: "TTSProvider") -> int:
    """Bounded concurrency for one provider, capped by the environment."""
    capability = max(1, int(getattr(provider, "max_concurrency", 1) or 1))
    requested = os.environ.get("VIBEBOOK_TTS_CONCURRENCY")
    if requested:
        try:
            value = int(requested)
        except ValueError:
            value = 0
        if value > 0:
            capability = min(capability, value)
    return min(capability, MAX_PROVIDER_CONCURRENCY)


@dataclass
class AudioResult:
    path: Path
    words: list[WordTiming] = field(default_factory=list)


class TTSProvider(Protocol):
    name: str
    audio_suffix: str
    max_concurrency: int

    def synthesize(
        self,
        text: str,
        voice: str,
        out_path: Path,
        style: str = "neutral",
        rate: str = "+0%",
    ) -> AudioResult: ...
