import wave
from pathlib import Path

import pytest

from audiol.tts.kokoro import _speed, _split_text
from audiol.tts.kokoro_assets import KokoroNotConfigured, kokoro_ready


def test_kokoro_speed_matches_the_rate():
    assert _speed("+0%") == 1.0
    assert _speed("-10%") == pytest.approx(1 / 0.9)
    assert _speed("-50%") == 2.0
    with pytest.raises(ValueError):
        _speed("-96%")


def test_kokoro_splits_long_text_without_exceeding_the_limit():
    text = " ".join(["Esta es una frase bastante larga que debe dividirse."] * 20)

    chunks = _split_text(text)

    assert len(chunks) > 1
    assert all(len(chunk) <= 260 for chunk in chunks)
    assert " ".join(chunks).replace("  ", " ").strip() == text.strip()


def test_kokoro_ready_is_false_without_assets(tmp_path: Path):
    assert kokoro_ready(tmp_path / "missing") is False


def test_kokoro_provider_requires_assets(tmp_path: Path):
    from audiol.tts.kokoro import KokoroProvider

    provider = KokoroProvider(root=tmp_path / "missing")
    with pytest.raises(KokoroNotConfigured):
        provider.synthesize("Hola", "ef_dora", tmp_path / "out.wav")


@pytest.mark.skipif(not kokoro_ready(), reason="Kokoro model is not installed")
def test_kokoro_synthesizes_spanish_audio(tmp_path: Path):
    from audiol.tts.kokoro import KokoroProvider

    output = tmp_path / "sample.wav"
    result = KokoroProvider().synthesize(
        "Hola. Esta es una prueba de la voz local en español.",
        "ef_dora",
        output,
        rate="-10%",
    )

    assert result.path == output
    assert output.stat().st_size > 10_000
    with wave.open(str(output), "rb") as handle:
        assert handle.getnchannels() == 1
        assert handle.getframerate() == 24_000
        assert handle.getnframes() > 24_000
