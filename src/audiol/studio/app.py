import logging
from collections.abc import Callable
from contextlib import asynccontextmanager
from importlib.metadata import PackageNotFoundError, version

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from audiol.studio.api import books, engines, jobs, reader, voices
from audiol.studio.api import settings as settings_api
from audiol.studio.db import Database
from audiol.studio.errors import install_error_handlers
from audiol.studio.jobs import JobManager
from audiol.studio.library import Library
from audiol.studio.security import install_security_middleware
from audiol.studio.settings import Settings
from audiol.studio.static import mount_static
from audiol.tools import find_binary
from audiol.tts.base import TTSProvider
from audiol.tts.factory import make_provider

logger = logging.getLogger(__name__)


def create_app(
    settings: Settings,
    provider_factory: Callable[[str], TTSProvider] | None = None,
) -> FastAPI:
    library = Library(settings.library_dir)
    db = Database(settings.library_dir / ".vibebook.db")
    resolved_factory = provider_factory or (
        lambda engine: make_provider(engine, allow_fake=settings.allow_fake)
    )
    job_manager = JobManager(
        db,
        library,
        resolved_factory,
        allow_fake=settings.allow_fake,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        db.migrate()
        db.reconcile(library.scan())
        job_manager.mark_interrupted()
        yield

    app = FastAPI(
        title="Vibebook Studio",
        version=_version(),
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.library = library
    app.state.db = db
    app.state.jobs = job_manager
    app.state.provider_factory = resolved_factory

    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["127.0.0.1", "localhost", "testserver"],
    )
    allowed_origins = [
        "tauri://localhost",
        "http://tauri.localhost",
        "https://tauri.localhost",
    ]
    if settings.dev:
        allowed_origins.extend(["http://localhost:5173", "http://127.0.0.1:5173"])
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    install_security_middleware(app, settings)

    app.include_router(books.router, prefix="/api")
    app.include_router(engines.router, prefix="/api")
    app.include_router(jobs.router, prefix="/api")
    app.include_router(reader.router, prefix="/api")
    app.include_router(voices.router, prefix="/api")
    app.include_router(settings_api.router, prefix="/api")

    @app.get("/api/health", tags=["system"])
    def health() -> dict:
        try:
            find_binary("ffmpeg")
            find_binary("ffprobe")
            has_ffmpeg = True
        except RuntimeError:
            has_ffmpeg = False
        return {
            "status": "ok",
            "version": _version(),
            "ffmpeg": has_ffmpeg,
            "library_dir": str(settings.library_dir),
        }

    install_error_handlers(app)
    mount_static(app, settings)
    return app


def _version() -> str:
    try:
        return version("vibebook")
    except PackageNotFoundError:
        return "dev"
