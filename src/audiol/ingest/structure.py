from __future__ import annotations

import posixpath
import re
from collections import Counter
from dataclasses import dataclass, field
from urllib.parse import unquote

from bs4 import BeautifulSoup, Comment, NavigableString, Tag

from audiol.models import TocNode

BLOCK_TAGS = ["p", "li", "blockquote", "pre", "div"]
TEXT_SEPARATOR_TAGS = {
    *BLOCK_TAGS,
    "br",
    "hr",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "section",
    "article",
    "header",
    "footer",
    "figure",
    "figcaption",
    "tr",
    "td",
    "th",
}
NAV_TITLES = {
    "contents",
    "copyright",
    "cubierta",
    "document outline",
    "fin",
    "indice",
    "portada",
    "table of contents",
    "title page",
    "índice",
}
FRONT_TITLES = {
    "author's note",
    "dedication",
    "dedicatoria",
    "epígrafe",
    "epigraph",
    "foreword",
    "introduccion",
    "introducción",
    "introduction",
    "nota del autor",
    "prefacio",
    "preface",
    "prologo",
    "prólogo",
    "prologue",
}
BACK_TITLES = {
    "afterword",
    "apendice",
    "apéndice",
    "appendix",
    "colofon",
    "colofón",
    "epilogo",
    "epílogo",
    "epilogue",
    "notas",
    "notes",
    "posfacio",
}
PART_TITLES = {"book", "libro", "part", "parte"}
ROMAN_PATTERN = re.compile(r"^[ivxlcdm]+$", re.IGNORECASE)


@dataclass(frozen=True)
class TocEntry:
    title: str
    href: str | None = None
    fragment: str | None = None
    level: int = 1
    kind: str = "chapter"
    children: tuple[TocEntry, ...] = ()


@dataclass(frozen=True)
class HeadingSection:
    title: str
    level: int
    kind: str
    blocks: tuple[Tag, ...] = ()
    fragment: str | None = None


@dataclass(frozen=True)
class HeadingSplit:
    sections: list[HeadingSection] = field(default_factory=list)
    prefix: list[Tag] = field(default_factory=list)


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


def normalize_href(href: str) -> tuple[str, str | None]:
    raw = unquote(href.strip())
    item, _, fragment = raw.partition("#")
    item = item.lstrip("/")
    item = posixpath.normpath(item) if item else ""
    return item, fragment or None


def classify_title(title: str) -> str:
    normalized = normalize(title)
    if normalized in NAV_TITLES:
        return "skip"
    if normalized in FRONT_TITLES:
        return "frontmatter"
    if normalized in BACK_TITLES:
        return "backmatter"
    if normalized in PART_TITLES or re.match(r"^(parte|part|libro|book)\b", normalized):
        return "part"
    return "chapter"


def parse_number(title: str) -> int | None:
    normalized = normalize(title)
    if normalized.isdigit():
        return int(normalized)
    match = re.match(r"^(?:capítulo|capitulo|chapter|parte|part|libro|book)\s+(\d+)\b", normalized)
    if match:
        return int(match.group(1))
    if ROMAN_PATTERN.match(normalized):
        return _roman_to_int(normalized)
    return None


def build_toc(book, title: str, author: str) -> list[TocEntry]:
    normalized_book = normalize(title)
    normalized_author = normalize(author)
    items = _toc_items(book.toc)
    return _convert_toc_items(
        items,
        depth=0,
        normalized_book=normalized_book,
        normalized_author=normalized_author,
    )


def _toc_items(value) -> list:
    if value is None:
        return []
    if hasattr(value, "title"):
        return [value]
    if (
        isinstance(value, tuple)
        and len(value) == 2
        and hasattr(value[0], "title")
        and isinstance(value[1], (list, tuple))
    ):
        return [value]
    if isinstance(value, (list, tuple)):
        return list(value)
    return []


def entries_by_document(entries: list[TocEntry]) -> dict[str, list[TocEntry]]:
    grouped: dict[str, list[TocEntry]] = {}

    def walk(node: TocEntry) -> None:
        if not node.children and node.href:
            grouped.setdefault(node.href, []).append(node)
        for child in node.children:
            walk(child)

    for entry in entries:
        walk(entry)
    return grouped


