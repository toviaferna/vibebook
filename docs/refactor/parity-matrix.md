# Matriz de paridad funcional

> Prioridad: **P0** = imprescindible para la primera beta Flutter; **P1** =
> importante, puede llegar en una beta posterior; **P2** = deseable.
> Estado objetivo: **Paridad**, **Condicional** (depende de plataforma/runtime),
> **Diferida** (aprobada para después) o **Baja** (requiere aprobación explícita).

| # | Funcionalidad actual | Prioridad | Objetivo Flutter | Notas |
|---|---|---|---|---|
| 1 | Biblioteca con portadas, búsqueda, orden y filtros | P0 | Paridad | Drift + FTS5; grillas virtualizadas |
| 2 | Importar EPUB con selector y drag/drop | P0 | Paridad | file_selector + desktop_drop |
| 3 | Validación de EPUB/ZIP/paths/ratio | P0 | Paridad | Tests de seguridad |
| 4 | Decodificación determinista de XHTML | P0 | Paridad | BOM/XML/meta/UTF-8/CP1252 |
| 5 | Detección de idioma real | P0 | Paridad | Port del detector actual |
| 6 | Estructura/TOC/títulos/imágenes | P0 | Paridad | Parser vendorizado |
| 7 | Portada extraída/generada/buscada | P0 | Paridad | Open Library/Google Books |
| 8 | Detalle con metadata y capítulos | P0 | Paridad | — |
| 9 | Borrar libro con confirmación | P0 | Paridad | No borrar fuera del libro |
| 10 | Conversión con motores locales/cloud | P0 | Paridad | Piper/cloud; Kokoro condicional |
| 11 | Estilos y rate | P0 | Paridad | Cloud; locales sin estilos |
| 12 | Jobs con progreso, cancelar, reanudar | P0 | Paridad | Drift + isolates |
| 13 | Caché de segmentos y duraciones | P0 | Paridad | Hash/fingerprint |
| 14 | Timings por segmento/palabra | P0 | Paridad | Exactos cloud; estimados local |
| 15 | M4B AAC con capítulos/metadata | P0 | Paridad | FFmpegKit; ARM64 condicional |
| 16 | Preview de voz | P1 | Paridad | — |
| 17 | Reparar sync y re-segmentar | P1 | Paridad | CLI y UI |
| 18 | Lector Texto | P0 | Paridad | CustomScrollView + spans |
| 19 | Lector Libro paginado | P0 | Paridad | Paginador propio, 2 páginas desktop |
| 20 | Lector Original | P1 | Condicional | HTML simplificado o WebView (G2) |
| 21 | Karaoke por palabra/segmento | P0 | Paridad | Fallback por cobertura |
| 22 | Player: play, ±15 s, capítulo, velocidad, volumen, timer | P0 | Paridad | just_audio/audio_service |
| 23 | Media Session / controles del sistema | P1 | Paridad en mobile/macOS | Desktop best-effort |
| 24 | Autoavance de capítulo | P1 | Paridad | — |
| 25 | Búsqueda en libro | P0 | Paridad | FTS5/índice |
| 26 | Bookmarks de audio y lectura | P0 | Paridad | Drift |
| 27 | Estado de lectura/audio persistente | P0 | Paridad | Debounce + secuencia |
| 28 | Tema app light/dark/system | P0 | Paridad | Tokens |
| 29 | Paletas del lector paper/sepia/night | P0 | Paridad | Por libro |
| 30 | Tipografía y tamaño del lector | P0 | Paridad | Fuentes bundleadas |
| 31 | Modo álbum/imágenes | P1 | Paridad | — |
| 32 | Atajos de teclado | P1 | Paridad | Desktop |
| 33 | Pantalla completa | P1 | Paridad | window_manager |
| 34 | Ambientación: assets/plan/análisis | P1 | Paridad | Fase F9 |
| 35 | Mezcla en vivo | P1 | Condicional | Players/Web Audio/native |
| 36 | Export M4B ambientado | P1 | Condicional | FFmpeg; ARM64 |
| 37 | Ajustes de apariencia/reproducción | P0 | Paridad | — |
| 38 | Proveedores y claves | P0 | Paridad | Secure storage |
| 39 | Plugins VEP | P2 | Paridad | HTTP/JSON |
| 40 | CLI | P1 | Paridad separada | Dart CLI o mantener Python CLI |
| 41 | Migración de biblioteca/DB/estado | P0 | Paridad | Backup/rollback |
| 42 | Auto-update desktop | P2 | Condicional | desktop_updater; firma |
| 43 | Accesibilidad AA | P0 | Paridad | Semantics/contraste/foco |
| 44 | i18n es/en | P1 | Paridad | ARB/gen_l10n |
| 45 | Sin telemetría por defecto | P0 | Paridad | Sentry opt-in |
| 46 | Android: leer + escuchar | P0 | Paridad | El objetivo original |
| 47 | Android: convertir en background | P1 | Condicional | Foreground service |
| 48 | iOS: leer + escuchar | P1 | Condicional | Firma/TestFlight |
| 49 | Web: lector | P2 | Condicional | Sin FFmpeg/M4B |
| 50 | Windows/Linux ARM64 | P2 | Condicional | FFmpeg/runners |

## Reglas de paridad

- Un P0 debe estar cubierto antes de declarar la beta “lista para cutover”.
- Un P1 puede diferirse con una decisión registrada y visible en la UI.
- Un P2 no bloquea la beta.
- “Condicional” debe mostrar un mensaje claro en la plataforma afectada; no
  fallar en silencio.
- Cualquier “Baja” requiere aprobación explícita del usuario y actualización de
  esta matriz.

## Funcionalidades en riesgo

| Funcionalidad | Riesgo | Plan |
|---|---|---|
| Kokoro español | Modelo/frontend no validado | Spike F0; fallback Piper/cloud o Python |
| EPUB Original | Fidelidad sin WebView | G2; HTML simplificado o WebView |
| Ambience vivo | Mezcla no sample-accurate | Players/FFI/Web Audio; medir |
| M4B ARM64 desktop | FFmpegKit sin arm64 | Binario/sistema/emulación |
| Background Android/iOS | Restricciones del OS | Foreground service/BGTask |
| Web | FFmpeg/FFI/filesystem | Best-effort/lector+nube |
| Auto-update | Firma/plataforma | desktop_updater; stores |
