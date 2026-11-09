import json
from pathlib import Path

import pytest

from audiol.convert import (
    ConversionCancelled,
    cache_key,
    convert,
    prepare_book,
    render_markdown,
    synthesize_with_retries,
)
from audiol.ingest.epub import read_epub
from audiol.models import Book, Chapter, Segment, TocNode, make_segment_id
from audiol.timing import (
    audio_duration_ms,
    read_chapter_timing,
    read_word_timings,
)
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
    assert book.chapters[0].segments[0].id == "c001p0001s00"


def test_prepare_book_joins_hyphenated_words(hyphenated_epub: Path):
    book = prepare_book(read_epub(hyphenated_epub))
    texts = [segment.text for segment in book.chapters[0].segments]

    assert texts == [
        "Primera: la cosa ultima parte.",
        "Segunda: la cosa ultima parte.",
    ]


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


def test_prepare_book_preserves_structure_metadata():
    segment = Segment(
        id=make_segment_id(1, 1),
        chapter_index=1,
        paragraph_index=1,
        text="Hola mundo.",
    )
    book = Book(
        title="Libro",
        author="Autora",
        chapters=[
            Chapter(
                index=1,
                title="La casa",
                segments=[segment],
                level=1,
                kind="chapter",
                number=1,
            )
        ],
        toc=[
            TocNode(
                title="Parte I",
                level=0,
                kind="part",
                children=[TocNode(title="La casa", level=1, chapter_index=1)],
            )
        ],
    )

    prepared = prepare_book(book)

    assert prepared.chapters[0].number == 1
    assert prepared.chapters[0].kind == "chapter"
    assert prepared.toc[0].title == "Parte I"
    assert prepared.toc[0].children[0].chapter_index == 1


def test_prepare_book_keeps_paragraph_index_for_chunks():
    paragraph = " ".join(["palabra"] * 80)
    source = Segment(
        id=make_segment_id(1, 1),
        chapter_index=1,
        paragraph_index=1,
        text=paragraph,
        source_href="chapter.xhtml",
        source_fragment="inicio",
    )
    book = Book(
        title="Libro",
        author="Autora",
        chapters=[Chapter(index=1, title="Capítulo 1", segments=[source])],
    )

    prepared = prepare_book(book, max_chars=50)
    segments = prepared.chapters[0].segments

    assert len(segments) > 1
    assert {segment.paragraph_index for segment in segments} == {1}
    assert [segment.chunk_index for segment in segments] == list(range(len(segments)))
    assert len({segment.id for segment in segments}) == len(segments)
    assert all(segment.source_href == "chapter.xhtml" for segment in segments)
    assert all(segment.source_fragment == "inicio" for segment in segments)


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

    result = convert(book, "es-MX-JorgeNeural", "fake", provider, out_dir, rate="-6%")

    assert result.m4b_path.exists()
    assert result.total_segments == 2
    assert result.cached_segments == 0
    assert result.duration_ms > 0
    assert (out_dir / "manifest.json").exists()
    assert provider.calls == 2
    manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema_version"] == 2
    assert manifest["status"] == "ready"
    assert manifest["voice"] == "es-MX-JorgeNeural"
    assert manifest["style"] == "neutral"
    assert manifest["rate"] == "-6%"
    assert len(manifest["chapters"]) == 2
    assert manifest["chapters"][0]["audio"] == "audio/chapters/chapter_001.mp3"
    assert manifest["chapters"][0]["timing"] == "timings/chapter_001.json"
    assert manifest["chapters"][0]["duration_ms"] > 0
    assert (out_dir / "timings" / "chapter_001.json").exists()


@requires_ffmpeg
def test_convert_reports_progress_sequence(tiny_epub: Path, tmp_path: Path):
    book = prepare_book(read_epub(tiny_epub))
    events = []

    convert(
        book,
        "es-MX-JorgeNeural",
        "fake",
        CountingProvider(),
        tmp_path / "book",
        on_progress=events.append,
    )

    assert events[0].stage == "preparing"
    assert events[0].completed_segments == 0
    assert events[0].total_segments == 2
    assert [event.stage for event in events].count("synthesizing") == 2
    assert "assembling" in [event.stage for event in events]
    assert "finalizing" in [event.stage for event in events]
    assert events[-1].stage == "done"
    assert events[-1].completed_segments == 2
    assert events[-1].total_segments == 2