def heading_split(soup: BeautifulSoup, book_title: str | None = None) -> HeadingSplit:
    headings = [
        heading
        for heading in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])
        if heading.get_text(" ", strip=True) and heading.find_parent("nav") is None
    ]
    if not headings:
        return HeadingSplit(sections=[_whole_document(soup, "")])

    split_level = _choose_heading_level(headings, book_title)
    if split_level is None:
        title = headings[0].get_text(" ", strip=True)
        return HeadingSplit(sections=[_whole_document(soup, title)])

    split_headings = [heading for heading in headings if _heading_level(heading) == split_level]
    if not split_headings:
        return HeadingSplit(sections=[_whole_document(soup, headings[0].get_text(" ", strip=True))])

    order = {id(tag): index for index, tag in enumerate(soup.find_all(True))}
    blocks = top_level_blocks(soup)
    prefix: list[Tag] = []
    sections: list[HeadingSection] = []
    current_tag: Tag | None = None
    current_title = ""
    current_kind = "chapter"
    current_blocks: list[Tag] = []
    split_positions = [(order[id(heading)], heading) for heading in split_headings]

    for block in blocks:
        position = order[id(block)]
        candidate = None
        for heading_position, heading in split_positions:
            if heading_position < position:
                candidate = heading
            else:
                break
        if candidate is None:
            if current_tag is None:
                prefix.append(block)
            else:
                current_blocks.append(block)
            continue
        if candidate is not current_tag:
            if current_tag is not None:
                sections.append(
                    HeadingSection(
                        title=current_title,
                        level=1,
                        kind=current_kind,
                        blocks=tuple(current_blocks),
                        fragment=_tag_id(current_tag),
                    )
                )
                current_blocks = []
            current_tag = candidate
            current_title = candidate.get_text(" ", strip=True)
            current_kind = classify_title(current_title)
        current_blocks.append(block)

    if current_tag is not None:
        sections.append(
            HeadingSection(
                title=current_title,
                level=1,
                kind=current_kind,
                blocks=tuple(current_blocks),
                fragment=_tag_id(current_tag),
            )
        )
    return HeadingSplit(sections=sections, prefix=prefix)


def top_level_blocks(soup: BeautifulSoup) -> list[Tag]:
    selected: list[Tag] = []
    for block in soup.find_all(BLOCK_TAGS):
        if block.name == "div" and block.find(BLOCK_TAGS):
            continue
        if block.find_parent(["p", "li", "blockquote", "pre"]) is not None:
            continue
        selected.append(block)
    return selected


def extract_text(element: Tag, *, keep_lines: bool = False) -> str:
    """Extract text without inventing spaces between inline elements.

    ``Tag.get_text(" ")`` inserts a space between every inline span, which turns
    ``ulti-</span><span>ma`` into ``ulti- ma``. This walks text nodes directly and
    only adds separators for real block/line-break boundaries.
    """
    parts: list[str] = []
    inline_boundary = False
    for child in element.descendants:
        if isinstance(child, Comment):
            continue
        if isinstance(child, NavigableString):
            value = str(child)
            if (
                inline_boundary
                and parts
                and parts[-1].endswith(("-", "\u2010", "\u2011"))
                and re.match(r"^[a-záéíóúüñ]", value)
            ):
                parts[-1] = parts[-1].rstrip("-\u2010\u2011")
            parts.append(value)
            inline_boundary = False
        elif isinstance(child, Tag):
            if child.name in TEXT_SEPARATOR_TAGS:
                parts.append("\n")
                inline_boundary = False
            else:
                inline_boundary = True
    text = "".join(parts).replace("\u00a0", " ")
    lines = [re.sub(r"[ \t\f\v]+", " ", line).strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines) if keep_lines else " ".join(lines)


def block_texts(blocks: list[Tag] | tuple[Tag, ...]) -> list[str]:
    return [text for block in blocks if (text := extract_text(block))]


def extract_bare_text(soup: BeautifulSoup) -> list[str]:
    fallback = BeautifulSoup(str(soup), "lxml")
    for heading in fallback.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
        heading.decompose()
    container = fallback.body or fallback
    return [
        line.strip()
        for line in extract_text(container, keep_lines=True).splitlines()
        if line.strip()
    ]


def is_label(text: str, title: str) -> bool:
    normalized = normalize(text)
    normalized_title = normalize(title)
    if normalized == normalized_title:
        return True
    if normalized.isdigit():
        return normalized_title in {
            normalized,
            f"capítulo {normalized}",
            f"capitulo {normalized}",
            f"chapter {normalized}",
        }
    return False


