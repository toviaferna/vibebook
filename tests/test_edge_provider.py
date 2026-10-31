from pathlib import Path

import pytest

from audiol.tts.edge import EdgeProvider


class FakeCommunicate:
    def __init__(self, text: str, voice: str, **kwargs) -> None:
        self.text = text
        self.voice = voice

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

    result = EdgeProvider().synthesize("Hola", "es-MX-JorgeNeural", output)

    assert result.path == output
    assert output.read_bytes() == b"ID3fake-audio"
    assert result.word_boundaries[0]["text"] == "Hola"


def test_edge_provider_rejects_empty_text():
    with pytest.raises(ValueError):
        EdgeProvider().synthesize("   ", "es-MX-JorgeNeural", Path("x.mp3"))
