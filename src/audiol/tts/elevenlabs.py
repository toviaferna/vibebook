from __future__ import annotations

import base64
import logging
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any

import requests

from audiol.models import WordTiming
from audiol.provider_keys import get_provider_key
from audiol.tools import require_ffmpeg
from audiol.tts.base import AudioResult, validate_rate

logger = logging.getLogger(__name__)

API_ROOT = "https://api.elevenlabs.io/v1"
VOICE_ADAM = "pNInz6obpgDQGcFmaJgB"
DEFAULT_MODEL = "eleven_turbo_v2_5"
EXPRESSIVE_MODEL = "eleven_v3"
MAX_ATTEMPTS = 3

# The style field is not a named emotion in ElevenLabs; these values shape the
# delivery without changing the transcript. For v3 we also add an inline tag.
STYLE_SETTINGS = {
    "neutral": (0.15, 0.65),
    "chat": (0.35, 0.55),
    "cheerful": (0.55, 0.45),
    "excited": (0.65, 0.4),
    "sad": (0.5, 0.7),
    "whispering": (0.6, 0.8),
    "epic": (0.6, 0.5),
    "suspense": (0.5, 0.7),
}
STYLE_TAGS = {
    "sad": "[sad]",
    "whispering": "[whispers]",
    "epic": "[dramatic]",
    "suspense": "[whispers]",
}


