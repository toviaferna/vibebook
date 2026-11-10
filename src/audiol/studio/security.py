import hmac
import zipfile
from pathlib import Path, PurePosixPath

from fastapi import Request, UploadFile

from audiol.studio.errors import ApiError, error_response
from audiol.studio.settings import Settings

EPUB_CONTAINER = "META-INF/container.xml"
CHUNK_SIZE = 1024 * 1024


async def save_epub_upload(upload: UploadFile, destination: Path, settings: Settings) -> None:
    filename = upload.filename or ""
    if not filename.lower().endswith(".epub"):
        raise ApiError(422, "invalid_epub", "El archivo debe tener extensión .epub.")

    destination.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    try:
        with destination.open("wb") as handle:
            while chunk := await upload.read(1024 * 1024):
                total += len(chunk)
                if total > settings.max_upload_bytes:
                    raise ApiError(
                        413,
                        "file_too_large",
                        "El EPUB supera el tamaño máximo permitido.",
                    )
                handle.write(chunk)
        _validate_epub_archive(destination, settings)
    except BaseException:
        destination.unlink(missing_ok=True)
        raise


def _validate_epub_archive(path: Path, settings: Settings) -> None:
    with path.open("rb") as handle:
        magic = handle.read(4)
    if magic != b"PK\x03\x04":
        raise ApiError(422, "invalid_epub", "El archivo no es un EPUB/ZIP válido.")
    try:
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
            names = {info.filename for info in infos}
            if EPUB_CONTAINER not in names:
                raise ApiError(
                    422,
                    "invalid_epub",
                    "El EPUB no contiene META-INF/container.xml.",
                )
            if len(infos) > settings.max_archive_entries:
                raise ApiError(
                    422,
                    "invalid_epub",
                    "El EPUB contiene demasiadas entradas.",
                )
            if sum(info.file_size for info in infos) > settings.max_uncompressed_bytes:
                raise ApiError(
                    422,
                    "invalid_epub",
                    "El EPUB descomprimido supera el tamaño permitido.",
                )
            if any(info.flag_bits & 0x1 for info in infos):
                raise ApiError(
                    422,
                    "invalid_epub",
                    "El EPUB está cifrado y no se puede procesar.",
                )
            if any(_is_symlink(info) for info in infos):
                raise ApiError(
                    422,
                    "invalid_epub",
                    "El EPUB contiene enlaces simbólicos.",
                )
            if any(not _is_safe_archive_name(info.filename) for info in infos):
                raise ApiError(
                    422,
                    "invalid_epub",
                    "El EPUB contiene rutas de archivo no seguras.",
                )
            _validate_expanded_size(archive, infos, settings)
    except zipfile.BadZipFile as exc:
        raise ApiError(422, "invalid_epub", "El archivo no es un EPUB/ZIP válido.") from exc


def _validate_expanded_size(
    archive: zipfile.ZipFile,
    infos: list[zipfile.ZipInfo],
    settings: Settings,
) -> None:
    total = 0
    for info in infos:
        if info.is_dir():
            continue
        if info.file_size > settings.max_entry_bytes:
            raise ApiError(422, "invalid_epub", "Una entrada del EPUB es demasiado grande.")
        if info.compress_size > 0:
            ratio = info.file_size / info.compress_size
            if ratio > settings.max_compression_ratio:
                raise ApiError(
                    422,
                    "invalid_epub",
                    "El EPUB tiene una compresión sospechosa.",
                )
        elif info.file_size > 0:
            raise ApiError(
                422,
                "invalid_epub",
                "El EPUB tiene una compresión sospechosa.",
            )
        try:
            with archive.open(info) as handle:
                entry_total = 0
                while chunk := handle.read(CHUNK_SIZE):
                    entry_total += len(chunk)
                    total += len(chunk)
                    if entry_total > settings.max_entry_bytes:
                        raise ApiError(
                            422,
                            "invalid_epub",
                            "Una entrada del EPUB es demasiado grande.",
                        )
                    if total > settings.max_uncompressed_bytes:
                        raise ApiError(
                            422,
                            "invalid_epub",
                            "El EPUB descomprimido supera el tamaño permitido.",
                        )
        except (RuntimeError, zipfile.BadZipFile) as exc:
            raise ApiError(422, "invalid_epub", "El EPUB contiene datos dañados.") from exc


def _is_safe_archive_name(name: str) -> bool:
    if not name or "\x00" in name:
        return False
    normalized = name.replace("\\", "/")
    path = PurePosixPath(normalized)
    if path.is_absolute():
        return False
    return not any(part == ".." for part in path.parts)


def _is_symlink(info: zipfile.ZipInfo) -> bool:
    mode = (info.external_attr >> 16) & 0o170000
    return mode == 0o120000


def install_security_middleware(app, settings: Settings) -> None:
    @app.middleware("http")
    async def security_middleware(request: Request, call_next):
        if (
            request.method == "POST"
            and request.url.path == "/api/books/import"
            and (length := request.headers.get("content-length"))
        ):
            try:
                too_large = int(length) > settings.max_upload_bytes + 1024 * 1024
            except ValueError:
                too_large = False
            if too_large:
                return _secure_response(
                    error_response(
                        413,
                        "file_too_large",
                        "El EPUB supera el tamaño máximo permitido.",
                    )
                )

        if (
            request.method != "OPTIONS"
            and settings.token
            and request.url.path.startswith("/api")
            and request.url.path != "/api/health"
        ):
            provided = request.headers.get("X-Vibebook-Token") or request.query_params.get(
                "token", ""
            )
            if not hmac.compare_digest(provided.encode("utf-8"), settings.token.encode("utf-8")):
                return _secure_response(
                    error_response(
                        401,
                        "invalid_token",
                        "Token local inválido o ausente.",
                    )
                )
        response = await call_next(request)
        return _secure_response(response)


def _secure_response(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response
