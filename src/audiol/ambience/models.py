from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

SoundKind = Literal["ambience", "effect", "music"]
SoundProvider = Literal["procedural", "pack", "freesound", "plugin", "import"]


class SoundAssetCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt: str = Field(min_length=1, max_length=240)
    kind: SoundKind = "ambience"
    tags: list[str] = Field(default_factory=list)
    provider: SoundProvider = "import"
    model: str | None = None
    seed: int | None = None
    loopable: bool = False
    license: str = Field(min_length=1, max_length=120)
    attribution: str | None = Field(default=None, max_length=500)
    source_url: str | None = Field(default=None, max_length=1000)

    @field_validator("license")
    @classmethod
    def license_must_be_known(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned or cleaned.lower() in {"unknown", "desconocida", "sin licencia"}:
            raise ValueError("The asset needs a known license")
        return cleaned

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, value: list[str]) -> list[str]:
        return sorted({tag.strip().lower() for tag in value if tag.strip()})


class SoundAssetResponse(SoundAssetCreate):
    id: str
    duration_ms: int
    sample_rate: int
    channels: int
    loudness_lufs: float | None = None
    checksum: str
    approved: bool = False
    created_at: str
    last_used_at: str | None = None
    usage_count: int = 0
    audio_url: str


class SoundAssetList(BaseModel):
    items: list[SoundAssetResponse]
    total: int
    limit: int
    offset: int


class AmbienceAnchor(BaseModel):
    model_config = ConfigDict(extra="forbid")

    segment_id: str = Field(min_length=1, max_length=120)
    offset_ms: int = Field(default=0, ge=0)


class AmbienceBed(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asset_id: str = Field(min_length=1, max_length=120)
    kind: Literal["ambience"] = "ambience"
    start_ms: int = Field(default=0, ge=0)
    end_ms: int | None = Field(default=None, ge=0)
    loop: bool = True
    gain_db: float = Field(default=-24, ge=-60, le=0)
    fade_in_ms: int = Field(default=1500, ge=0, le=10_000)
    fade_out_ms: int = Field(default=2000, ge=0, le=10_000)
    confidence: float = Field(default=0.8, ge=0, le=1)
    reason: str = Field(default="", max_length=300)


class AmbienceEffect(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asset_id: str = Field(min_length=1, max_length=120)
    kind: Literal["effect"] = "effect"
    anchor: AmbienceAnchor
    duration_ms: int = Field(ge=100, le=30_000)
    gain_db: float = Field(default=-16, ge=-60, le=0)
    confidence: float = Field(default=0.7, ge=0, le=1)
    reason: str = Field(default="", max_length=300)


class AmbienceChapter(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chapter_index: int = Field(ge=1)
    bed: AmbienceBed | None = None
    effects: list[AmbienceEffect] = Field(default_factory=list)


class AmbienceSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    master_gain_db: float = Field(default=-18, ge=-60, le=0)
    ducking_db: float = Field(default=-12, ge=-40, le=0)


class AmbiencePlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = 1
    chapters: list[AmbienceChapter] = Field(default_factory=list)


class AmbienceResponse(BaseModel):
    book_id: str
    settings: AmbienceSettings
    plan: AmbiencePlan


class AmbiencePlanUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    settings: AmbienceSettings = Field(default_factory=AmbienceSettings)
    plan: AmbiencePlan = Field(default_factory=AmbiencePlan)


class AmbienceAnalyzeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: Literal["heuristic"] = "heuristic"
    force: bool = False


class AmbienceGenerateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    preset: Literal["rain", "wind", "sea", "room", "fire", "night"] | None = None


class FreesoundImportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=2, max_length=200)
    license_filter: str = Field(default="license:Creative Commons 0", max_length=100)
    limit: int = Field(default=5, ge=1, le=20)


class PluginImportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt: str = Field(min_length=1, max_length=500)
    kind: SoundKind = "ambience"
    duration_ms: int = Field(default=30_000, ge=1_000, le=120_000)


class ProviderStatus(BaseModel):
    id: str
    label: str
    configured: bool
    description: str


class ProviderList(BaseModel):
    items: list[ProviderStatus]
