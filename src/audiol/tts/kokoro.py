from __future__ import annotations

import logging
import os
import re
import threading
import wave
from pathlib import Path
from typing import Any

from audiol.tts.base import AudioResult, validate_rate
from audiol.tts.kokoro_assets import (
    KOKORO_MODEL,
    KOKORO_VOICES,
    KokoroNotConfigured,
    espeak_data_dir,
    kokoro_ready,
    kokoro_root,
)

logger = logging.getLogger(__name__)

DEFAULT_LANGUAGE = "es"
LANGUAGE_BY_VOICE = {
    "ef_dora": "es",
    "em_alex": "es",
    "em_santa": "es",
}
MAX_CHUNK_CHARS = 260
CHUNK_PAUSE_SECONDS = 0.12

_CACHE: dict[str, Any] = {}
_CACHE_LOCK = threading.Lock()
_SYNTH_LOCK = threading.Lock()


class KokoroProvider:
    name = "kokoro"
    audio_suffix = ".wav"
    max_concurrency = 1

    def __init__(self, root: Path | None = None) -> None:
        self.root = root

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
            raise ValueError("Kokoro received empty text")
        rate = validate_rate(rate)
        if style != "neutral":
            logger.warning("Kokoro does not expose Azure styles; using neutral for style=%s", style)
        base = self.root or kokoro_root()
        if not kokoro_ready(base):
            raise KokoroNotConfigured(
                "Kokoro still needs its local model. Install it from Studio first."
            )

        import numpy as np

        kokoro = _load(base)
        speed = _speed(rate)
        language = LANGUAGE_BY_VOICE.get(voice, DEFAULT_LANGUAGE)
        chunks = _split_text(text)
        samples: list[Any] = []
        sample_rate = 24_000
        with _SYNTH_LOCK:
            for index, chunk in enumerate(chunks):
                audio, sample_rate = kokoro.create(
                    chunk,
                    voice=voice,
                    speed=speed,
                    lang=language,
                )
                samples.append(np.asarray(audio, dtype=np.float32))
                if index + 1 < len(chunks):
                    samples.append(
                        np.zeros(int(sample_rate * CHUNK_PAUSE_SECONDS), dtype=np.float32)
                    )

        merged = np.concatenate(samples) if samples else np.zeros(0, dtype=np.float32)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(out_path), "wb") as handle:
            handle.setnchannels(1)
            handle.setsampwidth(2)
            handle.setframerate(sample_rate)
            handle.writeframes((np.clip(merged, -1.0, 1.0) * 32767).astype(np.int16).tobytes())
        return AudioResult(path=out_path, words=[])


def _load(base: Path) -> Any:
    key = str(base)
    with _CACHE_LOCK:
        cached = _CACHE.get(key)
        if cached is not None:
            return cached
        try:
            import espeakng_loader
            from kokoro_onnx import EspeakConfig, Kokoro
        except ImportError as exc:
            raise KokoroNotConfigured("kokoro-onnx is not installed") from exc

        data = espeak_data_dir(base)
        os.environ["ESPEAK_DATA_PATH"] = str(data)
        os.environ["PHONEMIZER_ESPEAK_PATH"] = str(data)
        library = espeakng_loader.get_library_path()
        os.environ["PHONEMIZER_ESPEAK_LIBRARY"] = library

        model = base / KOKORO_MODEL.name
        voices = base / KOKORO_VOICES.name
        if not model.is_file() or not voices.is_file():
            raise KokoroNotConfigured("Kokoro model files are missing")
        kokoro = Kokoro(
            str(model),
            str(voices),
            espeak_config=EspeakConfig(data_path=str(data), lib_path=library),
        )
        _CACHE[key] = kokoro
        return kokoro


def _speed(rate: str) -> float:
    percent = int(rate.rstrip("%"))
    if percent <= -95:
        raise ValueError("Kokoro cannot synthesize below -95% rate")
    return 1.0 / (1.0 + percent / 100.0)


_SENTENCE = re.compile(r"(?<=[.!?…])\s+")


def _split_text(text: str) -> list[str]:
    if len(text) <= MAX_CHUNK_CHARS:
        return [text]
    pieces: list[str] = []
    current = ""
    for sentence in _SENTENCE.split(text):
        candidate = f"{current} {sentence}".strip()
        if len(candidate) <= MAX_CHUNK_CHARS:
            current = candidate
            continue
        if current:
            pieces.append(current)
        if len(sentence) <= MAX_CHUNK_CHARS:
            current = sentence
            continue
        words = sentence.split()
        buffer = ""
        for word in words:
            candidate = f"{buffer} {word}".strip()
            if len(candidate) <= MAX_CHUNK_CHARS:
                buffer = candidate
            else:
                if buffer:
                    pieces.append(buffer)
                buffer = word
        current = buffer
    if current:
        pieces.append(current)
    return [piece for piece in pieces if piece.strip()] or [text]
