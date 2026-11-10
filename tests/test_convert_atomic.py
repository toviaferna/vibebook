import json
from pathlib import Path

import pytest

from audiol.convert import ConversionCancelled, convert, prepare_book
from audiol.ingest.epub import read_epub
from audiol.manifest import load_manifest
from audiol.storage import recover_incomplete_commit
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


class FailingSecondChapter(FakeProvider):
    def __init__(self) -> None:
        super().__init__()
        self.calls = 0

    def synthesize(self, text, voice, out_path, style="neutral", rate="+0%"):
        self.calls += 1
        if self.calls >= 2:
            raise RuntimeError("boom")
        return super().synthesize(text, voice, out_path, style=style, rate=rate)


@requires_ffmpeg
def test_failed_reconversion_preserves_previous_ready_book(tiny_epub: Path, tmp_path: Path):
    out_dir = tmp_path / "book"
    book = prepare_book(read_epub(tiny_epub))
    convert(book, "es-MX-JorgeNeural", "fake", FakeProvider(), out_dir)
    manifest_before = (out_dir / "manifest.json").read_bytes()
    chapter_before = (out_dir / "audio" / "chapters" / "chapter_001.mp3").read_bytes()

    with pytest.raises(RuntimeError, match="boom"):
        convert(
            book,
            "es-MX-JorgeNeural",
            "fake",
            FailingSecondChapter(),
            out_dir,
            force=True,
        )

    assert (out_dir / "manifest.json").read_bytes() == manifest_before
    assert (out_dir / "audio" / "chapters" / "chapter_001.mp3").read_bytes() == chapter_before
    assert load_manifest(out_dir / "manifest.json")["status"] == "ready"
    assert not list(out_dir.glob(".staging/*"))


@requires_ffmpeg
def test_cancelled_reconversion_preserves_previous_ready_book(tiny_epub: Path, tmp_path: Path):
    out_dir = tmp_path / "book"
    book = prepare_book(read_epub(tiny_epub))
    convert(book, "es-MX-JorgeNeural", "fake", FakeProvider(), out_dir)
    manifest_before = (out_dir / "manifest.json").read_bytes()
    calls = {"count": 0}

    def cancel() -> bool:
        calls["count"] += 1
        return calls["count"] > 2

    with pytest.raises(ConversionCancelled):
        convert(
            book,
            "es-MX-JorgeNeural",
            "fake",
            FakeProvider(),
            out_dir,
            force=True,
            should_cancel=cancel,
        )

    assert (out_dir / "manifest.json").read_bytes() == manifest_before
    assert not list(out_dir.glob(".staging/*"))


@requires_ffmpeg
def test_successful_reconversion_replaces_chapters_and_manifest(tiny_epub: Path, tmp_path: Path):
    out_dir = tmp_path / "book"
    book = prepare_book(read_epub(tiny_epub))
    convert(book, "es-MX-JorgeNeural", "fake", FakeProvider(), out_dir)
    (out_dir / "old-title.m4b").write_bytes(b"stale")

    result = convert(book, "es-MX-JorgeNeural", "fake", FakeProvider(), out_dir, force=True)

    manifest = load_manifest(out_dir / "manifest.json")
    assert manifest["status"] == "ready"
    assert manifest["m4b"]
    assert result.m4b_path.is_file()
    assert not (out_dir / "old-title.m4b").exists()


@requires_ffmpeg
def test_orphan_staging_is_cleaned_without_touching_ready_book(tiny_epub: Path, tmp_path: Path):
    out_dir = tmp_path / "book"
    book = prepare_book(read_epub(tiny_epub))
    convert(book, "es-MX-JorgeNeural", "fake", FakeProvider(), out_dir)
    manifest_before = (out_dir / "manifest.json").read_bytes()
    staging = out_dir / ".staging" / "orphan"
    staging.mkdir(parents=True)
    (staging / "state.json").write_text(json.dumps({"state": "staging"}), encoding="utf-8")
    (staging / "basura.txt").write_text("x", encoding="utf-8")

    recover_incomplete_commit(out_dir)

    assert not staging.exists()
    assert (out_dir / "manifest.json").read_bytes() == manifest_before
