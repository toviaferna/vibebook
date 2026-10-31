from dataclasses import dataclass, field


@dataclass(frozen=True)
class Segment:
    id: str
    chapter_index: int
    paragraph_index: int
    text: str
    style: str = "neutral"
    voice: str | None = None


@dataclass
class Chapter:
    index: int
    title: str
    segments: list[Segment] = field(default_factory=list)


@dataclass
class Book:
    title: str
    author: str
    language: str = "es-419"
    chapters: list[Chapter] = field(default_factory=list)
