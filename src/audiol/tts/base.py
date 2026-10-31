from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol


@dataclass
class AudioResult:
    path: Path
    word_boundaries: list[dict] = field(default_factory=list)


class TTSProvider(Protocol):
    name: str
    audio_suffix: str

    def synthesize(
        self,
        text: str,
        voice: str,
        out_path: Path,
        style: str = "neutral",
    ) -> AudioResult:
        ...
