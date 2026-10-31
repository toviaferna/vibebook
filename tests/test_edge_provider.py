from pathlib import Path

import pytest

from audiol.tts.edge import EdgeProvider


class FakeCommunicate:
    last = None

    def __init__(self, text: str, voice: str, **kwargs) -> None:
        self.text = text
        self.voice = voice
        self.rate = kwargs.get("rate")
        FakeCommunicate.last = self

    async def stream(self):
        yield {"type": "audio", "data": b"ID3fake-audio"}
        yield {
            "type": "WordBoundary",
            "text": "Hola",
            "offset": 1_000_000,
            "duration": 5_000_000,
        }


def test_edge_provider_writes_audio(monkeypatch, tmp_path: Path):
    monkeypatch.setattr("audiol.tts.edge.edge_tts.Communicate", FakeCommunicate)
    output = tmp_path / "sample.mp3"

    result = EdgeProvider().synthesize(
        "Hola", "es-MX-JorgeNeural", output, rate="-6%"
    )

    assert result.path == output
    assert output.read_bytes() == b"ID3fake-audio"
    assert result.word_boundaries[0]["text"] == "Hola"
    assert FakeCommunicate.last.rate == "-6%"


def test_edge_provider_rejects_empty_text():
    with pytest.raises(ValueError):
        EdgeProvider().synthesize("   ", "es-MX-JorgeNeural", Path("x.mp3"))


def test_edge_provider_rejects_invalid_rate():
    with pytest.raises(ValueError):
        EdgeProvider().synthesize(
            "Hola", "es-MX-JorgeNeural", Path("x.mp3"), rate="fast"
        )


def test_edge_provider_paces_requests(monkeypatch, tmp_path: Path):
    sleeps: list[float] = []
    monkeypatch.setattr("audiol.tts.edge.time.monotonic", lambda: 0.0)
    monkeypatch.setattr(
        "audiol.tts.edge.time.sleep", lambda seconds: sleeps.append(seconds)
    )
    monkeypatch.setattr("audiol.tts.edge.edge_tts.Communicate", FakeCommunicate)
    provider = EdgeProvider()

    provider.synthesize("Hola", "es-MX-JorgeNeural", tmp_path / "a.mp3")
    provider.synthesize("Hola", "es-MX-JorgeNeural", tmp_path / "b.mp3")

    assert provider.request_delay == 1.0
    assert sleeps == [1.0]
