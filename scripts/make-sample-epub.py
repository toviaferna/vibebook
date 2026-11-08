from pathlib import Path

from ebooklib import epub

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "samples" / "lector-de-prueba.epub"

CHAPTERS = [
    (
        "El taller de los relojes",
        [
            (
                "En una calle estrecha de la ciudad había un taller de relojes "
                "que abría antes del amanecer."
            ),
            (
                "Su dueña, Elena, decía que los relojes no medían el tiempo: "
                "lo guardaban en pequeñas cajas de metal."
            ),
        ],
    ),
    (
        "La voz del papel",
        [
            "Una mañana llegó un libro sin portada. Sus páginas olían a madera y a lluvia.",
            "Elena lo leyó en voz alta mientras los relojes hacían coro con sus tic-tacs.",
        ],
    ),
    (
        "Un minuto más",
        [
            (
                "Cuando terminó la última página, el taller pareció quedarse "
                "un minuto más en silencio."
            ),
            "Desde entonces, los relojes de Elena siempre daban la hora con una pequeña sonrisa.",
        ],
    ),
]


def main() -> None:
    book = epub.EpubBook()
    book.set_identifier("vibebook-sample-lector-de-prueba")
    book.set_title("Lector de prueba")
    book.set_language("es")
    book.add_author("Vibebook")

    items = []
    for index, (title, paragraphs) in enumerate(CHAPTERS, start=1):
        item = epub.EpubHtml(title=title, file_name=f"chapter_{index}.xhtml", lang="es")
        body = "".join(f"<p>{paragraph}</p>" for paragraph in paragraphs)
        item.content = f"<h1>{title}</h1>{body}"
        book.add_item(item)
        items.append(item)

    book.toc = tuple(items)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav", *[item.id for item in items]]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    epub.write_epub(str(OUT), book)
    print(OUT)


if __name__ == "__main__":
    main()
