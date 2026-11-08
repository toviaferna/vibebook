from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

from audiol.tools import find_optional_binary
from audiol.tts.base import AudioResult, validate_rate
from audiol.tts.paths import to_ascii_path

logger = logging.getLogger(__name__)

DEFAULT_ESPEAK_VOICE = "es-419"
DEFAULT_SPEED_WPM = 175
DEFAULT_TIMEOUT_SECONDS = 60.0


class EspeakNotConfigured(ValueError):
    pass


class EspeakProvider:
    name = "espeak"
    audio_suffix = ".wav"

    def __init__(
        self,
        binary: str | Path | None = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        resolved_binary = Path(binary).expanduser() if binary else resolve_espeak_binary()
        if resolved_binary is None:
            raise EspeakNotConfigured("eSpeak NG binary is not configured")
        self.binary = resolved_binary
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
            raise ValueError("eSpeak NG received empty text")
        rate = validate_rate(rate)
        if style != "neutral":
            logger.warning("eSpeak NG does not support styles; using neutral for style=%s", style)

        speed = _speed(rate)
        voice = voice or DEFAULT_ESPEAK_VOICE
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(b"")
        try:
            binary = _ascii_path(self.binary, "binary")
            output = _ascii_path(out_path, "output")
            data_dir = resolve_espeak_path(self.binary)
            data_path = _ascii_path(data_dir, "espeak-ng-data") if data_dir else None
        except EspeakNotConfigured:
            out_path.unlink(missing_ok=True)
            raise

        command = [
            str(binary),
            "-v",
            voice,
            "-s",
            str(speed),
            "-b",
            "1",
            "-w",
            str(output),
            "--stdin",
        ]
        if data_path:
            command.extend(["--path", str(data_path)])

        try:
            result = subprocess.run(
                command,
                input=f"{text}\n",
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                timeout=self.timeout,
                check=False,
                creationflags=_creation_flags(),
            )
        except subprocess.TimeoutExpired as exc:
            out_path.unlink(missing_ok=True)
            raise RuntimeError(
                f"eSpeak NG timed out after {self.timeout:.0f} seconds while synthesizing {voice}"
            ) from exc
        except OSError as exc:
            out_path.unlink(missing_ok=True)
            raise RuntimeError(f"eSpeak NG could not be started: {exc}") from exc

        if result.returncode != 0:
            out_path.unlink(missing_ok=True)
            detail = (result.stderr or result.stdout or "").strip()[-800:]
            raise RuntimeError(
                f"eSpeak NG failed with exit code {result.returncode}"
                + (f": {detail}" if detail else "")
            )
        if not out_path.is_file() or out_path.stat().st_size == 0:
            out_path.unlink(missing_ok=True)
            raise RuntimeError("eSpeak NG did not produce an audio file")
        return AudioResult(path=out_path, words=[])


def resolve_espeak_binary(optional: bool = False) -> Path | None:
    configured = os.environ.get("VIBEBOOK_ESPEAK_BIN")
    candidates: list[str] = [configured] if configured else []
    if not configured:
        if bundled := _bundled_espeak():
            candidates.append(str(bundled))
        for name in ("espeak-ng", "espeak"):
            if found := find_optional_binary(name):
                candidates.append(found)

    for candidate in candidates:
        path = _resolve_executable(candidate)
        if path is not None:
            return path

    if optional:
        return None
    raise EspeakNotConfigured(
        "eSpeak NG binary not found. Set VIBEBOOK_ESPEAK_BIN or install espeak-ng."
    )


def resolve_espeak_path(binary: Path) -> Path | None:
    configured = os.environ.get("VIBEBOOK_ESPEAK_PATH")
    if configured:
        path = Path(configured).expanduser()
        return path.parent if path.name == "espeak-ng-data" else path

    for candidate in (binary.parent, binary.parent.parent):
        if (candidate / "espeak-ng-data").is_dir():
            return candidate
    return None


def espeak_ready() -> bool:
    return resolve_espeak_binary(optional=True) is not None


def _resolve_executable(value: str) -> Path | None:
    path = Path(value).expanduser()
    if path.is_file():
        return path
    found = shutil.which(value)
    return Path(found) if found else None


def _bundled_espeak() -> Path | None:
    if not getattr(sys, "frozen", False):
        return None
    bundle = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    for root in (bundle / "espeak" / "bin", Path(sys.executable).parent / "espeak" / "bin"):
        for name in ("espeak-ng", "espeak", "espeak-ng.exe", "espeak.exe"):
            candidate = root / name
            if candidate.is_file():
                return candidate
    return None


def _speed(rate: str) -> int:
    percent = int(rate.rstrip("%"))
    if percent <= -100:
        raise ValueError("eSpeak NG cannot synthesize at -100% rate")
    return max(80, min(450, round(DEFAULT_SPEED_WPM * (1.0 + percent / 100.0))))


def _ascii_path(path: Path, label: str) -> Path:
    ascii_path = to_ascii_path(path)
    if ascii_path is None:
        raise EspeakNotConfigured(
            f"eSpeak NG cannot open non-ASCII {label} paths on this system. "
            "Use an ASCII folder or enable Windows 8.3 short paths."
        )
    return ascii_path


def _creation_flags() -> int:
    if os.name != "nt":
        return 0
    return getattr(subprocess, "CREATE_NO_WINDOW", 0)