def build_manifest_toc(
    entries: list[TocEntry],
    chapter_sources: dict[tuple[str, str | None], int],
) -> list[TocNode]:
    result: list[TocNode] = []
    for entry in entries:
        children = build_manifest_toc(list(entry.children), chapter_sources)
        chapter_index = None
        container_duplicates_child = entry.children and any(
            child.href == entry.href and child.fragment == entry.fragment
            for child in entry.children
        )
        if entry.href and not container_duplicates_child:
            chapter_index = chapter_sources.get((entry.href, entry.fragment))
            if chapter_index is None and entry.fragment is None:
                chapter_index = chapter_sources.get((entry.href, None))
        if chapter_index is None and not children:
            continue
        level = 0 if children and chapter_index is None else 1
        result.append(
            TocNode(
                title=entry.title,
                level=level,
                chapter_index=chapter_index,
                kind=entry.kind,
                children=children,
            )
        )
    return result


def toc_from_chapters(chapters) -> list[TocNode]:
    return [
        TocNode(
            title=chapter.title,
            level=chapter.level,
            chapter_index=chapter.index,
            kind=chapter.kind,
        )
        for chapter in chapters
    ]


def _convert_toc_items(
    items,
    *,
    depth: int,
    normalized_book: str,
    normalized_author: str,
) -> list[TocEntry]:
    result: list[TocEntry] = []
    for item in items:
        if isinstance(item, tuple):
            section, children = item
            title = str(getattr(section, "title", "") or "").strip()
            href = str(getattr(section, "href", "") or "").strip() or None
            raw_children = children
        else:
            title = str(getattr(item, "title", "") or "").strip()
            href = str(getattr(item, "href", "") or "").strip() or None
            raw_children = []
        child_entries = _convert_toc_items(
            _toc_items(raw_children),
            depth=depth + 1,
            normalized_book=normalized_book,
            normalized_author=normalized_author,
        )
        normalized_title = normalize(title)
        if _skip_title(normalized_title, normalized_book, normalized_author):
            result.extend(child_entries)
            continue
        item_name, fragment = normalize_href(href) if href else ("", None)
        kind = classify_title(title)
        if not item_name and not child_entries:
            continue
        if child_entries and kind == "chapter":
            kind = "part"
        result.append(
            TocEntry(
                title=title,
                href=item_name or None,
                fragment=fragment,
                level=depth,
                kind=kind,
                children=tuple(child_entries),
            )
        )
    return result


def _skip_title(normalized_title: str, normalized_book: str, normalized_author: str) -> bool:
    if not normalized_title:
        return True
    if normalized_title in NAV_TITLES:
        return True
    if normalized_title in {normalized_book, normalized_author}:
        return True
    return bool(
        normalized_book
        and normalized_author
        and normalized_book in normalized_title
        and normalized_author in normalized_title
    )


def _choose_heading_level(headings: list[Tag], book_title: str | None) -> int | None:
    counts = Counter(_heading_level(heading) for heading in headings)
    if counts.get(1, 0) >= 2:
        return 1
    if (
        counts.get(1, 0) == 1
        and counts.get(2, 0) >= 1
        and book_title
        and normalize(headings[0].get_text(" ", strip=True)) == normalize(book_title)
    ):
        return 2
    if counts.get(1, 0) == 1 and counts.get(2, 0) >= 2:
        return 2
    for level in (2, 3, 4, 5, 6):
        if counts.get(level, 0) >= 2:
            return level
    return None


def _heading_level(heading: Tag) -> int:
    return int(heading.name[1])


def _tag_id(tag: Tag) -> str | None:
    value = tag.get("id")
    return str(value) if value else None


def _whole_document(soup: BeautifulSoup, title: str) -> HeadingSection:
    blocks = top_level_blocks(soup)
    paragraphs = block_texts(blocks) or extract_bare_text(soup)
    if not paragraphs:
        return HeadingSection(title=title, level=1, kind=classify_title(title), blocks=())
    return HeadingSection(
        title=title,
        level=1,
        kind=classify_title(title),
        blocks=tuple(blocks),
    )


def _roman_to_int(value: str) -> int | None:
    values = {"i": 1, "v": 5, "x": 10, "l": 50, "c": 100, "d": 500, "m": 1000}
    total = 0
    previous = 0
    for char in reversed(value.lower()):
        current = values.get(char)
        if current is None:
            return None
        if current < previous:
            total -= current
        else:
            total += current
            previous = current
    return total or None
