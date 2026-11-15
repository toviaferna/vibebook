from __future__ import annotations

import base64
import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Any

import requests

from audiol.provider_keys import get_provider_key
from audiol.tools import require_ffmpeg
from audiol.tts.base import AudioResult, validate_rate

logger = logging.getLogger(__name__)

API_URL = "https://generativelanguage.googleapis.com/v1beta/interactions"
MODEL = "gemini-3.8-flash-tts"
MAX_ATTEMPTS = 3
RETRY_SECONDS = 65.0

STYLE_INSTRUCTIONS = {
    "neutral": "",
    "chat": "warm, conversational, close and natural, like a friendly audiobook narrator",
    "cheerful": "cheerful, bright and friendly",
    "excited": "excited, energetic and lively",
    "sad": "sad, melancholic and restrained",
    "whispering": "whispering, intimate and very quiet",
    "epic": "epic, dramatic and measured",
    "suspense": "tense, suspenseful and low",
}


class GeminiProvider:
    name = "gemini"
    audio_suffix = ".wav"
    max_concurrency = 1

    def __init__(self, api_key: str | None = None, timeout: float = 180.0) -> None:
        self.api_key = api_key or get_provider_key("gemini")
        self.timeout = timeout

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
            raise ValueError("Gemini TTS received empty text")
        rate = validate_rate(rate)
        if not self.api_key:
            raise ValueError("Gemini TTS needs an API key in Ajustes or GEMINI_API_KEY.")
        if style not in STYLE_INSTRUCTIONS:
            raise ValueError(f"Unsupported Gemini style: {style}")

        payload = _request(self.api_key, text, voice, style, self.timeout)
        audio = _audio_block(payload)
        if audio is None:
            raise RuntimeError("Gemini TTS did not return audio")

        out_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = out_path.with_name(f"{out_path.name}.{os.getpid()}.part")
        try:
            temporary.write_bytes(audio)
            _apply_rate(temporary, rate, out_path)
        finally:
            temporary.unlink(missing_ok=True)
        return AudioResult(path=out_path, words=[])


def _request(
    api_key: str,
    text: str,
    voice: str,
    style: str,
    timeout: float,
) -> dict[str, Any]:
    annotations = []
    instruction = STYLE_INSTRUCTIONS.get(style, "")
    if instruction:
        annotations.append({"type": "speech_metadata", "style": instruction})
    body: dict[str, Any] = {
        "model": MODEL,
        "input": [
            {
                "type": "user_input",
                "content": [
                    {
                        "type": "text",
                        "text": text,
                        **({"annotations": annotations} if annotations else {}),
                    }
                ],
            }
        ],
        "response_format": {"type": "audio"},
        "generation_config": {"speech_config": [{"voice": voice}]},
    }
    last_error: Exception | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = requests.post(
                API_URL,
                json=body,
                headers={"x-goog-api-key": api_key},
                timeout=(15, timeout),
            )
        except requests.RequestException as exc:
            last_error = exc
            if attempt == MAX_ATTEMPTS:
                break
            time.sleep(min(30.0, 2.0**attempt))
            continue
        if response.status_code == 429:
            last_error = RuntimeError("Gemini TTS rate limit reached")
            if attempt == MAX_ATTEMPTS:
                break
            time.sleep(_retry_delay(response, RETRY_SECONDS))
            continue
        if response.status_code >= 400:
            message = _error_message(response)
            if response.status_code in {400, 401, 402, 403, 404}:
                raise ValueError(message)
            last_error = RuntimeError(message)
            if attempt == MAX_ATTEMPTS:
                break
            time.sleep(min(30.0, 2.0**attempt))
            continue
        try:
            return response.json()
        except ValueError as exc:
            raise RuntimeError("Gemini TTS returned invalid JSON") from exc
    raise RuntimeError(f"Gemini TTS failed: {last_error}")


def _audio_block(payload: dict[str, Any]) -> bytes | None:
    blocks: list[dict[str, Any]] = []
    for step in payload.get("steps", []) or []:
        if not isinstance(step, dict):
            continue
        for content in step.get("content", []) or []:
            if isinstance(content, dict) and content.get("type") == "audio":
                blocks.append(content)
    if not blocks:
        output = payload.get("output_audio")
        if isinstance(output, dict) and isinstance(output.get("data"), str):
            blocks.append({"data": output["data"], "mime_type": output.get("mimeType")})
    if not blocks:
        for candidate in payload.get("candidates", []) or []:
            for part in candidate.get("content", {}).get("parts", []) or []:
                inline = part.get("inlineData") if isinstance(part, dict) else None
                if isinstance(inline, dict) and isinstance(inline.get("data"), str):
                    blocks.append({"data": inline["data"], "mime_type": inline.get("mimeType")})
    if not blocks:
        return None
    data = blocks[-1].get("data")
    if not isinstance(data, str):
        return None
    try:
        raw = base64.b64decode(data)
    except ValueError as exc:
        raise RuntimeError("Gemini TTS returned invalid base64 audio") from exc
    mime = str(blocks[-1].get("mime_type") or blocks[-1].get("mimeType") or "")
    if "l16" in mime:
        return _wrap_pcm(raw)
    if raw[:4] in {b"RIFF", b"OggS"} or raw.startswith((b"ID3", b"\xff")):
        return raw
    return _wrap_pcm(raw)


def _wrap_pcm(payload: bytes) -> bytes:
    import io
    import wave

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(24_000)
        handle.writeframes(payload)
    return buffer.getvalue()


def _apply_rate(source: Path, rate: str, target: Path) -> None:
    percent = int(rate.rstrip("%"))
    if percent == 0:
        os.replace(source, target)
        return
    factor = 1.0 + percent / 100.0
    if factor <= 0:
        raise ValueError("Gemini TTS cannot synthesize at -100% rate")
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
        "24000",
        "-f",
        "wav",
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
        raise RuntimeError(f"Could not apply Gemini rate: {detail}")


def _retry_delay(response: requests.Response, default: float) -> float:
    header = response.headers.get("retry-after")
    if header:
        try:
            return min(120.0, max(1.0, float(header)))
        except ValueError:
            pass
    return default


def _error_message(response: requests.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return f"Gemini TTS returned HTTP {response.status_code}"
    error = payload.get("error") if isinstance(payload, dict) else None
    if isinstance(error, dict) and error.get("message"):
        return str(error["message"])
    detail = payload.get("detail") if isinstance(payload, dict) else None
    if isinstance(detail, dict) and detail.get("message"):
        return str(detail["message"])
    return f"Gemini TTS returned HTTP {response.status_code}"
