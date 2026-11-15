"""Build the permanent reader fixture used for manual and automated tests.

The EPUB includes a cover, a title page, a nested table of contents, five
chapters, dialogues, long and short paragraphs, and an illustration. It is
small enough to convert with the fake engine in seconds but long enough to
paginate into several reading pages.
"""

from __future__ import annotations

import io
from pathlib import Path

from ebooklib import epub
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "samples" / "lector-de-prueba.epub"

PAPER = (239, 230, 213)
INK = (38, 34, 29)
OXBLOOD = (91, 32, 34)
BRASS = (166, 132, 71)
SLATE = (64, 80, 91)
SEA = (74, 101, 111)
LIGHT_SEA = (177, 194, 191)

CHAPTERS = [
    (
        "El mapa de las mareas",
        [
            "La casa de los Ferrer se levantaba sobre una loma que olía a sal y a romero. "
            "Desde la ventana del norte se veía el puerto, las grúas dormidas y una línea de "
            "barcos que entraban y salían con la paciencia de las cosas que siempre vuelven.",
            "Lucía había heredado la casa en marzo, junto con un mapa que no representaba "
            "ninguna costa conocida. El papel era grueso, casi tela, y en el borde inferior "
            "alguien había escrito una fecha: 14 de agosto de 1932.",
            "—No es un mapa —dijo el bibliotecario—. Es una partitura.\n"
            "—¿De qué?\n"
            "—De lo que se mueve cuando nadie mira.",
            "Lucía dobló el mapa con cuidado. Afuera, la marea subía y el muelle crujía como "
            "un mueble viejo. Decidió volver al día siguiente, cuando hubiera luz suficiente "
            "para distinguir las marcas del papel.",
        ],
    ),
    (
        "La casa del relojero",
        [
            "El taller del relojero ocupaba la planta baja de una casa estrecha. Había "
            "relojes de pared, relojes de bolsillo y un autómata de madera que movía la "
            "cabeza cada cuarto de hora, como si aprobara alguna conversación invisible.",
            "—Mi padre decía que los relojes no miden el tiempo —contó el hombre—. Lo "
            "guardan. Cada uno tiene su manera de hacerlo.",
            "Lucía apoyó el mapa sobre el mostrador. El relojero lo miró sin tocarlo. "
            "Después encendió una lámpara y acercó una lupa con montura de latón.",
            "—Aquí hay una ruta —dijo—. Pero no empieza en el puerto. Empieza en tu casa, "
            "en la habitación que da al norte.",
            "El autómata levantó la cabeza. En la calle, una campana respondió a lo lejos, "
            "y por un instante Lucía tuvo la certeza de que el mapa había cambiado de color.",
        ],
    ),
    (
        "Lo que la marea devuelve",
        [
            "Aquella noche Lucía subió a la habitación del norte con una vela y el mapa. "
            "La ventana estaba abierta; el viento movía las cortinas con una insistencia "
            "que no era del todo natural.",
            "En la pared encontró una grieta que no recordaba. Dentro había una caja de "
            "madera, del tamaño de un libro de oraciones. La tapa tenía la misma marca que "
            "el borde del mapa: tres olas concéntricas.",
            "Dentro de la caja había una carta y una llave. La letra era pequeña, inclinada, "
            "y hablaba de una barca que no debía volver a zarpar.",
            "«Si alguien encuentra esto —decía la carta—, que no encienda la luz del faro "
            "hasta que la marea haya bajado del todo. Hay cosas que solo regresan cuando "
            "la costa se queda a oscuras.»",
            "Lucía leyó la carta dos veces. Luego miró por la ventana. El faro estaba "
            "apagado, pero la marea ya empezaba a retirarse.",
        ],
    ),
    (
        "La barca sin nombre",
        [
            "Al amanecer bajó al puerto con la llave en el bolsillo. El agua tenía ese "
            "color gris que anuncia un día sin decisiones fáciles. Los pescadores "
            "preparaban las redes y nadie parecía advertir la ausencia de la barca.",
            "En el extremo del muelle, detrás de una caseta de madera, encontró el nombre "
            "pintado en un cartel: «La barca sin nombre». Sonrió a pesar del frío.",
            "La llave abrió una caja de herramientas. Dentro no había herramientas, sino "
            "un cuaderno de bitácora y una brújula que no apuntaba al norte. La aguja "
            "señalaba la casa de Lucía.",
            "—Tu abuelo decía que esa brújula estaba rota —dijo una voz detrás de ella.\n"
            "Lucía se giró. Era el relojero, con un abrigo demasiado grande y los zapatos "
            "llenos de arena.\n"
            "—No estaba rota —respondió—. Solo buscaba otra cosa.",
        ],
    ),
    (
        "La luz del faro",
        [
            "La tormenta llegó antes de lo previsto. Las olas golpeaban el malecón y el "
            "viento arrancaba las últimas hojas de los plátanos. Lucía subió al faro con "
            "la llave y el cuaderno.",
            "En la sala de máquinas encontró una lámpara distinta a las demás. No tenía "
            "cable, ni mecha, ni botón. Solo una pequeña ranura con la forma de la aguja "
            "de la brújula.",
            "—Si la enciendes, la costa va a cambiar —dijo el relojero desde la puerta—. "
            "No sé si para mejor.",
            "Lucía pensó en la casa, en la carta, en la barca que llevaba años esperando "
            "en el muelle. Pensó también en las cosas que se guardan para que otro las "
            "encuentre.",
            "Encendió la lámpara. La luz no fue blanca ni dorada: fue del color exacto "
            "del mapa. Y en el puerto, muy lejos, la marea empezó a devolver un barco "
            "que nadie recordaba haber perdido.",
        ],
    ),
]


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        Path("C:/Windows/Fonts/georgia.ttf" if not bold else "C:/Windows/Fonts/georgiab.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"),
        Path("/Library/Fonts/Georgia.ttf"),
        Path("/System/Library/Fonts/Supplemental/Georgia.ttf"),
    ]
    for candidate in candidates:
        if candidate.is_file():
            try:
                return ImageFont.truetype(str(candidate), size)
            except OSError:
                continue
    return ImageFont.load_default()


