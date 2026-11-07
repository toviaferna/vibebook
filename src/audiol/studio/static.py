from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse

from audiol.studio.settings import Settings


def mount_static(app: FastAPI, settings: Settings) -> None:
    if settings.web_dist is not None and (settings.web_dist / "index.html").is_file():
        root = settings.web_dist.resolve()
        index = root / "index.html"

        @app.get("/{path:path}", include_in_schema=False)
        def spa(path: str):
            if path == "api" or path.startswith("api/"):
                return HTMLResponse("Not found", status_code=404)
            candidate = (root / path).resolve()
            if candidate.is_file() and candidate.is_relative_to(root):
                return FileResponse(candidate)
            return FileResponse(index)

        return

    @app.get("/", include_in_schema=False)
    def placeholder() -> HTMLResponse:
        return HTMLResponse(
            """
            <!doctype html>
            <html lang="es">
              <head><meta charset="utf-8"><title>Vibebook Studio</title></head>
              <body style="font-family: system-ui; max-width: 42rem; margin: 4rem auto">
                <h1>Vibebook Studio</h1>
                <p>El backend está corriendo. La interfaz web llega en la Fase 3.</p>
                <ul>
                  <li><a href="/docs">Documentación de la API</a></li>
                  <li><a href="/api/health">Estado del servicio</a></li>
                  <li><a href="/api/books">Biblioteca</a></li>
                </ul>
              </body>
            </html>
            """
        )
