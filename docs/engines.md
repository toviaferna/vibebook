# Motores TTS

Vibebook resuelve los motores desde un registro común. La API
`GET /api/engines` muestra cuáles están implementados, configurados y qué
capacidades tienen.

| Motor | Tipo | Timings | Estado |
|---|---|---|---|
| Piper | local | segmento | Implementado; requiere binario y voz |
| eSpeak NG | local | segmento | Implementado; fallback local |
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

## eSpeak NG

eSpeak NG es el fallback local cuando Piper no está disponible. Es pequeño,
GPL-3.0 y suena más robótico, pero no necesita red ni cuenta.

```bash
export VIBEBOOK_ESPEAK_BIN=/ruta/a/espeak-ng
uv run vibebook convert libro.epub \
  --engine espeak \
  --voice es-419 \
  --out out/libro-espeak
```

La voz por defecto es `es-419` (español latinoamericano). En Windows, el
instalador MSI deja `espeak-ng.exe` y `espeak-ng-data` en la misma carpeta; el
proveedor pasa `--path` automáticamente. Si los datos están en otra ruta:

```bash
export VIBEBOOK_ESPEAK_PATH=/ruta/que-contiene/espeak-ng-data
```

También usa rutas cortas 8.3 en Windows para salida y datos cuando la ruta del
usuario tiene caracteres no ASCII.

## Plugins VEP

Un plugin es un servidor HTTP/JSON que cumple **Vibebook Engine Protocol v1**.
Puede estar escrito en cualquier lenguaje y no se instala ni se descarga solo.

### Contrato

| Método | Ruta | Uso |
|---|---|---|
| `GET` | `/v1/info` | Manifiesto, licencia, fuente, capacidades, límites y voces |
| `GET` | `/v1/health` | Salud del plugin |
| `GET` | `/v1/voices` | Voces disponibles |
| `POST` | `/v1/synthesize` | Texto a audio |

`/v1/info` devuelve como mínimo:

```json
{
  "protocol": "vep/1",
  "id": "mi-motor",
  "name": "Mi motor",
  "version": "1.0.0",
  "license": "MIT",
  "source": "https://github.com/...",
  "capabilities": {
    "languages": ["es"],
    "styles": [],
    "timings": "segment",
    "streaming": false
  },
  "limits": {
    "max_chars": 400,
    "max_concurrency": 1,
    "timeout_seconds": 120
  },
  "voices": [
    {"id": "es-MX-demo", "locale": "es-MX", "gender": "female", "styles": []}
  ]
}
```

`POST /v1/synthesize` recibe `text`, `voice`, `style`, `rate` y `format`
(`wav`) y devuelve:

```json
{
  "audio_base64": "...",
  "format": "wav",
  "duration_ms": 1234,
  "words": []
}
```

`words` puede ser `[]`. Vibebook valida que el WAV sea legible, limita la
respuesta a 50 MB y aplica timeout. Los errores usan
`{"error":{"code":"...","message":"..."}}`.

### Agregar un plugin

```bash
curl -X POST http://127.0.0.1:8765/api/engines/plugins \
  -H "Content-Type: application/json" \
  -H "X-Vibebook-Token: <token>" \
  -d '{"url":"http://127.0.0.1:9001","token":"opcional"}'
```

El plugin aparece en `GET /api/engines`, `GET /api/engines/plugins` y sus voces
en `GET /api/voices?engine=<id>`. La UI de Ajustes permite agregar, probar y
eliminar plugins, y muestra licencia y fuente.

Endpoints de administración:

- `GET /api/engines/plugins`
- `POST /api/engines/plugins`
- `DELETE /api/engines/plugins/{id}`
- `PUT /api/engines/{id}/config`
- `POST /api/engines/{id}/test`
- `GET /api/engines/{id}/voices`

### Seguridad

- Los plugins locales por HTTP solo se aceptan en `127.0.0.1`, `localhost` o
  `::1`; los remotos deben usar HTTPS.
- El token opcional se envía en `X-Vibebook-Plugin-Token`, se guarda en
  `secrets.json` con permisos restringidos y nunca se devuelve a la interfaz.
- No se instala ni se descarga código automáticamente.
- Los textos no se registran en logs.
- La licencia y la fuente se muestran antes de usar el plugin.

### Plantilla

Hay un servidor mínimo funcional en
[`examples/plugin-template`](../examples/plugin-template/README.md). Se puede
usar como base y probar con:

```bash
python examples/plugin-template/server.py --port 9001
```

## Motor por defecto

El orden local-first es:

1. **Piper** si el binario y una voz están disponibles.
2. **eSpeak NG** si el binario está disponible.
3. **Edge** como último recurso legado si no hay motor local.

`vibebook convert` sin `--engine` usa el primer motor local disponible. Si no
hay ninguno, falla con un mensaje que pide instalar Piper/eSpeak o pasar
`--engine edge` explícitamente. El Studio muestra Edge como último recurso y
permite cambiar el motor y la voz por defecto en Ajustes.

## Variables de entorno

| Variable | Uso |
|---|---|
| `VIBEBOOK_PIPER_BIN` | Ruta o nombre del binario Piper |
| `VIBEBOOK_PIPER_VOICES` | Carpeta con `<voz>.onnx` y `<voz>.onnx.json` |
| `VIBEBOOK_PIPER_MODEL` | Ruta explícita al `.onnx` de la voz por defecto |
| `VIBEBOOK_PIPER_CONFIG` | Ruta explícita al `.onnx.json` |
| `VIBEBOOK_PIPER_ESPEAK_DATA` | Carpeta de datos de espeak-ng para Piper |
| `VIBEBOOK_ESPEAK_BIN` | Ruta o nombre del binario eSpeak NG |
| `VIBEBOOK_ESPEAK_PATH` | Carpeta que contiene `espeak-ng-data` |

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

- Piper es GPL-3.0-or-later y eSpeak NG es GPL-3.0-or-later. Ambos se ejecutan
  como procesos separados; no se importan en el sidecar.
- La voz `es_MX-ald-medium` usa el dataset de Aldo con licencia Unlicense. La
  fuente y el modelo están en `rhasspy/piper-voices`.
- No hay `shell=True`: los argumentos se pasan como lista.
- Hay timeout por segmento; un fallo del motor se reporta como error de
  conversión y no bloquea el sidecar.
- Las claves de Azure nunca se exponen en `GET /api/engines`; solo se publican
  los nombres de las variables.
