from pathlib import Path

from audiol.ingest.epub import read_epub


def test_read_epub_metadata(tiny_epub: Path):
    book = read_epub(tiny_epub)
    assert book.title == "Libro de prueba"
    assert book.author == "Autora"
    assert book.language.startswith("es")


def test_read_epub_chapters_and_segments(tiny_epub: Path):
    book = read_epub(tiny_epub)
    assert len(book.chapters) == 2
    assert book.chapters[0].title == "Capítulo 1"
    assert book.chapters[0].segments[0].id == "c001p0001"
    assert book.chapters[0].segments[0].text.startswith("Pues sepa")
    assert book.chapters[1].segments[0].text.startswith("Mi viuda madre")


def test_read_epub_keeps_chapters_without_paragraphs(block_text_epub: Path):
    book = read_epub(block_text_epub)
    assert len(book.chapters) == 2
    assert book.chapters[0].segments[0].text == "Texto del capítulo sin párrafos."
    assert any(
        segment.text == "Texto suelto sin etiquetas."
        for segment in book.chapters[1].segments
    )
