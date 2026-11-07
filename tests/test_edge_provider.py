from pathlib import Path

import edge_tts
import pytest

from audiol.tts.edge import EdgeProvider


class FakeCommunicate:
    last = None

    def __init__(self, text: str, voice: str, **kwargs) -> None:
        self.text = text
        self.voice = voice
        self.rate = kwargs.get("rate")
        self.boundary = kwargs.get("boundary")
        FakeCommunicate.last = self

    async def stream(self):
        yield {"type": "audio", "data": b"ID3fake-audio"}


def test_edge_provider_writes_audio(monkeypatch, tmp_path: Path):
    monkeypatch.setattr("audiol.tts.edge.edge_tts.Communicate", FakeCommunicate)
    output = tmp_path / "sample.mp3"

    result = EdgeProvider().synthesize("Hola", "es-MX-JorgeNeural", output, rate="-6%")

    assert result.path == output
    assert output.read_bytes() == b"ID3fake-audio"
    assert FakeCommunicate.last.rate == "-6%"
    assert FakeCommunicate.last.boundary == "WordBoundary"
    assert result.words == []


def test_edge_provider_collects_word_boundaries(monkeypatch, tmp_path: Path):
    class BoundariesCommunicate(FakeCommunicate):
        async def stream(self):
            yield {"type": "audio", "data": b"ID3fake-audio"}
            yield {
                "type": "WordBoundary",
                "offset": 0,
                "duration": 3_000_000,
                "text": "Hola",
            }
            yield {
                "type": "WordBoundary",
                "offset": 3_000_000,
                "duration": 2_000_000,
                "text": "mundo",
            }

    monkeypatch.setattr("audiol.tts.edge.edge_tts.Communicate", BoundariesCommunicate)
    output = tmp_path / "sample.mp3"

    result = EdgeProvider().synthesize("Hola mundo", "es-MX-JorgeNeural", output)

    assert [(word.text, word.start_ms, word.end_ms) for word in result.words] == [
        ("Hola", 0, 300),
        ("mundo", 300, 500),
    ]


def test_edge_provider_rejects_empty_text():
    with pytest.raises(ValueError):
        EdgeProvider().synthesize("   ", "es-MX-JorgeNeural", Path("x.mp3"))


def test_edge_provider_rejects_invalid_rate():
    with pytest.raises(ValueError):
        EdgeProvider().synthesize("Hola", "es-MX-JorgeNeural", Path("x.mp3"), rate="fast")


def test_edge_provider_cools_down_without_audio(monkeypatch, tmp_path: Path):
    calls: list[int] = []
    sleeps: list[float] = []
    output = tmp_path / "sample.mp3"

    async def fake_stream(self, text, voice, out_path, rate):
        calls.append(1)
        if len(calls) < 3:
            raise edge_tts.exceptions.NoAudioReceived("no audio")
        out_path.write_bytes(b"ID3fake-audio")

    monkeypatch.setattr("audiol.tts.edge.EdgeProvider._stream", fake_stream)
    monkeypatch.setattr("audiol.tts.edge.time.sleep", lambda seconds: sleeps.append(seconds))

    result = EdgeProvider().synthesize("Hola", "es-MX-JorgeNeural", output)

    assert result.path == output
    assert output.read_bytes() == b"ID3fake-audio"
    assert sleeps == [60.0, 120.0]


def test_edge_provider_raises_after_cooldowns(monkeypatch, tmp_path: Path):
    sleeps: list[float] = []
    output = tmp_path / "sample.mp3"

    async def fake_stream(self, text, voice, out_path, rate):
        raise edge_tts.exceptions.NoAudioReceived("no audio")

    monkeypatch.setattr("audiol.tts.edge.EdgeProvider._stream", fake_stream)
    monkeypatch.setattr("audiol.tts.edge.time.sleep", lambda seconds: sleeps.append(seconds))

    with pytest.raises(edge_tts.exceptions.NoAudioReceived):
        EdgeProvider().synthesize("Hola", "es-MX-JorgeNeural", output)

    assert not output.exists()
    assert sleeps == [60.0, 120.0, 240.0, 480.0]


def test_edge_provider_paces_requests(monkeypatch, tmp_path: Path):
    sleeps: list[float] = []
    monkeypatch.setattr("audiol.tts.edge.time.monotonic", lambda: 0.0)
    monkeypatch.setattr("audiol.tts.edge.time.sleep", lambda seconds: sleeps.append(seconds))
    monkeypatch.setattr("audiol.tts.edge.edge_tts.Communicate", FakeCommunicate)
    provider = EdgeProvider()

    provider.synthesize("Hola", "es-MX-JorgeNeural", tmp_path / "a.mp3")
    provider.synthesize("Hola", "es-MX-JorgeNeural", tmp_path / "b.mp3")

    assert provider.request_delay == 1.0
    assert sleeps == [1.0]
