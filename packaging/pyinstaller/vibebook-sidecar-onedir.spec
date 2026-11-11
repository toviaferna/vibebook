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

datas = [(str(WEB_DIST), "web/dist")]
PIPER_ROOT = ROOT / "packaging" / "piper"
PIPER_BIN = PIPER_ROOT / "bin"
if PIPER_BIN.is_dir():
    for item in sorted(PIPER_BIN.iterdir()):
        if item.is_dir():
            datas.append((str(item), f"bin/{item.name}"))
        else:
            binaries.append((str(item), "bin"))
PIPER_VOICES = PIPER_ROOT / "voices"
if PIPER_VOICES.is_dir():
    datas.append((str(PIPER_VOICES), "piper-voices"))
ESPEAK_BIN = ROOT / "packaging" / "espeak" / "bin"
if ESPEAK_BIN.is_dir():
    for item in sorted(ESPEAK_BIN.iterdir()):
        if item.is_dir():
            datas.append((str(item), f"espeak/bin/{item.name}"))
        else:
            binaries.append((str(item), "espeak/bin"))

analysis = Analysis(
    [str(ROOT / "packaging" / "pyinstaller" / "sidecar_entry.py")],
    pathex=[str(SRC)],
    binaries=binaries,
    datas=datas,
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
    [],
    exclude_binaries=True,
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

coll = COLLECT(
    exe,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=False,
    name="vibebook-sidecar",
)
