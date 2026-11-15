from __future__ import annotations

import json
import os
import threading
from pathlib import Path

from platformdirs import user_data_path

PROVIDERS: dict[str, dict[str, object]] = {
    "gemini": {
        "label": "Google Gemini TTS",
        "description": (
            "Emociones y estilo por instrucción; audio WAV. Requiere clave de Google AI Studio."
        ),
        "docs_url": "https://ai.google.dev/gemini-api/docs/speech-generation",
        "key_url": "https://aistudio.google.com/apikey",
        "requires_region": False,
    },
    "elevenlabs": {
        "label": "ElevenLabs",
        "description": (
            "Timings exactos por carácter y etiquetas emocionales. 10.000 créditos ≈ 10 minutos."
        ),
        "docs_url": "https://elevenlabs.io/docs/api-reference/text-to-speech",
        "key_url": "https://elevenlabs.io/app/settings/api-keys",
        "requires_region": False,
    },
    "azure": {
        "label": "Azure Speech",
        "description": "Estilos de emoción por voz y word boundaries. Requiere clave y región.",
        "docs_url": "https://learn.microsoft.com/azure/ai-services/speech-service/",
        "key_url": "https://portal.azure.com",
        "requires_region": True,
    },
}

_ENV_KEYS = {
    "gemini": ("GEMINI_API_KEY", "GOOGLE_API_KEY"),
    "elevenlabs": ("ELEVENLABS_API_KEY",),
    "azure": ("AZURE_SPEECH_KEY",),
}
_ENV_REGIONS = {"azure": ("AZURE_SPEECH_REGION",)}
_LOCK = threading.RLock()


def provider_keys_path() -> Path:
    configured = os.environ.get("VIBEBOOK_PROVIDER_KEYS")
    if configured:
        return Path(configured).expanduser()
    return user_data_path("vibebook") / "provider-keys.json"


def provider_metadata(provider: str) -> dict[str, object]:
    try:
        return PROVIDERS[provider]
    except KeyError as exc:
        raise ValueError(f"Unknown provider: {provider}") from exc


def _load() -> dict[str, dict[str, str]]:
    path = provider_keys_path()
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(payload, dict):
        return {}
    result: dict[str, dict[str, str]] = {}
    for provider, values in payload.items():
        if not isinstance(provider, str) or not isinstance(values, dict):
            continue
        cleaned = {
            key: str(value).strip()
            for key, value in values.items()
            if key in {"api_key", "region"} and isinstance(value, str) and value.strip()
        }
        if cleaned:
            result[provider] = cleaned
    return result


def _save(payload: dict[str, dict[str, str]]) -> None:
    path = provider_keys_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.{os.getpid()}.part")
    try:
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        os.replace(temporary, path)
        if os.name != "nt":
            os.chmod(path, 0o600)
    finally:
        temporary.unlink(missing_ok=True)


def _env_value(provider: str, names: tuple[str, ...]) -> str | None:
    for name in names:
        value = os.environ.get(name)
        if value and value.strip():
            return value.strip()
    return None


def get_provider_key(provider: str) -> str | None:
    provider_metadata(provider)
    from_env = _env_value(provider, _ENV_KEYS.get(provider, ()))
    if from_env:
        return from_env
    with _LOCK:
        values = _load().get(provider, {})
    return values.get("api_key") or None


def get_provider_region(provider: str) -> str | None:
    provider_metadata(provider)
    from_env = _env_value(provider, _ENV_REGIONS.get(provider, ()))
    if from_env:
        return from_env
    with _LOCK:
        values = _load().get(provider, {})
    return values.get("region") or None


def provider_configured(provider: str) -> bool:
    metadata = provider_metadata(provider)
    key = get_provider_key(provider)
    if not key:
        return False
    return not (metadata.get("requires_region") and not get_provider_region(provider))


def provider_source(provider: str) -> str | None:
    if _env_value(provider, _ENV_KEYS.get(provider, ())):
        return "env"
    with _LOCK:
        if _load().get(provider, {}).get("api_key"):
            return "file"
    return None


def provider_hint(provider: str) -> str | None:
    key = get_provider_key(provider)
    if not key:
        return None
    return f"•••• {key[-4:]}" if len(key) > 4 else "••••"


def set_provider_key(provider: str, api_key: str, region: str | None = None) -> None:
    metadata = provider_metadata(provider)
    cleaned = api_key.strip()
    if len(cleaned) < 8:
        raise ValueError("La clave es demasiado corta.")
    if any(character.isspace() for character in cleaned):
        raise ValueError("La clave no puede contener espacios.")
    cleaned_region = (region or "").strip()
    if metadata.get("requires_region") and not cleaned_region:
        raise ValueError("Esta clave necesita una región.")
    with _LOCK:
        payload = _load()
        values = payload.setdefault(provider, {})
        values["api_key"] = cleaned
        if cleaned_region:
            values["region"] = cleaned_region
        elif "region" in values:
            values.pop("region")
        _save(payload)


def delete_provider_key(provider: str) -> None:
    provider_metadata(provider)
    with _LOCK:
        payload = _load()
        payload.pop(provider, None)
        _save(payload)


def provider_status(provider: str) -> dict[str, object]:
    metadata = provider_metadata(provider)
    return {
        "id": provider,
        "label": metadata["label"],
        "description": metadata["description"],
        "docs_url": metadata["docs_url"],
        "key_url": metadata["key_url"],
        "requires_region": metadata["requires_region"],
        "configured": provider_configured(provider),
        "hint": provider_hint(provider),
        "source": provider_source(provider),
        "region": get_provider_region(provider),
    }


def list_provider_status() -> list[dict[str, object]]:
    return [provider_status(provider) for provider in PROVIDERS]
