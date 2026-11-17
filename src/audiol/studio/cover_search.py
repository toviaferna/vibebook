from __future__ import annotations

import io
import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_COVER_BYTES = 8 * 1024 * 1024
MAX_COVER_WIDTH = 1600
ALLOWED_HOSTS = {
    "covers.openlibrary.org",
    "books.google.com",
    "books.googleusercontent.com",
    "lh3.googleusercontent.com",
}
USER_AGENT = "Vibebook/0.8 (+https://github.com/toviaferna/vibebook)"


class CoverSearchError(Exception):
    pass


@dataclass(frozen=True)
class CoverHit:
    source: str
    title: str
    author: str
    year: int | None
    cover_url: str
    edition_url: str | None
    score: float


def normalize(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", normalized).strip()


def _title_score(query: str, candidate: str) -> float:
    left, right = normalize(query), normalize(candidate)
    if not left or not right:
        return 0.0
    if left == right:
        return 1.0
    if left in right or right in left:
        return 0.95
    ratio = SequenceMatcher(None, left, right).ratio()
    return ratio if ratio >= 0.82 else 0.0


def _author_matches(query: str, candidates: list[str]) -> bool:
    if not query or not candidates:
        return False
    words = [word for word in normalize(query).split() if len(word) > 2]
    haystack = " ".join(normalize(author) for author in candidates)
    return bool(words) and any(word in haystack for word in words)


def search_covers(title: str, author: str, limit: int = 8) -> list[CoverHit]:
    hits: list[CoverHit] = []
    errors: list[str] = []
    try:
        hits.extend(_search_open_library(title, author))
    except CoverSearchError as exc:
        errors.append(str(exc))
    if len(hits) < limit:
        try:
            hits.extend(_search_google_books(title, author))
        except CoverSearchError as exc:
            errors.append(str(exc))
    if not hits and errors:
        raise CoverSearchError("; ".join(errors))

    unique: dict[tuple[str, str], CoverHit] = {}
    for hit in hits:
        key = (normalize(hit.title), normalize(hit.author))
        current = unique.get(key)
        if current is None or hit.score > current.score:
            unique[key] = hit
    ordered = sorted(unique.values(), key=lambda hit: hit.score, reverse=True)
    return ordered[:limit]


def _search_open_library(title: str, author: str) -> list[CoverHit]:
    params: dict[str, str | int] = {
        "title": title,
        "author": author,
        "limit": 12,
        "fields": "key,title,author_name,cover_i,first_publish_year",
    }
    try:
        response = requests.get(
            "https://openlibrary.org/search.json",
            params=params,
            headers={"User-Agent": USER_AGENT},
            timeout=8,
        )
    except requests.RequestException as exc:
        raise CoverSearchError("Open Library no respondió.") from exc
    if response.status_code != 200:
        raise CoverSearchError(f"Open Library devolvió {response.status_code}.")
    try:
        docs = response.json().get("docs", [])
    except ValueError as exc:
        raise CoverSearchError("Open Library devolvió datos inválidos.") from exc

    hits: list[CoverHit] = []
    for doc in docs if isinstance(docs, list) else []:
        if not isinstance(doc, dict) or not doc.get("cover_i"):
            continue
        candidate_title = str(doc.get("title") or "")
        score = _title_score(title, candidate_title)
        if score == 0:
            continue
        authors = [str(name) for name in doc.get("author_name") or []]
        if author and _author_matches(author, authors):
            score += 0.1
        cover_id = doc["cover_i"]
        hits.append(
            CoverHit(
                source="Open Library",
                title=candidate_title,
                author=", ".join(authors) or "Autor desconocido",
                year=_optional_int(doc.get("first_publish_year")),
                cover_url=f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg",
                edition_url=f"https://openlibrary.org{doc['key']}" if doc.get("key") else None,
                score=round(score, 3),
            )
        )
    return hits


def _search_google_books(title: str, author: str) -> list[CoverHit]:
    query = f'intitle:"{title}"'
    if author:
        query += f' inauthor:"{author}"'
    try:
        params: dict[str, str | int] = {
            "q": query,
            "maxResults": 12,
            "printType": "books",
        }
        response = requests.get(
            "https://www.googleapis.com/books/v1/volumes",
            params=params,
            headers={"User-Agent": USER_AGENT},
            timeout=8,
        )
    except requests.RequestException as exc:
        raise CoverSearchError("Google Books no respondió.") from exc
    if response.status_code != 200:
        raise CoverSearchError(f"Google Books devolvió {response.status_code}.")
    try:
        items = response.json().get("items", [])
    except ValueError as exc:
        raise CoverSearchError("Google Books devolvió datos inválidos.") from exc

    hits: list[CoverHit] = []
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        volume = item.get("volumeInfo") or {}
        if not isinstance(volume, dict):
            continue
        candidate_title = str(volume.get("title") or "")
        score = _title_score(title, candidate_title)
        if score == 0:
            continue
        authors = [str(name) for name in volume.get("authors") or []]
        if author and _author_matches(author, authors):
            score += 0.1
        image = volume.get("imageLinks") or {}
        cover_url = str(image.get("thumbnail") or image.get("smallThumbnail") or "")
        if not cover_url:
            continue
        cover_url = cover_url.replace("http://", "https://").replace("&zoom=1", "&zoom=2")
        hits.append(
            CoverHit(
                source="Google Books",
                title=candidate_title,
                author=", ".join(authors) or "Autor desconocido",
                year=_optional_int(str(volume.get("publishedDate") or "")[:4]),
                cover_url=cover_url,
                edition_url=str(volume.get("infoLink") or "") or None,
                score=round(score, 3),
            )
        )
    return hits


def download_cover(url: str) -> bytes:
    response = _request_image(url)
    if response.status_code != 200:
        raise CoverSearchError(f"El servicio de portadas devolvió {response.status_code}.")
    content_type = response.headers.get("content-type", "")
    if not content_type.startswith("image/"):
        raise CoverSearchError("El recurso descargado no es una imagen.")
    payload = bytearray()
    for chunk in response.iter_content(64 * 1024):
        payload.extend(chunk)
        if len(payload) > MAX_COVER_BYTES:
            raise CoverSearchError("La portada supera el tamaño permitido.")
    return normalize_cover(bytes(payload))


def _request_image(url: str) -> requests.Response:
    current = url
    for _ in range(3):
        parsed = urlparse(current)
        if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
            raise CoverSearchError("La portada no viene de un servicio permitido.")
        try:
            response = requests.get(
                current,
                headers={"User-Agent": USER_AGENT},
                timeout=12,
                stream=True,
                allow_redirects=False,
            )
        except requests.RequestException as exc:
            raise CoverSearchError("No se pudo descargar la portada.") from exc
        location = response.headers.get("location")
        if response.status_code in {301, 302, 303, 307, 308} and location:
            current = urljoin(current, location)
            continue
        return response
    raise CoverSearchError("La portada redirige demasiadas veces.")


def normalize_cover(payload: bytes) -> bytes:
    try:
        opened = Image.open(io.BytesIO(payload))
        opened.load()
    except (UnidentifiedImageError, OSError) as exc:
        raise CoverSearchError("La portada descargada no es una imagen válida.") from exc
    image: Image.Image = ImageOps.exif_transpose(opened)
    if image.mode in {"RGBA", "LA"} or (image.mode == "P" and "transparency" in image.info):
        background = Image.new("RGB", image.size, (239, 230, 213))
        alpha = image.convert("RGBA")
        background.paste(alpha, mask=alpha.getchannel("A"))
        image = background
    else:
        image = image.convert("RGB")
    if image.width > MAX_COVER_WIDTH:
        height = round(image.height * MAX_COVER_WIDTH / image.width)
        image = image.resize((MAX_COVER_WIDTH, height), Image.Resampling.LANCZOS)
    output = io.BytesIO()
    image.save(output, format="JPEG", quality=88, optimize=True)
    return output.getvalue()


def _optional_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
