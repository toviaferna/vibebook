import logging
from dataclasses import dataclass
from pathlib import Path

import ebooklib
from bs4 import BeautifulSoup
from ebooklib import epub

from audiol.ingest.structure import (
    HeadingSection,
    TocEntry,
    block_texts,
    build_manifest_toc,
    build_toc,
    entries_by_document,
    extract_bare_text,
    heading_split,
    is_label,
    normalize_href,
    parse_number,
    toc_from_chapters,
    top_level_blocks,
)
from audiol.models import Book, Chapter, Segment, make_segment_id

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _SplitChapter:
    title: str
    paragraphs: list[str]
    fragment: str | None
    level: int
    kind: str


def read_epub(path: Path) -> Book:
    raw = epub.read_epub(str(path))
    title = _first_metadata(raw, "title") or path.stem
    author = _first_metadata(raw, "creator") or "Desconocido"
    language = _first_metadata(raw, "language") or "es"
    toc = build_toc(raw, title, author)
    by_document = entries_by_document(toc)

    chapters: list[Chapter] = []
    chapter_index = 0

    for idref, linear in raw.spine:
        if linear == "no":
            continue
        item = raw.get_item_with_id(idref)
        if item is None or item.get_type() != ebooklib.ITEM_DOCUMENT:
            continue
        item_name, _ = normalize_href(item.get_name())
        if item_name.endswith(("nav.xhtml", "toc.xhtml")):
            continue

        soup = BeautifulSoup(item.get_content(), "lxml")
        entries = by_document.get(item_name, [])
        fragment_entries = [entry for entry in entries if entry.fragment]

        if fragment_entries:
            prefix, split_chapters = _split_document(soup, fragment_entries)
            if prefix and chapters:
                _add_paragraphs(chapters[-1], prefix, source_href=item_name)
            for split_chapter in split_chapters:
                chapter_index = _append_chapter(
                    chapters,
                    chapter_index,
                    split_chapter.title,
                    split_chapter.paragraphs,
                    source_href=item_name,
                    source_fragment=split_chapter.fragment,
                    level=split_chapter.level,
                    kind=split_chapter.kind,
                )
            continue

        split = heading_split(soup, title)
        if split.prefix and chapters:
            prefix_texts = block_texts(split.prefix)
            if prefix_texts:
                _add_paragraphs(chapters[-1], prefix_texts, source_href=item_name)

        if not entries and len(split.sections) == 1 and split.sections[0].kind == "skip":
            logger.warning("Skipping navigation document %s", item.get_name())
            continue

        sections = [
            section
            for section in split.sections
            if section.kind != "skip" and (section.blocks or extract_bare_text(soup))
        ]
        if len(sections) > 1:
            for heading_section in sections:
                paragraphs = block_texts(heading_section.blocks) or extract_bare_text(soup)
                if not paragraphs:
                    continue
                chapter_index = _append_chapter(
                    chapters,
                    chapter_index,
                    heading_section.title,
                    paragraphs,
                    source_href=item_name,
                    source_fragment=heading_section.fragment,
                    level=heading_section.level,
                    kind=heading_section.kind,
                )
            continue

        entry_title = entries[0].title if entries else ""
        selected_section: HeadingSection | None = sections[0] if sections else None
        chapter_title = entry_title or (selected_section.title if selected_section else "")
        generated_title = not bool(chapter_title)
        if not chapter_title:
            chapter_title = f"CapÃƒÂ­tulo {chapter_index + 1}"
        paragraphs = block_texts(selected_section.blocks) if selected_section else []
        if not paragraphs:
            paragraphs = extract_bare_text(soup)
        if not paragraphs:
            logger.warning("Skipping spine document %s: no readable text", item.get_name())
            continue
        kind = _entry_kind(entries, selected_section)
        if kind == "skip":
            logger.warning("Skipping navigation document %s", item.get_name())
            continue
        chapter_index = _append_chapter(
            chapters,
            chapter_index,
            chapter_title,
            paragraphs,
            source_href=item_name,
            source_fragment=selected_section.fragment if selected_section else None,
            level=selected_section.level if selected_section else 1,
            kind=kind,
            generated_title=generated_title,
        )

    chapter_sources = _chapter_sources(chapters)
    manifest_toc = build_manifest_toc(toc, chapter_sources)
    if not manifest_toc:
        manifest_toc = toc_from_chapters(chapters)
    return Book(
        title=title,
        author=author,
        language=language,
        chapters=chapters,
        toc=manifest_toc,
    )


