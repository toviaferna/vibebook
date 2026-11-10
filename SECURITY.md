# Seguridad

## Versiones soportadas

| Versión | Soporte |
|---|---|
| `0.6.x` (desktop) | Sí |
| `0.5.x` (desktop) | Sí |
| anteriores | No |

## Reportar una vulnerabilidad

No abras un issue público para vulnerabilidades. Usá **GitHub Security
Advisories** del repositorio (`Security` → `Report a vulnerability`) con:

- versión afectada;
- pasos de reproducción;
- impacto esperado;
- logs o capturas sin datos personales.

Vibebook es una app local; no hay servidor público ni cuentas de usuario.

## Modelo de amenaza

- El backend escucha en `127.0.0.1` por defecto. Un host no loopback exige token
  local; el Studio no arranca en LAN sin autenticación.
- El desktop genera un token efímero por arranque y lo envía al sidecar por
  `stdin`, no por `argv`. El token viaja en `X-Vibebook-Token`, nunca en URLs.
- Los medios (audio, portadas, EPUB, imágenes, M4B, ambiente, previews y sonidos)
  usan tickets HMAC de corta duración, ligados a libro + tipo + ruta. El ticket
  expira a los 5 minutos y el cliente lo renueva 30 segundos antes.
- El token en query string ya no se acepta. Los enlaces de medios se firman con
  `?ticket=`.
- Las subidas validan extensión, tamaño, ZIP, cifrado, symlinks, rutas internas,
  tamaño real descomprimido y ratio de compresión.
- El EPUB original se renderiza en un iframe sandbox sin `allow-scripts`, con
  sanitización de scripts/handlers/URLs externas y CSP restrictiva.
- Tauri usa una CSP de producción y una `devCsp` separada. La CSP permite IPC,
  sidecar en loopback, `blob:` para audio y `data:`/`blob:` para imágenes.
- Los plugins remotos deben usar HTTPS, resolver a direcciones públicas y no
  pueden redirigir a otro host. Loopback solo se permite con
  `allow_local_plugins` o `--dev`.
- Los EPUB, plugins y manifiestos se consideran datos no confiables.

## Riesgos conocidos

- Edge TTS es un servicio no oficial y requiere red.
- FFmpeg y los binarios descargados por `static-ffmpeg` tienen su propia
  licencia y superficie de ataque.
- La app no está firmada en todas las plataformas; SmartScreen puede advertir.
- Un EPUB malicioso puede consumir CPU/memoria antes de ser rechazado; los
  límites de tamaño, entradas, ratio y descompresión real reducen el impacto,
  no lo eliminan.
- El iframe original conserva estilos del libro; la CSP puede bloquear recursos
  externos.
- DNS rebinding: el plugin se revalida antes de cada request y no sigue
  redirects, pero no se fija la IP resuelta. Queda como deuda de la ola 4.
- HTTP plano en LAN con token sigue siendo sensible a sniffing; se recomienda
  loopback, túnel TLS o pareo.
- La CSP de Tauri se validó con `cargo check` y el build de escritorio, pero no
  se probó visualmente en un WebView de cada plataforma.
- Las dependencias se revisan con `npm audit` y `pip-audit`; `@xmldom/xmldom`
  está fijado con override por advisories de Epub.js.

## Buenas prácticas para contribuciones

- No agregues telemetría ni llamadas de red no documentadas.
- No debilites el token, el sandbox, la CSP, los tickets ni la validación de EPUB.
- Agregá tests para paths, uploads, tokens, tickets y contenido no confiable.
- Ejecutá `uv run pytest`, `uv run mypy src`, `npm run test`, `npm run e2e`,
  `npm audit` y `uvx pip-audit` antes de un PR.
