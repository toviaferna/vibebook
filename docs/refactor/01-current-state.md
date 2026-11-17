# 01 — Auditoría del estado actual

## 1. Producto y alcance

Vibebook convierte EPUB sin DRM en audiolibros en español latinoamericano.
La app de escritorio incluye:

- biblioteca local con portadas, búsqueda, orden, filtros y progreso;
- importación de EPUB y detección del idioma real del texto;
- estudio de conversión con motores TTS locales y cloud;
- lector sincronizado con audio, karaoke, modo Libro/Texto/Original;
- búsqueda, marcadores y estado de lectura;
- ambientación por capítulo, biblioteca de sonidos y export M4B ambientado;
- ajustes de apariencia, reproducción, motores, proveedores y plugins;
- CLI para convertir, reparar, listar voces/motores y ejecutar Studio.

El objetivo declarado es local-first: la biblioteca, la lectura y los motores
locales funcionan sin cuenta ni nube. Los proveedores cloud son opcionales.

## 2. Arquitectura actual

```text
Tauri (Rust)
  ├─ inicia y supervisa un sidecar Python onefile
  ├─ pasa token efímero por stdin
  └─ WebView con la SPA React

Sidecar Python (FastAPI + uvicorn)
  ├─ SQLite de biblioteca, jobs, estado, bookmarks, settings, assets
  ├─ filesystem: <library>/<book-id>/
  │    ├─ manifest.json
  │    ├─ book.md
  │    ├─ source.epub
  │    ├─ cover.* / images/
  │    ├─ audio/segments/, audio/chapters/
  │    ├─ timings/chapter_XXX.json
  │    ├─ ambience/plan.json
  │    └─ <titulo>.m4b
  ├─ ingest EPUB (ebooklib + lxml + decodificación determinista)
  ├─ segmentación, limpieza, chunking, language detection
  ├─ TTS: Piper, Kokoro, eSpeak, Edge, Gemini, ElevenLabs, Azure, plugins VEP
  ├─ ffmpeg/ffprobe: ensamblado, M4B, ambience procedural y mezcla
  └─ jobs persistentes con progreso, cancelación y reanudación por caché

Web React (Vite)
  ├─ React 19 + React Router 7 + TanStack Query
  ├─ epubjs para el modo Original
  ├─ OpenPageFlip + Motion para el modo Libro
  ├─ Web Audio para ambientación en vivo
  └─ chunk inicial pequeño; lector y estudio lazy
```

El sidecar se empaqueta con PyInstaller onefile y se incluye como recurso de
Tauri. En Android el sidecar se compila fuera (`#[cfg(not(mobile))]`); por eso
el APK 0.8.0 solo podía leer.

## 3. Tamaño y estructura del código

| Área | Medición |
|---|---:|
| Python (`src/audiol`) | ~13.860 líneas |
| Web (`web/src`) | ~16.235 líneas |
| Tests backend | 531 passed, 2 skipped |
| Tests web | 118 |
| Tests e2e | 19 |
| Endpoints HTTP | ~60 rutas en 8 routers |
| Motores TTS | 8 (incluye fake de test) |
| Workflows CI | `test`, `web`, `desktop`, `desktop-linux`, `e2e` |

Módulos Python principales:

- `ingest/`: EPUB, estructura, TOC, imágenes, encoding.
- `tts/`: spec/registry, providers, keys, Kokoro, Piper, eSpeak, cloud.
- `studio/`: API, DB, jobs, library, settings, plugins, media tickets, static.
- `ambience/`: assets, procedural beds, plan, analyzer, mix, providers.
- `convert.py`, `assemble.py`, `timing.py`, `manifest.py`, `storage.py`.
- `cli.py`, `repair.py`, `resegment.py`, `sync_report.py`.

Features web:

- `library`, `import`, `studio`, `reader`, `settings`.
- Componentes de shell, portadas, menús, formularios y player.
- `web/src/lib/tauri.ts` es el puente con el shell Tauri.

## 4. Modelo de datos

### Manifest del libro

`manifest.json` es la fuente de verdad por libro. Contiene, entre otros:

- `title`, `author`, `language`, `language_declared`, `language_checked`;
- `voice`, `engine`, `style`, `rate`, `status`;
- `chapters[]` con `index`, `title`, `segments[]`, `audio`, `timing`, duración;
- `toc[]`, `images[]`, `cover`, `source_epub`, `m4b`;
- `ambience` con plan, enabled, master gain y ducking;
- versiones de schema/segmentation/pause policy.

Cada `Segment` tiene `id` determinista (`c001p0002s00`), texto, índices de
capítulo/párrafo/chunk, `source_href`, `source_fragment`, `boundary` y
`continuation`.

