from pathlib import Path

import pytest

from audiol.cli import main
from audiol.tools import find_binary


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


@requires_ffmpeg
def test_cli_convert_with_fake_provider(tiny_epub: Path, tmp_path: Path, capsys):
    out_dir = tmp_path / "out"
    code = main(
        [
            "convert",
            str(tiny_epub),
            "--engine",
            "fake",
            "--rate",
            "-4%",
            "--out",
            str(out_dir),
        ]
    )
    assert code == 0
    assert (out_dir / "book.md").exists()
    assert (out_dir / "manifest.json").exists()
    assert list(out_dir.glob("*.m4b"))
    assert '"rate": "-4%"' in (out_dir / "manifest.json").read_text(encoding="utf-8")
    assert "M4B:" in capsys.readouterr().out


def test_cli_dry_run_does_not_write(tiny_epub: Path, tmp_path: Path, capsys):
    out_dir = tmp_path / "out"
    code = main(
        [
            "convert",
            str(tiny_epub),
            "--engine",
            "fake",
            "--dry-run",
            "--out",
            str(out_dir),
        ]
    )
    assert code == 0
    assert not out_dir.exists()
    assert "chapters" in capsys.readouterr().out
