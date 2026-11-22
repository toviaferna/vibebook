from pathlib import Path

from audiol.tools import resolve_shimmed_binary


def _scoop_layout(tmp_path: Path, versions: list[str]) -> tuple[Path, dict[str, Path]]:
    root = tmp_path / "scoop"
    shim = root / "shims" / "ffmpeg.EXE"
    shim.parent.mkdir(parents=True)
    shim.write_bytes(b"shim")
    binaries: dict[str, Path] = {}
    for version in versions:
        binary = root / "apps" / "ffmpeg" / version / "bin" / "ffmpeg.exe"
        binary.parent.mkdir(parents=True)
        binary.write_bytes(b"real")
        binaries[version] = binary
    return shim, binaries


def test_resolve_scoop_shim_to_the_real_binary(tmp_path: Path):
    shim, binaries = _scoop_layout(tmp_path, ["9.0.2"])

    assert resolve_shimmed_binary(str(shim), "ffmpeg", windows=True) == str(binaries["9.0.2"])


def test_resolve_scoop_shim_prefers_the_latest_version(tmp_path: Path):
    shim, binaries = _scoop_layout(tmp_path, ["8.0.0", "9.0.2"])

    assert resolve_shimmed_binary(str(shim), "ffmpeg", windows=True) == str(binaries["9.0.2"])


def test_resolve_scoop_shim_ignores_non_shim_paths(tmp_path: Path):
    binary = tmp_path / "bin" / "ffmpeg.exe"
    binary.parent.mkdir(parents=True)
    binary.write_bytes(b"real")

    assert resolve_shimmed_binary(str(binary), "ffmpeg", windows=True) is None


def test_resolve_scoop_shim_returns_none_when_the_app_is_missing(tmp_path: Path):
    shim = tmp_path / "shims" / "ffmpeg.exe"
    shim.parent.mkdir(parents=True)
    shim.write_bytes(b"shim")

    assert resolve_shimmed_binary(str(shim), "ffmpeg", windows=True) is None


def test_resolve_scoop_shim_is_windows_only(tmp_path: Path):
    shim, _ = _scoop_layout(tmp_path, ["9.0.2"])

    assert resolve_shimmed_binary(str(shim), "ffmpeg", windows=False) is None