### SQLite del Studio

Tablas: `books`, `jobs`, `book_state`, `bookmarks`, `settings`, `reading_state`,
`reading_bookmarks`, `book_preferences`, `sound_assets`. Migraciones 1–3.
Índices para estado, fecha, título, duración, bookmarks y assets. La DB es un
índice/estado; la biblioteca en disco sigue siendo portable.

### Biblioteca en disco

`Library.import_epub` crea `<library>/<slug>-<sha8>/` en un directorio temporal
y lo mueve de forma atómica. Guarda `source.epub`, `book.md`, portada, manifiesto
y, tras convertir, audio/timings/M4B. `storage.py` implementa staging, backup,
commit y recuperación de conversiones interrumpidas.

## 5. Funcionalidades por dominio

### Biblioteca

- Listado paginado (60), búsqueda, orden por reciente/título/duración/progreso.
- Portada extraída del EPUB o generada; búsqueda en Open Library/Google Books.
- Detalle con metadatos, capítulos, estado, acciones y borrado.
- Revisión de libros legacy: crea portada faltante, corrige idioma y reconstruye
  el índice si hace falta.
- Acciones por tarjeta y menú contextual; en desktop se suprime el menú nativo.

### Importación

- Selector y drag/drop.
- Validación de extensión, ZIP, cifrado, symlinks, rutas, tamaño comprimido y
  ratio de compresión.
- Decodificación determinista de XHTML: BOM, XML/meta charset, UTF-8 estricto,
  luego Windows-1252.
- Detección conservadora de idioma `es`/`en` desde el texto; guarda el valor
  declarado para diagnóstico.
- Estructura real del EPUB: partes, capítulos, títulos, TOC, imágenes.
- Segmentación y limpieza reutilizadas por el Studio y el CLI.

### Estudio / conversión

- Motor y voz filtrados por disponibilidad; estilos y rate.
- Progreso en vivo por SSE, cancelación y reanudación.
- Caché por segmento con hash de texto+voz+motor+estilo+rate+fingerprint.
- Concurrencia adaptativa por proveedor.
- Ensamblado solapado con la síntesis del capítulo siguiente.
- Timings por segmento y palabra; sidecars por capítulo.
- M4B AAC con capítulos y metadata; previews de voz.
- Reparación/re-segmentación con backup y restauración.

### Lector

- Modos Texto, Libro (paginado, doble página en desktop) y Original (EPUB).
- Audio sincronizado, karaoke por palabra, autoavance, velocidad, volumen,
  temporizador y Media Session.
- Búsqueda, TOC, bookmarks de audio y de lectura, estado por libro.
- Paletas paper/sepia/night independientes del tema de la app.
- Tipografía, tamaño, modo álbum, imágenes y selección de texto.
- Atajos de teclado y pantalla completa.
- OpenPageFlip con giro 3D y `prefers-reduced-motion`.
- Lee libros importados sin audio y ofrece convertir.

### Ambientación

- Assets importados/CC0 con licencia, hash, metadata y aprobación.
- Seis camas procedurales de 30 s generadas con ffmpeg.
- Plan por capítulo: 1 cama + hasta 3 efectos, separación mínima 8 s, guardas 2 s.
- Analizador heurístico español offline.
- Mezcla en vivo con Web Audio (loop, ducking, cues, seek).
- Export M4B ambientado con sidechain y límites.
- Freesound/plugin local opcionales, nunca por defecto.

### Ajustes y proveedores

- Tema system/light/dark, paleta y tipografía del lector.
- Voz/motor por defecto, rate, reproducción.
- Claves de Gemini/ElevenLabs/Azure; región Azure; variables de entorno con
  prioridad.
- Plugins VEP: URL, token, test, voces y borrado.
- La API nunca devuelve la clave completa.

### CLI

- `vibebook convert`, `voices`, `engines`, `studio`, `piper download/status`,
  `repair-sync`, `repair-segments`, `repair-restore`, `sync-report`.
- Salida Markdown, manifiesto, timings, segmentos, MP3 por capítulo y M4B.

## 6. Seguridad actual

- Backend en loopback por defecto; host no loopback exige token.
- Token efímero por stdin, nunca por argv; header `X-Vibebook-Token`.
- Tickets HMAC de corta duración para medios; no se acepta token en query.
- Validación estricta de uploads/EPUB (ZIP, cifrado, symlinks, ratio).
- EPUB Original en iframe sandbox sin scripts y CSP restrictiva.
- Plugins remotos HTTPS, IP pública, sin redirects; loopback solo explícito.
- Claves de proveedores en archivo local 0600 en Unix; en Windows no hay
  Credential Manager todavía.
