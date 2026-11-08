from __future__ import annotations

import hashlib
import os
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import requests
from platformdirs import user_data_path

DEFAULT_PIPER_VOICE = "es_MX-ald-medium"
PIPER_VOICE_BASE_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/main"


class PiperNotConfigured(ValueError):
    pass


@dataclass(frozen=True)
class PiperVoiceFile:
    path: str
    size: int
    md5: str


@dataclass(frozen=True)
class PiperVoiceSpec:
    id: str
    locale: str
    gender: str
    quality: str
    license: str
    source_url: str
    files: tuple[PiperVoiceFile, ...]


PIPER_VOICES: dict[str, PiperVoiceSpec] = {
    "es_MX-ald-medium": PiperVoiceSpec(
        id="es_MX-ald-medium",
        locale="es-MX",
        gender="male",
        quality="medium",
        license="Unlicense (dataset); Piper GPL-3.0",
        source_url="https://huggingface.co/rhasspy/piper-voices/tree/main/es/es_MX/ald/medium",
        files=(
            PiperVoiceFile(
                path="es/es_MX/ald/medium/es_MX-ald-medium.onnx",
                size=63_201_294,
                md5="86374058e59b41ac3b7fe4181e1daad6",
            ),
            PiperVoiceFile(
                path="es/es_MX/ald/medium/es_MX-ald-medium.onnx.json",
                size=4_878,
                md5="aedc07cd37e61360144f04aebb05f7dd",
            ),
        ),
    ),
}


def get_piper_voice(voice_id: str) -> PiperVoiceSpec:
    try:
        return PIPER_VOICES[voice_id]
    except KeyError as exc:
        raise ValueError(f"Unknown Piper voice: {voice_id}") from exc


def piper_voice_dir() -> Path:
    configured = os.environ.get("VIBEBOOK_PIPER_VOICES")
    if configured:
        return Path(configured).expanduser()
    return user_data_path("vibebook") / "piper-voices"


def _voice_candidates() -> list[Path]:
    candidates: list[Path] = []
    if configured := os.environ.get("VIBEBOOK_PIPER_VOICES"):
        candidates.append(Path(configured).expanduser())

    configured_model = os.environ.get("VIBEBOOK_PIPER_MODEL")
    if configured_model:
        candidates.append(Path(configured_model).expanduser().parent)

    candidates.append(piper_voice_dir())

    if getattr(sys, "frozen", False):
        bundle = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        candidates.extend([bundle / "piper-voices", Path(sys.executable).parent / "piper-voices"])
    else:
        project_root = Path(__file__).resolve().parents[3]
        candidates.extend(
            [
                Path.cwd() / "piper-voices",
                project_root / "piper-voices",
                project_root / "packaging" / "piper" / "voices",
            ]
        )

    unique: list[Path] = []
    for candidate in candidates:
        if candidate not in unique:
            unique.append(candidate)
    return unique


def resolve_piper_model(voice_id: str, optional: bool = False) -> Path | None:
    get_piper_voice(voice_id)
    configured = os.environ.get("VIBEBOOK_PIPER_MODEL")
    if configured and voice_id == DEFAULT_PIPER_VOICE:
        model = Path(configured).expanduser()
        if _voice_files_present(model):
            return model
        if optional:
            return None
        raise PiperNotConfigured(
            f"VIBEBOOK_PIPER_MODEL points to a missing or incomplete voice: {model}"
        )

    for directory in _voice_candidates():
        model = directory / f"{voice_id}.onnx"
        if _voice_files_present(model):
            return model

    if optional:
        return None
    raise PiperNotConfigured(
        f"Piper voice {voice_id} is not installed. "
        f"Run `vibebook piper download --voice {voice_id}` or set VIBEBOOK_PIPER_VOICES."
    )


def resolve_piper_config(model: Path) -> Path:
    config = _configured_config(model)
    if not config.is_file():
        raise PiperNotConfigured(f"Piper voice config is missing: {config}")
    return config


def _configured_config(model: Path) -> Path:
    configured = os.environ.get("VIBEBOOK_PIPER_CONFIG")
    if configured:
        return Path(configured).expanduser()
    return model.with_name(f"{model.name}.json")


def piper_voice_available(voice_id: str = DEFAULT_PIPER_VOICE) -> bool:
    return resolve_piper_model(voice_id, optional=True) is not None


def _voice_files_present(model: Path) -> bool:
    return model.is_file() and model.stat().st_size > 0 and _configured_config(model).is_file()


def verify_file(path: Path, expected: PiperVoiceFile) -> bool:
    if not path.is_file() or path.stat().st_size != expected.size:
        return False
    digest = hashlib.md5(usedforsecurity=False)
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest() == expected.md5


def verify_piper_voice(voice_id: str = DEFAULT_PIPER_VOICE, directory: Path | None = None) -> bool:
    spec = get_piper_voice(voice_id)
    root = directory or piper_voice_dir()
    return all(verify_file(root / Path(item.path).name, item) for item in spec.files)


def download_piper_voice(
    voice_id: str = DEFAULT_PIPER_VOICE,
    destination: Path | None = None,
    force: bool = False,
    on_progress: Callable[[str], None] | None = None,
) -> Path:
    spec = get_piper_voice(voice_id)
    root = Path(destination).expanduser() if destination else piper_voice_dir()
    root.mkdir(parents=True, exist_ok=True)

    for item in spec.files:
        target = root / Path(item.path).name
        if not force and verify_file(target, item):
            if on_progress:
                on_progress(f"{target.name}: ya existe y coincide con el manifiesto")
            continue
        if on_progress:
            on_progress(f"{target.name}: descargando")
        _download_file(f"{PIPER_VOICE_BASE_URL}/{item.path}", target, item)

    model = root / f"{spec.id}.onnx"
    if not _voice_files_present(model):
        raise PiperNotConfigured(f"Piper voice download is incomplete: {model}")
    return model


def _download_file(url: str, target: Path, expected: PiperVoiceFile) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f"{target.name}.{os.getpid()}.part")
    digest = hashlib.md5(usedforsecurity=False)
    received = 0
    try:
        try:
            with requests.get(url, stream=True, timeout=(10, 120)) as response:
                response.raise_for_status()
                with temporary.open("wb") as handle:
                    for block in response.iter_content(chunk_size=1024 * 1024):
                        if not block:
                            continue
                        handle.write(block)
                        digest.update(block)
                        received += len(block)
        except requests.RequestException as exc:
            raise PiperNotConfigured(f"Could not download {target.name}: {exc}") from exc
        if received != expected.size or digest.hexdigest() != expected.md5:
            raise PiperNotConfigured(
                f"Downloaded file does not match the manifest: {target.name} "
                f"({received} bytes, md5 {digest.hexdigest()})"
            )
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
