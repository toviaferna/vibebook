from pathlib import Path

import pytest
from ebooklib import epub


@pytest.fixture
def tiny_epub(tmp_path: Path) -> Path:
    book = epub.EpubBook()
    book.set_identifier("audiol-test-123")
    book.set_title("Libro de prueba")
    book.set_language("es")
    book.add_author("Autora")

    chapters = []
    for index, (title, body) in enumerate(
        [
            ("Capítulo 1", "Pues sepa V.M. que a mí llaman Lázaro."),
            ("Capítulo 2", "Mi viuda madre determinó arrimarse a los buenos."),
        ],
        start=1,
    ):
        item = epub.EpubHtml(
            title=title,
            file_name=f"chap_{index}.xhtml",
            lang="es",
        )
        item.content = f"<h1>{title}</h1><p>{body}</p>"
        book.add_item(item)
        chapters.append(item)

    book.toc = tuple(chapters)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav", *[chapter.id for chapter in chapters]]

    path = tmp_path / "tiny.epub"
    epub.write_epub(str(path), book)
    return path


@pytest.fixture
def block_text_epub(tmp_path: Path) -> Path:
    book = epub.EpubBook()
    book.set_identifier("audiol-test-block-123")
    book.set_title("Libro con bloques")
    book.set_language("es")
    book.add_author("Autora")

    chapters = []
    for index, (title, body) in enumerate(
        [
            (
                "Capítulo de bloque",
                "<h1>Capítulo de bloque</h1>"
                "<div>Texto del capítulo sin párrafos.</div>",
            ),
            (
                "Capítulo suelto",
                "<h1>Capítulo suelto</h1>Texto suelto sin etiquetas.",
            ),
        ],
        start=1,
    ):
        item = epub.EpubHtml(
            title=title,
            file_name=f"block_{index}.xhtml",
            lang="es",
        )
        item.content = body
        book.add_item(item)
        chapters.append(item)

    book.toc = tuple(chapters)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav", *[chapter.id for chapter in chapters]]

    path = tmp_path / "blocks.epub"
    epub.write_epub(str(path), book)
    return path
