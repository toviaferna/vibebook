import base64
import io
import wave
from pathlib import Path

import pytest

from audiol.models import WordTiming
from audiol.tts.elevenlabs import ElevenLabsProvider, _alignment_words, _scale_words
from audiol.tts.gemini import GeminiProvider


def _wav(payload: bytes = b"\x00\x00" * 2400) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(24_000)
        handle.writeframes(payload)
    return buffer.getvalue()


class FakeResponse:
    def __init__(self, status_code: int, payload: dict | None = None, text: str = "") -> None:
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text
        self.headers: dict[str, str] = {}

    def json(self) -> dict:
        return self._payload


def test_gemini_requests_style_and_writes_wav(tmp_path: Path, monkeypatch):
    captured: dict = {}
    audio = _wav()

    def fake_post(url, json, headers, timeout):
        captured.update(url=url, json=json, headers=headers, timeout=timeout)
        return FakeResponse(
            200,
            {
                "steps": [
                    {
                        "type": "model_output",
                        "content": [
                            {
                                "type": "audio",
                                "data": base64.b64encode(audio).decode(),
                                "mime_type": "audio/wav",
                            }
                        ],
                    }
                ]
            },
        )

    monkeypatch.setattr("audiol.tts.gemini.requests.post", fake_post)
    output = tmp_path / "gemini.wav"

    result = GeminiProvider("gemini-key").synthesize(
        "La casa olía a sal.", "Kore", output, style="sad"
    )

    assert result.path == output
    assert result.words == []
    assert output.read_bytes() == audio
    assert captured["headers"] == {"x-goog-api-key": "gemini-key"}
    content = captured["json"]["input"][0]["content"][0]
    assert content["text"] == "La casa olía a sal."
    assert content["annotations"][0]["style"].startswith("sad")
    assert captured["json"]["generation_config"]["speech_config"] == [{"voice": "Kore"}]


def test_gemini_needs_a_key(tmp_path: Path):
    with pytest.raises(ValueError, match="API key"):
        GeminiProvider("").synthesize("Hola", "Kore", tmp_path / "out.wav")


def test_elevenlabs_maps_style_and_alignment(tmp_path: Path, monkeypatch):
    captured: dict = {}
    text = "Hola mundo"
    characters = list(text)
    starts = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
    ends = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]

    def fake_post(url, json, headers, timeout):
        captured.update(url=url, json=json, headers=headers, timeout=timeout)
        return FakeResponse(
            200,
            {
                "audio_base64": base64.b64encode(b"ID3fake-audio").decode(),
                "alignment": {
                    "characters": characters,
                    "character_start_times_seconds": starts,
                    "character_end_times_seconds": ends,
                },
            },
        )

    monkeypatch.setattr("audiol.tts.elevenlabs.requests.post", fake_post)
    output = tmp_path / "eleven.mp3"

    result = ElevenLabsProvider("eleven-key").synthesize(
        "Hola mundo", "pNInz6obpgDQGcFmaJgB", output, style="sad"
    )

    assert output.read_bytes() == b"ID3fake-audio"
    assert [(word.text, word.start_ms, word.end_ms) for word in result.words] == [
        ("Hola", 0, 400),
        ("mundo", 500, 1000),
    ]
    assert captured["headers"]["xi-api-key"] == "eleven-key"
    assert captured["json"]["model_id"] == "eleven_v3"
    assert captured["json"]["text"].startswith("[sad]")


def test_elevenlabs_drops_style_tag_from_alignment():
    text = "[sad] Hola mundo"
    starts = [index * 0.1 for index in range(len(text))]
    ends = [(index + 1) * 0.1 for index in range(len(text))]

    words = _alignment_words(
        {
            "characters": list(text),
            "character_start_times_seconds": starts,
            "character_end_times_seconds": ends,
        }
    )

    assert [word.text for word in words] == ["Hola", "mundo"]


def test_elevenlabs_scales_word_times_with_rate():
    words = [WordTiming(text="Hola", start_ms=0, end_ms=900)]

    slower = _scale_words(words, "-10%")
    faster = _scale_words(words, "+10%")

    assert slower[0].end_ms == 1000
    assert faster[0].end_ms == 818


def test_elevenlabs_reports_plan_errors(tmp_path: Path, monkeypatch):
    def fake_post(url, json, headers, timeout):
        return FakeResponse(
            402,
            {"detail": {"message": "Free users cannot use library voices via the API."}},
        )

    monkeypatch.setattr("audiol.tts.elevenlabs.requests.post", fake_post)

    with pytest.raises(ValueError, match="plan de ElevenLabs"):
        ElevenLabsProvider("eleven-key").synthesize(
            "Hola", "pNInz6obpgDQGcFmaJgB", tmp_path / "out.mp3"
        )
