# Piper local

Esta carpeta es opcional y no se versiona. El build de escritorio incluye su
contenido en el sidecar cuando existe:

```text
packaging/piper/
  bin/
    piper.exe              # o piper en Linux/macOS
    *.dll                  # dependencias del binario en Windows
    espeak-ng-data/        # datos de espeak-ng que usa Piper
  voices/
    es_MX-ald-medium.onnx
    es_MX-ald-medium.onnx.json
```

## Voz

Descargala y verificá sus checksums con:

```bash
uv run vibebook piper download --dest packaging/piper/voices
```

El comando usa el manifiesto público de `rhasspy/piper-voices`, valida tamaño y
MD5, y escribe los archivos de forma atómica. La voz por defecto es
`es_MX-ald-medium` (Unlicense en el dataset; Piper es GPL-3.0).

## Binario

Vibebook no descarga binarios automáticamente. Colocá un build de Piper para la
plataforma en `packaging/piper/bin` o configurá `VIBEBOOK_PIPER_BIN` para
desarrollo. El binario debe poder encontrar `espeak-ng-data` junto a él o en
`VIBEBOOK_PIPER_ESPEAK_DATA`.

En Windows, si la ruta del usuario tiene caracteres no ASCII, Vibebook usa rutas
cortas 8.3 para el binario, la voz, la salida y `espeak-ng-data`. Si el volumen
tiene las rutas cortas deshabilitadas, usá una carpeta ASCII y apuntá
`VIBEBOOK_PIPER_VOICES` ahí.

## Licencias

Piper es GPL-3.0-or-later. Se ejecuta como proceso separado, nunca dentro del
sidecar. Al distribuir binarios hay que ofrecer el código fuente correspondiente
y conservar los avisos de `THIRD_PARTY_NOTICES.md`.
