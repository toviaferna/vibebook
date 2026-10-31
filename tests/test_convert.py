import json
import shutil
from pathlib import Path

import pytest

from audiol.convert import convert, prepare_book, render_markdown
from audiol.ingest.epub import read_epub
from audiol.tts.fake import FakeProvider

requires_ffmpeg = pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
    reason="ffmpeg/ffprobe not installed",
)


class CountingProvider(FakeProvider):
    def __init__(self) -> None:
        super().__init__()
        self.calls = 0

    def synthesize(self, text, voice, out_path, style="neutral"):
        self.calls += 1
        return super().synthesize(text, voice, out_path, style)


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

    m4b = convert(book, "es-MX-JorgeNeural", "fake", provider, out_dir)

    assert m4b.exists()
    assert (out_dir / "manifest.json").exists()
    assert provider.calls == 2
    manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["voice"] == "es-MX-JorgeNeural"
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


class FlakyProvider(FakeProvider):
    def __init__(self) -> None:
        super().__init__()
        self.calls = 0

    def synthesize(self, text, voice, out_path, style="neutral"):
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("transient")
        return super().synthesize(text, voice, out_path, style)


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
