from pathlib import Path

import pytest

from audiol.ambience.procedural import PRESETS, render_bed


@pytest.mark.parametrize("preset", sorted(PRESETS))
def test_every_procedural_preset_renders(preset: str, tmp_path: Path):
    target = tmp_path / f"{preset}.ogg"

    render_bed(preset, target, seconds=2)

    assert target.is_file()
    assert target.stat().st_size > 1_000
