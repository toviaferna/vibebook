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
                "<h1>Capítulo de bloque</h1><div>Texto del capítulo sin párrafos.</div>",
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


@pytest.fixture
def toc_epub(tmp_path: Path) -> Path:
    book = epub.EpubBook()
    book.set_identifier("audiol-test-toc-123")
    book.set_title("Libro con índice")
    book.set_language("es")
    book.add_author("Autora")

    content = epub.EpubHtml(title="Contenido", file_name="content.xhtml", lang="es")
    content.content = (
        "<p>Front matter.</p>"
        '<p><a id="top"></a>Libro con índice</p>'
        '<p><a id="ch1"></a>1</p>'
        "<p>Primer párrafo.</p>"
        "<p>Segundo párrafo.</p>"
        '<p><a id="ch2"></a>2</p>'
        "<p>Tercer párrafo.</p>"
    )
    book.add_item(content)

    outline = epub.EpubHtml(title="Document Outline", file_name="outline.xhtml", lang="es")
    outline.content = "<h1>Document Outline</h1><ul><li>1</li><li>2</li></ul>"
    book.add_item(outline)

    continuation = epub.EpubHtml(title="Continuación", file_name="continuation.xhtml", lang="es")
    continuation.content = (
        '<p>Continuación del capítulo 2.</p><p><a id="ch3"></a>3</p><p>Cuarto párrafo.</p>'
    )
    book.add_item(continuation)

    book.toc = (
        epub.Link("content.xhtml#top", "Libro con índice", "top"),
        epub.Link("content.xhtml#ch1", "1", "ch1"),
        epub.Link("content.xhtml#ch2", "2", "ch2"),
        epub.Link("continuation.xhtml#ch3", "3", "ch3"),
        epub.Link("content.xhtml#top", "FIN", "fin"),
    )
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav", content.id, continuation.id, outline.id]

    path = tmp_path / "toc.epub"
    epub.write_epub(str(path), book)
    return path


@pytest.fixture
def cover_epub(tmp_path: Path) -> Path:
    book = epub.EpubBook()
    book.set_identifier("audiol-test-cover-123")
    book.set_title("Libro con portada")
    book.set_language("es")
    book.add_author("Autora")
    book.set_cover("cover.jpg", b"\xff\xd8\xff\xe0" + b"0" * 64)

    chapter = epub.EpubHtml(title="Capítulo 1", file_name="cover_chapter.xhtml", lang="es")
    chapter.content = "<h1>Capítulo 1</h1><p>Texto con portada.</p>"
    book.add_item(chapter)
    book.toc = (chapter,)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav", chapter.id]

    path = tmp_path / "cover.epub"
    epub.write_epub(str(path), book)
    return path


@pytest.fixture
def mixed_block_epub(tmp_path: Path) -> Path:
    book = epub.EpubBook()
    book.set_identifier("audiol-test-mixed-123")
    book.set_title("Libro con bloques mixtos")
    book.set_language("es")
    book.add_author("Autora")

    chapters = []
    for index, (title, body) in enumerate(
        [
            (
                "Capítulo mixto",
                "<h1>Capítulo mixto</h1>"
                "<p>Intro.</p>"
                "<blockquote>Cita.</blockquote>"
                "<div>Bloque.</div>"
                "<ul><li><p>Anidado.</p></li></ul>",
            ),
            (
                "Capítulo suelto",
                "<h1>Capítulo suelto</h1>Texto suelto.",
            ),
        ],
        start=1,
    ):
        item = epub.EpubHtml(
            title=title,
            file_name=f"mixed_{index}.xhtml",
            lang="es",
        )
        item.content = body
        book.add_item(item)
        chapters.append(item)

    book.toc = tuple(chapters)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav", *[chapter.id for chapter in chapters]]

    path = tmp_path / "mixed.epub"
    epub.write_epub(str(path), book)
    return path
