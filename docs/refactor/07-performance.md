# 07 — Rendimiento, profiling y presupuestos

## 1. Enfoque

No se optimiza por intuición. Cada fase tiene una **línea base medida** y un
presupuesto. Un cambio que empeora >10% un presupuesto debe justificarse con
evidencia. Los números de Flutter de este documento son **objetivos**, no
mediciones; se validan en el spike y en cada release.

## 2. Línea base actual (Tauri/React/Python)

Datos medidos en Windows 11, v0.9.0 (ver `docs/performance.md`):

| Métrica | Valor actual |
|---|---:|
| Sidecar onefile listo | ~4,4 s |
| UI interactiva | ≤3,0 s (presupuesto) |
| Primer listado 100 libros | ~550 ms |
| Listado caliente 100 libros | ~18 ms |
| Working set sidecar | ~13 MB |
| JS inicial | ~118,9 KiB gzip |
| CSS inicial | ~8,4 KiB gzip |
| Chunk lector | ~73,0 KiB gzip |
| Instalador NSIS/MSI | ~150 MB |
| ZIP portable | ~148 MB |

La app Flutter no tiene que “ganar” todas las métricas: el objetivo es no
regresar la experiencia percibida y reducir el arranque y la memoria del shell.

## 3. Presupuestos propuestos

### Arranque

| Métrica | Desktop | Mobile |
|---|---:|---:|
| Primer frame | ≤2,0 s | ≤2,5 s |
| UI interactiva (biblioteca) | ≤2,5 s | ≤3,0 s |
| Abrir libro/lector | ≤1,5 s | ≤2,0 s |
| Cambiar de pantalla | ≤300 ms | ≤400 ms |
| Reanudar app desde background | ≤500 ms | ≤800 ms |

### Memoria

| Estado | Desktop | Mobile |
|---|---:|---:|
| App idle (biblioteca) | ≤180 MB | ≤220 MB |
| Lector con audio | ≤300 MB | ≤350 MB |
| Conversión activa | ≤500 MB | ≤600 MB |
| Pico importando EPUB 100 MB | ≤400 MB | ≤500 MB |

### Listas y datos

| Operación | Presupuesto |
|---|---:|
| Query de 100 libros en caliente | ≤50 ms |
| Scroll de 10k libros | 60 fps |
| Búsqueda FTS5 en 10k libros | ≤100 ms |
| Abrir detalle | ≤200 ms |
| Paginar capítulo | ≤50 ms |
| Page-turn | 60 fps (16 ms/frame) |

### Audio/TTS

| Operación | Presupuesto |
|---|---:|
| Piper RTF (CPU) | ≤2× tiempo real |
| Kokoro RTF (CPU, desktop) | ≤3× tiempo real |
| Carga de modelo local | ≤3 s (después del primer uso) |
| Playback start | ≤300 ms |
| Seek | ≤200 ms |
| Mezcla ambience en vivo | sin underruns; ≤10% CPU |
| Ensamblado capítulo 10 min | ≤30 s |
| M4B 1 h | ≤2 min |

### Distribución

| Artefacto | Presupuesto |
|---|---:|
| Windows installer x64 | ≤180 MB |
| macOS DMG | ≤180 MB |
| Linux AppImage | ≤200 MB |
| Android AAB (arm64, sin modelos) | ≤180 MB |
| iOS IPA | ≤180 MB |
| Web inicial | ≤5 MB gzip (sin modelos) |

Los modelos Kokoro/Piper se descargan aparte; no cuentan en el artefacto base.

## 4. Herramientas

### Flutter/DevTools

- `flutter run --profile --trace-startup` para arranque.
- DevTools **Performance**: frames, jank, timeline, raster/UI.
- DevTools **Memory**: snapshots, allocations, leaks.
- DevTools **CPU profiler**.
- `flutter build <target> --analyze-size` para tamaño.
- `flutter test integration_test/perf` + `IntegrationTestWidgetsFlutterBinding`
  `watchPerformance`.
- `Timeline`/`dart:developer` para eventos de import/TTS/ffmpeg/reader.

### Plataforma

| Plataforma | Herramientas |
|---|---|
| Windows | Windows Performance Analyzer, ETW, Task Manager, `flutter run --profile` |
| macOS | Instruments (Time Profiler, Allocations, Leaks), `xcrun` |
| Linux | `perf`, `valgrind --tool=massif`, `heaptrack`, DevTools |
| Android | Android Studio Profiler, `adb shell dumpsys gfxinfo`, Perfetto, `simpleperf` |
| iOS | Xcode Instruments, MetricKit |
| Web | Chrome DevTools Performance/Memory, Lighthouse |

### Base de datos

- Drift: `EXPLAIN QUERY PLAN`, índices, FTS5.
- Medir queries con 1k/10k/100k filas sintéticas.
- Evitar N+1; usar joins/streams.

## 5. Reglas de optimización

### UI

