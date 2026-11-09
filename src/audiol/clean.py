import re
from collections.abc import Iterable

PAGE_NUMBER = re.compile(r"^\s*\d{1,4}\s*$")
GUTENBERG = re.compile(
    r"project gutenberg|gutenberg\.org|produced by|transcriber|proofread",
    re.IGNORECASE,
)
WATERMARK = re.compile(r"^\s*(?:https?://)?(?:www\.)?oceanofpdf\.com/?\s*$", re.IGNORECASE)
ZERO_WIDTH = re.compile(r"[\u200b\u200c\u200d\ufeff]")
LINE_HYPHEN = re.compile(r"(?<=\w)[\u2010\u2011-]\s*\n\s*(?=\w)")
SPACE_HYPHEN = re.compile(r"(?<=\w)[\u2010\u2011-]\s+(?=[a-záéíóúüñ])")
ELLIPSIS = re.compile(r"\.{3,}")
SPACE_BEFORE_PUNCT = re.compile(r"\s+([,.;:!?…])")
MULTISPACE = re.compile(r"[ \t\f\v]+")
MULTINEWLINE = re.compile(r"\n{3,}")


def clean_text(text: str) -> str:
    text = text.replace("\u00ad", "")
    text = ZERO_WIDTH.sub("", text)
    text = (
        text.replace("\u2010", "-")
        .replace("\u2011", "-")
        .replace("\u2012", "-")
        .replace("\u00a0", " ")
        .replace("\u202f", " ")
        .replace("\u2009", " ")
    )
    text = LINE_HYPHEN.sub("", text)
    text = SPACE_HYPHEN.sub("", text)
    text = ELLIPSIS.sub("…", text)
    text = SPACE_BEFORE_PUNCT.sub(r"\1", text)
    text = MULTISPACE.sub(" ", text)
    text = MULTINEWLINE.sub("\n\n", text)
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
        if cleaned:
            previous, previous_payload = cleaned[-1]
            if re.search(r"[\u2010\u2011-]$", previous) and re.match(
                r"^[-\u2010\u2011]?[a-záéíóúüñ]",
                paragraph,
            ):
                merged = previous.rstrip("-\u2010\u2011") + re.sub(
                    r"^[-\u2010\u2011]\s*",
                    "",
                    paragraph,
                )
                cleaned[-1] = (clean_text(merged), previous_payload)
                continue
            if paragraph == previous:
                continue
        cleaned.append((paragraph, payload))
    return cleaned


def clean_paragraphs(paragraphs: list[str]) -> list[str]:
    return [
        paragraph for paragraph, _ in clean_paragraph_items((text, None) for text in paragraphs)
    ]
