import asyncio
import logging
from pathlib import Path

import edge_tts

from audiol.tts.base import AudioResult

logger = logging.getLogger(__name__)


class EdgeProvider:
    name = "edge"
    audio_suffix = ".mp3"
    request_delay = 1.0

    def synthesize(
        self,
        text: str,
        voice: str,
        out_path: Path,
        style: str = "neutral",
    ) -> AudioResult:
        text = text.strip()
        if not text:
            raise ValueError("Edge TTS received empty text")

        if style != "neutral":
            logger.warning(
                "Edge TTS does not support SSML styles; using neutral voice for style=%s",
                style,
            )

        out_path.parent.mkdir(parents=True, exist_ok=True)
        boundaries = asyncio.run(self._stream(text, voice, out_path))
        return AudioResult(path=out_path, word_boundaries=boundaries)

    async def _stream(self, text: str, voice: str, out_path: Path) -> list[dict]:
        communicate = edge_tts.Communicate(text, voice)
        boundaries: list[dict] = []
        with out_path.open("wb") as audio_file:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_file.write(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    boundaries.append(
                        {
                            "text": chunk["text"],
                            "offset": chunk["offset"],
                            "duration": chunk["duration"],
                        }
                    )
        return boundaries
