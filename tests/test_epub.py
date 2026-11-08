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
        "1",
        "2",
        "3",
    ]
    assert [chapter.number for chapter in book.chapters] == [1, 2, 3]
    assert [chapter.kind for chapter in book.chapters] == ["chapter", "chapter", "chapter"]
    assert [node.title for node in book.toc] == ["1", "2", "3"]
    assert [segment.text for segment in book.chapters[0].segments] == [
        "Primer párrafo.",
        "Segundo párrafo.",
    ]
    assert [segment.text for segment in book.chapters[1].segments] == [
        "Tercer párrafo.",
        "Continuación del capítulo 2.",
    ]
    assert book.chapters[1].segments[-1].source_href == "continuation.xhtml"
    assert [segment.text for segment in book.chapters[2].segments] == ["Cuarto párrafo."]


def test_read_epub_preserves_real_chapter_titles(titled_toc_epub: Path):
    book = read_epub(titled_toc_epub)

    assert [chapter.title for chapter in book.chapters] == [
        "La casa de los relojes",
        "La voz del papel",
    ]
    assert all(chapter.number is None for chapter in book.chapters)
    assert [chapter.level for chapter in book.chapters] == [1, 1]
    assert [node.title for node in book.toc] == [
        "La casa de los relojes",
        "La voz del papel",
    ]


def test_read_epub_builds_nested_toc(nested_toc_epub: Path):
    book = read_epub(nested_toc_epub)

    assert [chapter.title for chapter in book.chapters] == ["La casa", "El zorro"]
    assert len(book.toc) == 1
    part = book.toc[0]
    assert part.title == "Parte I"
    assert part.level == 0
    assert part.chapter_index is None
    assert [child.title for child in part.children] == ["La casa", "El zorro"]
    assert [child.chapter_index for child in part.children] == [1, 2]


def test_read_epub_splits_by_headings_without_toc(heading_chapters_epub: Path):
    book = read_epub(heading_chapters_epub)

    assert [chapter.title for chapter in book.chapters] == ["La casa", "El zorro"]
    assert all(not chapter.generated_title for chapter in book.chapters)
    assert [node.title for node in book.toc] == ["La casa", "El zorro"]


def test_read_epub_keeps_frontmatter(frontmatter_epub: Path):
    book = read_epub(frontmatter_epub)

    assert [chapter.title for chapter in book.chapters] == ["Prólogo", "La casa"]
    assert [chapter.kind for chapter in book.chapters] == ["frontmatter", "chapter"]
    assert [node.title for node in book.toc] == ["Prólogo", "La casa"]


def test_read_epub_extracts_images(image_epub: Path, tmp_path: Path):
    image_dir = tmp_path / "images"
    book = read_epub(image_epub, image_dir=image_dir)

    assert len(book.images) == 1
    image = book.images[0]
    assert image.alt == "Una casa verde"
    assert image.caption == "La casa del bosque"
    assert image.role == "illustration"
    assert image.chapter_index == 1
    assert image.paragraph_index == 1
    assert image.position == "after"
    assert image.width == 320
    assert image.height == 200
    assert image.path is not None
    assert (image_dir / Path(image.path).name).is_file()
