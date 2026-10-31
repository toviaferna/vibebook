import math
import struct
import wave
from pathlib import Path

from audiol.tts.base import AudioResult


class FakeProvider:
    name = "fake"
    audio_suffix = ".wav"

    def __init__(self, sample_rate: int = 24000) -> None:
        self.sample_rate = sample_rate

    def synthesize(
        self,
        text: str,
        voice: str,
        out_path: Path,
        style: str = "neutral",
    ) -> AudioResult:
        duration = max(0.2, len(text) / 20.0)
        frame_count = int(duration * self.sample_rate)
        frames = bytearray()
        for index in range(frame_count):
            value = int(1000 * math.sin(2 * math.pi * 440 * index / self.sample_rate))
            frames += struct.pack("<h", value)

        out_path.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(out_path), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(self.sample_rate)
            wav.writeframes(frames)

        return AudioResult(path=out_path)
