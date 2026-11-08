from pathlib import Path

from ebooklib import epub

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"


def build(path: Path, title: str) -> None:
    book = epub.EpubBook()
    book.set_identifier(f"vibebook-e2e-{path.stem}")
    book.set_title(title)
    book.set_language("es")
    book.add_author("Equipo de pruebas")

    chapters = []
    contents = [
        (
            "Capítulo 1",
            [
                "Hola mundo desde Vibebook. Esta es la primera prueba de lectura sincronizada.",
                "El lector debe resaltar el párrafo y la palabra mientras avanza el audio.",
            ],
        ),
        (
            "Capítulo 2",
            [
                "Segundo capítulo de prueba. El audio debe continuar y el texto debe seguirlo.",
                "Al recargar, la posición y la velocidad deben conservarse sin autoplay.",
            ],
        ),
    ]
    for index, (chapter_title, paragraphs) in enumerate(contents, start=1):
        item = epub.EpubHtml(
            title=chapter_title,
            file_name=f"chapter_{index}.xhtml",
            lang="es",
        )
        body = "".join(f"<p>{paragraph}</p>" for paragraph in paragraphs)
        item.content = f"<h1>{chapter_title}</h1>{body}"
        book.add_item(item)
        chapters.append(item)

    book.toc = tuple(chapters)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav", *[chapter.id for chapter in chapters]]
    epub.write_epub(str(path), book)


def main() -> None:
    FIXTURES.mkdir(parents=True, exist_ok=True)
    build(FIXTURES / "e2e-reader.epub", "Lector E2E")
    build(FIXTURES / "e2e-studio.epub", "Studio E2E")


if __name__ == "__main__":
    main()
