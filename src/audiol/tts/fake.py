import math
import struct
import wave
from pathlib import Path

from audiol.models import WordTiming
from audiol.tts.base import AudioResult, validate_rate


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
        rate: str = "+0%",
    ) -> AudioResult:
        validate_rate(rate)
        duration = max(0.2, len(text) / 20.0)
        duration_ms = int(duration * 1000)
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

        return AudioResult(path=out_path, words=_word_timings(text, duration_ms))


def _word_timings(text: str, duration_ms: int) -> list[WordTiming]:
    tokens = text.split()
    if not tokens:
        return []
    total_chars = sum(len(token) for token in tokens)
    timings: list[WordTiming] = []
    cursor = 0
    for index, token in enumerate(tokens):
        if index == len(tokens) - 1:
            end = duration_ms
        else:
            end = cursor + max(1, round(duration_ms * len(token) / total_chars))
            end = min(end, duration_ms)
        if end <= cursor:
            end = min(cursor + 1, duration_ms)
        timings.append(WordTiming(text=token, start_ms=cursor, end_ms=end))
        cursor = end
    return timings
