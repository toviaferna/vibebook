import json
from pathlib import Path

import pytest

from audiol.convert import (
    convert,
    prepare_book,
    render_markdown,
    synthesize_with_retries,
)
from audiol.ingest.epub import read_epub
from audiol.tools import find_binary
from audiol.tts.fake import FakeProvider


def _has_ffmpeg() -> bool:
    try:
        find_binary("ffmpeg")
        find_binary("ffprobe")
        return True
    except RuntimeError:
        return False


requires_ffmpeg = pytest.mark.skipif(
    not _has_ffmpeg(),
    reason="ffmpeg/ffprobe not available",
)


def test_synthesize_with_retries_rejects_zero_attempts(tmp_path: Path):
    with pytest.raises(ValueError):
        synthesize_with_retries(
            FakeProvider(),
            "Hola",
            "es-MX-JorgeNeural",
            tmp_path / "x.wav",
            "neutral",
            "+0%",
            max_attempts=0,
        )


class CountingProvider(FakeProvider):
    def __init__(self) -> None:
        super().__init__()
        self.calls = 0

    def synthesize(self, text, voice, out_path, style="neutral", rate="+0%"):
        self.calls += 1
        return super().synthesize(text, voice, out_path, style, rate)


def test_prepare_book_chunks_and_cleans(tiny_epub: Path):
    book = prepare_book(read_epub(tiny_epub))
    assert book.chapters[0].segments[0].text.startswith("Pues sepa")
    assert book.chapters[0].segments[0].id == "c001p0001"


def test_prepare_book_preserves_text(tiny_epub: Path):
    original = read_epub(tiny_epub)
    prepared = prepare_book(original)
    original_text = " ".join(
        segment.text for chapter in original.chapters for segment in chapter.segments
    )
    prepared_text = " ".join(
        segment.text for chapter in prepared.chapters for segment in chapter.segments
    )
    assert prepared_text == original_text


def test_render_markdown_contains_chapters(tiny_epub: Path):
    book = prepare_book(read_epub(tiny_epub))
    markdown = render_markdown(book)
    assert "# Libro de prueba" in markdown
    assert "## Capítulo 1" in markdown
    assert "Pues sepa" in markdown


@requires_ffmpeg
def test_convert_writes_manifest_and_audio(tiny_epub: Path, tmp_path: Path):
    book = prepare_book(read_epub(tiny_epub))
    out_dir = tmp_path / "book"
    provider = CountingProvider()

    m4b = convert(book, "es-MX-JorgeNeural", "fake", provider, out_dir, rate="-6%")

    assert m4b.exists()
    assert (out_dir / "manifest.json").exists()
    assert provider.calls == 2
    manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["voice"] == "es-MX-JorgeNeural"
    assert manifest["style"] == "neutral"
    assert manifest["rate"] == "-6%"
    assert len(manifest["chapters"]) == 2


@requires_ffmpeg
def test_convert_reuses_cached_segments(tiny_epub: Path, tmp_path: Path):
    book = prepare_book(read_epub(tiny_epub))
    out_dir = tmp_path / "book"
    first = CountingProvider()
    convert(book, "es-MX-JorgeNeural", "fake", first, out_dir)

    second = CountingProvider()
    convert(book, "es-MX-JorgeNeural", "fake", second, out_dir)
    assert second.calls == 0

    forced = CountingProvider()
    convert(book, "es-MX-JorgeNeural", "fake", forced, out_dir, force=True)
    assert forced.calls == 2


@requires_ffmpeg
def test_convert_reuses_cache_by_text_key(tiny_epub: Path, tmp_path: Path):
    book = prepare_book(read_epub(tiny_epub))
    out_dir = tmp_path / "book"
    first = CountingProvider()
    convert(book, "es-MX-JorgeNeural", "fake", first, out_dir)

    segments = out_dir / "audio" / "segments"
    for path in list(segments.glob("*.wav")):
        path.rename(path.with_name(f"old_{path.name}"))

    second = CountingProvider()
    convert(book, "es-MX-JorgeNeural", "fake", second, out_dir)
    assert second.calls == 0


@requires_ffmpeg
def test_convert_rate_changes_cache_key(tiny_epub: Path, tmp_path: Path):
    book = prepare_book(read_epub(tiny_epub))
    out_dir = tmp_path / "book"
    first = CountingProvider()
    convert(book, "es-MX-JorgeNeural", "fake", first, out_dir, rate="-6%")

    second = CountingProvider()
    convert(book, "es-MX-JorgeNeural", "fake", second, out_dir, rate="-10%")

    assert second.calls == 2


class FlakyProvider(FakeProvider):
    def __init__(self) -> None:
        super().__init__()
        self.calls = 0

    def synthesize(self, text, voice, out_path, style="neutral", rate="+0%"):
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("transient")
        return super().synthesize(text, voice, out_path, style, rate)


class InvalidProvider(FakeProvider):
    def __init__(self) -> None:
        super().__init__()
        self.calls = 0

    def synthesize(self, text, voice, out_path, style="neutral", rate="+0%"):
        self.calls += 1
        raise ValueError("invalid input")


@requires_ffmpeg
def test_convert_does_not_retry_value_errors(tiny_epub: Path, tmp_path: Path):
    book = prepare_book(read_epub(tiny_epub))
    provider = InvalidProvider()

    with pytest.raises(ValueError):
        convert(book, "es-MX-JorgeNeural", "fake", provider, tmp_path / "book")

    assert provider.calls == 1


@requires_ffmpeg
def test_convert_retries_transient_failure(tiny_epub: Path, tmp_path: Path):
    book = prepare_book(read_epub(tiny_epub))
    out_dir = tmp_path / "book"
    provider = FlakyProvider()

    convert(
        book,
        "es-MX-JorgeNeural",
        "fake",
        provider,
        out_dir,
        retry_delay=0.0,
    )

    assert provider.calls == 3


class PartialProvider(FakeProvider):
    def synthesize(self, text, voice, out_path, style="neutral", rate="+0%"):
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(b"partial")
        raise RuntimeError("boom")


@requires_ffmpeg
def test_convert_discards_partial_files_after_failed_synthesis(tiny_epub: Path, tmp_path: Path):
    book = prepare_book(read_epub(tiny_epub))
    out_dir = tmp_path / "book"

    with pytest.raises(RuntimeError):
        convert(
            book,
            "es-MX-JorgeNeural",
            "fake",
            PartialProvider(),
            out_dir,
            retry_delay=0.0,
        )

    assert list((out_dir / "audio" / "segments").glob("*.wav")) == []

    provider = CountingProvider()
    m4b = convert(book, "es-MX-JorgeNeural", "fake", provider, out_dir)
    assert provider.calls == 2
    assert m4b.exists()


class InterruptingProvider(FakeProvider):
    def __init__(self) -> None:
        super().__init__()
        self.calls = 0

    def synthesize(self, text, voice, out_path, style="neutral", rate="+0%"):
        self.calls += 1
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(b"partial")
        raise KeyboardInterrupt()


@requires_ffmpeg
def test_convert_removes_partial_temp_on_keyboard_interrupt(tiny_epub: Path, tmp_path: Path):
    book = prepare_book(read_epub(tiny_epub))
    out_dir = tmp_path / "book"
    provider = InterruptingProvider()

    with pytest.raises(KeyboardInterrupt):
        convert(book, "es-MX-JorgeNeural", "fake", provider, out_dir)

    assert not list((out_dir / "audio" / "segments").glob("*"))

    fresh = CountingProvider()
    convert(book, "es-MX-JorgeNeural", "fake", fresh, out_dir)
    assert fresh.calls == 2
