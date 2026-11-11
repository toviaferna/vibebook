# Roadmap

v0 convierte EPUB en M4B con Edge TTS o Azure. Lo pendiente se ordena por
impacto en la escucha, no por dificultad.

## Estado actual

- Core, Studio, lector sincronizado, búsqueda, marcadores, EPUB original y app
  Tauri están implementados.
- Olas 1A, 1B, 2 y 3 cerradas: integridad, seguridad, lector P1 y audio
  versionado.
- Release 0.5.0 publicado; 0.6.0 prepara tickets de medios, CSP, Flatpak y
  documentación de seguridad.
- Licencia definida: AGPL-3.0-only.
- Android sigue como lector EPUB; el puente, audio local y on-device no están
  implementados.
- [x] Release 0.6.0 publicado con 13 assets y checksums.
- [x] Decisión de lenguaje documentada en `docs/language-decision.md`.
- [ ] Flatpak verificado en Ubuntu 20.04/24.04.
- [ ] APK probado en dispositivo Android.
- [ ] Firma de binarios y capturas finales.

## Plataformas

- Linux: ver [`docs/linux.md`](linux.md) para la matriz Ubuntu 20.04/22.04/24.04,
  AppImage, DEB y Flatpak.
- Android: ver [`docs/android.md`](android.md).

## Decisión de voz

- [ ] Comparar `es-MX-JorgeNeural`, `es-MX-DaliaNeural`, `es-PY-MarioNeural` y
  `es-PY-TaniaNeural` durante 30 minutos.
- [ ] Elegir entre MX y PY y actualizar el default del CLI y este documento.
- [x] Velocidad confirmada en `-10%`; es el default del CLI.
- [ ] Anotar el resultado en
  [`results/listening-scorecard.md`](../results/listening-scorecard.md).

## Salida M4B

- [ ] Definir el ajuste pendiente del M4B: volumen, tamaño o velocidad. Los
  previews y el M4B están cerca de -19,5 LUFS, así que el volumen no explica
  la diferencia por sí solo.
- [ ] Medir bitrate, tamaño y duración de un capítulo completo antes de cambiar
  los parámetros de `assemble.py`.

## Azure y estilos

- [ ] Probar los estilos `chat`, `cheerful`, `sad`, `excited` y `whispering`
  con `es-MX-JorgeNeural`.
- [ ] Comparar cada estilo contra Edge con la misma voz.
- [ ] Elegir un estilo solo si mejora la emoción sin artefactos.

## Producto

- [x] Marcas de tiempo por segmento y por palabra para el lector sincronizado.
- [ ] Evaluar PDF como entrada. Queda fuera de v0.
- [ ] Evaluar SFX y música. Queda fuera de v0.
- [ ] Decidir la licencia del repositorio.

## Deuda técnica

- [ ] Renombrar el paquete `audiol` a `vibebook`. El intento con `git mv` falló
  por un directorio inaccesible en `/mnt/c` de WSL; hace falta una estrategia
  segura antes de reintentarlo. El comando `vibebook` ya funciona y `audiol`
  queda como alias.
- [ ] Añadir una prueba de humo con un EPUB real al CI, sin red.
