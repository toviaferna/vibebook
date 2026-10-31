import time
from pathlib import Path

from audiol.chunk import chunk_text
from audiol.tts.edge import EdgeProvider

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out" / "bakeoff_latam"
VOICES = [
    "es-MX-JorgeNeural",
    "es-MX-DaliaNeural",
    "es-PY-MarioNeural",
    "es-PY-TaniaNeural",
]


def main() -> None:
    text = (ROOT / "samples" / "excerpt.txt").read_text(encoding="utf-8")
    preview_parts: list[str] = []
    for chunk in chunk_text(text, max_chars=400):
        preview_parts.append(chunk)
        if len(" ".join(preview_parts)) >= 800:
            break
    preview = " ".join(preview_parts)
    OUT.mkdir(parents=True, exist_ok=True)
    provider = EdgeProvider()
    for voice in VOICES:
        output = OUT / f"{voice}.mp3"
        for attempt in range(3):
            try:
                provider.synthesize(preview, voice, output)
                break
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(2 * (attempt + 1))
        print(output)


if __name__ == "__main__":
    main()
