# ADR-0001 — Motor Flutter + Dart puro (con fallback Python)

- **Estado:** Propuesto; pendiente G1.
- **Fecha:** 2026-11-17.

## Contexto

El motor actual es Python (13.860 líneas, 531 tests) con FastAPI, ebooklib,
ffmpeg, ONNX y TTS. Tauri lo ejecuta como sidecar en desktop, pero no puede
ejecutarlo en Android/iOS. Flutter resuelve la UI multiplataforma, pero no el
motor.

## Decisión

Adoptar **Flutter 3.50 + Dart 3.14** como stack de producto y apuntar a un
**motor Dart puro** para la primera versión Flutter, condicionado a un spike
técnico (F0). Si el spike falla en Kokoro español, FFmpeg/M4B, lector o
background, adoptar **Python embebido con `serious_python`** como plan de
contingencia, conservando la UI y la arquitectura.

## Alternativas

- **Python embebido desde el inicio:** menor riesgo funcional, pero mantiene dos
  lenguajes y un runtime pesado.
- **Rust core + Flutter:** mejor rendimiento, pero reescritura y cross-compile
  de FFmpeg/ONNX muy costosos.
- **Servidor/cliente:** rápido, pero depende de PC/servidor y no es local-first.
- **KMP/Compose:** reescritura total en Kotlin; no reutiliza el motor actual.

## Consecuencias

- Si G1 = Dart puro: se reescriben ingest, TTS, ffmpeg/M4B, ambience y jobs en
  Dart; se conservan los tests actuales como especificación.
- Si G1 = Python embebido: se conserva el motor y se reemplaza Tauri por
  Flutter + `serious_python`; Web queda fuera o con backend.
- En ambos casos, la UI React se reescribe en Flutter.
- La decisión final se toma con evidencia de F0, no por preferencia.

## Criterios de revisión

- F0 demuestra Piper/Kokoro, FFmpeg/M4B, lector y background en Android y
  Windows.
- Se mide tamaño, arranque, memoria y RTF.
- El usuario aprueba G1.