class ElevenLabsProvider:
    name = "elevenlabs"
    audio_suffix = ".mp3"
    max_concurrency = 1

    def __init__(self, api_key: str | None = None, timeout: float = 180.0) -> None:
        self.api_key = api_key or get_provider_key("elevenlabs")
        self.timeout = timeout
        self.model = os.environ.get("ELEVENLABS_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL

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
            raise ValueError("ElevenLabs received empty text")
        rate = validate_rate(rate)
        if not self.api_key:
            raise ValueError("ElevenLabs needs an API key in Ajustes or ELEVENLABS_API_KEY.")
        if style not in STYLE_SETTINGS:
            raise ValueError(f"Unsupported ElevenLabs style: {style}")

        model = EXPRESSIVE_MODEL if style in STYLE_TAGS else self.model
        tag = STYLE_TAGS.get(style, "")
        spoken = f"{tag} {text}".strip() if tag else text
        payload = self._request(spoken, voice, model, style)
        audio = _decode_audio(payload)
        words = _alignment_words(payload.get("alignment"))

        out_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = out_path.with_name(f"{out_path.name}.{os.getpid()}.part")
        try:
            temporary.write_bytes(audio)
            _apply_rate(temporary, rate, out_path)
        finally:
            temporary.unlink(missing_ok=True)
        return AudioResult(path=out_path, words=_scale_words(words, rate))

    def _request(self, text: str, voice: str, model: str, style: str) -> dict[str, Any]:
        style_value, stability = STYLE_SETTINGS.get(style, STYLE_SETTINGS["neutral"])
        body: dict[str, Any] = {
            "text": text,
            "model_id": model,
            "voice_settings": {
                "stability": stability,
                "similarity_boost": 0.75,
                "style": style_value,
                "use_speaker_boost": True,
            },
        }
        last_error: Exception | None = None
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                response = requests.post(
                    f"{API_ROOT}/text-to-speech/{voice}/with-timestamps",
                    json=body,
                    headers={"xi-api-key": self.api_key or "", "Accept": "application/json"},
                    timeout=(15, self.timeout),
                )
            except requests.RequestException as exc:
                last_error = exc
                if attempt == MAX_ATTEMPTS:
                    break
                time.sleep(min(30.0, 2.0**attempt))
                continue
            if response.status_code == 429:
                last_error = RuntimeError("ElevenLabs rate limit reached")
                if attempt == MAX_ATTEMPTS:
                    break
                time.sleep(_retry_delay(response))
                continue
            if response.status_code == 402:
                raise ValueError(
                    "Tu plan de ElevenLabs no permite esta voz o modelo. "
                    "Probá Adam, Antoni, Arnold o Bella, o cambiá de plan."
                )
            if response.status_code in {400, 401, 403, 404, 422}:
                raise ValueError(_error_message(response))
            if response.status_code >= 500:
                last_error = RuntimeError(_error_message(response))
                if attempt == MAX_ATTEMPTS:
                    break
                time.sleep(min(30.0, 2.0**attempt))
                continue
            if response.status_code != 200:
                raise ValueError(_error_message(response))
            try:
                return response.json()
            except ValueError as exc:
                raise RuntimeError("ElevenLabs returned invalid JSON") from exc
        raise RuntimeError(f"ElevenLabs failed: {last_error}")


def _decode_audio(payload: dict[str, Any]) -> bytes:
    encoded = payload.get("audio_base64")
    if not isinstance(encoded, str) or not encoded:
        raise RuntimeError("ElevenLabs did not return audio")
    try:
        return base64.b64decode(encoded)
    except ValueError as exc:
        raise RuntimeError("ElevenLabs returned invalid base64 audio") from exc


def _alignment_words(alignment: Any) -> list[WordTiming]:
    if not isinstance(alignment, dict):
        return []
    characters = alignment.get("characters")
    starts = alignment.get("character_start_times_seconds")
    ends = alignment.get("character_end_times_seconds")
    if not (
        isinstance(characters, list)
        and isinstance(starts, list)
        and isinstance(ends, list)
        and len(characters) == len(starts) == len(ends)
    ):
        return []
    words: list[WordTiming] = []
    text = ""
    start = 0.0
    end = 0.0
    for character, start_seconds, end_seconds in zip(characters, starts, ends, strict=True):
        if not isinstance(character, str) or not character:
            continue
        if character.isspace():
            if text:
                words.append(_word(text, start, end))
                text = ""
            continue
        if not text:
            start = _seconds(start_seconds)
        text += character
        end = _seconds(end_seconds)
    if text:
        words.append(_word(text, start, end))
    return [word for word in words if word.end_ms > word.start_ms and not _TAG.fullmatch(word.text)]


_TAG = re.compile(r"\[[a-zA-Z][a-zA-Z _-]*\]")


def _scale_words(words: list[WordTiming], rate: str) -> list[WordTiming]:
    percent = int(rate.rstrip("%"))
    if percent == 0 or not words:
        return words
    factor = 1.0 + percent / 100.0
    if factor <= 0:
        raise ValueError("ElevenLabs cannot synthesize at -100% rate")
    return [
        WordTiming(
            text=word.text,
            start_ms=max(0, round(word.start_ms / factor)),
            end_ms=max(1, round(word.end_ms / factor)),
        )
        for word in words
    ]


def _word(text: str, start: float, end: float) -> WordTiming:
    return WordTiming(
        text=text,
        start_ms=max(0, round(start * 1000)),
        end_ms=max(1, round(end * 1000)),
    )


def _seconds(value: Any) -> float:
    try:
        return max(0.0, float(value))
    except (TypeError, ValueError):
        return 0.0


def _apply_rate(source: Path, rate: str, target: Path) -> None:
    percent = int(rate.rstrip("%"))
    if percent == 0:
        os.replace(source, target)
        return
    factor = 1.0 + percent / 100.0
    if factor <= 0:
        raise ValueError("ElevenLabs cannot synthesize at -100% rate")
    ffmpeg, _ = require_ffmpeg()
    filters = []
    remaining = factor
    while remaining > 2.0:
        filters.append("atempo=2.0")
        remaining /= 2.0
    while remaining < 0.5:
        filters.append("atempo=0.5")
        remaining /= 0.5
    filters.append(f"atempo={remaining:.4f}")
    command = [
        ffmpeg,
        "-nostdin",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(source),
        "-filter:a",
        ",".join(filters),
        "-ac",
        "1",
        "-ar",
        "44100",
        "-c:a",
        "libmp3lame",
        "-b:a",
        "128k",
        "-f",
        "mp3",
        str(target),
    ]
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0 or not target.is_file():
        target.unlink(missing_ok=True)
        detail = (result.stderr or result.stdout or "").strip()[-500:]
        raise RuntimeError(f"Could not apply ElevenLabs rate: {detail}")


def _retry_delay(response: requests.Response) -> float:
    header = response.headers.get("retry-after")
    if header:
        try:
            return min(120.0, max(1.0, float(header)))
        except ValueError:
            pass
    return 5.0


def _error_message(response: requests.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return f"ElevenLabs returned HTTP {response.status_code}"
    detail = payload.get("detail") if isinstance(payload, dict) else None
    if isinstance(detail, dict) and detail.get("message"):
        return str(detail["message"])
    if isinstance(detail, str):
        return detail
    return f"ElevenLabs returned HTTP {response.status_code}"
