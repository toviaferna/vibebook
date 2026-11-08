from __future__ import annotations

import subprocess
from pathlib import Path

from audiol.tools import require_ffmpeg

SAMPLE_RATE = 48_000
BED_SECONDS = 30
PRESETS: dict[str, tuple[str, float, str]] = {
    "rain": ("white", 0.35, "highpass=f=400,lowpass=f=8000,volume=0.55"),
    "wind": ("brown", 0.50, "bandpass=f=500:width_type=h:w=300,tremolo=f=0.15:d=0.35,volume=0.7"),
    "sea": ("brown", 0.45, "lowpass=f=900,tremolo=f=0.08:d=0.55,volume=0.6"),
    "room": ("pink", 0.12, "lowpass=f=1200,volume=0.35"),
    "fire": ("pink", 0.30, "highpass=f=900,lowpass=f=5000,tremolo=f=1.8:d=0.25,volume=0.5"),
    "night": ("brown", 0.25, "lowpass=f=600,volume=0.4"),
}


class ProceduralError(RuntimeError):
    pass


def render_bed(preset: str, destination: Path, seconds: int = BED_SECONDS) -> Path:
    if preset not in PRESETS:
        raise ValueError(f"Unknown procedural preset: {preset}")
    if seconds < 2:
        raise ValueError("A procedural bed needs at least 2 seconds")
    color, amplitude, filters = PRESETS[preset]
    fade_out_start = max(0, seconds - 1)
    filter_chain = f"{filters},afade=t=in:st=0:d=1,afade=t=out:st={fade_out_start}:d=1"
    destination.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg, _ = require_ffmpeg()
    source = (
        f"anoisesrc=color={color}:amplitude={amplitude}:"
        f"duration={seconds}:sample_rate={SAMPLE_RATE}"
    )
    errors: list[str] = []
    for codec in ("libopus", "libvorbis"):
        command = [
            ffmpeg,
            "-y",
            "-f",
            "lavfi",
            "-i",
            source,
            "-af",
            filter_chain,
            "-ac",
            "1",
            "-ar",
            str(SAMPLE_RATE),
            "-c:a",
            codec,
            "-b:a",
            "48k",
            str(destination),
        ]
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
        if completed.returncode == 0 and destination.is_file() and destination.stat().st_size > 0:
            return destination
        errors.append(completed.stderr[-500:])
    destination.unlink(missing_ok=True)
    raise ProceduralError(f"Could not render procedural bed {preset}: {errors[-1]}")
