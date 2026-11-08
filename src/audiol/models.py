from dataclasses import dataclass, field


@dataclass(frozen=True)
class WordTiming:
    text: str
    start_ms: int
    end_ms: int


def make_segment_id(chapter_index: int, paragraph_index: int, chunk_index: int = 0) -> str:
    return f"c{chapter_index:03d}p{paragraph_index:04d}s{chunk_index:02d}"


@dataclass(frozen=True)
class Segment:
    id: str
    chapter_index: int
    paragraph_index: int
    text: str
    chunk_index: int = 0
    source_href: str | None = None
    source_fragment: str | None = None


@dataclass
class TocNode:
    title: str
    level: int = 1
    chapter_index: int | None = None
    kind: str = "chapter"
    children: list["TocNode"] = field(default_factory=list)


@dataclass
class BookImage:
    id: str
    path: str | None = None
    alt: str = ""
    caption: str | None = None
    role: str = "illustration"
    chapter_index: int | None = None
    paragraph_index: int = 0
    position: str = "after"
    width: int | None = None
    height: int | None = None


@dataclass
class Chapter:
    index: int
    title: str
    segments: list[Segment] = field(default_factory=list)
    source_href: str | None = None
    source_fragment: str | None = None
    level: int = 1
    kind: str = "chapter"
    number: int | None = None
    generated_title: bool = False


@dataclass
class Book:
    title: str
    author: str
    language: str = "es-419"
    chapters: list[Chapter] = field(default_factory=list)
    toc: list[TocNode] = field(default_factory=list)
    images: list[BookImage] = field(default_factory=list)