- Sin telemetría; sin cuentas.

## 7. Pruebas y CI

- Backend: pytest + coverage, ruff, ruff format, mypy.
- Web: biome, tsc, vitest, build, bundle budget, Playwright e2e + axe.
- Desktop: PyInstaller sidecar, cargo fmt/check en Windows y Linux.
- Release: Windows ZIP/NSIS/MSI, Linux AppImage/DEB, macOS arm64/x64 DMG,
  checksums por plataforma. Firma pendiente; Gatekeeper/SmartScreen documentados.
- E2E cubre biblioteca, detalle, estudio, lector, ambientación, ajustes,
  proveedores, a11y y mobile.

## 8. Rendimiento observado

Datos de `docs/performance.md` y `docs/release.md` (Windows 11, v0.9.0):

| Métrica | Valor |
|---|---:|
| Sidecar onefile listo para health | ~4,4 s |
| Primer listado de 100 libros | ~550 ms |
| Listado en caliente de 100 libros | ~18 ms |
| Working set del sidecar | ~13 MB |
| JS inicial | ~118,9 KiB gzip |
| CSS inicial | ~8,4 KiB gzip |
| Chunk del lector | ~73,0 KiB gzip |
| Instaladores NSIS/MSI | ~150 MB |
| ZIP portable | ~148 MB |

Presupuestos actuales: sidecar ≤5 s, UI interactiva ≤3 s, listar 100 ≤100 ms,
abrir lector ≤1,5 s, paginar ≤50 ms, page-turn 60 fps, lector ≤200 MB,
Piper ≤2× tiempo real.

## 9. Plataformas

| Plataforma | Estado actual | Notas |
|---|---|---|
| Windows x64 | Soportado | WebView2; NSIS/MSI/ZIP; sin firma |
| Linux x64 | Soportado | WebKitGTK 4.1, GTK3, FUSE2; AppImage/DEB |
| macOS arm64/x64 | Soportado | DMG sin firma/notarización; Gatekeeper |
| Android | Eliminado en 0.9.0 | Último APK 0.8.0 era reader-only |
| iOS | Nunca soportado | Sin target |
| Web | Solo desarrollo/Studio local | No es un target de producto |
| Windows ARM64 | No soportado | Tauri/WebView2 y sidecar no se probaron |
| Linux ARM64 | No soportado | Sin artefactos |

## 10. Deuda y limitaciones relevantes para la refactorización

- **Dos runtimes y dos lenguajes** (Rust/Tauri + Python + React) con tres
  toolchains y tres ecosistemas de dependencias.
- **El sidecar Python no es portable a Android** con PyInstaller; fue la causa
  del lector-only.
- **El modo EPUB Original depende de WebView/iframe y epubjs**; replicarlo en
  Flutter requiere decisión de producto.
- **La ambientación en vivo depende de Web Audio**; Flutter no tiene un grafo
  de audio equivalente sin un motor nativo.
- **Kokoro español** depende de `kokoro-onnx` + espeak-ng; no está garantizado
  en todos los targets móviles.
- **FFmpeg en Windows/Linux ARM64** no está cubierto por FFmpegKit.
- **Claves en archivo local**, no en Credential Manager/Keychain.
- **Sin auto-update**; releases manuales y checksums.
- **Sin firma** en Windows/macOS; SmartScreen/Gatekeeper.
- **Migración de datos**: la biblioteca en disco es portable, pero la DB y el
  estado de lectura/jobs viven en SQLite del Studio.
- **Cobertura de dispositivos**: no hay pruebas en hardware Android/iOS real.
- **Documentación desactualizada** en algunos puntos (por ejemplo,
  `docs/architecture.md` dice que Kokoro está descartado cuando el código lo
  implementa).

## 11. Implicaciones para la nueva arquitectura

1. La biblioteca en disco y el manifiesto deben seguir siendo la fuente de
   verdad o migrarse con un plan reversible. No se debe tocar `.books/` sin
   backup.
2. El motor TTS necesita una interfaz estable por capacidades (local/cloud,
   estilos, timings, concurrencia, tamaño máximo) para no repetir el acoplamiento
   actual.
3. El lector es el feature más caro: paginación, karaoke, imágenes, modos y
   accesibilidad. Debe tener un spike propio.
4. La ambientación en vivo necesita un motor de mezcla nativo o una limitación
   explícita por plataforma.
5. El pipeline de conversión debe ser persistente y reanudable, con jobs en
   SQLite y workers en isolates/servicios.
6. La migración de datos y la compatibilidad con la biblioteca existente son
   un requisito de producto, no un detalle técnico.
