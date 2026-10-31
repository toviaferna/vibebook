from pathlib import Path

import ebooklib
from bs4 import BeautifulSoup
from ebooklib import epub

from audiol.models import Book, Chapter, Segment


def read_epub(path: Path) -> Book:
    raw = epub.read_epub(str(path))
    title = _first_metadata(raw, "title") or path.stem
    author = _first_metadata(raw, "creator") or "Desconocido"
    language = _first_metadata(raw, "language") or "es"

    chapters: list[Chapter] = []
    chapter_index = 0

    for idref, _linear in raw.spine:
        item = raw.get_item_with_id(idref)
        if item is None or item.get_type() != ebooklib.ITEM_DOCUMENT:
            continue
        name = item.get_name().lower()
        if name.endswith(("nav.xhtml", "toc.xhtml")):
            continue

        soup = BeautifulSoup(item.get_content(), "lxml")
        heading = soup.find(["h1", "h2", "h3"])
        chapter_title = (
            heading.get_text(" ", strip=True) if heading else f"Capítulo {chapter_index + 1}"
        )
        paragraphs = [
            element.get_text(" ", strip=True)
            for element in soup.find_all(["p", "li"])
        ]
        paragraphs = [paragraph for paragraph in paragraphs if paragraph]
        if not paragraphs:
            continue

        chapter_index += 1
        segments = [
            Segment(
                id=f"c{chapter_index:03d}p{index + 1:04d}",
                chapter_index=chapter_index,
                paragraph_index=index + 1,
                text=text,
            )
            for index, text in enumerate(paragraphs)
        ]
        chapters.append(
            Chapter(index=chapter_index, title=chapter_title, segments=segments)
        )

    return Book(title=title, author=author, language=language, chapters=chapters)


def _first_metadata(book: epub.EpubBook, name: str) -> str | None:
    values = book.get_metadata("DC", name)
    return values[0][0] if values else None