@requires_ffmpeg
def test_convert_writes_word_sidecars_and_exact_timings(tiny_epub: Path, tmp_path: Path):
    book = prepare_book(read_epub(tiny_epub))
    out_dir = tmp_path / "book"

    convert(book, "es-MX-JorgeNeural", "fake", CountingProvider(), out_dir)

    segment_id = book.chapters[0].segments[0].id
    segment_path = next((out_dir / "audio" / "segments").glob(f"{segment_id}_*.wav"))
    words = read_word_timings(segment_path.with_suffix(".timing.json"))
    assert words
    assert words[0].start_ms == 0
    assert words[-1].end_ms > 0

    timing = read_chapter_timing(out_dir / "timings" / "chapter_001.json")
    assert timing.precision == "exact"
    assert timing.segments[0].start_ms == 0
    assert timing.segments[0].end_ms <= timing.duration_ms
    assert timing.segments[0].words[0].text == words[0].text
    assert timing.segments[0].words[0].start_ms == 0


@requires_ffmpeg
def test_convert_no_timings_skips_sidecars(tiny_epub: Path, tmp_path: Path):
    book = prepare_book(read_epub(tiny_epub))
    out_dir = tmp_path / "book"

    result = convert(
        book,
        "es-MX-JorgeNeural",
        "fake",
        CountingProvider(),
        out_dir,
        capture_timings=False,
    )

    assert result.m4b_path.exists()
    assert not (out_dir / "timings").exists()
    assert not list((out_dir / "audio" / "segments").glob("*.timing.json"))
    manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["chapters"][0]["timing"] is None


@requires_ffmpeg
def test_convert_no_timings_removes_stale_files(tiny_epub: Path, tmp_path: Path):
    book = prepare_book(read_epub(tiny_epub))
    out_dir = tmp_path / "book"
    convert(book, "es-MX-JorgeNeural", "fake", CountingProvider(), out_dir)
    assert (out_dir / "timings" / "chapter_001.json").exists()

    convert(
        book,
        "es-MX-JorgeNeural",
        "fake",
        CountingProvider(),
        out_dir,
        capture_timings=False,
    )

    assert not list((out_dir / "timings").glob("chapter_*.json"))
    manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["chapters"][0]["timing"] is None


@requires_ffmpeg
def test_convert_counts_cached_segments(tiny_epub: Path, tmp_path: Path):
    book = prepare_book(read_epub(tiny_epub))
    out_dir = tmp_path / "book"
    convert(book, "es-MX-JorgeNeural", "fake", CountingProvider(), out_dir)

    result = convert(book, "es-MX-JorgeNeural", "fake", CountingProvider(), out_dir)

    assert result.total_segments == 2
    assert result.cached_segments == 2


def _two_segment_book() -> Book:
    return Book(
        title="Libro",
        author="Autora",
        chapters=[
            Chapter(
                index=1,
                title="Capítulo 1",
                segments=[
                    Segment(
                        id=make_segment_id(1, 1),
                        chapter_index=1,
                        paragraph_index=1,
                        text="Hola mundo.",
                    ),
                    Segment(
                        id=make_segment_id(1, 2),
                        chapter_index=1,
                        paragraph_index=2,
                        text="Adiós mundo.",
                    ),
                ],
            )
        ],
    )


