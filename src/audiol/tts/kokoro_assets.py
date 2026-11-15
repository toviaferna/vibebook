from __future__ import annotations

import hashlib
import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import requests
from platformdirs import user_data_path

MODEL_URL = (
    "https://github.com/thewh1teagle/kokoro-onnx/releases/download/"
    "model-files-v1.0/kokoro-v1.0.onnx"
)
VOICES_URL = (
    "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin"
)


class KokoroNotConfigured(ValueError):
    pass


@dataclass(frozen=True)
class KokoroFile:
    name: str
    url: str
    size: int
    sha256: str


KOKORO_MODEL = KokoroFile(
    name="kokoro-v1.0.onnx",
    url=MODEL_URL,
    size=325_532_387,
    sha256="7d5df8ecf7d4b1878015a32686053fd0eebe2bc377234608764cc0ef3636a6c5",
)
KOKORO_VOICES = KokoroFile(
    name="voices-v1.0.bin",
    url=VOICES_URL,
    size=28_214_398,
    sha256="bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d",
)
KOKORO_FILES = (KOKORO_MODEL, KOKORO_VOICES)
ESPEAK_DIR = "espeak-ng-data"


def _is_ascii(path: Path) -> bool:
    return str(path).isascii()


def _writable(directory: Path) -> bool:
    try:
        directory.mkdir(parents=True, exist_ok=True)
        probe = directory / ".write-test"
        probe.write_text("ok", encoding="ascii")
        probe.unlink(missing_ok=True)
        return True
    except OSError:
        return False


def kokoro_root() -> Path:
    configured = os.environ.get("VIBEBOOK_KOKORO_DIR")
    if configured:
        root = Path(configured).expanduser()
        if os.name == "nt" and not _is_ascii(root):
            raise KokoroNotConfigured("VIBEBOOK_KOKORO_DIR must use an ASCII path on Windows.")
        if not _writable(root):
            raise KokoroNotConfigured(f"VIBEBOOK_KOKORO_DIR is not writable: {root}")
        return root

    candidates: list[Path] = []
    if os.name == "nt":
        # ONNX Runtime and espeak-ng open files through narrow Win32 APIs, which
        # fail when the user profile contains characters such as "ø" or "ñ".
        program_data = os.environ.get("PROGRAMDATA")
        public = os.environ.get("PUBLIC")
        if program_data:
            candidates.append(Path(program_data) / "Vibebook" / "kokoro")
        if public:
            candidates.append(Path(public) / "Vibebook" / "kokoro")
        candidates.append(user_data_path("vibebook") / "kokoro")
    else:
        candidates.append(user_data_path("vibebook") / "kokoro")

    for candidate in candidates:
        if os.name == "nt" and not _is_ascii(candidate):
            continue
        if _writable(candidate):
            return candidate
    raise KokoroNotConfigured("Kokoro needs an ASCII, writable folder. Set VIBEBOOK_KOKORO_DIR.")


def espeak_data_dir(root: Path | None = None) -> Path:
    return (root or kokoro_root()) / ESPEAK_DIR


def _model_paths(root: Path | None = None) -> tuple[Path, Path]:
    base = root or kokoro_root()
    return base / KOKORO_MODEL.name, base / KOKORO_VOICES.name


def _size_ok(path: Path, expected: KokoroFile) -> bool:
    return path.is_file() and path.stat().st_size == expected.size


def kokoro_ready(root: Path | None = None) -> bool:
    try:
        base = root or kokoro_root()
    except KokoroNotConfigured:
        return False
    model, voices = _model_paths(base)
    phontab = espeak_data_dir(base) / "phontab"
    return _size_ok(model, KOKORO_MODEL) and _size_ok(voices, KOKORO_VOICES) and phontab.is_file()


def ensure_kokoro_assets(
    root: Path | None = None,
    force: bool = False,
    on_progress: Callable[[str], None] | None = None,
) -> Path:
    base = root or kokoro_root()
    base.mkdir(parents=True, exist_ok=True)
    _ensure_espeak_data(base)
    for spec in KOKORO_FILES:
        target = base / spec.name
        if not force and _size_ok(target, spec) and _sha256(target) == spec.sha256:
            if on_progress:
                on_progress(f"{spec.name}: listo")
            continue
        if on_progress:
            on_progress(f"{spec.name}: descargando {spec.size // (1024 * 1024)} MB")
        _download(spec, target)
        if on_progress:
            on_progress(f"{spec.name}: verificado")
    if not kokoro_ready(base):
        raise KokoroNotConfigured(f"Kokoro assets are incomplete in {base}")
    return base


def _ensure_espeak_data(base: Path) -> None:
    target = base / ESPEAK_DIR
    if (target / "phontab").is_file():
        return
    try:
        import espeakng_loader
    except ImportError as exc:
        raise KokoroNotConfigured("espeakng-loader is not installed") from exc
    source = Path(espeakng_loader.get_data_path())
    if not (source / "phontab").is_file():
        raise KokoroNotConfigured(f"Bundled espeak-ng data is incomplete: {source}")
    target.mkdir(parents=True, exist_ok=True)
    for item in source.iterdir():
        destination = target / item.name
        if item.is_dir():
            _copy_tree(item, destination)
        elif item.is_file() and not destination.exists():
            destination.write_bytes(item.read_bytes())


def _copy_tree(source: Path, target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    for item in source.iterdir():
        destination = target / item.name
        if item.is_dir():
            _copy_tree(item, destination)
        elif item.is_file() and not destination.exists():
            destination.write_bytes(item.read_bytes())


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _download(spec: KokoroFile, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f"{target.name}.{os.getpid()}.part")
    digest = hashlib.sha256()
    received = 0
    try:
        try:
            with requests.get(spec.url, stream=True, timeout=(15, 180)) as response:
                response.raise_for_status()
                with temporary.open("wb") as handle:
                    for block in response.iter_content(chunk_size=1024 * 1024):
                        if not block:
                            continue
                        handle.write(block)
                        digest.update(block)
                        received += len(block)
        except requests.RequestException as exc:
            raise KokoroNotConfigured(f"Could not download {spec.name}: {exc}") from exc
        if received != spec.size or digest.hexdigest() != spec.sha256:
            raise KokoroNotConfigured(
                f"Downloaded file does not match the manifest: {spec.name} "
                f"({received} bytes, sha256 {digest.hexdigest()})"
            )
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
