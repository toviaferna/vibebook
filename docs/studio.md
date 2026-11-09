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

Abre `http://127.0.0.1:8765`. La documentación de la API está en `/docs`. La
misma interfaz corre dentro de la app Tauri con un sidecar Python; ver
[desktop.md](desktop.md) y [reader.md](reader.md).

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

- Biblioteca con búsqueda, orden, filtros, progreso de lectura y estado.
- Importación por arrastre o selector de archivo.
- Estudio por pasos: libro, voz, salida y conversión. El selector de motor se
  alimenta de `GET /api/engines`: muestra Piper, eSpeak NG, Edge y Azure con su
  estado de configuración; Fake solo aparece cuando está habilitado.
- Ajustes permite elegir el motor y la voz por defecto. El backend resuelve
  Piper → eSpeak NG → Edge como fallback legado.
- Ajustes incluye plugins VEP: agregar por URL, token opcional, probar,
  eliminar y ver licencia/fuente. Los plugins agregados aparecen como motores
  y sus voces se suman al selector.
- Progreso en vivo, cancelación y reanudación.
- Ajustes de voz, tema, tipografía y reproducción.
- Lector sincronizado con resaltado por palabra, índice, temas, tipografía,
  temporizador, atajos de teclado y modo Libro paginado.

### Lector

La ruta `#/books/{id}/read` carga el manifest, el capítulo y su timing. Un libro
importado se puede leer aunque todavía no tenga audio: el capítulo devuelve
`timing: null` y el lector funciona sin player. El resaltado por palabra se usa
cuando el timing es `exact` y la alineación supera el 80 % de cobertura; si no,
se resalta el segmento completo. La posición de audio, el capítulo y la velocidad
se guardan con debounce en `PUT /api/books/{id}/state`, y se restauran sin
autoplay al volver a abrir el libro. La posición de lectura y sus bookmarks viven
aparte, en `reading-state` y `reading-bookmarks`.

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
- `GET/POST /api/books/{id}/resegment`, `GET /api/books/{id}/resegment/backups`,
  `POST /api/books/{id}/resegment/restore`
- `GET /api/jobs/{id}`, `GET /api/jobs/{id}/events`, `POST /api/jobs/{id}/cancel`, `POST /api/jobs/{id}/resume`
- `GET /api/books/{id}/manifest`, `/chapters/{n}`, `/audio/{n}`, `/m4b`, `/epub`
- `GET /api/books/{id}/images/{image_id}`
- `GET/PUT /api/books/{id}/state`
- `GET/PUT /api/books/{id}/reading-state`
- `GET/POST /api/books/{id}/reading-bookmarks`, `DELETE /api/books/{id}/reading-bookmarks/{id}`
- `GET/PUT /api/books/{id}/preferences`
- `GET /api/books/{id}/search?q=`
- `GET/POST /api/books/{id}/bookmarks`, `DELETE /api/books/{id}/bookmarks/{bookmark_id}`
- `GET /api/engines`
- `GET /api/voices?engine=`, `POST /api/voices/preview`, `GET /api/previews/{key}`
- `GET/PUT /api/settings`

### Motores locales

El Studio puede convertir con Piper si el binario y la voz están instalados, o
con eSpeak NG si el binario está en el sistema:

```bash
uv run vibebook piper download
uv run vibebook engines
```

Si Piper no aparece como disponible, revisá [engines.md](engines.md). Si Piper
no está instalado, el Studio usa eSpeak NG como fallback local. La conversión
local no usa red ni cuentas y produce timing por segmento.

Más detalle en `/docs` (OpenAPI) mientras el servidor está corriendo.

En la app de escritorio, los recursos que no pueden enviar headers (audio,
portadas y M4B) aceptan el token como `?token=...`. Las llamadas JSON siguen
usando `X-Vibebook-Token`.
