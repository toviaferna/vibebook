from __future__ import annotations

import contextlib
import json
import logging
import os
import shutil
import tempfile
import threading
import time
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from audiol.tts.base import TTSProvider
from audiol.tts.plugin import (
    PluginError,
    PluginInfo,
    PluginProvider,
    PluginVoiceSpec,
    fetch_plugin_health,
    fetch_plugin_info,
    fetch_plugin_voices,
    normalize_plugin_url,
)
from audiol.tts.registry import ENGINES
from audiol.tts.registry import make_provider as make_builtin_provider

logger = logging.getLogger(__name__)


class PluginNotFound(PluginError):
    pass


class PluginRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    info: PluginInfo
    url: str
    enabled: bool = True
    added_at: str
    updated_at: str


class PluginListFile(BaseModel):
    model_config = ConfigDict(extra="ignore")

    items: list[PluginRecord] = Field(default_factory=list)


class PluginRegistry:
    def __init__(self, directory: Path, allow_local: bool = False) -> None:
        self.directory = directory
        self.manifests_path = directory / "plugins.json"
        self.secrets_path = directory / "secrets.json"
        self.allow_local = allow_local
        self._lock = threading.RLock()
        self._records: dict[str, PluginRecord] = {}
        self._secrets: dict[str, str] = {}
        self._corrupt = False
        self._load()

    def records(self) -> list[PluginRecord]:
        with self._lock:
            return sorted(self._records.values(), key=lambda record: record.info.name.lower())

    def has(self, plugin_id: str) -> bool:
        with self._lock:
            return plugin_id in self._records

    def get(self, plugin_id: str) -> PluginRecord:
        with self._lock:
            try:
                return self._records[plugin_id]
            except KeyError as exc:
                raise PluginNotFound(f"Unknown plugin: {plugin_id}") from exc

    def token(self, plugin_id: str) -> str | None:
        with self._lock:
            return self._secrets.get(plugin_id)

    def has_token(self, plugin_id: str) -> bool:
        return self.token(plugin_id) is not None

    def add(self, url: str, token: str | None = None) -> PluginRecord:
        normalized = normalize_plugin_url(url, allow_local=self.allow_local)
        token = token.strip() if token else None
        info = fetch_plugin_info(normalized, token=token, allow_local=self.allow_local)
        if info.id in ENGINES:
            raise PluginError(f"The plugin id {info.id} is reserved by a built-in engine")
        with self._lock:
            existing = self._records.get(info.id)
            if existing is not None and existing.url != normalized:
                raise PluginError(f"The plugin id {info.id} is already registered with another URL")
            now = _now()
            record = PluginRecord(
                info=info,
                url=normalized,
                enabled=True,
                added_at=existing.added_at if existing else now,
                updated_at=now,
            )
            self._records[info.id] = record
            if token is not None:
                self._secrets[info.id] = token
            self._save()
            return record

    def remove(self, plugin_id: str) -> None:
        with self._lock:
            if plugin_id not in self._records:
                raise PluginNotFound(f"Unknown plugin: {plugin_id}")
            del self._records[plugin_id]
            self._secrets.pop(plugin_id, None)
            self._save()

    def update_config(
        self,
        plugin_id: str,
        token: str | None = None,
        enabled: bool | None = None,
    ) -> PluginRecord:
        with self._lock:
            record = self.get(plugin_id)
            if token is not None:
                cleaned = token.strip()
                if cleaned:
                    self._secrets[plugin_id] = cleaned
                else:
                    self._secrets.pop(plugin_id, None)
            if enabled is not None:
                record = record.model_copy(update={"enabled": enabled, "updated_at": _now()})
                self._records[plugin_id] = record
            self._save()
            return record

    def refresh(self, plugin_id: str) -> PluginRecord:
        record = self.get(plugin_id)
        info = fetch_plugin_info(
            record.url, token=self.token(plugin_id), allow_local=self.allow_local
        )
        with self._lock:
            current = self.get(plugin_id)
            updated = current.model_copy(update={"info": info, "updated_at": _now()})
            self._records[plugin_id] = updated
            self._save()
            return updated

    def voices(self, plugin_id: str) -> list[PluginVoiceSpec]:
        return list(self.get(plugin_id).info.voices)

    def make_provider(self, engine: str, allow_fake: bool = False) -> TTSProvider:
        if engine in ENGINES:
            return make_builtin_provider(engine, allow_fake=allow_fake)
        record = self.get(engine)
        if not record.enabled:
            raise PluginError(f"The plugin {engine} is disabled")
        return PluginProvider(
            record.url,
            token=self.token(engine),
            timeout=record.info.limits.timeout_seconds,
            max_chars=record.info.limits.max_chars,
            allow_local=self.allow_local,
        )

    def test(self, plugin_id: str) -> dict:
        record = self.get(plugin_id)
        started = time.perf_counter()
        health = fetch_plugin_health(
            record.url, token=self.token(plugin_id), allow_local=self.allow_local
        )
        if health.get("ok") is False:
            raise PluginError("The plugin health check failed")
        voices = fetch_plugin_voices(
            record.url, token=self.token(plugin_id), allow_local=self.allow_local
        )
        if not voices:
            raise PluginError("The plugin does not expose any voices")
        provider = self.make_provider(plugin_id)
        with tempfile.TemporaryDirectory(prefix="vibebook-plugin-test-") as temporary:
            provider.synthesize(
                "Hola. Esta es una prueba del plugin.",
                voices[0].id,
                Path(temporary) / "test.wav",
                rate="+0%",
            )
        return {
            "ok": True,
            "latency_ms": int((time.perf_counter() - started) * 1000),
            "voice_count": len(voices),
            "message": "Plugin disponible y síntesis correcta.",
        }

    def _load(self) -> None:
        if self.manifests_path.is_file():
            try:
                payload = json.loads(self.manifests_path.read_text(encoding="utf-8"))
                self._records = {
                    record.info.id: record
                    for record in PluginListFile.model_validate(payload).items
                }
            except (OSError, ValueError):
                logger.warning("Could not read plugin manifests", exc_info=True)
                self._backup_corrupt(self.manifests_path)
                self._corrupt = True
                self._records = {}
        if self.secrets_path.is_file():
            try:
                payload = json.loads(self.secrets_path.read_text(encoding="utf-8"))
                if isinstance(payload, dict):
                    self._secrets = {
                        str(key): str(value)
                        for key, value in payload.items()
                        if isinstance(value, str)
                    }
            except (OSError, ValueError):
                logger.warning("Could not read plugin secrets", exc_info=True)
                self._backup_corrupt(self.secrets_path)
                self._corrupt = True
                self._secrets = {}

    def _backup_corrupt(self, path: Path) -> None:
        stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S-%f")
        target = path.with_name(f"{path.name}.corrupt-{stamp}")
        try:
            shutil.copy2(path, target)
        except OSError:
            logger.warning("Could not back up the corrupt plugin file %s", path, exc_info=True)

    def _save(self) -> None:
        if self._corrupt:
            raise PluginError(
                "The plugin registry is corrupt; fix or remove the .corrupt backup before saving"
            )
        self.directory.mkdir(parents=True, exist_ok=True)
        _write_json(
            self.manifests_path,
            PluginListFile(items=list(self._records.values())).model_dump(mode="json"),
        )
        _write_json(self.secrets_path, self._secrets, private=True)


def _write_json(path: Path, payload: dict | list, private: bool = False) -> None:
    temporary = path.with_name(f"{path.name}.{os.getpid()}.part")
    try:
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, path)
        if private:
            with contextlib.suppress(OSError):
                path.chmod(0o600)
    finally:
        temporary.unlink(missing_ok=True)


def _now() -> str:
    return datetime.now(UTC).isoformat()
