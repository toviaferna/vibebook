import io

import pytest
from PIL import Image

from audiol.studio.cover_search import (
    CoverSearchError,
    _title_score,
    download_cover,
    normalize,
    normalize_cover,
)


def test_normalize_ignores_accents_and_punctuation():
    assert normalize("  Cien años de soledad ") == "cien anos de soledad"


def test_title_score_rejects_unrelated_books():
    assert _title_score("Cien años de soledad", "Cien años de soledad") == 1
    assert _title_score("Cien años de soledad", "Cien años de soledad (edición especial)") == 0.95
    assert _title_score("Cien años de soledad", "Rayuela") == 0


def test_normalize_cover_returns_a_jpeg():
    buffer = io.BytesIO()
    Image.new("RGBA", (400, 600), (20, 30, 40, 128)).save(buffer, format="PNG")

    jpeg = normalize_cover(buffer.getvalue())

    assert jpeg.startswith(b"\xff\xd8")
    with Image.open(io.BytesIO(jpeg)) as image:
        assert image.format == "JPEG"
        assert image.mode == "RGB"


def test_download_cover_rejects_untrusted_hosts():
    with pytest.raises(CoverSearchError):
        download_cover("https://example.com/cover.jpg")
    with pytest.raises(CoverSearchError):
        download_cover("http://covers.openlibrary.org/b/id/1-L.jpg")
