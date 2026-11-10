import re
from dataclasses import dataclass

from audiol.clean import clean_text

ABBREVIATIONS = (
    "EE. UU.",
    "p. ej.",
    "V.M.",
    "Vd.",
    "Uds.",
    "Ud.",
    "Srta.",
    "Sra.",
    "Sr.",
    "Dr.",
    "Dra.",
    "Dña.",
    "Lic.",
    "Ing.",
    "Prof.",
    "etc.",
    "núm.",
    "Núm.",
    "pág.",
    "Pág.",
    "vol.",
    "art.",
    "cap.",
    "tel.",
    "Tel.",
    "av.",
    "Av.",
    "Cía.",
    "S. A.",
    "S.A.",
    "Ilmo.",
    "Ilma.",
)
SENTENCE_END = re.compile(r"(?<=[.!?…])\s+")


@dataclass(frozen=True)
class TextChunk:
    text: str
    boundary: str
    continuation: bool


def split_sentences(text: str) -> list[str]:
    protected = text
    for index, abbreviation in enumerate(ABBREVIATIONS):
        protected = protected.replace(abbreviation, f"@@{index}@@")

    parts = [part.strip() for part in SENTENCE_END.split(protected) if part.strip()]

    restored: list[str] = []
    for part in parts:
        for index, abbreviation in enumerate(ABBREVIATIONS):
            part = part.replace(f"@@{index}@@", abbreviation)
        restored.append(part)
    return restored


def chunk_text(text: str, max_chars: int = 400) -> list[str]:
    return [part.text for part in chunk_text_parts(text, max_chars=max_chars)]


def chunk_text_parts(text: str, max_chars: int = 400) -> list[TextChunk]:
    chunks = _chunk_text(text, max_chars=max_chars)
    return [
        TextChunk(
            text=chunk,
            boundary="paragraph" if index == len(chunks) - 1 else _boundary_for(chunk),
            continuation=index > 0,
        )
        for index, chunk in enumerate(chunks)
    ]


def _chunk_text(text: str, max_chars: int = 400) -> list[str]:
    text = clean_text(text)
    chunks: list[str] = []
    buffer = ""
    for sentence in split_sentences(text):
        sentence = sentence.strip()
        if not sentence:
            continue
        if len(sentence) > max_chars:
            if buffer:
                chunks.append(buffer)
                buffer = ""
            chunks.extend(_split_long(sentence, max_chars))
            continue
        candidate = f"{buffer} {sentence}".strip()
        if len(candidate) <= max_chars:
            buffer = candidate
        else:
            if buffer:
                chunks.append(buffer)
            buffer = sentence
    if buffer:
        chunks.append(buffer)
    return [chunk for chunk in chunks if chunk]


def _boundary_for(chunk: str) -> str:
    stripped = chunk.rstrip()
    if stripped.endswith((".", "!", "?", "…")):
        return "sentence"
    if stripped.endswith((",", ";", ":")):
        return "clause"
    return "word"


def _split_long(text: str, max_chars: int) -> list[str]:
    chunks: list[str] = []
    buffer = ""
    for part in re.split(r"(?<=[,;:])\s+", text):
        candidate = f"{buffer} {part}".strip()
        if len(candidate) <= max_chars:
            buffer = candidate
            continue
        if buffer:
            chunks.append(buffer)
        if len(part) <= max_chars:
            buffer = part
            continue
        words = part.split()
        word_buffer = ""
        for word in words:
            candidate_word = f"{word_buffer} {word}".strip()
            if len(candidate_word) <= max_chars:
                word_buffer = candidate_word
            else:
                if word_buffer:
                    chunks.append(word_buffer)
                word_buffer = word
        buffer = word_buffer
    if buffer:
        chunks.append(buffer)
    return chunks
