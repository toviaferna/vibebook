from __future__ import annotations

import base64
import binascii
import json
import os
import re
import wave
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse, urlunparse

import requests
from mutagen.mp3 import MP3
from pydantic import BaseModel, ConfigDict, Field, field_validator

from audiol.models import WordTiming
from audiol.tts.base import AudioResult, validate_rate

VEP_PROTOCOL = "vep/1"
MAX_INFO_BYTES = 1024 * 1024
MAX_AUDIO_BYTES = 50 * 1024 * 1024
MAX_RESPONSE_BYTES = MAX_INFO_BYTES + MAX_AUDIO_BYTES
PLUGIN_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}


class PluginError(ValueError):
    pass


class PluginVoiceSpec(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(min_length=1, max_length=100)
    locale: str = Field(min_length=2, max_length=20)
    gender: str = Field(default="neutral", max_length=20)
    styles: list[str] = Field(default_factory=list)


class PluginCapabilities(BaseModel):
    model_config = ConfigDict(extra="ignore")

    languages: list[str] = Field(default_factory=list)
    styles: list[str] = Field(default_factory=list)
    timings: Literal["native_word", "estimated_word", "segment"] = "segment"
    streaming: bool = False


class PluginLimits(BaseModel):
    model_config = ConfigDict(extra="ignore")

    max_chars: int = Field(default=400, ge=1, le=5000)
    max_concurrency: int = Field(default=1, ge=1, le=16)
    timeout_seconds: float = Field(default=120.0, ge=1.0, le=300.0)


class PluginInfo(BaseModel):
    model_config = ConfigDict(extra="ignore")

    protocol: Literal["vep/1"]
    id: str
    name: str = Field(min_length=1, max_length=120)
    version: str = Field(default="0.0.0", max_length=40)
    license: str = Field(default="Desconocida", max_length=120)
    source: str = Field(default="", max_length=500)
    capabilities: PluginCapabilities = Field(default_factory=PluginCapabilities)
    limits: PluginLimits = Field(default_factory=PluginLimits)
    voices: list[PluginVoiceSpec] = Field(min_length=1)

    @field_validator("id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        if not PLUGIN_ID_PATTERN.match(value):
            raise ValueError(
                "Plugin IDs must be lowercase letters, digits, dots, dashes or underscores"
            )
        return value


class PluginProvider:
    name = "plugin"
    audio_suffix = ".wav"

    def __init__(
        self,
        url: str,
        token: str | None = None,
        timeout: float = 120.0,
        max_chars: int = 400,
    ) -> None:
        self.url = normalize_plugin_url(url)
        self.token = token
        self.timeout = timeout
        self.max_chars = max_chars

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
            raise ValueError("The plugin received empty text")
        if len(text) > self.max_chars:
            raise ValueError(f"The plugin accepts at most {self.max_chars} characters")
        rate = validate_rate(rate)

        payload = {
            "text": text,
            "voice": voice,
            "style": style,
            "rate": rate,
            "format": "wav",
        }
        try:
            with requests.post(
                f"{self.url}/v1/synthesize",
                json=payload,
                headers=self._headers(),
                timeout=self.timeout,
                stream=True,
            ) as response:
                content = _read_limited(response, MAX_RESPONSE_BYTES, RuntimeError)
                status = response.status_code
        except requests.RequestException as exc:
            raise RuntimeError(f"Could not reach the plugin: {exc}") from exc

        if status >= 400:
            message = _error_message(content)
            if status < 500:
                raise ValueError(message)
            raise RuntimeError(message)

        try:
            body = json.loads(content)
        except ValueError as exc:
            raise RuntimeError("The plugin returned invalid JSON") from exc
        if not isinstance(body, dict):
            raise RuntimeError("The plugin returned an invalid response")
        audio_format = body.get("format", "wav")
        if audio_format != "wav":
            raise RuntimeError(f"Unsupported plugin audio format: {audio_format}")
        encoded = body.get("audio_base64")
        if not isinstance(encoded, str) or not encoded:
            raise RuntimeError("The plugin did not return audio")
        try:
            audio = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise RuntimeError("The plugin returned invalid base64 audio") from exc
        if not audio or len(audio) > MAX_AUDIO_BYTES:
            raise RuntimeError("The plugin returned an invalid audio size")

        words = _parse_words(body.get("words"))
        out_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = out_path.with_name(f"{out_path.name}.{os.getpid()}.part")
        try:
            temporary.write_bytes(audio)
            _validate_wav(temporary)
            os.replace(temporary, out_path)
        finally:
            temporary.unlink(missing_ok=True)
        return AudioResult(path=out_path, words=words)

    def _headers(self) -> dict[str, str]:
        return {"X-Vibebook-Plugin-Token": self.token} if self.token else {}


def normalize_plugin_url(url: str) -> str:
    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise PluginError("The plugin URL must be an absolute http(s) URL")
    if parsed.scheme == "http" and (parsed.hostname or "").lower() not in LOCAL_HOSTS:
        raise PluginError("Remote plugins must use HTTPS")
    path = parsed.path.rstrip("/")
    if path.endswith("/v1"):
        path = path[:-3]
    if path.endswith("/v1/synthesize") or path.endswith("/v1/info"):
        path = path.rsplit("/v1/", 1)[0]
    normalized = urlunparse((parsed.scheme, parsed.netloc, path, "", "", "")).rstrip("/")
    if not normalized:
        raise PluginError("The plugin URL is invalid")
    return normalized


def fetch_plugin_info(url: str, token: str | None = None, timeout: float = 10.0) -> PluginInfo:
    body = _get_json(f"{normalize_plugin_url(url)}/v1/info", token, timeout)
    try:
        return PluginInfo.model_validate(body)
    except ValueError as exc:
        raise PluginError(f"Invalid VEP manifest: {exc}") from exc


def fetch_plugin_health(url: str, token: str | None = None, timeout: float = 10.0) -> dict:
    return _get_json(f"{normalize_plugin_url(url)}/v1/health", token, timeout)


def fetch_plugin_voices(
    url: str, token: str | None = None, timeout: float = 10.0
) -> list[PluginVoiceSpec]:
    body = _get_json(f"{normalize_plugin_url(url)}/v1/voices", token, timeout)
    voices = body.get("voices", body)
    if not isinstance(voices, list):
        raise PluginError("The plugin returned invalid voices")
    try:
        return [PluginVoiceSpec.model_validate(voice) for voice in voices]
    except ValueError as exc:
        raise PluginError(f"Invalid plugin voices: {exc}") from exc


def _get_json(url: str, token: str | None, timeout: float) -> dict:
    headers = {"X-Vibebook-Plugin-Token": token} if token else {}
    try:
        with requests.get(url, headers=headers, timeout=timeout, stream=True) as response:
            content = _read_limited(response, MAX_INFO_BYTES, PluginError)
            status = response.status_code
    except requests.RequestException as exc:
        raise PluginError(f"Could not reach the plugin: {exc}") from exc
    if status >= 400:
        raise PluginError(f"The plugin returned HTTP {status}")
    try:
        body = json.loads(content)
    except ValueError as exc:
        raise PluginError("The plugin returned invalid JSON") from exc
    if not isinstance(body, dict):
        raise PluginError("The plugin returned an invalid response")
    return body


def _read_limited(
    response: requests.Response,
    limit: int,
    error: type[Exception],
) -> bytes:
    length = response.headers.get("Content-Length")
    if length is not None:
        try:
            declared = int(length)
        except ValueError:
            declared = 0
        if declared > limit:
            raise error("The plugin response is too large")
    chunks: list[bytes] = []
    total = 0
    for chunk in response.iter_content(chunk_size=1024 * 1024):
        if not chunk:
            continue
        total += len(chunk)
        if total > limit:
            raise error("The plugin response is too large")
        chunks.append(chunk)
    return b"".join(chunks)


def _error_message(content: bytes) -> str:
    try:
        body = json.loads(content)
    except ValueError:
        return "The plugin returned an error"
    if isinstance(body, dict):
        error = body.get("error")
        if isinstance(error, dict) and isinstance(error.get("message"), str):
            return error["message"]
    return "The plugin returned an error"


def _parse_words(value: object) -> list[WordTiming]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise RuntimeError("The plugin returned invalid word timings")
    words: list[WordTiming] = []
    for item in value:
        if not isinstance(item, dict):
            raise RuntimeError("The plugin returned invalid word timings")
        try:
            text = str(item["text"])
            start_ms = int(item["start_ms"])
            end_ms = int(item["end_ms"])
        except (KeyError, TypeError, ValueError) as exc:
            raise RuntimeError("The plugin returned invalid word timings") from exc
        if not text or start_ms < 0 or end_ms <= start_ms:
            raise RuntimeError("The plugin returned invalid word timings")
        words.append(WordTiming(text=text, start_ms=start_ms, end_ms=end_ms))
    return words


def _validate_wav(path: Path) -> None:
    try:
        with wave.open(str(path), "rb") as audio:
            if audio.getnframes() <= 0 or audio.getsampwidth() <= 0:
                raise RuntimeError("The plugin returned an empty WAV")
    except (wave.Error, EOFError, OSError) as exc:
        raise RuntimeError("The plugin returned invalid WAV audio") from exc


def _validate_mp3(path: Path) -> None:
    try:
        audio = MP3(path)
    except Exception as exc:
        raise RuntimeError("The plugin returned invalid MP3 audio") from exc
    length = getattr(audio.info, "length", None)
    if not length or length <= 0:
        raise RuntimeError("The plugin returned an empty MP3")
