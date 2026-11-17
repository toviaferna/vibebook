# Changelog

## Sin publicar

### Agregado

- La preferencia de karaoke de **Libro/Álbum** se guarda por libro
  (`book_karaoke`, migración 3) y también se edita desde los ajustes de lectura.
  El valor global de v0.8.0 (`localStorage`) queda como default para libros sin
  preferencia.
- Portadas generadas para libros sin arte: composición editorial determinista
  con título, autor y paleta; la portada original se conserva cuando existe.
- Búsqueda de portadas en Open Library y Google Books con coincidencia estricta
  de título, vista previa same-origin y reemplazo seguro de la portada.
- Voces favoritas persistentes, filtro de favoritas y perfiles de lectura
  (Claro, Cálido, Melancólico, Susurro) en Studio.
- Panel **Ajustes → Proveedores en la nube** para guardar y probar claves de
  Gemini, ElevenLabs y Azure. Las claves nunca se devuelven completas.
- Motor **Gemini 3.8 Flash TTS** con estilos por `speech_metadata.style` y
  timings estimados.
- Motor **ElevenLabs** con timings exactos por carácter, etiquetas `[sad]` y
  `[whispers]` en `eleven_v3`, y voces curadas para el plan gratuito.
- Motor local **Kokoro-82M** en CPU, con descarga opcional del modelo de 354 MB
  y verificación SHA-256.
- Panel de ambiente por capítulo: cama o música, ganancia, mezcla global,
  importación de audio y exportación M4B.
- Mezcla de ambiente con faders independientes para cama sonora y efectos, con
  fundido de salida.
- EPUB de prueba editorial con portada, página de título, cinco capítulos,
  diálogos, metadatos e ilustración interna.
- Preflight de Git y normalización de finales de línea.

### Cambiado

- El giro dura 520 ms con `easeInOutCubic`, una sombra más marcada y una entrada
  solo por opacidad.
- El resaltado envuelve únicamente el segmento activo; las demás páginas siguen
  memorizadas y no se vuelven a renderizar con cada palabra.
- El libro abierto y la columna del lector aprovechan el ancho disponible en
  pantallas 2K en lugar de quedar limitados a 1380 px.

### Corregido

- El botón flotante **Volver al audio** ya no agrega altura al documento cuando
  aparece tras un giro manual.
- El resaltado por palabra encuentra los segmentos de párrafos que no empiezan
  en el offset cero.
- El auto-giro usa el offset de la palabra activa, evita reintentos durante la
  animación y vuelve a la página del audio después de la pausa manual.
- El karaoke de Libro sigue la palabra activa también en la página derecha del
  pliego; antes el índice de palabra se descartaba al cambiar de página.
- Los timings estimados de Piper ya no desactivan el resaltado palabra a palabra.
- Los presets de emoción solo se muestran cuando el motor y la voz declaran
  estilos; Edge y los motores locales ofrecen únicamente perfiles de velocidad.
- El idioma del libro se detecta a partir del texto: si el EPUB declara `en`
  pero la narraci?n es espa?ola, la biblioteca y Studio muestran `ES`.
- Las voces de ElevenLabs ahora declaran su idioma real: Adam, Antoni, Arnold
  y Bella son ingl?s multiling?e; Fernando, Cristina, Alberto, Carolina,
  Diego y Valeria son voces espa?olas de biblioteca (plan pago).
- Studio avisa cuando la voz elegida no coincide con el idioma del libro.
- Studio muestra solo las voces del motor elegido y actualiza su disponibilidad
  al guardar o quitar una clave, sin reiniciar la app. Si hay otro motor cloud
  conectado, aparece un acceso directo **Usar …** junto a las voces.
- La cama procedural `sea` usaba una frecuencia de tremolo fuera de rango y
  abortaba la generación; ahora las seis camas se generan y una falla aislada no
  descarta las demás.
- La velocidad de Gemini y ElevenLabs se aplica con ffmpeg y los timings exactos
  de ElevenLabs se reescalan para seguir sincronizados.
- La importación deja de emitir `XMLParsedAsHTMLWarning` al quitar la declaración
  XML antes del parser HTML.
- La regla de aprobación previa a releases quedó escrita en `AGENTS.md`.

### Eliminado

- El objetivo Android, sus scripts, workflow, configuración y documentación.