@requires_ffmpeg
def test_convert_cancels_between_segments_without_losing_cache(tmp_path: Path):
    book = _two_segment_book()
    out_dir = tmp_path / "book"
    cancelled = False
    events = []

    def on_progress(event):
        nonlocal cancelled
        events.append(event)
        if event.completed_segments == 1:
            cancelled = True

    with pytest.raises(ConversionCancelled):
        convert(
            book,
            "es-MX-JorgeNeural",
            "fake",
            CountingProvider(),
            out_dir,
            on_progress=on_progress,
            should_cancel=lambda: cancelled,
        )

    assert events[-1].completed_segments == 1
    assert len(list((out_dir / "audio" / "segments").glob("*.wav"))) == 1
    assert not (out_dir / "audio" / "chapters" / "chapter_001.mp3").exists()
    manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "interrupted"
    assert manifest["duration_ms"] is None

    second = CountingProvider()
    result = convert(book, "es-MX-JorgeNeural", "fake", second, out_dir)

    assert second.calls == 1
    assert result.total_segments == 2
    assert result.cached_segments == 1
    assert result.m4b_path.exists()
    manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "ready"


@requires_ffmpeg
def test_convert_cancel_after_assembly_does_not_build_m4b(tiny_epub: Path, tmp_path: Path):
    book = prepare_book(read_epub(tiny_epub))
    out_dir = tmp_path / "book"
    cancelled = False

    def on_progress(event):
        nonlocal cancelled
        if event.stage == "assembling":
            cancelled = True

    with pytest.raises(ConversionCancelled):
        convert(
            book,
            "es-MX-JorgeNeural",
            "fake",
            CountingProvider(),
            out_dir,
            on_progress=on_progress,
            should_cancel=lambda: cancelled,
        )

    assert not list(out_dir.glob("*.m4b"))
    manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "interrupted"


@requires_ffmpeg
def test_convert_failure_preserves_previous_ready_manifest(tiny_epub: Path, tmp_path: Path):
    book = prepare_book(read_epub(tiny_epub))
    out_dir = tmp_path / "book"
    convert(book, "es-MX-JorgeNeural", "fake", CountingProvider(), out_dir)
    before = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))

    with pytest.raises(ValueError):
        convert(
            book,
            "es-MX-JorgeNeural",
            "fake",
            InvalidProvider(),
            out_dir,
            rate="-20%",
        )

    after = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    assert after["status"] == "ready"
    assert after["rate"] == before["rate"]


@requires_ffmpeg
def test_convert_recovers_from_corrupt_cached_segment(tiny_epub: Path, tmp_path: Path):
    book = prepare_book(read_epub(tiny_epub))
    out_dir = tmp_path / "book"
    segments_dir = out_dir / "audio" / "segments"
    segments_dir.mkdir(parents=True)
    segment = book.chapters[0].segments[0]
    key = cache_key(segment, "es-MX-JorgeNeural", "fake", "neutral", "+0%")
    corrupt = segments_dir / f"{segment.id}_{key}.wav"
    corrupt.write_bytes(b"not audio")

    result = convert(book, "es-MX-JorgeNeural", "fake", CountingProvider(), out_dir)

    assert result.m4b_path.exists()
    assert corrupt.stat().st_size > len(b"not audio")


@requires_ffmpeg
def test_convert_manifest_chapter_durations_match_audio(tiny_epub: Path, tmp_path: Path):
    book = prepare_book(read_epub(tiny_epub))
    out_dir = tmp_path / "book"
    convert(book, "es-MX-JorgeNeural", "fake", CountingProvider(), out_dir)
    manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))

    for chapter in manifest["chapters"]:
        audio = out_dir / chapter["audio"]
        assert abs(chapter["duration_ms"] - audio_duration_ms(audio)) <= 500


@requires_ffmpeg
def test_convert_supports_apostrophe_in_output_path(tiny_epub: Path, tmp_path: Path):
    book = prepare_book(read_epub(tiny_epub))
    out_dir = tmp_path / "O'Brien" / "book"

    result = convert(book, "es-MX-JorgeNeural", "fake", CountingProvider(), out_dir)

    assert result.m4b_path.exists()


def test_audio_duration_reads_fake_wav(tmp_path: Path):
    path = tmp_path / "sample.wav"
    FakeProvider().synthesize("Hola mundo", "es-MX-JorgeNeural", path)

    assert audio_duration_ms(path) > 0


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
    result = convert(book, "es-MX-JorgeNeural", "fake", provider, out_dir)
    assert provider.calls == 2
    assert result.m4b_path.exists()


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
