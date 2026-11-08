from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx

from audiol.ambience.library import AmbienceLibrary
from audiol.ambience.models import SoundAssetCreate

FREESOUND_API = "https://freesound.org/apiv2"
CC0_FILTER = "license:Creative Commons 0"


class FreesoundError(RuntimeError):
    pass


@dataclass(frozen=True)
class FreesoundResult:
    id: int
    name: str
    preview_url: str
    license: str
    attribution: str
    source_url: str
    duration_ms: int
    tags: list[str]


class FreesoundProvider:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = FREESOUND_API,
        client: httpx.Client | None = None,
    ) -> None:
        self.api_key = api_key or ""
        self.base_url = base_url.rstrip("/")
        self.client = client or httpx.Client(timeout=20)

    @classmethod
    def from_env(cls, client: httpx.Client | None = None) -> FreesoundProvider:
        return cls(os.environ.get("FREESOUND_API_KEY", ""), client=client)

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def search(
        self,
        query: str,
        limit: int = 10,
        license_filter: str = CC0_FILTER,
    ) -> list[FreesoundResult]:
        if not self.configured:
            raise FreesoundError("FREESOUND_API_KEY no está configurada.")
        response = self.client.get(
            f"{self.base_url}/search/text/",
            params={
                "query": query,
                "filter": license_filter,
                "fields": "id,name,previews,license,username,description,tags,duration",
                "page_size": min(max(limit, 1), 50),
            },
            headers={"Authorization": f"Token {self.api_key}"},
        )
        if response.status_code >= 400:
            raise FreesoundError(f"Freesound respondió {response.status_code}.")
        payload = response.json()
        results: list[FreesoundResult] = []
        for item in payload.get("results", []):
            if not isinstance(item, dict):
                continue
            previews = item.get("previews") or {}
            preview = (
                previews.get("preview-hq-mp3")
                or previews.get("preview-lq-mp3")
                or previews.get("preview-hq-ogg")
            )
            if not preview:
                continue
            license_name = str(item.get("license") or "")
            results.append(
                FreesoundResult(
                    id=int(item.get("id", 0)),
                    name=str(item.get("name") or "freesound"),
                    preview_url=str(preview),
                    license=license_name,
                    attribution=(
                        f"{item.get('name') or 'Freesound'} by "
                        f"{item.get('username') or 'unknown'} (Freesound)"
                    ),
                    source_url=f"https://freesound.org/s/{item.get('id')}/",
                    duration_ms=round(float(item.get("duration") or 0) * 1000),
                    tags=[str(tag) for tag in item.get("tags", [])],
                )
            )
        return results

    def import_asset(
        self,
        result: FreesoundResult,
        library: AmbienceLibrary,
        prompt: str | None = None,
    ) -> dict[str, Any]:
        if not result.license:
            raise FreesoundError("El sonido no declara licencia.")
        response = self.client.get(result.preview_url)
        if response.status_code >= 400 or not response.content:
            raise FreesoundError("No se pudo descargar el preview de Freesound.")
        suffix = _suffix(result.preview_url)
        temporary = library.root / f".freesound-{uuid4().hex}{suffix}"
        try:
            temporary.write_bytes(response.content)
            return library.import_file(
                temporary,
                SoundAssetCreate(
                    prompt=prompt or result.name,
                    kind="ambience",
                    tags=result.tags,
                    provider="freesound",
                    model="freesound",
                    loopable=False,
                    license=result.license,
                    attribution=result.attribution,
                    source_url=result.source_url,
                ),
            )
        finally:
            temporary.unlink(missing_ok=True)


def _suffix(url: str) -> str:
    path = url.split("?", 1)[0]
    suffix = Path(path).suffix.lower()
    return suffix if suffix in {".mp3", ".ogg", ".wav", ".m4a"} else ".mp3"
