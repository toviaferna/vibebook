from pathlib import Path

from ebooklib import epub

from audiol.ingest.epub import read_epub


def _write_epub(path: Path, language: str, text: str) -> None:
    book = epub.EpubBook()
    book.set_identifier(f"language-fixture-{language}")
    book.set_title("Idioma de prueba")
    book.set_language(language)
    book.add_author("Autora")
    chapter = epub.EpubHtml(title="Capítulo 1", file_name="chapter_1.xhtml", lang=language)
    chapter.content = f"<h1>Capítulo 1</h1><p>{text}</p>"
    book.add_item(chapter)
    book.toc = (chapter,)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav", chapter]
    epub.write_epub(str(path), book)


def test_spanish_text_overrides_english_metadata(tmp_path: Path):
    path = tmp_path / "wrong-language.epub"
    _write_epub(
        path,
        "en",
        "La casa de los Ferrer se levantaba sobre una loma que olía a sal y a romero. "
        "Desde la ventana del norte se veía el puerto y una línea de barcos que entraban "
        "y salían con la paciencia de las cosas que siempre vuelven.",
    )

    book = read_epub(path)

    assert book.language == "es"


def test_english_text_overrides_spanish_metadata(tmp_path: Path):
    path = tmp_path / "wrong-language-en.epub"
    _write_epub(
        path,
        "es",
        "The house of the Ferrer family stood on a hill that smelled of salt and rosemary. "
        "From the north window you could see the harbor and a line of boats that came and "
        "went with the patience of things that always return.",
    )

    book = read_epub(path)

    assert book.language == "en"
