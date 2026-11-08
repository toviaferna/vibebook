import base64
import importlib.util
import io
import wave
from pathlib import Path

from fastapi.testclient import TestClient

TEMPLATE = Path(__file__).resolve().parents[1] / "examples" / "plugin-template" / "server.py"


def _load_template():
    spec = importlib.util.spec_from_file_location("vibebook_vep_template", TEMPLATE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_plugin_template_implements_vep_contract():
    module = _load_template()
    client = TestClient(module.app)

    info = client.get("/v1/info")
    assert info.status_code == 200
    assert info.json()["protocol"] == "vep/1"
    assert info.json()["id"] == "demo-sine"
    assert info.json()["voices"][0]["id"] == "es-MX-demo"

    assert client.get("/v1/health").json() == {"ok": True}
    assert client.get("/v1/voices").json()["voices"][0]["id"] == "es-MX-demo"

    response = client.post(
        "/v1/synthesize",
        json={"text": "Hola", "voice": "es-MX-demo", "format": "wav"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["format"] == "wav"
    assert body["duration_ms"] == 400
    audio = base64.b64decode(body["audio_base64"])
    with wave.open(io.BytesIO(audio), "rb") as wav:
        assert wav.getnframes() > 0


def test_plugin_template_uses_vep_error_shape():
    module = _load_template()
    client = TestClient(module.app)

    response = client.post(
        "/v1/synthesize",
        json={"text": "Hola", "voice": "nope", "format": "wav"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "unknown_voice"
