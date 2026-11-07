import re
from collections.abc import Iterable

PAGE_NUMBER = re.compile(r"^\s*\d{1,4}\s*$")
GUTENBERG = re.compile(
    r"project gutenberg|gutenberg\.org|produced by|transcriber|proofread",
    re.IGNORECASE,
)
WATERMARK = re.compile(r"^\s*(?:https?://)?(?:www\.)?oceanofpdf\.com/?\s*$", re.IGNORECASE)


def clean_text(text: str) -> str:
    text = text.replace("\u00ad", "")
    text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def clean_paragraph_items[T](items: Iterable[tuple[str, T]]) -> list[tuple[str, T]]:
    cleaned: list[tuple[str, T]] = []
    for paragraph, payload in items:
        paragraph = clean_text(paragraph)
        if not paragraph:
            continue
        if PAGE_NUMBER.match(paragraph) or GUTENBERG.search(paragraph):
            continue
        if WATERMARK.match(paragraph):
            continue
        if cleaned and paragraph == cleaned[-1][0]:
            continue
        cleaned.append((paragraph, payload))
    return cleaned


def clean_paragraphs(paragraphs: list[str]) -> list[str]:
    return [
        paragraph for paragraph, _ in clean_paragraph_items((text, None) for text in paragraphs)
    ]