def _entry_kind(entries: list[TocEntry], section: HeadingSection | None) -> str:
    if entries:
        entry = entries[0]
        if entry.kind != "chapter":
            return entry.kind
    if section is not None:
        return section.kind
    return "chapter"


def _chapter_level(entry: TocEntry) -> int:
    return 0 if entry.kind == "part" else 1


def _chapter_sources(chapters: list[Chapter]) -> dict[tuple[str, str | None], int]:
    sources: dict[tuple[str, str | None], int] = {}
    for chapter in chapters:
        if not chapter.source_href:
            continue
        sources.setdefault((chapter.source_href, chapter.source_fragment), chapter.index)
        sources.setdefault((chapter.source_href, None), chapter.index)
    return sources


def _append_chapter(
    chapters: list[Chapter],
    chapter_index: int,
    title: str,
    paragraphs: list[str],
    source_href: str | None = None,
    source_fragment: str | None = None,
    level: int = 1,
    kind: str = "chapter",
    generated_title: bool = False,
) -> int:
    paragraphs = [paragraph for paragraph in paragraphs if paragraph]
    if not paragraphs or kind == "skip":
        return chapter_index
    chapter_index += 1
    chapter = Chapter(
        index=chapter_index,
        title=title,
        source_href=source_href,
        source_fragment=source_fragment,
        level=level,
        kind=kind,
        number=parse_number(title) if not generated_title else None,
        generated_title=generated_title,
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


def _split_document(
    soup: BeautifulSoup, entries: list[TocEntry]
) -> tuple[list[str], list[_SplitChapter]]:
    blocks = top_level_blocks(soup)
    if len(entries) == 1 and entries[0].fragment is None:
        entry = entries[0]
        return [], [
            _SplitChapter(
                title=entry.title,
                paragraphs=block_texts(blocks) or extract_bare_text(soup),
                fragment=None,
                level=_chapter_level(entry),
                kind=entry.kind,
            )
        ]

    order = {id(tag): index for index, tag in enumerate(soup.find_all(True))}
    anchors: list[tuple[int, str, TocEntry]] = []
    for entry in entries:
        if entry.fragment is None:
            continue
        tag = soup.find(id=entry.fragment)
        if tag is None:
            logger.warning("TOC anchor %s not found", entry.fragment)
            continue
        anchors.append((order[id(tag)], entry.fragment, entry))
    if not anchors:
        first = entries[0]
        return [], [
            _SplitChapter(
                title=first.title,
                paragraphs=block_texts(blocks) or extract_bare_text(soup),
                fragment=None,
                level=_chapter_level(first),
                kind=first.kind,
            )
        ]

    prefix: list[str] = []
    chapters: list[_SplitChapter] = []
    for block in blocks:
        anchor_ids = {tag.get("id") for tag in block.find_all(id=True)}
        inside = [entry for entry in anchors if entry[1] in anchor_ids]
        block_position = order[id(block)]
        before = [entry for entry in anchors if entry[0] < block_position]
        candidate = inside[0] if inside else (before[-1] if before else None)
        text = block.get_text(" ", strip=True)
        if candidate is None:
            if text and not is_label(text, entries[0].title):
                prefix.append(text)
            continue
        entry = candidate[2]
        if not chapters or chapters[-1].title != entry.title:
            chapters.append(
                _SplitChapter(
                    title=entry.title,
                    paragraphs=[],
                    fragment=entry.fragment,
                    level=_chapter_level(entry),
                    kind=entry.kind,
                )
            )
        if text and not is_label(text, entry.title):
            chapters[-1].paragraphs.append(text)
    if not any(chapter.paragraphs for chapter in chapters):
        first = entries[0]
        return prefix, [
            _SplitChapter(
                title=first.title,
                paragraphs=extract_bare_text(soup),
                fragment=None,
                level=_chapter_level(first),
                kind=first.kind,
            )
        ]
    return prefix, chapters
