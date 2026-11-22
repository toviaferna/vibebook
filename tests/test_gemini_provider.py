from __future__ import annotations

import base64
import io
import wave
from pathlib import Path

import pytest

from audiol.tts import gemini
from audiol.tts.gemini import GeminiProvider, _audio_block


class FakeResponse:
    def __init__(
        self,
        status_code: int,
        payload: dict | None = None,
        *,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self._payload = payload or {}
        self.headers = headers or {}
        self.text = ""

    def json(self) -> dict:
        return self._payload


def _wav(payload: bytes = b"\x00\x00" * 2400) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(24_000)
        handle.writeframes(payload)
    return buffer.getvalue()


def _audio_response() -> FakeResponse:
    return FakeResponse(
        200,
        {
            "steps": [
                {
                    "type": "model_output",
                    "content": [
                        {
                            "type": "audio",
                            "data": base64.b64encode(_wav()).decode(),
                            "mime_type": "audio/wav",
                        }
                    ],
                }
            ]
        },
    )


def test_gemini_retries_rate_limits_with_retry_after(tmp_path: Path, monkeypatch):
    responses = iter(
        [
            FakeResponse(
                429,
                {"error": {"message": "quota"}},
                headers={"retry-after": "0"},
            ),
            _audio_response(),
        ]
    )
    sleeps: list[float] = []
    calls: list[dict] = []

    def fake_post(url, json, headers, timeout):
        calls.append(json)
        return next(responses)

    monkeypatch.setattr(gemini.requests, "post", fake_post)
    monkeypatch.setattr(gemini.time, "sleep", sleeps.append)

    result = GeminiProvider("key").synthesize("Hola", "Kore", tmp_path / "out.wav")

    assert result.path.is_file()
    assert len(calls) == 2
    assert sleeps == [1.0]


def test_gemini_retries_server_errors_with_backoff(tmp_path: Path, monkeypatch):
    responses = iter(
        [
            FakeResponse(503, {"error": {"message": "unavailable"}}),
            _audio_response(),
        ]
    )
    sleeps: list[float] = []
    monkeypatch.setattr(gemini.requests, "post", lambda *args, **kwargs: next(responses))
    monkeypatch.setattr(gemini.time, "sleep", sleeps.append)

    GeminiProvider("key").synthesize("Hola", "Kore", tmp_path / "out.wav")

    assert sleeps == [2.0]


def test_gemini_gives_up_after_the_attempt_limit(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(
        gemini.requests,
        "post",
        lambda *args, **kwargs: FakeResponse(500, {"error": {"message": "boom"}}),
    )
    monkeypatch.setattr(gemini.time, "sleep", lambda _: None)

    with pytest.raises(RuntimeError, match="boom"):
        GeminiProvider("key").synthesize("Hola", "Kore", tmp_path / "out.wav")


def test_gemini_raises_friendly_client_errors(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(
        gemini.requests,
        "post",
        lambda *args, **kwargs: FakeResponse(400, {"error": {"message": "bad voice"}}),
    )

    with pytest.raises(ValueError, match="bad voice"):
        GeminiProvider("key").synthesize("Hola", "Kore", tmp_path / "out.wav")


def test_gemini_rejects_invalid_json(tmp_path: Path, monkeypatch):
    class BadJson(FakeResponse):
        def json(self) -> dict:
            raise ValueError("not json")

    monkeypatch.setattr(gemini.requests, "post", lambda *args, **kwargs: BadJson(200))

    with pytest.raises(RuntimeError, match="invalid JSON"):
        GeminiProvider("key").synthesize("Hola", "Kore", tmp_path / "out.wav")


def test_gemini_neutral_style_has_no_annotations(tmp_path: Path, monkeypatch):
    captured: dict = {}

    def fake_post(url, json, headers, timeout):
        captured.update(json)
        return _audio_response()

    monkeypatch.setattr(gemini.requests, "post", fake_post)
    GeminiProvider("key").synthesize("Hola", "Kore", tmp_path / "out.wav")

    content = captured["input"][0]["content"][0]
    assert "annotations" not in content


def test_gemini_applies_rate_with_ffmpeg(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(gemini.requests, "post", lambda *args, **kwargs: _audio_response())
    output = tmp_path / "out.wav"

    GeminiProvider("key").synthesize("Hola", "Kore", output, rate="+10%")

    assert output.read_bytes()[:4] == b"RIFF"
    assert output.stat().st_size > 0


def test_audio_block_accepts_output_audio_and_keeps_known_format():
    raw = b"OggS" + b"\x00" * 20
    audio = _audio_block(
        {
            "output_audio": {
                "data": base64.b64encode(raw).decode(),
                "mimeType": "audio/ogg",
            }
        }
    )

    assert audio == raw


def test_audio_block_wraps_raw_pcm_from_candidates():
    payload = b"\x01\x00" * 240
    audio = _audio_block(
        {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "inlineData": {
                                    "data": base64.b64encode(payload).decode(),
                                    "mimeType": "audio/l16",
                                }
                            }
                        ]
                    }
                }
            ]
        }
    )

    assert audio is not None
    assert audio[:4] == b"RIFF"
    with wave.open(io.BytesIO(audio), "rb") as handle:
        assert handle.getnframes() == 240
        assert handle.getframerate() == 24_000


def test_audio_block_rejects_invalid_base64():
    with pytest.raises(RuntimeError, match="invalid base64"):
        _audio_block({"output_audio": {"data": "!!!not-base64!!!"}})


def test_audio_block_returns_none_without_audio():
    assert _audio_block({"steps": []}) is None
    assert _audio_block({"steps": [{"content": [{"type": "text"}]}]}) is None
