from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ConvertRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    voice: str
    engine: Literal["edge", "azure", "fake"] = "edge"
    style: str = "neutral"
    rate: str = "-10%"
    force: bool = False


class BookStateUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    position_ms: int = Field(ge=0)
    chapter_index: int = Field(ge=1)
    playback_rate: float = Field(default=1.0, ge=0.5, le=3.0)


class PreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    voice: str
    engine: Literal["edge", "azure", "fake"] = "edge"
    style: str = "neutral"
    rate: str = "-10%"
    text: str = Field(min_length=1, max_length=120)


class SettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    default_voice: str | None = None
    default_rate: str | None = None
    reader_theme: Literal["light", "sepia", "night"] | None = None
    reader_font: Literal["serif", "sans", "hyperlegible"] | None = None
    reader_size: int | None = Field(default=None, ge=14, le=28)
    auto_scroll: bool | None = None
    skip_seconds: int | None = Field(default=None, ge=5, le=60)


class BookStateResponse(BaseModel):
    position_ms: int
    chapter_index: int
    playback_rate: float
    updated_at: str | None = None


class JobResponse(BaseModel):
    id: str
    book_id: str
    status: str
    stage: str
    completed_segments: int = 0
    total_segments: int = 0
    chapter_index: int | None = None
    chapter_title: str | None = None
    current_text: str | None = None
    message: str | None = None
    error: str | None = None
    options: dict = Field(default_factory=dict)
    created_at: str
    updated_at: str
    started_at: str | None = None
    finished_at: str | None = None


class BookResponse(BaseModel):
    id: str
    title: str
    author: str
    language: str
    status: str
    chapter_count: int
    duration_ms: int | None = None
    voice: str | None = None
    engine: str | None = None
    rate: str | None = None
    cover_url: str | None = None
    progress: float = 0.0
    last_position_ms: int = 0
    last_chapter_index: int = 1
    created_at: str
    updated_at: str


class BookDetailResponse(BookResponse):
    state: BookStateResponse
    last_job: JobResponse | None = None


class BookListResponse(BaseModel):
    items: list[BookResponse]
    total: int
    limit: int
    offset: int


class ChapterResponse(BaseModel):
    chapter: dict
    timing: dict


class SearchResult(BaseModel):
    chapter_index: int
    chapter_title: str
    segment_id: str
    position_ms: int
    excerpt: str
    offset: int


class SearchResponse(BaseModel):
    items: list[SearchResult]


class BookmarkCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chapter_index: int = Field(ge=1)
    position_ms: int = Field(ge=0)
    note: str | None = Field(default=None, max_length=500)


class BookmarkResponse(BaseModel):
    id: int
    book_id: str
    chapter_index: int
    position_ms: int
    note: str | None = None
    created_at: str


class BookmarkListResponse(BaseModel):
    items: list[BookmarkResponse]


class VoiceResponse(BaseModel):
    id: str
    locale: str
    gender: str
    engines: list[str]
    styles: list[str]


class PreviewResponse(BaseModel):
    url: str
    key: str


class SettingsResponse(BaseModel):
    library_dir: str
    default_voice: str
    default_rate: str
    reader_theme: str
    reader_font: str
    reader_size: int
    auto_scroll: bool
    skip_seconds: int
    azure_configured: bool
