import re
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

RATE_PATTERN = re.compile(r"^[+-]?(100|\d{1,2})%$")


def validate_rate(rate: str) -> str:
    if not RATE_PATTERN.match(rate):
        raise ValueError(f"Invalid rate: {rate!r}; expected a percentage such as '-10%' or '+0%'")
    return rate


@dataclass
class AudioResult:
    path: Path


class TTSProvider(Protocol):
    name: str
    audio_suffix: str

    def synthesize(
        self,
        text: str,
        voice: str,
        out_path: Path,
        style: str = "neutral",
        rate: str = "+0%",
    ) -> AudioResult: ...
