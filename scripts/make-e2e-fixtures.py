from pathlib import Path

from ebooklib import epub

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"


SHORT_CONTENTS = [
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

LONG_PARAGRAPHS = [
    "La casa de la colina guardaba el rumor del viento entre sus paredes de piedra.",
    "Cada mañana, el sol entraba por la ventana del este y dibujaba líneas sobre la mesa.",
    "Nadie recordaba quién había plantado el olivo del patio, pero todos cuidaban de él.",
    "Los cuadernos de la abuela dormían en un cajón con olor a madera y a romero.",
    "Cuando llegó el invierno, las chimeneas encendidas cambiaron el color del valle.",
    "El pan de cada tarde se repartía en silencio, sin que faltara un solo trozo.",
    "En el desván había mapas antiguos y una brújula que apuntaba siempre al norte.",
    "La lluvia golpeaba las tejas con un ritmo que los niños aprendieron a imitar.",
    "Al caer la noche, la lámpara del comedor reunía historias de varias generaciones.",
    "El río bajaba frío y claro, arrastrando hojas, promesas y algún nombre olvidado.",
]

LONG_CONTENTS = [
    (
        f"Capítulo {chapter}",
        [
            f"Párrafo {index + 1}. {LONG_PARAGRAPHS[(chapter * 3 + index) % len(LONG_PARAGRAPHS)]}"
            for index in range(24)
        ],
    )
    for chapter in range(1, 4)
]


def build(path: Path, title: str, contents: list[tuple[str, list[str]]]) -> None:
    book = epub.EpubBook()
    book.set_identifier(f"vibebook-e2e-{path.stem}")
    book.set_title(title)
    book.set_language("es")
    book.add_author("Equipo de pruebas")

    chapters = []
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
    build(FIXTURES / "e2e-reader.epub", "Lector E2E", SHORT_CONTENTS)
    build(FIXTURES / "e2e-studio.epub", "Studio E2E", SHORT_CONTENTS)
    build(FIXTURES / "e2e-book.epub", "Libro E2E", LONG_CONTENTS)


if __name__ == "__main__":
    main()