## v0.8.0 — 2026-11-15

### Agregado

- **Karaoke en Libro:** el párrafo activo y la palabra que suena se resaltan
  sobre la página, con un toggle **Karaoke** que se recuerda en `localStorage`.
- **Paso automático de página:** con **Seguir** activo, el audio avanza al
  pliego donde continúa la lectura; un giro manual pausa el seguimiento unos
  segundos para poder releer.
- Menú de acciones por libro en la biblioteca: botón visible al pasar el mouse o
  tocar, y clic derecho sobre la tarjeta abre **Leer**, **Ver detalles** y
  **Eliminar libro**.
- Eliminar un libro desde la biblioteca pide confirmación y borra EPUB, audio,
  sincronización y estado de lectura; el detalle del libro también muestra la
  acción en la cabecera.

### Corregido

- La vista Libro decide el pliego por la orientación real del motor, así que en
  mobile muestra una sola página en vez de comprimir dos.
- El giro de página se recorta en el área del libro y ya no ensancha el
  documento ni desplaza el resto de la app durante la animación.
- Preferencias ya no desborda con rutas de biblioteca largas: el grid usa
  `auto-fit` con `min-width: 0`, la ruta se parte dentro del panel y las filas
  de resumen se envuelven.
- El formulario de plugins alinea URL y token en dos columnas y deja el botón en
  su propia fila; en pantallas angostas pasa a una columna.
- Las opciones de tema y paleta se acomodan sin apretar las etiquetas.
- La app de escritorio ya no muestra el menú contextual del navegador
  (Recargar, Inspeccionar, etc.) al hacer clic derecho; se conserva en campos
  editables para copiar y pegar.
- La importación de EPUB decodifica el XHTML de forma determinista: BOM y
  declaración primero, UTF-8 antes de CP1252. Los libros viejos en Windows-1252
  o con una declaración Latin-1 incorrecta ya no convierten `á`, `é`, `í`, `ó`,
  `ú` y `ñ` en `?` ni en mojibake.
- La lectura usa los bytes originales del XHTML en vez de la reserialización de
  ebooklib, que descartaba los acentos sin declaración antes de decodificar.
- El título de capítulo generado vuelve a decir "Capítulo N" en vez de una
  cadena con codificación rota.
- El CLI configura stdout/stderr a UTF-8 en Windows para que los acentos no se
  pierdan al redirigir la salida.
- Un test de regresión detecta mojibake en el código fuente.

## v0.7.0 — 2026-11-15

### Agregado

- Síntesis TTS concurrente y acotada por motor (Piper 2, Edge 2, Azure 4,
  plugin según su `max_concurrency`), con el ensamblado del capítulo anterior
  solapado con la síntesis del siguiente.
- Caché de duraciones por segmento en `audio/segments/durations.json`,
  invalidada por tamaño y `mtime`, para evitar ffprobe/mutagen en
  reconversiones.
- Métricas de conversión: concurrencia, segmentos cacheados, tiempos de
  síntesis/ensamblado y aciertos de la caché de duraciones.
- `VIBEBOOK_TTS_CONCURRENCY` para reducir la concurrencia de un motor.
- Lector realista en **Libro** con tapas, lomo, canto de hojas y giro 3D de
  OpenPageFlip; doble página en escritorio y una página en mobile.
- **Libro** es el modo por defecto en escritorio (≥ 981 px); **Texto** sigue
  siendo el default mobile y el fallback accesible.
- La paginación rellena la página en curso partiendo el párrafo siguiente, sin
  dejar media página en blanco.
- `check:bundle` vigila también el chunk lazy del lector (≤ 100 KiB gzip) y su
  CSS (≤ 8 KiB gzip).

### Cambiado

- La vista Libro ya no usa un slide de 220 ms: el giro, el arrastre de borde y
  el swipe los resuelve el motor especializado, con respeto a
  `prefers-reduced-motion`.
- El escenario del libro se ajusta al pliego real: el alto se deriva del ancho
  disponible y no deja franjas vacías alrededor de las tapas.
- El reproductor se compacta entre 641 y 1100 px para liberar alto en laptops.

### Corregido

- El staging de una conversión activa ya no se borra cuando la biblioteca se
  lista durante el job.
- La paginación mide el cuerpo real de la página y ya no acepta una línea que
  luego se recortaba en anchos estrechos.

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
