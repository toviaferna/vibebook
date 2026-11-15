from pathlib import Path

from PIL import Image

from audiol.ingest.epub import read_epub
from audiol.studio.library import extract_cover

SAMPLE = Path(__file__).resolve().parents[1] / "samples" / "lector-de-prueba.epub"


def test_sample_has_metadata_toc_and_chapters():
    book = read_epub(SAMPLE)

    assert book.title == "El mapa de las mareas"
    assert book.author == "Lucía Ferrer"
    assert len(book.chapters) >= 5
    assert all(chapter.segments for chapter in book.chapters)
    assert any("—" in segment.text for chapter in book.chapters for segment in chapter.segments)


def test_sample_cover_is_a_readable_image(tmp_path: Path):
    cover = extract_cover(SAMPLE, tmp_path)

    assert cover is not None
    assert cover.name == "cover.png"
    with Image.open(cover) as image:
        assert image.width >= 1000
        assert image.height >= 1500
        image.verify()


def test_sample_extracts_internal_illustration(tmp_path: Path):
    images_dir = tmp_path / "images"
    book = read_epub(SAMPLE, image_dir=images_dir)

    assert book.images
    placement = book.images[0]
    files = list(images_dir.glob("*"))
    assert files
    assert placement.alt
    with Image.open(files[0]) as image:
        image.verify()
