from __future__ import annotations

import ctypes
import logging
import os
import shutil
import subprocess
from pathlib import Path

from audiol.tools import find_optional_binary
from audiol.tts.base import AudioResult, validate_rate
from audiol.tts.piper_voices import (
    DEFAULT_PIPER_VOICE,
    PiperNotConfigured,
    piper_voice_available,
    resolve_piper_config,
    resolve_piper_model,
)

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 120.0


class PiperProvider:
    name = "piper"
    audio_suffix = ".wav"

    def __init__(
        self,
        binary: str | Path | None = None,
        model: str | Path | None = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        resolved_binary = Path(binary).expanduser() if binary else resolve_piper_binary()
        if resolved_binary is None:
            raise PiperNotConfigured("Piper binary is not configured")
        self.binary = resolved_binary
        self.model = Path(model).expanduser() if model else None
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
            raise ValueError("Piper received empty text")
        rate = validate_rate(rate)
        if style != "neutral":
            logger.warning("Piper does not support styles; using neutral for style=%s", style)

        resolved_model = self.model or resolve_piper_model(voice)
        if resolved_model is None:
            raise PiperNotConfigured(f"Piper voice is not installed: {voice}")
        model = resolved_model
        config = resolve_piper_config(model)
        length_scale = _length_scale(rate)

        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(b"")
        try:
            output = _piper_path(out_path)
            binary = _piper_path(self.binary)
            model_path = _piper_path(model)
            config_path = _piper_path(config)
            espeak_data = resolve_espeak_data(self.binary)
            espeak_path = _piper_path(espeak_data) if espeak_data else None
        except PiperNotConfigured:
            out_path.unlink(missing_ok=True)
            raise

        command = [
            str(binary),
            "-m",
            str(model_path),
            "-c",
            str(config_path),
            "-f",
            str(output),
            "--length_scale",
            f"{length_scale:.3f}",
        ]
        if espeak_path:
            command.extend(["--espeak_data", str(espeak_path)])

        try:
            result = subprocess.run(
                command,
                input=f"{text}\n",
                text=True,
                capture_output=True,
                timeout=self.timeout,
                check=False,
                creationflags=_creation_flags(),
            )
        except subprocess.TimeoutExpired as exc:
            out_path.unlink(missing_ok=True)
            raise RuntimeError(
                f"Piper timed out after {self.timeout:.0f} seconds while synthesizing {voice}"
            ) from exc
        except OSError as exc:
            out_path.unlink(missing_ok=True)
            raise RuntimeError(f"Piper could not be started: {exc}") from exc

        if result.returncode != 0:
            out_path.unlink(missing_ok=True)
            detail = (result.stderr or result.stdout or "").strip()[-800:]
            raise RuntimeError(
                f"Piper failed with exit code {result.returncode}"
                + (f": {detail}" if detail else "")
            )
        if not out_path.is_file() or out_path.stat().st_size == 0:
            out_path.unlink(missing_ok=True)
            raise RuntimeError("Piper did not produce an audio file")
        return AudioResult(path=out_path, words=[])


def resolve_piper_binary(optional: bool = False) -> Path | None:
    configured = os.environ.get("VIBEBOOK_PIPER_BIN")
    candidates = [configured] if configured else []
    if not configured:
        found = find_optional_binary("piper")
        if found:
            candidates.append(found)

    for candidate in candidates:
        if candidate is None:
            continue
        path = _resolve_executable(candidate)
        if path is not None:
            return path

    if optional:
        return None
    raise PiperNotConfigured(
        "Piper binary not found. Set VIBEBOOK_PIPER_BIN or install piper in PATH."
    )


def _resolve_executable(value: str) -> Path | None:
    path = Path(value).expanduser()
    if path.is_file():
        return path
    found = shutil.which(value)
    return Path(found) if found else None


def piper_ready() -> bool:
    return resolve_piper_binary(optional=True) is not None and piper_voice_available(
        DEFAULT_PIPER_VOICE
    )


def resolve_espeak_data(binary: Path) -> Path | None:
    configured = os.environ.get("VIBEBOOK_PIPER_ESPEAK_DATA")
    if configured:
        path = Path(configured).expanduser()
        if path.is_dir():
            return path
        raise PiperNotConfigured(f"VIBEBOOK_PIPER_ESPEAK_DATA does not exist: {path}")

    for candidate in (binary.parent / "espeak-ng-data", binary.parent.parent / "espeak-ng-data"):
        if candidate.is_dir():
            return candidate
    return None


def _length_scale(rate: str) -> float:
    percent = int(rate.rstrip("%"))
    if percent <= -100:
        raise ValueError("Piper cannot synthesize at -100% rate")
    return 1.0 / (1.0 + percent / 100.0)


def _piper_path(path: Path) -> Path:
    if str(path).isascii() or os.name != "nt":
        return path
    short = _windows_short_path(path)
    if short is not None and str(short).isascii():
        return short
    raise PiperNotConfigured(
        "Piper cannot open non-ASCII paths on this system. "
        "Set VIBEBOOK_PIPER_BIN and VIBEBOOK_PIPER_VOICES to ASCII paths."
    )


def _windows_short_path(path: Path) -> Path | None:
    windll = getattr(ctypes, "windll", None)
    if windll is None:
        return None
    try:
        buffer = ctypes.create_unicode_buffer(32768)
        result = windll.kernel32.GetShortPathNameW(str(path), buffer, len(buffer))
    except (AttributeError, OSError):
        return None
    return Path(buffer.value) if result else None


def _creation_flags() -> int:
    if os.name != "nt":
        return 0
    return getattr(subprocess, "CREATE_NO_WINDOW", 0)
