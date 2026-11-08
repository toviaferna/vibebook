from __future__ import annotations

import base64
import os
from typing import Any
from uuid import uuid4

import httpx

from audiol.ambience.library import AmbienceLibrary
from audiol.ambience.models import SoundAssetCreate

PROTOCOL = "vep-sound/1"


class PluginSoundError(RuntimeError):
    pass


class PluginSoundProvider:
    def __init__(
        self,
        base_url: str | None = None,
        token: str | None = None,
        timeout: float = 30,
        client: httpx.Client | None = None,
    ) -> None:
        self.base_url = (base_url or "").rstrip("/")
        self.token = token or ""
        self.client = client or httpx.Client(timeout=timeout)

    @classmethod
    def from_env(cls, client: httpx.Client | None = None) -> PluginSoundProvider:
        return cls(
            os.environ.get("VIBEBOOK_AMBIENCE_PLUGIN_URL", ""),
            os.environ.get("VIBEBOOK_AMBIENCE_PLUGIN_TOKEN", ""),
            client=client,
        )

    @property
    def configured(self) -> bool:
        return bool(self.base_url)

    def health(self) -> dict[str, Any]:
        if not self.configured:
            raise PluginSoundError("El plugin de ambiente no está configurado.")
        response = self.client.get(f"{self.base_url}/health", headers=self._headers())
        if response.status_code >= 400:
            raise PluginSoundError(f"El plugin respondió {response.status_code}.")
        payload = response.json()
        if not isinstance(payload, dict):
            raise PluginSoundError("El plugin devolvió un health inválido.")
        return payload

    def generate(
        self,
        prompt: str,
        kind: str = "ambience",
        duration_ms: int = 30_000,
    ) -> tuple[bytes, dict[str, Any]]:
        if not self.configured:
            raise PluginSoundError("El plugin de ambiente no está configurado.")
        response = self.client.post(
            f"{self.base_url}/generate",
            json={"protocol": PROTOCOL, "prompt": prompt, "kind": kind, "duration_ms": duration_ms},
            headers=self._headers(),
        )
        if response.status_code >= 400:
            raise PluginSoundError(f"El plugin respondió {response.status_code}.")
        content_type = response.headers.get("content-type", "")
        if content_type.startswith("audio/"):
            return response.content, {}
        payload = response.json()
        if not isinstance(payload, dict):
            raise PluginSoundError("El plugin devolvió una respuesta inválida.")
        audio = payload.get("audio_base64")
        if isinstance(audio, str):
            try:
                return base64.b64decode(audio), payload
            except ValueError as exc:
                raise PluginSoundError("El audio base64 del plugin es inválido.") from exc
        return b"", payload

    def import_asset(
        self,
        prompt: str,
        library: AmbienceLibrary,
        kind: str = "ambience",
        duration_ms: int = 30_000,
    ) -> dict[str, Any]:
        audio, metadata = self.generate(prompt, kind, duration_ms)
        if not audio:
            raise PluginSoundError("El plugin no devolvió audio.")
        license_name = str(metadata.get("license") or "").strip()
        if not license_name:
            raise PluginSoundError("El plugin no declaró licencia.")
        suffix = ".wav" if metadata.get("format") == "wav" else ".ogg"
        temporary = library.root / f".plugin-{uuid4().hex}{suffix}"
        try:
            temporary.write_bytes(audio)
            return library.import_file(
                temporary,
                SoundAssetCreate(
                    prompt=prompt,
                    kind=kind,  # type: ignore[arg-type]
                    tags=[str(tag) for tag in metadata.get("tags", [])],
                    provider="plugin",
                    model=str(metadata.get("model") or "local-plugin"),
                    seed=metadata.get("seed"),
                    loopable=bool(metadata.get("loopable", False)),
                    license=license_name,
                    attribution=metadata.get("attribution"),
                    source_url=metadata.get("source_url"),
                ),
            )
        finally:
            temporary.unlink(missing_ok=True)

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json, audio/*"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers
