import logging
import re
from pathlib import Path

import ebooklib
from bs4 import BeautifulSoup, Tag
from ebooklib import epub

from audiol.models import Book, Chapter, Segment, make_segment_id

logger = logging.getLogger(__name__)

BLOCK_TAGS = ["p", "li", "blockquote", "pre", "div"]
NAV_TITLES = {
    "contents",
    "copyright",
    "cubierta",
    "dedication",
    "dedicatoria",
    "document outline",
    "fin",
    "indice",
    "portada",
    "table of contents",
    "title page",
    "índice",
}


def read_epub(path: Path) -> Book:
    raw = epub.read_epub(str(path))
    title = _first_metadata(raw, "title") or path.stem
    author = _first_metadata(raw, "creator") or "Desconocido"
    language = _first_metadata(raw, "language") or "es"
    toc = _toc_by_item(raw, title, author)

    chapters: list[Chapter] = []
    chapter_index = 0

    for idref, linear in raw.spine:
        if linear == "no":
            continue
        item = raw.get_item_with_id(idref)
        if item is None or item.get_type() != ebooklib.ITEM_DOCUMENT:
            continue
        name = item.get_name().lower()
        if name.endswith(("nav.xhtml", "toc.xhtml")):
            continue

        soup = BeautifulSoup(item.get_content(), "lxml")
        entries = toc.get(item.get_name())
        if entries:
            prefix, split_chapters = _split_document(soup, entries)
            if prefix and chapters:
                _add_paragraphs(chapters[-1], prefix, source_href=item.get_name())
            for chapter_title, paragraphs, fragment in split_chapters:
                chapter_index = _append_chapter(
                    chapters,
                    chapter_index,
                    chapter_title,
                    paragraphs,
                    source_href=item.get_name(),
                    source_fragment=fragment,
                )
            continue

        heading = soup.find(["h1", "h2", "h3"])
        if heading and _normalize(heading.get_text(" ", strip=True)) in NAV_TITLES:
            logger.warning("Skipping navigation document %s", item.get_name())
            continue
        chapter_title = (
            heading.get_text(" ", strip=True) if heading else f"Capítulo {chapter_index + 1}"
        )
        paragraphs = [element.get_text(" ", strip=True) for element in _top_level_blocks(soup)]
        paragraphs = [paragraph for paragraph in paragraphs if paragraph]
        if not paragraphs:
            paragraphs = _extract_bare_text(soup)
        if not paragraphs:
            logger.warning("Skipping spine document %s: no readable text", item.get_name())
            continue
        chapter_index = _append_chapter(
            chapters,
            chapter_index,
            chapter_title,
            paragraphs,
            source_href=item.get_name(),
        )

    return Book(title=title, author=author, language=language, chapters=chapters)


def _append_chapter(
    chapters: list[Chapter],
    chapter_index: int,
    title: str,
    paragraphs: list[str],
    source_href: str | None = None,
    source_fragment: str | None = None,
) -> int:
    paragraphs = [paragraph for paragraph in paragraphs if paragraph]
    if not paragraphs:
        return chapter_index
    chapter_index += 1
    chapter = Chapter(
        index=chapter_index,
        title=title,
        source_href=source_href,
        source_fragment=source_fragment,
    )
    _add_paragraphs(chapter, paragraphs)
    chapters.append(chapter)
    return chapter_index


def _add_paragraphs(
    chapter: Chapter,
    paragraphs: list[str],
    source_href: str | None = None,
    source_fragment: str | None = None,
) -> None:
    start = len(chapter.segments) + 1
    resolved_href = source_href if source_href is not None else chapter.source_href
    resolved_fragment = source_fragment if source_fragment is not None else chapter.source_fragment
    for offset, text in enumerate(paragraphs):
        index = start + offset
        chapter.segments.append(
            Segment(
                id=make_segment_id(chapter.index, index),
                chapter_index=chapter.index,
                paragraph_index=index,
                text=text,
                source_href=resolved_href,
                source_fragment=resolved_fragment,
            )
        )


def _first_metadata(book: epub.EpubBook, name: str) -> str | None:
    values = book.get_metadata("DC", name)
    return values[0][0] if values else None


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


