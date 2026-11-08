from __future__ import annotations

import hashlib
import io
import logging
import posixpath
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote

from bs4 import BeautifulSoup, Tag
from ebooklib import ITEM_IMAGE, epub
from PIL import Image, ImageOps, UnidentifiedImageError

from audiol.ingest.structure import normalize_href, top_level_blocks
from audiol.models import BookImage, Chapter

logger = logging.getLogger(__name__)

MAX_IMAGES = 200
MAX_WIDTH = 1600
MAX_PIXELS = 40_000_000
MIN_DECORATIVE = 64

Image.MAX_IMAGE_PIXELS = MAX_PIXELS


@dataclass(frozen=True)
class ImagePlacement:
    image: BookImage
    source_href: str
    after_text: str | None
    before_text: str | None


def image_items(book: epub.EpubBook) -> dict[str, epub.EpubItem]:
    items: dict[str, epub.EpubItem] = {}
    for item in book.get_items():
        name, _ = normalize_href(item.get_name())
        if name:
            items[name] = item
    return items


def extract_document_images(
    soup: BeautifulSoup,
    document_name: str,
    image_dir: Path,
    items: dict[str, epub.EpubItem],
    seen_hashes: set[str],
    remaining: int,
) -> list[ImagePlacement]:
    if remaining <= 0:
        return []
    image_dir.mkdir(parents=True, exist_ok=True)
    order = {id(tag): index for index, tag in enumerate(soup.find_all(True))}
    block_positions = [
        (order[id(block)], block.get_text(" ", strip=True))
        for block in top_level_blocks(soup)
        if block.get_text(" ", strip=True)
    ]
    placements: list[ImagePlacement] = []

    for img in soup.find_all("img"):
        if len(placements) >= remaining:
            break
        if img.find_parent("nav") is not None:
            continue
        src = _attr(img, "src")
        item_name = _resolve_src(document_name, src)
        if item_name is None:
            continue
        item = items.get(item_name)
        if item is None or item.get_type() != ITEM_IMAGE:
            continue
        position = order[id(img)]
        previous = [text for block_position, text in block_positions if block_position < position]
        following = [text for block_position, text in block_positions if block_position > position]
        after_text = previous[-1] if previous else None
        before_text = following[0] if following else None
        alt = _attr(img, "alt")
        caption = _caption(img)
        role = _role(img, alt, caption)
        if role == "cover":
            continue
        data = item.get_content()
        digest = hashlib.sha256(data).hexdigest()
        if digest in seen_hashes:
            continue
        processed = _process_image(data, digest, image_dir)
        if processed is None:
            continue
        path, width, height = processed
        if role == "decorative" and max(width, height) < MIN_DECORATIVE:
            continue
        seen_hashes.add(digest)
        placements.append(
            ImagePlacement(
                image=BookImage(
                    id=f"img-{digest[:12]}",
                    path=path,
                    alt=alt,
                    caption=caption,
                    role=role,
                    position="after",
                    width=width,
                    height=height,
                ),
                source_href=document_name,
                after_text=after_text,
                before_text=before_text,
            )
        )
    return placements


def assign_images(placements: list[ImagePlacement], chapters: list[Chapter]) -> list[BookImage]:
    by_href: dict[str, list[Chapter]] = {}
    for chapter in chapters:
        if chapter.source_href:
            by_href.setdefault(chapter.source_href, []).append(chapter)

    result: list[BookImage] = []
    for placement in placements:
        candidates = by_href.get(placement.source_href, [])
        if not candidates:
            continue
        after_chapter = _match_chapter(candidates, placement.after_text)
        before_chapter = _match_chapter(candidates, placement.before_text)
        image = placement.image
        if (
            before_chapter is not None
            and after_chapter is not None
            and before_chapter is not after_chapter
        ):
            segment = _match_segment(before_chapter, placement.before_text)
            image.chapter_index = before_chapter.index
            image.paragraph_index = segment.paragraph_index if segment is not None else 0
            image.position = "before"
        elif after_chapter is not None:
            segment = _match_segment(after_chapter, placement.after_text)
            if segment is not None:
                image.chapter_index = after_chapter.index
                image.paragraph_index = segment.paragraph_index
                image.position = "after"
            else:
                image.chapter_index = after_chapter.index
                image.paragraph_index = (
                    after_chapter.segments[-1].paragraph_index if after_chapter.segments else 0
                )
                image.position = "after"
        else:
            matched_chapter = before_chapter or candidates[0]
            segment = _match_segment(matched_chapter, placement.before_text)
            image.chapter_index = matched_chapter.index
            image.paragraph_index = segment.paragraph_index if segment is not None else 0
            image.position = "before"
        result.append(image)
    return result


def _match_chapter(chapters: list[Chapter], text: str | None) -> Chapter | None:
    if not text:
        return None
    for chapter in chapters:
        if _match_segment(chapter, text) is not None:
            return chapter
    return None


def _match_segment(chapter: Chapter, text: str | None):
    if not text:
        return None
    normalized = _normalize_text(text)
    for segment in chapter.segments:
        candidate = _normalize_text(segment.text)
        if candidate == normalized or normalized in candidate or candidate in normalized:
            return segment
    return None


def _normalize_text(text: str) -> str:
    return " ".join(text.split()).casefold()


def _attr(tag: Tag, name: str) -> str:
    value = tag.get(name)
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        return " ".join(str(item) for item in value).strip()
    return ""


def _resolve_src(document_name: str, src: str) -> str | None:
    if not src or src.startswith(("data:", "http:", "https:")):
        return None
    path = unquote(src.split("#", 1)[0]).lstrip("/")
    if not path:
        return None
    resolved, _ = normalize_href(posixpath.join(posixpath.dirname(document_name), path))
    return resolved


def _caption(img: Tag) -> str | None:
    figure = img.find_parent("figure")
    if figure is None:
        return None
    caption = figure.find("figcaption")
    if caption is None:
        return None
    text = caption.get_text(" ", strip=True)
    return text or None


def _role(img: Tag, alt: str, caption: str | None) -> str:
    marker = " ".join(
        [
            str(img.get("epub:type") or ""),
            str(img.get("role") or ""),
            str(img.get("class") or ""),
            str(img.get("id") or ""),
        ]
    ).casefold()
    if "cover" in marker or "doc-cover" in marker:
        return "cover"
    if "ornament" in marker or "decoration" in marker:
        return "ornament"
    if not alt and not caption:
        return "decorative"
    return "illustration"


def _process_image(data: bytes, digest: str, image_dir: Path) -> tuple[str, int, int] | None:
    try:
        with Image.open(io.BytesIO(data)) as image:
            image.load()
            working = ImageOps.exif_transpose(image)
            width, height = working.size
            if width < 8 or height < 8:
                return None
            if width > MAX_WIDTH:
                ratio = MAX_WIDTH / width
                working = working.resize(
                    (MAX_WIDTH, max(1, round(height * ratio))),
                    Image.Resampling.LANCZOS,
                )
                width, height = working.size
            has_alpha = working.mode in {"RGBA", "LA"} or "transparency" in working.info
            extension = ".png" if has_alpha else ".jpg"
            filename = f"{digest}{extension}"
            target = image_dir / filename
            if not target.exists():
                if has_alpha:
                    working.convert("RGBA").save(target, "PNG", optimize=True)
                else:
                    working.convert("RGB").save(target, "JPEG", quality=85, optimize=True)
            return f"images/{filename}", width, height
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        logger.warning("Skipping unreadable image", exc_info=True)
        return None
