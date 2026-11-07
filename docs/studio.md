# Studio

La app local incluye una interfaz web para biblioteca, importación, conversión,
lector sincronizado y ajustes, más una API para el lector.

## Arranque

```powershell
uv sync
cd web
npm ci
npm run build
cd ..
uv run vibebook studio --library out
```

Abre `http://127.0.0.1:8765`. La documentación de la API está en `/docs`.

## Desarrollo

```powershell
# terminal 1
uv run vibebook studio --library out --allow-fake --no-browser

# terminal 2
cd web
npm run dev
```

Vite abre `http://localhost:5173` y hace proxy de `/api` al backend. En
desarrollo se habilita el motor `Fake` para probar sin red.

## Interfaz

- Biblioteca con búsqueda, orden, progreso y estado.
- Importación por arrastre o selector de archivo.
- Estudio por pasos: libro, voz, salida y conversión.
- Progreso en vivo, cancelación y reanudación.
- Ajustes de voz, tema, tipografía y reproducción.
- Lector sincronizado con resaltado por palabra, índice, temas, tipografía,
  temporizador y atajos de teclado.

### Lector

La ruta `#/books/{id}/read` carga el manifest, el capítulo y su timing. El
resaltado por palabra se usa cuando el timing es `exact` y la alineación supera
el 80 % de cobertura; si no, se resalta el segmento completo. La posición,
el capítulo y la velocidad se guardan con debounce en
`PUT /api/books/{id}/state`, y se restauran sin autoplay al volver a abrir el
libro.

Opciones:

| Opción | Descripción |
|---|---|
| `--library PATH` | Biblioteca a usar. Por defecto, la carpeta de datos de la app |
| `--host` | Interfaz; por defecto `127.0.0.1` |
| `--port` | Puerto; `0` elige uno libre |
| `--no-browser` | No abre el navegador |
| `--allow-fake` | Habilita el motor fake para desarrollo/tests |
| `--token` | Exige `X-Vibebook-Token` en las rutas `/api` |
| `--dev` | CORS para Vite en `localhost:5173` |

Sin `web/dist`, `GET /` muestra una página de estado; con `web/dist` sirve la SPA.

## Flujo mínimo por API

```bash
curl -H "X-Vibebook-Token: smoke" \
  -F "file=@libro.epub;type=application/epub+zip" \
  http://127.0.0.1:8765/api/books/import

curl -X POST http://127.0.0.1:8765/api/books/<id>/convert \
  -H "Content-Type: application/json" \
  -H "X-Vibebook-Token: smoke" \
  -d '{"voice":"es-MX-JorgeNeural","engine":"fake","rate":"-10%"}'

curl http://127.0.0.1:8765/api/jobs/<job_id> \
  -H "X-Vibebook-Token: smoke"
```

## Endpoints

- `GET /api/health`
- `GET /api/books`, `POST /api/books/import`, `POST /api/books/rescan`
- `GET/DELETE /api/books/{id}`, `GET /api/books/{id}/cover`
- `POST /api/books/{id}/convert`
- `GET /api/jobs/{id}`, `GET /api/jobs/{id}/events`, `POST /api/jobs/{id}/cancel`, `POST /api/jobs/{id}/resume`
- `GET /api/books/{id}/manifest`, `/chapters/{n}`, `/audio/{n}`, `/m4b`
- `GET/PUT /api/books/{id}/state`
- `GET /api/voices`, `POST /api/voices/preview`, `GET /api/previews/{key}`
- `GET/PUT /api/settings`

Más detalle en `/docs` (OpenAPI) mientras el servidor está corriendo.
