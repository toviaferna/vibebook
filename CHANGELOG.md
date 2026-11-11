# Changelog

## v0.6.0 — 2026-11-10

Olas 1A, 1B, 2 y 3: integridad, seguridad, lector P1 y audio versionado.

### Agregado

- Conversión y reparación atómicas con staging, backup y recuperación de
  commits incompletos.
- Caché de paginación por libro, contenido, imágenes, viewport y tipografía.
- Actividad única por libro con leases para conversión, ambiente, resegmentación,
  restore, import y delete.
- Migraciones SQLite numeradas con backup consistente y rollback.
- Tickets HMAC de medios con TTL de 5 minutos.
- CSP de producción y `devCsp` en Tauri.
- Plugins: bloqueo de IPs privadas/link-local, sin redirects, loopback explícito.
- Lector: secuencia monotónica, offsets de Texto, CFI de Original, búsqueda por
  offset, temporizador persistente, limpieza de audio y pliego impar correcto.
- Biblioteca paginada de a 60 libros.
- Segmentos con `boundary`/`continuation`, timings con `text_hash`/`config_hash`
  y cache fingerprint por proveedor.
- Flatpak, matriz Linux y auditoría de seguridad.

### Cambiado

- El token del escritorio viaja por `stdin`; los hosts no loopback exigen token.
- Los medios usan tickets; el token en query ya no se acepta.
- Los assets de ambiente deben estar aprobados y se comparan por palabra.
- La limpieza conserva números de página y diálogo fuera de front/back matter.
- Copy de biblioteca, ajustes, estados y errores en español.

### Corregido

- Una reconversión fallida ya no mezcla audio viejo con nuevo.
- `repair` elige audio por `cache_key` y rechaza ambigüedad.
- Preferencias parciales ya no borran columnas.
- El audio se detiene y libera al salir del lector.
- El tema rápido persiste y los jobs tienen polling de respaldo.
- El último pliego impar no repite página.
- Los offsets del texto ya no son rechazados con 422.

### Seguridad

- ZIP con límite real de descompresión, ratio y rutas seguras.
- Rutas de timing/audio contenidas en el libro.
- Registro de plugins corrupto se respalda y no se sobrescribe.
- `npm audit` y `pip-audit` sin vulnerabilidades conocidas.

## v0.5.0 — 2026-11-09

Ola N: calidad de lectura, audio y rendimiento.

### Agregado

- Reparación incremental de segmentación: detecta libros convertidos con texto
  viejo, vuelve a leer el EPUB fuente y regenera solo los segmentos afectados.
- Copias de seguridad por reparación en `backups/`, restaurables desde el
  detalle del libro, la API y `vibebook repair-restore`.
- CLI `vibebook repair-segments --dry-run` para revisar el impacto antes de
  tocar el audio.
- Los manifiestos nuevos guardan `segmentation_version` y `max_chars`.

### Cambiado

- Nueva identidad **Biblioteca**: pergamino cálido, tinta, oxblood, latón y
  pizarra; reemplaza la paleta verde anterior en app, lector y capturas.
- Lector: página más editorial (medida, interlineado, folios con filetes,
  ornamento de capítulo, lomo con sombra) y paletas papel, sepia y noche
  alineadas con la identidad.
- Responsive: el alto de la página se calcula con `100dvh` menos el chrome del
  lector; a 720p y 768p la página, la navegación y el player no se solapan.
- Mobile: la topbar pasa a dos filas y el toggle de vista ya no tapa acciones.

### Rendimiento

- Rutas de lector, estudio, detalle, importación y ajustes en lazy chunks con
  `Suspense`; el JS inicial baja de 155,6 a 118,0 KiB gzip y el CSS de 11,5 a
  8,4 KiB.
- `reader.css` viaja con el chunk del lector, no con el arranque.
- La API del lector cachea el manifiesto por ruta, mtime y tamaño; la
  paginación ya estaba cacheada por capítulo y tipografía.
- `staleTime` en detalle y reparación, e índices SQLite para fecha, título y
  duración.

### Corregido

