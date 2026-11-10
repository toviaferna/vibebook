# Auditoría de seguridad — ola 1B/4

Fecha: 2026-11-10. Alcance: backend Python, Studio, shell Tauri y cliente web.

## Controles implementados

| Área | Control | Evidencia |
|---|---|---|
| Rutas | `safe_book_path` en repair, sync report, analyzer, mix y biblioteca | `tests/test_repair.py`, `tests/test_sync_report.py`, `tests/test_ambience_analyzer.py` |
| ZIP | Límite por entrada, total real descomprimido, ratio y nombres seguros | `tests/studio/test_api_books.py` |
| Token | Header obligatorio fuera de loopback; `stdin` en el escritorio | `tests/studio/test_sidecar.py`, `test_api_books.py` |
| Medios | Ticket HMAC ligado a libro/tipo/ruta, TTL 300 s | `tests/studio/test_media_tickets.py` |
| Token en URL | Rechazado en query; el cliente pide tickets | `tests/studio/test_media_tickets.py`, `web/src/api/media.test.ts` |
| SSRF | DNS + rangos privados/link-local, sin redirects, loopback explícito | `tests/test_plugin.py` |
| Registro de plugins | Backup `.corrupt-*` y negativa a sobrescribir JSON corrupto | `tests/test_plugin.py` |
| CSP | Producción y `devCsp` en Tauri | `src-tauri/tauri.conf.json` |
| Headers | `nosniff`, `DENY`, `no-referrer` | `src/audiol/studio/security.py` |

## Dependencias

- `npm audit --omit=dev`: 0 vulnerabilidades (78 dependencias de producción).
- `uvx pip-audit`: sin vulnerabilidades conocidas.
- `npm audit` completo: 0 vulnerabilidades.

## Pruebas ejecutadas

- Suite backend: 464 tests.
- Vitest: 96 tests.
- Playwright: 10 tests, incluido a11y con axe.
- `cargo check` con la CSP nueva.
- `npm run check:bundle`: 118,9 KiB JS / 8,4 KiB CSS.

## Riesgos residuales

1. **DNS rebinding**: la URL se valida antes de cada request, pero la conexión
   vuelve a resolver. Mitigación futura: pinning por IP o proxy con allowlist.
2. **CSP en runtime**: falta abrir la app Tauri empaquetada en Windows, macOS y
   Linux y revisar la consola del WebView.
3. **Flatpak**: el sidecar y ffmpeg dentro del sandbox no se probaron en un
   host Linux real.
4. **Android**: el APK está firmado y verificado, pero no se probó en hardware;
   SAF/SQLite/audio local siguen pendientes.
5. **HTTP plano en LAN**: el token protege autenticación, no confidencialidad.
6. **Tickets en memoria**: reiniciar el sidecar invalida tickets; es aceptable
   por el TTL corto.

## Recomendaciones para la próxima ola

- Pinning de IP para plugins y prueba de rebinding.
- Probar la CSP empaquetada con un smoke test de Tauri por plataforma.
- Añadir `npm audit`/`pip-audit` al CI.
- Evaluar firma de binarios y notarización macOS.
