# Plugin VEP de ejemplo

Servidor mínimo que cumple **Vibebook Engine Protocol v1** (`vep/1`). Sirve para
probar el registro de plugins y como plantilla para motores propios.

## Ejecutar

```bash
python examples/plugin-template/server.py --port 9001
```

Opcionalmente, exigir un token:

```bash
VEP_TOKEN=mi-token python examples/plugin-template/server.py --port 9001
```

## Agregar a Vibebook

```bash
curl -X POST http://127.0.0.1:8765/api/engines/plugins \
  -H "Content-Type: application/json" \
  -H "X-Vibebook-Token: <token>" \
  -d '{"url":"http://127.0.0.1:9001"}'
```

Luego aparece en `GET /api/engines` y en `GET /api/voices?engine=demo-sine`.
La voz de ejemplo es `es-MX-demo`.

## Contrato

- `GET /v1/info`: manifiesto con protocolo, id, licencia, fuente, capacidades,
  límites y voces.
- `GET /v1/health`: `{"ok": true}`.
- `GET /v1/voices`: `{"voices": [...]}`.
- `POST /v1/synthesize`: recibe texto, voz, estilo, rate y formato; devuelve
  `audio_base64`, `format`, `duration_ms` y `words` (puede ser `[]`).

El audio debe ser WAV o MP3 válido y no superar 50 MB. Vibebook valida el
archivo antes de usarlo.

## Licencia

Este ejemplo es MIT. Un plugin real debe declarar su propia licencia y fuente en
`/v1/info`. Vibebook muestra ambos datos antes de usarlo.
