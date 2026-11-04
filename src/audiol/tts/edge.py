import asyncio
import logging
import time
from pathlib import Path

import edge_tts

from audiol.tts.base import AudioResult, validate_rate

logger = logging.getLogger(__name__)


class EdgeProvider:
    name = "edge"
    audio_suffix = ".mp3"
    request_delay = 1.0

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
        asyncio.run(self._stream(text, voice, out_path, rate))
        return AudioResult(path=out_path)

    async def _stream(self, text: str, voice: str, out_path: Path, rate: str) -> None:
        communicate = edge_tts.Communicate(text, voice, rate=rate)
        with out_path.open("wb") as audio_file:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_file.write(chunk["data"])
