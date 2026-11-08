# Motores TTS

Vibebook resuelve los motores desde un registro común. La API
`GET /api/engines` muestra cuáles están implementados, configurados y qué
capacidades tienen.

| Motor | Tipo | Timings | Estado |
|---|---|---|---|
| Piper | local | segmento | Implementado; requiere binario y voz |
| eSpeak NG | local | segmento | Reservado para E3 |
| Edge TTS | externo | palabra | Legado; requiere internet |
| Azure Speech | externo | palabra | Legado; requiere clave y cuota |
| Fake | prueba | segmento | Solo con `allow_fake` |

## Piper local

Piper corre como proceso separado, en CPU y sin cuenta. Vibebook no descarga
binarios automáticamente.

### 1. Instalar el binario

Descargá un build de Piper para tu plataforma y dejalo en el `PATH`, en
`packaging/piper/bin/` para el sidecar, o apuntá:

```bash
export VIBEBOOK_PIPER_BIN=/ruta/a/piper
```

En Windows también sirve `VIBEBOOK_PIPER_BIN=C:\ruta\piper.exe`. El binario
necesita sus DLLs y `espeak-ng-data`; si no están junto al ejecutable, indicá:

```bash
export VIBEBOOK_PIPER_ESPEAK_DATA=/ruta/a/espeak-ng-data
```

### 2. Descargar la voz

```bash
uv run vibebook piper download
```

Descarga `es_MX-ald-medium`, valida tamaño y MD5 contra el manifiesto público de
`rhasspy/piper-voices` y escribe los archivos de forma atómica. Opciones:

```bash
uv run vibebook piper download --voice es_MX-ald-medium
uv run vibebook piper download --dest /ruta/a/voces
uv run vibebook piper download --force
```

La voz queda en el directorio de datos de la app por defecto. También podés
usar una carpeta propia:

```bash
export VIBEBOOK_PIPER_VOICES=/ruta/a/voces
```

La carpeta debe contener:

```text
es_MX-ald-medium.onnx
es_MX-ald-medium.onnx.json
```

### 3. Verificar

```bash
uv run vibebook engines
uv run vibebook piper status
uv run vibebook voices --engine piper
```

`vibebook engines` muestra `piper` como disponible solo si encuentra el binario
y la voz.

### 4. Convertir

```bash
uv run vibebook convert libro.epub \
  --engine piper \
  --voice es_MX-ald-medium \
  --out out/libro-piper
```

La conversión no usa red. Piper no devuelve palabras, así que el timing queda
como `estimated` y el lector resalta por segmento, sin fingir karaoke por
palabra.

## Variables de entorno

| Variable | Uso |
|---|---|
| `VIBEBOOK_PIPER_BIN` | Ruta o nombre del binario Piper |
| `VIBEBOOK_PIPER_VOICES` | Carpeta con `<voz>.onnx` y `<voz>.onnx.json` |
| `VIBEBOOK_PIPER_MODEL` | Ruta explícita al `.onnx` de la voz por defecto |
| `VIBEBOOK_PIPER_CONFIG` | Ruta explícita al `.onnx.json` |
| `VIBEBOOK_PIPER_ESPEAK_DATA` | Carpeta de datos de espeak-ng |

## Rendimiento

El objetivo es al menos 2× tiempo real en CPU. Medí tu instalación con:

```bash
uv run python scripts/bench-piper.py
```

En un equipo de desarrollo con `es_MX-ald-medium`, 380 caracteres produjeron
27,4 s de audio en 4,5 s (≈6× tiempo real). El bench devuelve código de error si
baja de 2×.

## Windows y rutas no ASCII

El binario clásico de Piper abre la voz y la salida con rutas ANSI. Si la ruta
del usuario contiene caracteres no ASCII, Vibebook convierte binario, voz,
configuración, salida y `espeak-ng-data` a rutas cortas 8.3 antes de invocarlo.
Si el volumen tiene las rutas cortas deshabilitadas, configurá
`VIBEBOOK_PIPER_VOICES` y `VIBEBOOK_PIPER_BIN` en una carpeta ASCII.

## Licencias y seguridad

- Piper es GPL-3.0-or-later. Se ejecuta como proceso separado; no se importa en
  el sidecar.
- La voz `es_MX-ald-medium` usa el dataset de Aldo con licencia Unlicense. La
  fuente y el modelo están en `rhasspy/piper-voices`.
- No hay `shell=True`: los argumentos se pasan como lista.
- Hay timeout por segmento; un fallo de Piper se reporta como error de
  conversión y no bloquea el sidecar.
- Las claves de Azure nunca se exponen en `GET /api/engines`; solo se publican
  los nombres de las variables.
