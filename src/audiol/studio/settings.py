from dataclasses import dataclass
from ipaddress import ip_address
from pathlib import Path

from platformdirs import user_data_path

LOOPBACK_HOSTS = {"localhost", "localhost.localdomain", "ip6-localhost"}


def is_loopback_host(host: str) -> bool:
    candidate = host.strip().strip("[]").lower()
    if candidate in LOOPBACK_HOSTS:
        return True
    try:
        return ip_address(candidate).is_loopback
    except ValueError:
        return False


@dataclass(frozen=True)
class Settings:
    library_dir: Path
    host: str = "127.0.0.1"
    port: int = 8765
    token: str | None = None
    allow_fake: bool = False
    dev: bool = False
    allow_local_plugins: bool = False
    web_dist: Path | None = None
    max_upload_bytes: int = 200 * 1024 * 1024
    max_archive_entries: int = 5000
    max_uncompressed_bytes: int = 500 * 1024 * 1024
    max_entry_bytes: int = 100 * 1024 * 1024
    max_compression_ratio: int = 100

    def __post_init__(self) -> None:
        if self.token is not None:
            try:
                self.token.encode("ascii")
            except UnicodeEncodeError as exc:
                raise ValueError("The local token must contain only ASCII characters") from exc
        if not is_loopback_host(self.host) and not self.token:
            raise ValueError(
                "A local token is required when the Studio listens on a non-loopback host"
            )


def default_library_dir() -> Path:
    return user_data_path("vibebook") / "library"