def _text_width(draw: ImageDraw.ImageDraw, text: str, font) -> int:
    box = draw.textbbox((0, 0), text, font=font)
    return box[2] - box[0]


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if _text_width(draw, candidate, font) <= width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _cover() -> bytes:
    width, height = 1200, 1800
    image = Image.new("RGB", (width, height), PAPER)
    draw = ImageDraw.Draw(image)

    # Cloth-like horizontal grain.
    for y in range(0, height, 6):
        tone = tuple(max(0, channel - 4) for channel in PAPER)
        draw.line((0, y, width, y), fill=tone, width=1)

    draw.rectangle((0, 0, 96, height), fill=OXBLOOD)
    draw.rectangle((96, 0, 102, height), fill=BRASS)
    draw.text((132, 84), "VIBEBOOK · BIBLIOTECA", font=_font(24, bold=True), fill=BRASS)

    title_font = _font(108, bold=True)
    author_font = _font(46)
    label_font = _font(24, bold=True)
    title = "El mapa\nde las\nmareas"
    y = 300
    for line in title.splitlines():
        draw.text((132, y), line, font=title_font, fill=INK)
        y += 124

    draw.line((132, y + 36, 620, y + 36), fill=BRASS, width=3)
    draw.text((132, y + 62), "LUCÍA FERRER", font=author_font, fill=SLATE)
    draw.text((132, y + 132), "NOVELA", font=label_font, fill=BRASS)

    # A restrained wave motif at the foot of the cover.
    base = 1510
    for index in range(5):
        offset = index * 18
        draw.arc(
            (720 - offset, base - 240 - offset, 1160 + offset, base + 40 + offset),
            start=200,
            end=340,
            fill=SEA if index % 2 else LIGHT_SEA,
            width=5,
        )
    draw.text((132, 1680), "VB · 01", font=_font(22), fill=BRASS)

    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def _illustration() -> bytes:
    width, height = 1400, 820
    image = Image.new("RGB", (width, height), PAPER)
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, width, height), fill=PAPER)

    # Sky, sun, sea, and a small boat: an editorial line drawing in the app palette.
    draw.arc((930, 90, 1140, 300), start=0, end=360, fill=BRASS, width=6)
    for y, color, thickness in [
        (470, SEA, 4),
        (510, LIGHT_SEA, 3),
        (558, SEA, 3),
        (606, LIGHT_SEA, 2),
        (652, SEA, 2),
    ]:
        draw.line((90, y, 1310, y), fill=color, width=thickness)
    draw.polygon([(610, 500), (790, 500), (748, 560), (650, 560)], fill=PAPER, outline=OXBLOOD)
    draw.line((700, 500, 700, 340), fill=OXBLOOD, width=4)
    draw.polygon([(704, 345), (704, 470), (840, 470)], fill=OXBLOOD)
    draw.line((90, 700, 1310, 700), fill=BRASS, width=2)
    draw.text((90, 726), "La barca sin nombre · tinta sobre papel", font=_font(28), fill=SLATE)

    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def build() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    book = epub.EpubBook()
    book.set_identifier("vibebook-reader-lab-2026")
    book.set_title("El mapa de las mareas")
    book.set_language("es")
    book.add_author("Lucía Ferrer")
    book.add_metadata("DC", "publisher", "Biblioteca Vibebook")
    book.add_metadata(
        "DC",
        "description",
        "Fixture editorial con portada, índice, cinco capítulos, diálogos e ilustración.",
    )
    book.set_cover("cover.png", _cover())

    title_page = epub.EpubHtml(title="Portada interior", file_name="title.xhtml", lang="es")
    title_page.content = (
        "<section epub:type='titlepage'>"
        "<h1>El mapa de las mareas</h1>"
        "<p>Lucía Ferrer</p>"
        "<p>Biblioteca Vibebook · Edición de prueba</p>"
        "</section>"
    )
    book.add_item(title_page)

    image = epub.EpubImage()
    image.file_name = "images/la-barca.png"
    image.media_type = "image/png"
    image.content = _illustration()
    book.add_item(image)

    chapters: list[epub.EpubHtml] = []
    for index, (title, paragraphs) in enumerate(CHAPTERS, start=1):
        chapter = epub.EpubHtml(
            title=title,
            file_name=f"chapter_{index}.xhtml",
            lang="es",
        )
        body: list[str] = [f"<h1>{title}</h1>"]
        for paragraph_index, paragraph in enumerate(paragraphs, start=1):
            body.append(f"<p>{paragraph}</p>")
            if index == 3 and paragraph_index == 2:
                body.append(
                    "<figure>"
                    "<img src='images/la-barca.png' alt='Ilustración de una barca frente al mar'/>"
                    "<figcaption>La barca sin nombre, según el cuaderno del farero.</figcaption>"
                    "</figure>"
                )
        chapter.content = "<section>" + "".join(body) + "</section>"
        book.add_item(chapter)
        chapters.append(chapter)

    book.toc = tuple(chapters)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav", title_page, *chapters]
    epub.write_epub(str(OUT), book)
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    build()