def _flatten_toc(items) -> list:
    links = []
    for item in items:
        if isinstance(item, tuple):
            _, children = item
            links.extend(_flatten_toc(children))
        elif getattr(item, "href", None):
            links.append(item)
    return links


def _toc_by_item(
    book: epub.EpubBook, title: str, author: str
) -> dict[str, list[tuple[str | None, str]]]:
    grouped: dict[str, list[tuple[str | None, str]]] = {}
    normalized_book_title = _normalize(title)
    normalized_author = _normalize(author)
    for link in _flatten_toc(book.toc):
        raw_title = (link.title or "").strip()
        if not raw_title:
            continue
        normalized_title = _normalize(raw_title)
        if normalized_title in NAV_TITLES:
            continue
        if normalized_title in {normalized_book_title, normalized_author}:
            continue
        if normalized_book_title in normalized_title and normalized_author in normalized_title:
            continue
        item_name, _, fragment = link.href.partition("#")
        if not item_name:
            continue
        grouped.setdefault(item_name, []).append((fragment or None, _chapter_title(raw_title)))
    for item_name, entries in grouped.items():
        fragments = [entry for entry in entries if entry[0]]
        if fragments:
            grouped[item_name] = fragments
    return grouped


def _chapter_title(title: str) -> str:
    return f"Capítulo {title}" if title.isdigit() else title


def _split_document(
    soup: BeautifulSoup, entries: list[tuple[str | None, str]]
) -> tuple[list[str], list[tuple[str, list[str], str | None]]]:
    blocks = _top_level_blocks(soup)
    if len(entries) == 1 and entries[0][0] is None:
        return [], [(entries[0][1], _block_texts(blocks) or _extract_bare_text(soup), None)]

    order = {id(tag): index for index, tag in enumerate(soup.find_all(True))}
    anchors: list[tuple[int, str | None, str]] = []
    for anchor, title in entries:
        if anchor is None:
            anchors.append((-1, None, title))
            continue
        tag = soup.find(id=anchor)
        if tag is None:
            logger.warning("TOC anchor %s not found", anchor)
            continue
        anchors.append((order[id(tag)], anchor, title))
    if not anchors:
        return [], [(entries[0][1], _block_texts(blocks) or _extract_bare_text(soup), None)]

    prefix: list[str] = []
    chapters: list[tuple[str, list[str], str | None]] = []
    for block in blocks:
        anchor_ids = {tag.get("id") for tag in block.find_all(id=True)}
        inside = [entry for entry in anchors if entry[1] in anchor_ids]
        block_position = order[id(block)]
        before = [entry for entry in anchors if entry[0] < block_position]
        candidate = inside[0] if inside else (before[-1] if before else None)
        text = block.get_text(" ", strip=True)
        if candidate is None:
            if text and not _is_label(text, entries[0][1]):
                prefix.append(text)
            continue
        title = candidate[2]
        if not chapters or chapters[-1][0] != title:
            chapters.append((title, [], candidate[1]))
        if text and not _is_label(text, title):
            chapters[-1][1].append(text)
    if not any(paragraphs for _, paragraphs, _ in chapters):
        return prefix, [(entries[0][1], _extract_bare_text(soup), None)]
    return prefix, chapters


def _block_texts(blocks: list[Tag]) -> list[str]:
    return [block.get_text(" ", strip=True) for block in blocks if block.get_text(" ", strip=True)]


def _is_label(text: str, title: str) -> bool:
    normalized = _normalize(text)
    if normalized.isdigit() and _normalize(title) == f"capítulo {normalized}":
        return True
    return normalized == _normalize(title)


def _top_level_blocks(soup: BeautifulSoup) -> list:
    selected = []
    for block in soup.find_all(BLOCK_TAGS):
        if block.name == "div" and block.find(BLOCK_TAGS):
            continue
        if block.find_parent(["p", "li", "blockquote", "pre"]) is not None:
            continue
        selected.append(block)
    return selected


def _extract_bare_text(soup: BeautifulSoup) -> list[str]:
    fallback = BeautifulSoup(str(soup), "lxml")
    for heading in fallback.find_all(["h1", "h2", "h3"]):
        heading.decompose()

    container = fallback.body or fallback
    return [
        line.strip() for line in container.get_text("\n", strip=True).splitlines() if line.strip()
    ]
