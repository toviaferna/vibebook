# Roadmap

v0 convierte EPUB en M4B con Edge TTS o Azure. Lo pendiente se ordena por
impacto en la escucha, no por dificultad.

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

- [ ] Añadir marcas de tiempo por segmento si se necesita sincronización entre
  texto y audio. v0 no las genera.
- [ ] Evaluar PDF como entrada. Queda fuera de v0.
- [ ] Evaluar SFX y música. Queda fuera de v0.
- [ ] Decidir la licencia del repositorio.

## Deuda técnica

- [ ] Renombrar el paquete `audiol` a `vibebook`. El intento con `git mv` falló
  por un directorio inaccesible en `/mnt/c` de WSL; hace falta una estrategia
  segura antes de reintentarlo. El comando `vibebook` ya funciona y `audiol`
  queda como alias.
- [ ] Añadir una prueba de humo con un EPUB real al CI, sin red.
