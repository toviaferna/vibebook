import re

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


def clean_paragraphs(paragraphs: list[str]) -> list[str]:
    cleaned: list[str] = []
    for paragraph in paragraphs:
        paragraph = clean_text(paragraph)
        if not paragraph:
            continue
        if PAGE_NUMBER.match(paragraph) or GUTENBERG.search(paragraph):
            continue
        if WATERMARK.match(paragraph):
            continue
        if cleaned and paragraph == cleaned[-1]:
            continue
        cleaned.append(paragraph)
    return cleaned
