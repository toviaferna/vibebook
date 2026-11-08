from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from audiol.ambience.models import SoundAssetCreate
from audiol.ambience.procedural import render_bed
from audiol.naming import slugify
from audiol.studio.db import Database
from audiol.tools import find_binary

AUDIO_EXTENSIONS = {".ogg", ".opus", ".mp3", ".wav", ".flac", ".m4a"}
MAX_ASSET_BYTES = 12 * 1024 * 1024


class AmbienceError(RuntimeError):
    pass


class AmbienceLibrary:
    def __init__(self, root: Path, db: Database) -> None:
        self.root = root
        self.assets_dir = root / "assets"
        self.assets_dir.mkdir(parents=True, exist_ok=True)
        self.db = db

    def import_file(self, source: Path, create: SoundAssetCreate) -> dict[str, Any]:
        source = Path(source)
        if not source.is_file():
            raise FileNotFoundError(source)
        suffix = source.suffix.lower()
        if suffix not in AUDIO_EXTENSIONS:
            raise AmbienceError(f"Unsupported audio format: {suffix or 'unknown'}")
        if source.stat().st_size > MAX_ASSET_BYTES:
            raise AmbienceError("The sound asset is too large")
        checksum = _sha256(source)
        existing = self.db.get_sound_asset_by_checksum(checksum)
        if existing is not None:
            return existing
        duration_ms, sample_rate, channels = _probe_audio(source)
        asset_id = f"{create.provider}-{slugify(create.prompt) or 'sound'}-{checksum[:8]}"
        destination = self.assets_dir / f"{asset_id}{suffix}"
        shutil.copy2(source, destination)
        payload = {
            **create.model_dump(),
            "id": asset_id,
            "duration_ms": duration_ms,
            "sample_rate": sample_rate,
            "channels": channels,
            "loudness_lufs": None,
            "checksum": checksum,
            "approved": False,
            "created_at": datetime.now(UTC).isoformat(),
            "last_used_at": None,
            "usage_count": 0,
        }
        self._write_json(asset_id, payload)
        return self.db.upsert_sound_asset(payload)

    def generate_preset(self, preset: str) -> dict[str, Any]:
        temporary = self.root / f".generate-{uuid4().hex}.ogg"
        try:
            render_bed(preset, temporary)
            return self.import_file(
                temporary,
                SoundAssetCreate(
                    prompt=f"{preset} procedural bed",
                    kind="ambience",
                    tags=[preset, "procedural", "loop"],
                    provider="procedural",
                    loopable=True,
                    license="AGPL-3.0",
                    attribution="Generado por Vibebook",
                ),
            )
        finally:
            temporary.unlink(missing_ok=True)

    def generate_all(self) -> list[dict[str, Any]]:
        return [
            self.generate_preset(preset)
            for preset in ("rain", "wind", "sea", "room", "fire", "night")
        ]

    def audio_path(self, asset_id: str) -> Path:
        for path in sorted(self.assets_dir.glob(f"{asset_id}.*")):
            if path.suffix.lower() in AUDIO_EXTENSIONS:
                return path
        raise FileNotFoundError(asset_id)

    def approve(self, asset_id: str) -> dict[str, Any]:
        asset = self.db.set_sound_asset_approved(asset_id, True)
        self._write_json(asset_id, {**asset, "approved": True})
        return asset

    def delete(self, asset_id: str) -> None:
        asset = self.db.get_sound_asset(asset_id)
        if asset is None:
            raise KeyError(asset_id)
        if int(asset.get("usage_count") or 0) > 0:
            raise AmbienceError("The asset is in use and cannot be deleted")
        self.audio_path(asset_id).unlink(missing_ok=True)
        (self.assets_dir / f"{asset_id}.json").unlink(missing_ok=True)
        self.db.delete_sound_asset(asset_id)

    def record_use(self, asset_id: str) -> None:
        self.db.record_sound_asset_use(asset_id)

    def rebuild_index(self) -> int:
        count = 0
        for path in sorted(self.assets_dir.glob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if not isinstance(payload, dict) or "id" not in payload or "checksum" not in payload:
                continue
            self.db.upsert_sound_asset(payload)
            count += 1
        return count

    def _write_json(self, asset_id: str, payload: dict[str, Any]) -> None:
        path = self.assets_dir / f"{asset_id}.json"
        temporary = path.with_name(f"{path.name}.{uuid4().hex}.part")
        try:
            temporary.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)


def _probe_audio(path: Path) -> tuple[int, int, int]:
    ffprobe = find_binary("ffprobe")
    completed = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "stream=sample_rate,channels:format=duration",
            "-of",
            "json",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise AmbienceError(f"Could not read audio metadata: {path.name}")
    try:
        payload = json.loads(completed.stdout)
        stream = payload["streams"][0]
        duration = float(payload["format"]["duration"])
        return (
            max(0, round(duration * 1000)),
            int(stream.get("sample_rate") or 48_000),
            int(stream.get("channels") or 1),
        )
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise AmbienceError(f"Invalid audio metadata: {path.name}") from exc


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
