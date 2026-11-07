import wave
from pathlib import Path

from audiol.tts.fake import FakeProvider


def test_fake_provider_writes_wav(tmp_path: Path):
    output = tmp_path / "sample.wav"
    provider = FakeProvider()
    result = provider.synthesize("Hola mundo", "es-MX-JorgeNeural", output, rate="-6%")
    assert result.path == output
    assert output.exists()

    with wave.open(str(output), "rb") as wav:
        assert wav.getnchannels() == 1
        assert wav.getframerate() == 24000
        assert wav.getnframes() > 0

    assert [word.text for word in result.words] == ["Hola", "mundo"]
    assert result.words[0].start_ms == 0
    assert all(
        left.end_ms <= right.start_ms
        for left, right in zip(result.words, result.words[1:], strict=False)
    )
    assert result.words[-1].end_ms > 0