- Ambientación: consultar un libro inexistente devuelve 404 en lugar de 500.
- Reparación: se rechaza un `epub` del manifiesto que apunte fuera del libro y
  los errores internos ya no filtran rutas del servidor.
- Conversión: los libros importados con segmentación vieja se actualizan antes
  de generar el audio, sin esperar a que el usuario pulse “Reparar”.
- Reparación: `book.md` se regenera con el texto corregido.
- Lector: la página con una imagen ya no se salta al restaurar la posición
  cuando dos páginas comparten offset.
- Lector: se ignora el eco de `saveReadingState` que coincide con la página
  actual, evitando saltos al navegar.
- E2E: el test ilustrado reinicia la posición antes de buscar la figura.
- Segmentación TTS: palabras cortadas por guiones de línea, soft hyphens, spans
  inline y bloques separados ya no llegan al motor como dos fragmentos.
- Extracción de texto por bloque sin espacios artificiales entre etiquetas
  inline; `<br>` sigue separando palabras.
- Chunking con más abreviaturas protegidas y sin partir palabras largas.

## v0.4.1 — 2026-11-09

### Agregado

- APK Android lector-only firmado en CI y adjunto como asset experimental.
- Swipe horizontal y “Fin del libro” en el lector.

### Cambiado

- Lector: transición de página natural en lugar del giro 3D con hoja vacía.
- Lector: al llegar a la última página se pasa al capítulo siguiente; al
  retroceder en la primera se vuelve al capítulo anterior.
- Lector: la posición se conserva al cambiar tipografía/tamaño y se restaura si
  el estado de lectura llega tarde.
- Lector: swipe horizontal en mobile, rango de páginas y “Fin del libro”.

## v0.4.0 — 2026-11-08

Release de identidad, ambientación y plataformas.

### Agregado

- Identidad **Verdín** (I1–I5): contexto de diseño, tres direcciones, tokens,
  temas claro/oscuro, marca, estante, detalle, lector, ajustes y QA visual.
- Ambientación open source (A1–A6): biblioteca de sonidos, camas procedurales,
  plan por capítulo, analizador heurístico, mezcla Web Audio, M4B ambientado y
  providers opcionales de Freesound/plugin local.
- Sincronía karaoke Y1–Y4: diagnóstico, offsets PCM, cliente estable,
  calibración del encoder y `repair-sync`.
- Linux x64 (AppImage/deb) y macOS arm64/x64 (DMG unsigned).
- Workflow de release multi-plataforma con checksums y un único GitHub Release.
- Android lector-only MVP: file picker, IndexedDB, Epub.js y CFI persistente.
- Capturas de identidad, informe de contraste, axe y presupuesto de rendimiento.

### Cambiado

- El lector separa `theme_mode` de la app y `reader_palette` de la lectura.
- La UI deja la paleta crema/terracota por Verdín.
- Los assets de ambiente requieren licencia y aprobación explícita.

### Limitaciones conocidas

- macOS y Windows sin firma de código; SmartScreen/Gatekeeper pueden advertir.
- Android es un MVP lector-only; falta validar APK en CI/dispositivo y agregar
  SAF nativo, SQLite y audio local.
- Sin auto-update ni cuenta/cloud.
- Edge/Azure siguen como legado opt-in; el default es Piper/eSpeak local.
- Freesound y plugins de sonido son opcionales y no se configuran solos.

## v0.3.0 — 2026-11-08

Primera release pública.

### Agregado

- Lector sincronizado con karaoke por palabra, auto-scroll, temas y atajos.
- Búsqueda accent-insensitive y marcadores persistentes.
- Vista del EPUB original con sandbox y sanitización.
- App de escritorio Tauri con sidecar Python, instaladores Windows y ZIP portable.
- Word boundaries de Azure mediante el extra opcional `azure-sdk`.
- Suite E2E con Playwright y chequeos axe.

### Licencia

- Proyecto bajo GNU AGPL v3.0 only. Ver `LICENSE` y
  `packaging/THIRD_PARTY_NOTICES.md`.

### Limitaciones conocidas

- Windows x64 para la app de escritorio.
- Sin firma de código ni auto-update.
- Edge TTS es un servicio no oficial.
- EPUB con DRM no soportado.
