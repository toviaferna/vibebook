# Ambientación open source

Vibebook puede agregar una cama de sonido y efectos a un libro ya convertido sin
APIs pagas, cuentas ni créditos. La IA generativa es opcional y nunca es el
default.

## Fuentes y licencias

| Fuente | Licencia | Costo | Offline | Rol |
|---|---|---|---|---|
| Procedural (`ffmpeg`) | AGPL-3.0 | 0 | Sí | Default |
| Pack CC0 curado | CC0 | 0 | Sí, tras descarga | Default |
| Import del usuario | Responsabilidad del usuario | 0 | Sí | Custom |
| Freesound | CC0/CC-BY | API gratis | No | Opcional (A6) |
| Plugin IA local | Licencia del modelo | 0 | Sí, si está instalado | Opcional (A6) |

Cada asset guarda `license`, `attribution`, `source_url` y `checksum`. Un asset
sin licencia conocida no se importa. Los assets importados quedan
`approved=false` hasta que el usuario los escucha y aprueba.

## Biblioteca

`AmbienceLibrary` vive en `audiol/ambience/library.py` y usa
`<library>/ambience/assets/`:

- `<id>.ogg` (o el formato importado);
- `<id>.json` con metadata, hash, licencia y uso.

El índice SQLite `sound_assets` permite listar y filtrar sin recorrer archivos.
Si el índice se pierde, `rebuild_index()` lo reconstruye desde los JSON.

Campos principales:

```text
id, kind, prompt, tags, provider, model, seed, duration_ms, loopable,
sample_rate, channels, loudness_lufs, license, attribution, source_url,
checksum, approved, created_at, last_used_at, usage_count
```

### Camas procedurales

`ambience/procedural.py` genera seis camas loopables de 30 s, mono 48 kHz:
`rain`, `wind`, `sea`, `room`, `fire`, `night`. Usa `anoisesrc`, filtros de
ffmpeg, fades de 1 s y Opus/Vorbis. Se generan a pedido, no al arrancar.

## API

```text
GET    /api/ambience/assets?query=&kind=&license=&approved=
GET    /api/ambience/assets/{id}
POST   /api/ambience/assets/import       (multipart)
POST   /api/ambience/assets/generate     (preset opcional)
POST   /api/ambience/assets/{id}/approve
GET    /api/ambience/assets/{id}/audio
DELETE /api/ambience/assets/{id}         (solo si usage_count=0)

GET    /api/books/{id}/ambience
PUT    /api/books/{id}/ambience
POST   /api/books/{id}/ambience/analyze
```

## Plan de sonido

`ambience/plan.json` guarda por capítulo:

- una cama (`bed`) opcional;
- hasta 3 efectos (`effects`) con `segment_id` y `offset_ms`;
- ganancia, fades, confianza y razón.

Límites validados:

- 1 cama + 3 efectos por capítulo;
- separación mínima de 8 s entre efectos;
- nada en los primeros/últimos 2 s;
- confianza mínima 0.5;
- `segment_id` debe existir en el manifiesto;
- `asset_id` debe existir en la biblioteca.

El manifiesto del libro guarda:

```json
"ambience": {
  "version": 1,
  "plan": "ambience/plan.json",
  "enabled": false,
  "master_gain_db": -18,
  "ducking_db": -12
}
```

Un libro sin `ambience` se comporta exactamente como antes.

## Analizador heurístico

`ambience/analyzer.py` es offline, determinista y no inventa segment IDs. Usa un
lexicón español de escenas (lluvia, mar, viento, casa, fuego, noche) y efectos
(puerta, campana, pasos, trueno, cristal, pájaros). Elige el asset por tags o
prompt y calcula una confianza. Si no hay assets, devuelve un plan vacío.

El analizador acepta assets existentes; no genera audio automáticamente.

## Lector

`web/src/features/reader/soundscape/useSoundscape.ts` implementa la mezcla:

