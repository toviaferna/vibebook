from pathlib import Path
import sys

from PyInstaller.utils.hooks import collect_submodules

ROOT = Path(SPECPATH).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from audiol.tools import find_binary  # noqa: E402

WEB_DIST = ROOT / "web" / "dist"
if not (WEB_DIST / "index.html").is_file():
    raise SystemExit("web/dist is missing. Run `npm run build` in web/ first.")

binaries = []
for name in ("ffmpeg", "ffprobe"):
    try:
        binaries.append((find_binary(name), "bin"))
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc

analysis = Analysis(
    [str(ROOT / "packaging" / "pyinstaller" / "sidecar_entry.py")],
    pathex=[str(SRC)],
    binaries=binaries,
    datas=[(str(WEB_DIST), "web/dist")],
    hiddenimports=collect_submodules("audiol") + collect_submodules("uvicorn"),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(analysis.pure)

exe = EXE(
    pyz,
    analysis.scripts,
    analysis.binaries,
    analysis.datas,
    [],
    name="vibebook-sidecar",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
