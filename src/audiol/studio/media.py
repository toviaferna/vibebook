from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import secrets
import time
from datetime import UTC, datetime

TICKET_TTL_SECONDS = 300
_SECRET = secrets.token_bytes(32)

MEDIA_PATHS = {
    "cover": re.compile(r"^/api/books/[^/]+/cover$"),
    "epub": re.compile(r"^/api/books/[^/]+/epub$"),
    "m4b": re.compile(r"^/api/books/[^/]+/m4b$"),
    "audio": re.compile(r"^/api/books/[^/]+/audio/\d+$"),
    "images": re.compile(r"^/api/books/[^/]+/images/[^/]+$"),
    "ambience": re.compile(r"^/api/books/[^/]+/ambience/audio$"),
    "sound": re.compile(r"^/api/ambience/assets/[^/]+/audio$"),
    "preview": re.compile(r"^/api/previews/[a-f0-9]{16}\.(mp3|wav)$"),
}


def is_media_path(path: str) -> bool:
    return any(pattern.match(path) for pattern in MEDIA_PATHS.values())


def path_matches_kind(path: str, kind: str) -> bool:
    pattern = MEDIA_PATHS.get(kind)
    return pattern is not None and pattern.match(path) is not None


def issue_ticket(
    book_id: str, kind: str, path: str, ttl: int = TICKET_TTL_SECONDS
) -> tuple[str, str]:
    expires = int(time.time()) + ttl
    payload = {
        "book_id": book_id,
        "kind": kind,
        "path": path,
        "exp": expires,
    }
    encoded = _encode(payload)
    signature = _sign(encoded)
    expires_at = datetime.fromtimestamp(expires, tz=UTC).isoformat()
    return f"{encoded}.{signature}", expires_at


def verify_ticket(ticket: str, path: str) -> dict | None:
    try:
        encoded, signature = ticket.rsplit(".", 1)
    except ValueError:
        return None
    if not hmac.compare_digest(signature, _sign(encoded)):
        return None
    try:
        payload = _decode(encoded)
    except ValueError:
        return None
    if not isinstance(payload, dict):
        return None
    if payload.get("path") != path:
        return None
    expires = payload.get("exp")
    if not isinstance(expires, int) or expires < int(time.time()):
        return None
    return payload


def _sign(encoded: str) -> str:
    return hmac.new(_SECRET, encoded.encode("utf-8"), hashlib.sha256).hexdigest()


def _encode(payload: dict) -> str:
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _decode(encoded: str) -> dict:
    padding = "=" * (-len(encoded) % 4)
    raw = base64.urlsafe_b64decode(f"{encoded}{padding}".encode("ascii"))
    return json.loads(raw)
