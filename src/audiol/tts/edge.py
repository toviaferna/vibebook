import asyncio
import logging
import time
from pathlib import Path

import edge_tts

from audiol.models import WordTiming
from audiol.tts.base import AudioResult, validate_rate

logger = logging.getLogger(__name__)


class EdgeProvider:
    name = "edge"
    audio_suffix = ".mp3"
    request_delay = 1.0
    cooldown_seconds = 60.0
    max_cooldowns = 4

    def __init__(self) -> None:
        self._last_request: float | None = None

    def synthesize(
        self,
        text: str,
        voice: str,
        out_path: Path,
        style: str = "neutral",
        rate: str = "+0%",
    ) -> AudioResult:
        text = text.strip()
        if not text:
            raise ValueError("Edge TTS received empty text")
        rate = validate_rate(rate)

        if style != "neutral":
            logger.warning(
                "Edge TTS does not support SSML styles; using neutral voice for style=%s",
                style,
            )

        now = time.monotonic()
        if self._last_request is not None:
            wait = self.request_delay - (now - self._last_request)
            if wait > 0:
                time.sleep(wait)
        self._last_request = time.monotonic()

        out_path.parent.mkdir(parents=True, exist_ok=True)
        attempt = 0
        while True:
            try:
                words = asyncio.run(self._stream(text, voice, out_path, rate))
                return AudioResult(path=out_path, words=words or [])
            except edge_tts.exceptions.NoAudioReceived:
                out_path.unlink(missing_ok=True)
                if attempt >= self.max_cooldowns:
                    raise
                wait = self.cooldown_seconds * (2**attempt)
                logger.warning(
                    "Edge TTS returned no audio; waiting %.0f seconds before retrying",
                    wait,
                )
                time.sleep(wait)
                attempt += 1

    async def _stream(self, text: str, voice: str, out_path: Path, rate: str) -> list[WordTiming]:
        communicate = edge_tts.Communicate(text, voice, rate=rate)
        words: list[WordTiming] = []
        with out_path.open("wb") as audio_file:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_file.write(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    word = chunk.get("text", "").strip()
                    if not word:
                        continue
                    start_ms = int(chunk.get("offset", 0) / 10_000)
                    end_ms = start_ms + max(1, int(chunk.get("duration", 0) / 10_000))
                    words.append(WordTiming(text=word, start_ms=start_ms, end_ms=end_ms))
        return words
