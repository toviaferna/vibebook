# ADR-0006 — FFmpegKit audio + fallback ARM64

- **Estado:** Propuesto.
- **Fecha:** 2026-11-17.

## Contexto

La app necesita decodificar audio, concatenar PCM, codificar MP3/AAC, muxear
M4B con capítulos y mezclar ambience. FFmpegKit original está discontinuado.

## Decisión

Usar **ffmpeg_kit_flutter_new_audio 2.5.8** (FFmpeg 8.1.2, LGPL-3.0) en
Android, iOS, macOS, Windows x64 y Linux x64. En Windows/Linux ARM64, usar
FFmpeg del sistema, un binario empaquetado o emulación x64, con detección y
mensaje claro.

## Alternativas

- `ffmpeg_kit_flutter` 6.0.3: discontinuado.
- `ffmpeg_kit_flutter_new` full/GPL: más tamaño y GPL innecesario.
- `media_kit`/libmpv: reproducción, no ensamblado/M4B.
- FFmpeg del sistema en todas: UX inconsistente.

## Consecuencias

- Una API Dart para FFmpeg en la mayoría de plataformas.
- `licenses/ffmpeg_kit_flutter_new_audio/` se incluye en el artefacto.
- ARM64 desktop es condicional; se prueba en F10.
- No se usa el paquete GPL completo.

## Criterios de revisión

- WAV/MP3 → AAC/M4B reproducible en Android/Windows/macOS.
- Capítulos/metadata correctos.
- Cancelación y timeout.
- Tamaño dentro del presupuesto.