- crea el `AudioContext` solo cuando el usuario activa el ambiente;
- carga la cama y los efectos del capítulo actual con `fetch` + `decodeAudioData`;
- reproduce la cama en loop, con ganancia master y ducking cuando suena la voz;
- programa efectos one-shot desde `segment_id + offset_ms` y los reprograma al
  buscar más de 2 s;
- pausa/reanuda el contexto con la voz;
- libera buffers y cierra el contexto al salir o cambiar de capítulo.

El lector muestra un botón “Activar/ Apagar ambiente” en la topbar, una barra
con la escena y el volumen, y guarda `ambience_enabled` en `book_preferences`.
El volumen se recuerda en `localStorage`.

A4b usa el mismo motor sin voz: solo la cama, sin ducking y sin efectos. Sirve
para leer un EPUB importado con una sala de fondo.

En el detalle, “Generar camas” crea las seis camas procedurales y “Analizar
capítulos” propone el plan heurístico. El plan se puede editar por API; la UI de
edición fina queda para una iteración posterior.

## M4B ambientado (A5)

`POST /api/books/{id}/ambience/render` crea un job separado
(`kind=ambience_render`) y devuelve `{job_id}`. El job:

1. valida el plan contra el manifiesto y la biblioteca;
2. mezcla cada capítulo con `ffmpeg`:
   - voz + cama con `sidechaincompress` (la voz abre el ducking),
   - efectos con `adelay` y `amix`,
   - `alimiter` para evitar clipping;
3. escribe WAV intermedios y los convierte en `audio/ambientado.m4b`;
4. conserva el M4B original;
5. escribe `audio/ambientado-attribution.txt` si hay assets CC-BY.

El original no se sobrescribe. El resultado se descarga con
`GET /api/books/{id}/ambience/audio`; las atribuciones con
`GET /api/books/{id}/ambience/attribution`.

Desde el detalle, “Exportar ambientado” inicia el job y el botón de descarga
aparece al completarse.

## Fuentes opcionales (A6)

### Freesound

Requiere una API key gratuita en `FREESOUND_API_KEY` (no hay cuenta paga ni
créditos). El flujo es explícito:

```text
GET  /api/ambience/providers
POST /api/ambience/providers/freesound/import
     { "query": "rain", "license_filter": "license:Creative Commons 0" }
```

El backend busca, descarga el preview, exige licencia y atribución, y lo importa
como asset `provider=freesound` con `source_url`. Nunca se llama a Freesound de
forma automática.

### Plugin local de ambiente

Protocolo `vep-sound/1`, configurado con:

- `VIBEBOOK_AMBIENCE_PLUGIN_URL`
- `VIBEBOOK_AMBIENCE_PLUGIN_TOKEN` (opcional)

```text
POST /api/ambience/providers/plugin/import
     { "prompt": "rain on a tin roof", "kind": "ambience", "duration_ms": 30000 }
```

El plugin puede devolver `audio_base64` + metadata JSON o un cuerpo `audio/*`.
Debe declarar `license`; si falta, el asset se rechaza. Nunca se instala ni se
ejecuta solo, y el texto solo se envía cuando el usuario pide generar.

## Pruebas

```bash
uv run pytest tests/test_ambience_library.py tests/test_ambience_plan.py \
  tests/test_ambience_analyzer.py tests/studio/test_api_ambience.py

cd web && npm run test
cd web && npm run e2e
```

Cubren import, dedupe por checksum, licencia obligatoria, reconstrucción del
índice, borrado bloqueado por uso, camas procedurales, roundtrip del plan,
anchors inválidos, límites, analyzer, endpoints, scheduler de cues y el toggle
del lector.

## Estado

A1–A6 completas. No hay proveedores cloud obligatorios ni IA por default.

Limitaciones actuales:

- la cama se mantiene al pausar, pero los efectos ya pasados no se repiten;
- la edición visual del plan (mover/eliminar cues) todavía es por API;
- los efectos se limitan a assets existentes; no se generan por IA;
- el M4B ambientado se renderiza en un job de un solo worker; no hay cola
  paralela para varios libros.
