from __future__ import annotations

import json
import os
import shutil
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

from platformdirs import user_data_path

CONFIG_ENV = "VIBEBOOK_PIPER_SETTINGS"
CONFIG_NAME = "piper.json"

_ENV_MAP = {
    "binary": "VIBEBOOK_PIPER_BIN",
    "voices_dir": "VIBEBOOK_PIPER_VOICES",
    "espeak_data": "VIBEBOOK_PIPER_ESPEAK_DATA",
}


@dataclass(frozen=True)
class PiperSettings:
    binary: str | None = None
    voices_dir: str | None = None
    espeak_data: str | None = None

    def to_json(self) -> dict[str, str | None]:
        return asdict(self)

    @classmethod
    def from_json(cls, payload: object) -> PiperSettings:
        if not isinstance(payload, dict):
            return cls()
        values: dict[str, str | None] = {}
        for key in ("binary", "voices_dir", "espeak_data"):
            value = payload.get(key)
            values[key] = value.strip() if isinstance(value, str) and value.strip() else None
        return cls(**values)


def config_path() -> Path:
    configured = os.environ.get(CONFIG_ENV)
    if configured:
        return Path(configured).expanduser()
    return user_data_path("vibebook") / CONFIG_NAME


def load_piper_settings(path: Path | None = None) -> PiperSettings:
    file = Path(path) if path else config_path()
    if not file.is_file():
        return PiperSettings()
    try:
        return PiperSettings.from_json(json.loads(file.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return PiperSettings()


def save_piper_settings(
    settings: PiperSettings,
    path: Path | None = None,
) -> Path:
    file = Path(path) if path else config_path()
    file.parent.mkdir(parents=True, exist_ok=True)
    temporary = file.with_name(f"{file.name}.{os.getpid()}.part")
    try:
        temporary.write_text(
            json.dumps(settings.to_json(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        os.replace(temporary, file)
    finally:
        temporary.unlink(missing_ok=True)
    return file


def apply_piper_settings(settings: PiperSettings) -> None:
    for key, env_name in _ENV_MAP.items():
        value = getattr(settings, key)
        if value:
            os.environ[env_name] = value
        else:
            os.environ.pop(env_name, None)


def _resolve_executable(value: str) -> Path | None:
    path = Path(value).expanduser()
    if path.is_file():
        return path
    found = shutil.which(value)
    return Path(found) if found else None


def validate_piper_settings(settings: PiperSettings) -> list[str]:
    errors: list[str] = []
    if settings.binary and _resolve_executable(settings.binary) is None:
        errors.append(f"No encontré el binario de Piper: {settings.binary}")
    if settings.voices_dir and not Path(settings.voices_dir).expanduser().is_dir():
        errors.append(f"No encontré la carpeta de voces: {settings.voices_dir}")
    if settings.espeak_data and not Path(settings.espeak_data).expanduser().is_dir():
        errors.append(f"No encontré espeak-ng-data: {settings.espeak_data}")
    return errors


def flutter_voices_dir() -> Path | None:
    """The folder the Flutter app used for downloaded Piper voices."""
    if os.name == "nt":
        base = os.environ.get("APPDATA")
        if not base:
            return None
        candidate = Path(base) / "com.vibebook" / "vibebook_app" / "models" / "piper"
    elif sys.platform == "darwin":
        candidate = (
            Path.home()
            / "Library"
            / "Application Support"
            / "com.vibebook.vibebook_app"
            / "models"
            / "piper"
        )
    else:
        candidate = (
            Path.home() / ".local" / "share" / "com.vibebook.vibebook_app" / "models" / "piper"
        )
    return candidate if candidate.is_dir() else None


def suggested_voices_dirs() -> list[dict[str, object]]:
    suggestions: list[dict[str, object]] = []
    flutter = flutter_voices_dir()
    if flutter is not None:
        suggestions.append(
            {
                "path": str(flutter),
                "label": "Voces de la app Flutter anterior",
                "exists": True,
            }
        )
    default = user_data_path("vibebook") / "piper-voices"
    if default.is_dir():
        suggestions.append(
            {
                "path": str(default),
                "label": "Carpeta de voces de Vibebook",
                "exists": True,
            }
        )
    return suggestions
