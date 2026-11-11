# Linux

## Matriz de soporte

| Distribución | Formato | Estado |
|---|---|---|
| Ubuntu 22.04+ | AppImage / DEB | Soportado y construido en CI |
| Ubuntu 24.04+ | AppImage / DEB | Soportado y construido en CI |
| Ubuntu 20.04 | Flatpak o Studio en navegador | Soportado, Flatpak sin verificar en host |
| Otras distros con WebKitGTK 4.1 | AppImage / Flatpak | Experimental |

Ubuntu 20.04 no recibe WebKitGTK 4.1 reciente; por eso el camino recomendado es
Flatpak (runtime GNOME actualizado) o usar el Studio en el navegador con el
sidecar instalado aparte.

## Studio en navegador

```bash
uv run vibebook studio --library ~/Vibebook --port 8765 --no-browser
```

Abrí `http://127.0.0.1:8765`. El Studio escucha en loopback por defecto. Si
usás otro host, configurá un token; el servidor se niega a arrancar sin él.

## Flatpak

El manifiesto está en
[`packaging/flatpak/com.vibebook.Vibebook.yml`](../packaging/flatpak/com.vibebook.Vibebook.yml).
Empaqueta el binario Tauri, el sidecar PyInstaller, `web/dist`, el wrapper y el
icono. Usa la extensión `org.freedesktop.Platform.ffmpeg-full` para ffmpeg.

Requisitos para construir:

```bash
flatpak install flathub org.gnome.Platform//46 org.gnome.Sdk//46
flatpak-builder --user --install --force-clean build-dir \
  packaging/flatpak/com.vibebook.Vibebook.yml
```

Antes hay que generar los artefactos:

```bash
npm --prefix web run build
uv run pyinstaller packaging/pyinstaller/vibebook-sidecar.spec --noconfirm
npm run desktop:build -- --bundles appimage
```

El manifiesto espera:

- `src-tauri/target/release/vibebook`
- `dist/vibebook-sidecar`
- `web/dist/`

El wrapper agrega `/usr/lib/extensions/ffmpeg-full/bin` al `PATH` y exporta
`VIBEBOOK_SIDECAR`/`VIBEBOOK_WEB_DIST` para que Tauri encuentre el sidecar y la
web empaquetada.

### Permisos

- `--share=ipc`, Wayland y fallback X11.
- `--device=dri`.
- `--share=network` para Edge TTS y descargas de voces.
- `--filesystem=home` para la biblioteca.
- Portal de escritorio para el selector de archivos.

### Estado

El manifiesto y el wrapper están preparados, pero no se ejecutó `flatpak-builder`
en este entorno Windows. Queda pendiente el smoke test en Ubuntu 20.04/24.04 y
verificar que el sandbox permita lanzar el sidecar y ffmpeg.

## Notas

- El AppImage sigue siendo el formato principal para 22.04+.
- El DEB se construye en CI.
- No prometemos un AppImage nativo para 20.04: usa Flatpak o el Studio web.
- Los binarios no están firmados; Flatpak usa el runtime del sistema.
