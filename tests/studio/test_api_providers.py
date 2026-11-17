from typing import Any


class FakeResponse:
    def __init__(self, status_code: int, payload: dict[str, Any], text: str = "") -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = text
        self.headers: dict[str, str] = {}

    def json(self) -> dict[str, Any]:
        return self._payload


def test_list_providers_starts_empty(client):
    response = client.get("/api/providers")

    assert response.status_code == 200
    items = response.json()["items"]
    assert [item["id"] for item in items] == ["gemini", "elevenlabs", "azure"]
    assert all(item["configured"] is False for item in items)


def test_save_key_unlocks_the_engine_and_never_returns_it(client):
    response = client.put(
        "/api/providers/gemini",
        json={"api_key": "AQ.super-secret-key-1234"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["configured"] is True
    assert response.json()["hint"] == "•••• 1234"
    assert "AQ.super-secret-key-1234" not in response.text

    engines = client.get("/api/engines").json()["items"]
    gemini = next(item for item in engines if item["id"] == "gemini")
    assert gemini["available"] is True

    removed = client.delete("/api/providers/gemini")
    assert removed.status_code == 204
    assert client.get("/api/providers").json()["items"][0]["configured"] is False


def test_azure_requires_region(client):
    response = client.put("/api/providers/azure", json={"api_key": "azure-key-1234"})

    assert response.status_code == 422
    assert "región" in response.json()["error"]["message"]


def test_gemini_connection_test(client, monkeypatch):
    client.put("/api/providers/gemini", json={"api_key": "AQ.gemini-key-1234"})
    monkeypatch.setattr(
        "audiol.studio.api.providers.requests.get",
        lambda *args, **kwargs: FakeResponse(
            200,
            {"models": [{"name": "models/gemini-3.8-flash-tts"}]},
        ),
    )

    response = client.post("/api/providers/gemini/test")

    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert "Gemini 3.8" in response.json()["message"]


def test_elevenlabs_test_accepts_missing_read_permissions(client, monkeypatch):
    client.put("/api/providers/elevenlabs", json={"api_key": "sk_eleven-key-1234"})
    monkeypatch.setattr(
        "audiol.studio.api.providers.requests.get",
        lambda *args, **kwargs: FakeResponse(
            401,
            {"detail": {"code": "unauthorized", "status": "missing_permissions"}},
        ),
    )
    monkeypatch.setattr(
        "audiol.studio.api.providers.requests.post",
        lambda *args, **kwargs: FakeResponse(200, {}),
    )

    response = client.post("/api/providers/elevenlabs/test")

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True, body
    assert "permisos" in body["warning"]


def test_elevenlabs_test_reads_credits(client, monkeypatch):
    client.put("/api/providers/elevenlabs", json={"api_key": "sk_eleven-key-1234"})
    monkeypatch.setattr(
        "audiol.studio.api.providers.requests.get",
        lambda *args, **kwargs: FakeResponse(
            200,
            {"character_count": 250, "character_limit": 10_000},
        ),
    )

    response = client.post("/api/providers/elevenlabs/test")

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["credits_used"] == 250
    assert body["credits_limit"] == 10_000
    assert "9,750" in body["message"]
