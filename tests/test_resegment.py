import json
from pathlib import Path

import pytest

from audiol.cli import main
from audiol.convert import convert
from audiol.manifest import SEGMENTATION_VERSION, book_from_manifest, load_manifest
from audiol.resegment import (
    ResegmentError,
    analyze_resegmentation,
    list_backups,
    repair_segments,
    restore_resegmentation,
)
from audiol.studio.library import Library
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


def _imported(tmp_path: Path, epub: Path) -> tuple[Library, Path]:
    library = Library(tmp_path / "library")
    record = library.import_epub(epub)
    return library, record.path


def _write(book_dir: Path, payload: dict) -> None:
    (book_dir / "manifest.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _make_stale(book_dir: Path, text: str = "Viejo texto roto") -> None:
    manifest = load_manifest(book_dir / "manifest.json")
    manifest.pop("segmentation_version", None)
    manifest["chapters"][0]["segments"][0]["text"] = text
    _write(book_dir, manifest)


def _converted(tmp_path: Path, epub: Path) -> Path:
    _library, book_dir = _imported(tmp_path, epub)
    manifest = load_manifest(book_dir / "manifest.json")
    book = book_from_manifest(manifest)
    convert(
        book,
        str(manifest["voice"]),
        str(manifest["engine"]),
        FakeProvider(),
        book_dir,
        style=str(manifest["style"]),
        rate=str(manifest["rate"]),
        book_id=str(manifest["id"]),
    )
    return book_dir


def _drop_segment_audio(book_dir: Path, segment_id: str) -> None:
    for path in (book_dir / "audio" / "segments").glob(f"{segment_id}_*"):
        path.unlink()


def test_import_writes_segmentation_metadata(tmp_path, tiny_epub):
    _library, book_dir = _imported(tmp_path, tiny_epub)
    manifest = load_manifest(book_dir / "manifest.json")

    assert manifest["segmentation_version"] == SEGMENTATION_VERSION
    assert manifest["max_chars"] == 400


def test_analyze_detects_stale_segmentation(tmp_path, tiny_epub):
    _library, book_dir = _imported(tmp_path, tiny_epub)
    _make_stale(book_dir)

    plan = analyze_resegmentation(book_dir)

    assert plan.can_repair
    assert plan.needs_repair
    assert plan.current_version is None
    assert plan.changed_segments == 1
    assert plan.changed_chapters == [1]
    assert plan.chapters[0].changed_segments == 1


def test_analyze_reports_current_book_as_up_to_date(tmp_path, tiny_epub):
    _library, book_dir = _imported(tmp_path, tiny_epub)

    plan = analyze_resegmentation(book_dir)

    assert plan.can_repair
    assert not plan.needs_repair
    assert plan.changed_segments == 0


def test_analyze_reports_missing_source(tmp_path, tiny_epub):
    _library, book_dir = _imported(tmp_path, tiny_epub)
    (book_dir / "source.epub").unlink()

    plan = analyze_resegmentation(book_dir)

    assert not plan.can_repair
    assert plan.reason == "source_missing"


def test_dry_run_does_not_touch_the_manifest(tmp_path, tiny_epub):
    _library, book_dir = _imported(tmp_path, tiny_epub)
    _make_stale(book_dir)
    before = (book_dir / "manifest.json").read_text(encoding="utf-8")

    result = repair_segments(book_dir, dry_run=True)

    assert result["changed"] is True
    assert result["dry_run"] is True
    assert result["changed_segments"] == 1
    assert (book_dir / "manifest.json").read_text(encoding="utf-8") == before


def test_metadata_only_repair_refreshes_an_imported_book(tmp_path, tiny_epub):
    _library, book_dir = _imported(tmp_path, tiny_epub)
    _make_stale(book_dir)

    result = repair_segments(book_dir)

    assert result["changed"] is True
    assert result["backup_id"] is None
    manifest = load_manifest(book_dir / "manifest.json")
    assert manifest["segmentation_version"] == SEGMENTATION_VERSION
    assert manifest["status"] == "imported"
    assert manifest["chapters"][0]["segments"][0]["text"] != "Viejo texto roto"


def test_repair_is_idempotent(tmp_path, tiny_epub):
    _library, book_dir = _imported(tmp_path, tiny_epub)
    _make_stale(book_dir)

    assert repair_segments(book_dir)["changed"] is True
    second = repair_segments(book_dir)

    assert second["changed"] is False
    assert second["needs_repair"] is False


@requires_ffmpeg
def test_audio_repair_only_rebuilds_changed_chapters(tmp_path, tiny_epub):
    book_dir = _converted(tmp_path, tiny_epub)
    original = load_manifest(book_dir / "manifest.json")
    chapter_two_audio = (book_dir / original["chapters"][1]["audio"]).read_bytes()
    _make_stale(book_dir)
    _drop_segment_audio(book_dir, original["chapters"][0]["segments"][0]["id"])

    result = repair_segments(book_dir, provider=FakeProvider())

    assert result["changed"] is True
    assert result["rebuilt_chapters"] == [1]
    assert result["synthesized_segments"] >= 1
    assert result["backup_id"]
    manifest = load_manifest(book_dir / "manifest.json")
    assert manifest["segmentation_version"] == SEGMENTATION_VERSION
    assert manifest["status"] == "ready"
    assert manifest["chapters"][0]["segments"][0]["text"] != "Viejo texto roto"
    assert (book_dir / manifest["chapters"][0]["audio"]).is_file()
    assert (book_dir / manifest["chapters"][1]["audio"]).read_bytes() == chapter_two_audio
    assert list_backups(book_dir)


@requires_ffmpeg
def test_audio_repair_can_be_rolled_back(tmp_path, tiny_epub):
    book_dir = _converted(tmp_path, tiny_epub)
    _make_stale(book_dir)
    broken = load_manifest(book_dir / "manifest.json")

    result = repair_segments(book_dir, provider=FakeProvider())
    assert result["backup_id"]

    restored = restore_resegmentation(book_dir, result["backup_id"])

    assert restored["backup_id"] == result["backup_id"]
    manifest = load_manifest(book_dir / "manifest.json")
    assert manifest.get("segmentation_version") is None
    assert manifest["chapters"][0]["segments"][0]["text"] == "Viejo texto roto"
    assert manifest == broken


@requires_ffmpeg
def test_audio_repair_restores_the_backup_on_failure(tmp_path, tiny_epub):
    book_dir = _converted(tmp_path, tiny_epub)
    _make_stale(book_dir)
    _drop_segment_audio(
        book_dir, load_manifest(book_dir / "manifest.json")["chapters"][0]["segments"][0]["id"]
    )
    before = (book_dir / "manifest.json").read_text(encoding="utf-8")

    class FailingProvider(FakeProvider):
        def synthesize(self, text, voice, out_path, style="neutral", rate="+0%"):
            raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        repair_segments(
            book_dir,
            provider=FailingProvider(),
            max_attempts=1,
            retry_delay=0,
        )

    assert (book_dir / "manifest.json").read_text(encoding="utf-8") == before
    assert list_backups(book_dir)


def test_restore_rejects_a_backup_outside_the_book(tmp_path, tiny_epub):
    _library, book_dir = _imported(tmp_path, tiny_epub)

    with pytest.raises(ResegmentError, match="inválido"):
        restore_resegmentation(book_dir, "../escape")


def test_repair_segments_cli_dry_run(tmp_path, tiny_epub, capsys):
    _library, book_dir = _imported(tmp_path, tiny_epub)
    _make_stale(book_dir)

    assert main(["repair-segments", str(book_dir), "--dry-run"]) == 0
    output = capsys.readouterr().out
    assert "requiere reparación" in output
    assert "1 segmentos afectados" in output


def test_repair_segments_cli_applies_metadata_repair(tmp_path, tiny_epub, capsys):
    _library, book_dir = _imported(tmp_path, tiny_epub)
    _make_stale(book_dir)

    assert main(["repair-segments", str(book_dir)]) == 0
    output = capsys.readouterr().out
    assert "Reparado" in output
    assert load_manifest(book_dir / "manifest.json")["segmentation_version"] == 2


def test_restore_cli_lists_backups(tmp_path, tiny_epub, capsys):
    _library, book_dir = _imported(tmp_path, tiny_epub)

    assert main(["repair-restore", str(book_dir), "--list"]) == 0
    assert "No hay copias" in capsys.readouterr().out
