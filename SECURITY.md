# Seguridad

## Versiones soportadas

| Versión | Soporte |
|---|---|
| `0.3.x` (desktop) | Sí |
| `0.2.x` (navegador) | Sí |
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

- El backend escucha solo en `127.0.0.1`.
- El Studio puede exigir un token local. El desktop genera un token efímero por
  arranque y lo pasa al sidecar.
- Los recursos que no pueden enviar headers (audio, portadas, M4B, EPUB) aceptan
  `?token=`; el token no se registra en access logs cuando el sidecar arranca con
  `--json-ready`.
- Las subidas validan extensión, tamaño, ZIP, cifrado y symlinks.
- El EPUB original se renderiza en un iframe sandbox sin `allow-scripts`, con
  sanitización de scripts/handlers/URLs externas y CSP restrictiva.
- Los EPUB se consideran datos no confiables.

## Riesgos conocidos

- Edge TTS es un servicio no oficial y requiere red.
- FFmpeg y los binarios descargados por `static-ffmpeg` tienen su propia
  licencia y superficie de ataque.
- La app no está firmada; SmartScreen puede advertir.
- Un EPUB malicioso puede consumir CPU/memoria antes de ser rechazado; los
  límites de tamaño y entradas reducen el impacto, no lo eliminan.
- El iframe original conserva estilos del libro; la CSP puede bloquear recursos
  externos.
- Las dependencias se revisan con `npm audit`; `@xmldom/xmldom` está fijado con
  override por advisories de Epub.js.

## Buenas prácticas para contribuciones

- No agregues telemetría ni llamadas de red no documentadas.
- No debilites el token, el sandbox, la CSP ni la validación de EPUB.
- Agregá tests para paths, uploads, tokens y contenido no confiable.
- Ejecutá `uv run pytest`, `npm run test`, `npm run e2e` y `npm audit` antes de
  un PR.
