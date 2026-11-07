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
    assert book.chapters[0].segments[0].id == "c001p0001s00"
    assert book.chapters[0].segments[0].source_href == "chap_1.xhtml"
    assert book.chapters[0].source_href == "chap_1.xhtml"
    assert book.chapters[0].segments[0].text.startswith("Pues sepa")
    assert book.chapters[1].segments[0].text.startswith("Mi viuda madre")


def test_read_epub_keeps_chapters_without_paragraphs(block_text_epub: Path):
    book = read_epub(block_text_epub)
    assert len(book.chapters) == 2
    assert book.chapters[0].segments[0].text == "Texto del capítulo sin párrafos."
    assert any(
        segment.text == "Texto suelto sin etiquetas." for segment in book.chapters[1].segments
    )


def test_read_epub_keeps_mixed_block_markup(mixed_block_epub: Path):
    book = read_epub(mixed_block_epub)
    texts = [segment.text for segment in book.chapters[0].segments]
    assert texts == ["Intro.", "Cita.", "Bloque.", "Anidado."]
    assert texts.count("Anidado.") == 1


def test_read_epub_skips_heading_in_bare_text_chapter(mixed_block_epub: Path):
    book = read_epub(mixed_block_epub)
    texts = [segment.text for segment in book.chapters[1].segments]
    assert texts == ["Texto suelto."]
    assert "Capítulo suelto" not in texts


def test_read_epub_splits_by_toc_anchors(toc_epub: Path):
    book = read_epub(toc_epub)
    assert [chapter.title for chapter in book.chapters] == [
        "Capítulo 1",
        "Capítulo 2",
        "Capítulo 3",
    ]
    assert [segment.text for segment in book.chapters[0].segments] == [
        "Primer párrafo.",
        "Segundo párrafo.",
    ]
    assert [segment.text for segment in book.chapters[1].segments] == [
        "Tercer párrafo.",
        "Continuación del capítulo 2.",
    ]
    assert [segment.text for segment in book.chapters[2].segments] == ["Cuarto párrafo."]
