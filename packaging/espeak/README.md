# eSpeak NG local

Esta carpeta es opcional y no se versiona. El build de escritorio incluye su
contenido en el sidecar cuando existe:

```text
packaging/espeak/
  bin/
    espeak-ng.exe          # o espeak-ng en Linux/macOS
    libespeak-ng.dll       # dependencias en Windows
    espeak-ng-data/        # datos de voces y diccionarios
```

## Instalación

- Windows: instalador MSI oficial de
  [espeak-ng releases](https://github.com/espeak-ng/espeak-ng/releases).
- Linux: `sudo apt-get install espeak-ng`.
- macOS: `brew install espeak-ng`.

Para desarrollo podés apuntar al binario sin copiarlo:

```bash
export VIBEBOOK_ESPEAK_BIN=/ruta/a/espeak-ng
```

Si los datos no están junto al binario:

```bash
export VIBEBOOK_ESPEAK_PATH=/ruta/que-contiene/espeak-ng-data
```

La voz local por defecto es `es-419`. eSpeak NG es GPL-3.0-or-later y se ejecuta
como proceso separado. Al distribuir el binario hay que ofrecer el código fuente
correspondiente y conservar los avisos de `THIRD_PARTY_NOTICES.md`.
