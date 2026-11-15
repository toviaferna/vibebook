from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOTS = (ROOT / "src", ROOT / "web" / "src")
SUFFIXES = {".py", ".ts", ".tsx", ".css", ".json"}
# UTF-8 double-encoded markers and the replacement character. A source literal
# containing these almost always means a file was saved through the wrong
# codepage; the user-visible string would be corrupt.
MARKERS = ("\u00c3", "\u00c2", "\u00e2\u20ac", "\ufffd")


def test_sources_are_utf8_without_mojibake():
    offenders: list[str] = []
    for root in SOURCE_ROOTS:
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix not in SUFFIXES:
                continue
            text = path.read_text(encoding="utf-8")
            for line_number, line in enumerate(text.splitlines(), start=1):
                if any(marker in line for marker in MARKERS):
                    offenders.append(f"{path.relative_to(ROOT)}:{line_number}")
    assert not offenders, "Posible mojibake en el código: " + ", ".join(offenders)
