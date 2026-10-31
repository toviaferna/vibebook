import logging
from pathlib import Path

import ebooklib
from bs4 import BeautifulSoup
from ebooklib import epub

from audiol.models import Book, Chapter, Segment

logger = logging.getLogger(__name__)


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
            paragraphs = _extract_block_text(soup)
        if not paragraphs:
            logger.warning(
                "Skipping spine document %s: no readable text", item.get_name()
            )
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


def _extract_block_text(soup: BeautifulSoup) -> list[str]:
    blocks = [
        block
        for block in soup.find_all(["div", "blockquote"])
        if block.find_parent(["div", "blockquote"]) is None
    ]
    texts = [block.get_text(" ", strip=True) for block in blocks]
    texts = [text for text in texts if text]
    if texts:
        return texts

    container = soup.body or soup
    return [
        line.strip()
        for line in container.get_text("\n", strip=True).splitlines()
        if line.strip()
    ]
