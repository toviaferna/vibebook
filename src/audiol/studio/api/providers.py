from __future__ import annotations

import requests
from fastapi import APIRouter, Response

from audiol.provider_keys import (
    PROVIDERS,
    delete_provider_key,
    get_provider_key,
    get_provider_region,
    list_provider_status,
    set_provider_key,
)
from audiol.studio.errors import ApiError
from audiol.studio.models import (
    ProviderKeyRequest,
    ProviderListResponse,
    ProviderStatusResponse,
    ProviderTestResponse,
)

router = APIRouter(tags=["providers"])

GEMINI_MODELS_URL = "https://generativelanguage.googleapis.com/v1beta/models"
ELEVENLABS_API = "https://api.elevenlabs.io/v1"
ELEVENLABS_PROBE_VOICE = "pNInz6obpgDQGcFmaJgB"
AZURE_TOKEN_URL = "https://{region}.api.cognitive.microsoft.com/sts/v1.0/issueToken"


def _provider(provider_id: str) -> dict[str, object]:
    if provider_id not in PROVIDERS:
        raise ApiError(404, "provider_not_found", "El proveedor no existe.")
    return PROVIDERS[provider_id]


@router.get("/providers", response_model=ProviderListResponse)
def get_providers() -> ProviderListResponse:
    return ProviderListResponse(
        items=[ProviderStatusResponse.model_validate(item) for item in list_provider_status()]
    )


@router.put("/providers/{provider_id}", response_model=ProviderStatusResponse)
def save_provider(provider_id: str, payload: ProviderKeyRequest) -> ProviderStatusResponse:
    _provider(provider_id)
    try:
        set_provider_key(provider_id, payload.api_key, payload.region)
    except ValueError as exc:
        raise ApiError(422, "invalid_provider_key", str(exc)) from exc
    return ProviderStatusResponse.model_validate(
        next(item for item in list_provider_status() if item["id"] == provider_id)
    )


@router.delete("/providers/{provider_id}", status_code=204, response_model=None)
def remove_provider(provider_id: str) -> Response:
    _provider(provider_id)
    delete_provider_key(provider_id)
    return Response(status_code=204)


@router.post("/providers/{provider_id}/test", response_model=ProviderTestResponse)
def test_provider(provider_id: str) -> ProviderTestResponse:
    _provider(provider_id)
    key = get_provider_key(provider_id)
    if not key:
        return ProviderTestResponse(ok=False, message="La clave todavía no está configurada.")
    if provider_id == "gemini":
        return _test_gemini(key)
    if provider_id == "elevenlabs":
        return _test_elevenlabs(key)
    if provider_id == "azure":
        region = get_provider_region(provider_id)
        if not region:
            return ProviderTestResponse(ok=False, message="Falta la región de Azure.")
        return _test_azure(key, region)
    return ProviderTestResponse(ok=False, message="Proveedor sin prueba disponible.")


def _test_gemini(key: str) -> ProviderTestResponse:
    try:
        response = requests.get(
            GEMINI_MODELS_URL,
            headers={"x-goog-api-key": key},
            timeout=20,
        )
    except requests.RequestException as exc:
        return ProviderTestResponse(ok=False, message=f"No se pudo conectar: {exc}")
    if response.status_code != 200:
        return ProviderTestResponse(ok=False, message=_http_message(response, "Gemini"))
    names = {
        str(model.get("name", "")).removeprefix("models/")
        for model in response.json().get("models", [])
        if isinstance(model, dict)
    }
    if "gemini-3.8-flash-tts" not in names:
        return ProviderTestResponse(
            ok=False,
            message="La clave funciona, pero no tiene acceso a gemini-3.8-flash-tts.",
        )
    return ProviderTestResponse(ok=True, message="Conectado. Gemini 3.8 Flash TTS disponible.")


def _test_elevenlabs(key: str) -> ProviderTestResponse:
    try:
        response = requests.get(
            f"{ELEVENLABS_API}/user/subscription",
            headers={"xi-api-key": key},
            timeout=20,
        )
    except requests.RequestException as exc:
        return ProviderTestResponse(ok=False, message=f"No se pudo conectar: {exc}")
    if response.status_code == 200:
        data = response.json()
        used = _int(data.get("character_count"))
        limit = _int(data.get("character_limit"))
        remaining = limit - used if limit is not None and used is not None else None
        message = "Conectado."
        if remaining is not None:
            message = f"Conectado · {remaining:,} créditos restantes."
        return ProviderTestResponse(
            ok=True,
            message=message,
            credits_used=used,
            credits_limit=limit,
        )
    data = _deserialize(response)
    detail = data.get("detail") if isinstance(data, dict) else None
    code = detail.get("code") if isinstance(detail, dict) else None
    status = detail.get("status") if isinstance(detail, dict) else None
    if response.status_code == 401 and "missing_permissions" in {code, status}:
        probe = _probe_elevenlabs(key)
        if probe.ok:
            probe.warning = (
                "La clave sirve para TTS, pero no tiene permisos user_read/voices_read: "
                "no se puede leer el saldo ni listar voces."
            )
        return probe
    if response.status_code == 401:
        return ProviderTestResponse(ok=False, message="La clave de ElevenLabs no es válida.")
    return ProviderTestResponse(ok=False, message=_http_message(response, "ElevenLabs"))


def _probe_elevenlabs(key: str) -> ProviderTestResponse:
    try:
        response = requests.post(
            f"{ELEVENLABS_API}/text-to-speech/{ELEVENLABS_PROBE_VOICE}",
            json={"text": "Hola.", "model_id": "eleven_turbo_v2_5"},
            headers={"xi-api-key": key, "Accept": "audio/mpeg"},
            timeout=30,
        )
    except requests.RequestException as exc:
        return ProviderTestResponse(ok=False, message=f"No se pudo conectar: {exc}")
    if response.status_code == 200:
        return ProviderTestResponse(
            ok=True,
            message="Conectado para TTS. No se pudo leer el saldo por permisos de la clave.",
        )
    if response.status_code == 402:
        return ProviderTestResponse(
            ok=False,
            message=(
                "La clave conecta, pero tu plan no permite voces de biblioteca por API. "
                "Usá Adam, Antoni, Arnold o Bella, o cambiá de plan."
            ),
        )
    return ProviderTestResponse(
        ok=False,
        message=_http_message(response, "ElevenLabs"),
    )


def _test_azure(key: str, region: str) -> ProviderTestResponse:
    try:
        response = requests.post(
            AZURE_TOKEN_URL.format(region=region),
            headers={"Ocp-Apim-Subscription-Key": key},
            timeout=20,
        )
    except requests.RequestException as exc:
        return ProviderTestResponse(ok=False, message=f"No se pudo conectar: {exc}")
    if response.status_code == 200 and response.text.strip():
        return ProviderTestResponse(ok=True, message="Conectado. Azure Speech emitió un token.")
    return ProviderTestResponse(ok=False, message=_http_message(response, "Azure"))


def _deserialize(response: requests.Response) -> object:
    try:
        return response.json()
    except ValueError:
        return {}


def _http_message(response: requests.Response, provider: str) -> str:
    data = _deserialize(response)
    if isinstance(data, dict):
        detail = data.get("detail")
        if isinstance(detail, dict) and detail.get("message"):
            return str(detail["message"])
        if isinstance(detail, str):
            return detail
        error = data.get("error")
        if isinstance(error, dict) and error.get("message"):
            return str(error["message"])
    return f"{provider} devolvió HTTP {response.status_code}."


def _int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None