- `ListView.builder`/`SliverList` para listas; nunca `Column` con miles de hijos.
- `const` widgets; separar widgets para limitar rebuilds.
- Evitar `Opacity` animado; usar `AnimatedOpacity`/`FadeTransition`.
- Evitar `saveLayer`, `Clip.antiAliasWithSaveLayer`, `ShaderMask` innecesario.
- No usar `IntrinsicHeight/Width` en listas grandes.
- Imágenes: `cacheWidth/cacheHeight`, `ResizeImage`, formatos comprimidos.
- Portadas: thumbnails; no cargar originales en la grilla.
- Texto del lector: cachear páginas y `TextPainter`; no repaginar por frame.
- Animaciones: `transform`/`opacity`; duración ≤520 ms; reduced motion.

### Estado

- Providers selectivos (`select`) para evitar rebuilds globales.
- `AsyncNotifier` con cache; invalidación explícita.
- No bloquear el isolate de UI con parseo/hash/ffmpeg/TTS.
- Streams con backpressure; no emitir por segmento a 60 Hz.

### Datos

- Drift en isolate; queries paginadas; índices; FTS5.
- No cargar el manifiesto completo si solo se necesita metadata; cachear por
  path+mtime.
- Escrituras por lotes/transacciones; debounce de posición (350 ms) y
  secuencia monotónica.

### Audio/TTS

- No cargar modelos al arrancar; lazy load al primer uso.
- Reutilizar sesiones ONNX; no recrear por segmento.
- Chunking por caracteres; concurrencia por proveedor; no saturar CPU.
- Piper/Kokoro en isolate/worker; no en UI.
- ffmpeg con `-nostdin`, `-hide_banner`, `-loglevel error`; cancelar procesos.
- Cache de duraciones y segmentos; invalidar por hash/mtime.

### Arranque

- Diferir servicios no críticos (updates, providers, ambience).
- No abrir DB/parsear biblioteca antes del primer frame; skeleton + stream.
- Splash nativo; evitar trabajo síncrono en `main`.
- Tree-shake icons; evitar paquetes pesados en el arranque.
- Evaluar `deferred components` solo si hay evidencia; no por defecto.

## 6. Plan de medición por fase

| Fase | Medición |
|---|---|
| F0 Spike | Arranque, tamaño APK/desktop, TTS RTF, M4B, memoria |
| F1 Fundación | Primer frame, DB, navegación, tema |
| F2 Biblioteca | 10k libros, scroll, búsqueda, portadas |
| F3 TTS/Jobs | RTF, concurrencia, CPU, memoria, cancelación |
| F4 Lector | Paginación, page-turn, karaoke, memoria |
| F5 Ambience | Mezcla en vivo, CPU, export |
| F6 Plataformas | Builds, size, background, permisos |
| F7 Release | Regresión completa vs baseline |

Cada fase guarda resultados en `docs/refactor/benchmarks/<fecha>-<fase>.md` con:
hardware, OS, build mode, comando, métrica, valor, comparación.

## 7. App size

- `flutter build apk --analyze-size --target-platform android-arm64`.
- `flutter build windows --analyze-size`, `macos`, `linux`.
- Revisar `flutter pub deps --style=compact`.
- Evitar assets duplicados; subset de fuentes; SVG minificado.
- Modelos TTS fuera del binario; descarga con checksum.
- FFmpegKit: elegir variante `_audio` (no `_full`/GPL).
- Android: AAB con split por ABI; solo arm64 si el target lo permite.
- Web: tree-shake, deferred, compresión Brotli.

## 8. Perfilado de audio/TTS

- Medir RTF con textos de 1, 5 y 20 minutos, en hardware objetivo.
- Medir carga de modelo en frío/caliente.
- Medir concurrencia: 1/2/4 workers; CPU y memoria.
- Perfilar ONNX con `numThreads` óptimo por dispositivo; no asumir.
- Medir ffmpeg por capítulo y M4B; I/O vs CPU.
- Validar que el audio no se corta ni se desincroniza al cambiar velocidad.

## 9. Perfilado de lector

- Tiempo de paginación por capítulo y tamaño de texto.
- Page-turn: build/raster; `saveLayer`; sombras.
- Memoria de páginas cacheadas; límite LRU.
- Scroll de texto vs paginado; no re-renderizar todo el capítulo.
- Karaoke: actualizar solo spans activos, no todo el párrafo.
- Imágenes: decode/cache; no bloquear el frame.

## 10. CI de rendimiento

- Job nocturno/semanal en runners estables (no compartidos) para benchmarks.
- Comparar contra baseline; fallar si >10% en métricas críticas.
- No bloquear PRs por ruido de CI; usar tendencias.
- Publicar tabla en el PR cuando cambie una ruta caliente.

## 11. Criterios de aceptación

- [ ] Baseline medido y documentado antes de optimizar.
- [ ] Presupuestos de arranque, memoria, listas, lector y audio definidos.
- [ ] Cada release reporta las métricas y la comparación.
- [ ] No hay regresiones >10% sin justificación.
- [ ] TTS local no bloquea la UI ni supera el RTF objetivo.
- [ ] App size dentro del presupuesto o con plan de reducción.
- [ ] Perfilado en hardware real, no solo emulador.
