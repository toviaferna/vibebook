from dataclasses import dataclass
from pathlib import Path

from platformdirs import user_data_path


@dataclass(frozen=True)
class Settings:
    library_dir: Path
    host: str = "127.0.0.1"
    port: int = 8765
    token: str | None = None
    allow_fake: bool = False
    dev: bool = False
    web_dist: Path | None = None
    max_upload_bytes: int = 200 * 1024 * 1024
    max_archive_entries: int = 5000
    max_uncompressed_bytes: int = 500 * 1024 * 1024


def default_library_dir() -> Path:
    return user_data_path("vibebook") / "library"
