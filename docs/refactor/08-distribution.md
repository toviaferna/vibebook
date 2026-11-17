# 08 — Empaquetado, firma y distribución

## 1. Principios

- **No se publica nada sin aprobación explícita del usuario.** Esta regla del
  repo tiene prioridad sobre cualquier checklist.
- Un artefacto no está “listo” por compilar: se instala, se abre, se prueba el
  flujo crítico y se verifica su hash.
- Cada plataforma tiene su formato nativo; no se fuerza un único instalador.
- La actualización automática es una comodidad, no un requisito para la primera
  beta.
- La app sigue siendo AGPL-3.0-only; los avisos de terceros se actualizan.

## 2. Matriz de artefactos

| Plataforma | Arquitectura | Formatos | Firma | Auto-update |
|---|---|---|---|---|
| Windows | x64 | Inno Setup `.exe`, ZIP portable | Authenticode opcional | `desktop_updater` (Inno/ZIP) |
| Windows | ARM64 | Inno Setup `.exe`, ZIP portable | Authenticode opcional | `desktop_updater` (probar ARM64) |
| macOS | arm64 | `.dmg` / `.app` | Developer ID + notarización | `desktop_updater` |
| macOS | x64 | `.dmg` / `.app` | Developer ID + notarización | `desktop_updater` |
| Linux | x64 | AppImage, `.deb`, Flatpak | GPG/Flatpak | Flatpak/DEB/APT; updater ZIP preview |
| Linux | ARM64 | AppImage, `.deb`, Flatpak | GPG/Flatpak | Flatpak/DEB/APT |
| Android | arm64-v8a | `.aab`, `.apk` | Keystore | Play Store o manual |
| iOS | arm64 | `.ipa` | Apple Developer | App Store/TestFlight |
| Web | wasm/js | sitio estático/PWA | TLS | deploy |

## 3. Versionado

- `pubspec.yaml` `version: <semver>+<build>`.
- `package_info_plus` lee la versión en runtime.
- El build number se incrementa en cada release, incluso si el semver no cambia.
- `CHANGELOG.md` con secciones por versión; no se reutiliza una versión ya
  publicada.
- No se crean tags ni releases sin aprobación; el flujo es:
  analizar → implementar → probar → revisar → instalador de prueba → aprobación
  → tag/release.
- Checksums SHA-256 por artefacto; un `SHA256SUMS.txt` por plataforma.

## 4. Windows

### Build

```powershell
flutter build windows --release
# x64: build/windows/x64/runner/Release/
```

Para ARM64, usar el toolchain/runner ARM64 correspondiente y verificar que
todos los plugins tengan binarios arm64. Si un plugin no los tiene, se excluye
la feature o se usa fallback.

### Instalador

- **Inno Setup 7.1** (soporta x64/ARM64) con:
  - `AppId` estable;
  - `DefaultDirName={autopf}\Vibebook`;
  - `PrivilegesRequired=lowest` o `admin` según instalación;
  - asociación `.epub` opcional;
  - `UninstallDisplayIcon`;
  - licencia y notices;
  - modo portable con `portable.flag`.
- **ZIP portable** con `LEEME.md`, `THIRD_PARTY_NOTICES.md`, `licenses/`.
- **MSIX** opcional para Store/empresa; `msix` 3.18. No se mezcla con el
  updater directo.

### Firma

- `signtool sign /fd SHA256 /tr <timestamp> /td SHA256` con certificado
  Authenticode.
- Sin certificado: documentar SmartScreen (“Más información → Ejecutar de
  todas formas”).
- Verificar `signtool verify /pa`.

### Update

- `desktop_updater` 3.2:
  - feed `app-archive.json` → `release.json` → ZIP/Inno;
  - claves Ed25519 pinneadas;
  - hash/length verificados;
  - recovery store;
  - UI integrada.
- Probar actualización desde la versión anterior instalada, no solo fresh
  install.

## 5. macOS

### Build

```bash
flutter build macos --release
```

- arm64 en Apple Silicon; x64 en Intel o universal si el tamaño lo permite.
- `Info.plist` con `CFBundleShortVersionString` y `CFBundleVersion` enteros.
- Entitlements mínimos; sandbox si App Store.

### Firma y notarización

```bash
codesign --deep --force --options runtime --sign "Developer ID Application: ..." "Vibebook.app"
xcrun notarytool submit "Vibebook.zip" --keychain-profile "vibebook" --wait
xcrun stapler staple "Vibebook.app"
```

- Sin Developer ID: DMG unsigned; documentar Gatekeeper y `xattr`.
- Verificar `codesign --verify --deep --strict` y `spctl --assess`.
- `desktop_updater` requiere helper embebido y política firmada; seguir su guía
  antes de prometer auto-update.

### DMG

- `create-dmg` o `hdiutil`; fondo simple, icono,Applications link.
- Nombre: `Vibebook_<version>_<arch>.dmg`.
- Checksum por DMG.

## 6. Linux

### Build

```bash
flutter build linux --release
```

- Requisitos de build: GTK3, `libsecret-1-dev`, `libjson-glib-dev`, clang,
  cmake, ninja, pkg-config.
- x64 y ARM64; el segundo requiere runner/entorno ARM64.

### Formatos

- **AppImage**: `linuxdeploy` + `appimagetool`; incluir `libsecret` si no está
  en el sistema; FUSE2 documentado.
- **DEB**: `dpkg-deb` con dependencias (`libgtk-3-0`, `libsecret-1-0`,
  `libjson-glib-1.0-0`, `libwebkit2gtk` no aplica en Flutter); postinst para
  iconos/desktop file.
- **Flatpak**: manifest, runtime, permisos (home/read, downloads), portal de
  archivos; recomendado para updates.
- **Tarball**: opcional para power users.

### Firma

- GPG para DEB/AppImage; Flatpak firma el repo.
- Verificar con `dpkg-deb --info`, `appimage --appimage-extract`, `flatpak
  install`.

### Update

- Flatpak/DEB/APT recomendado; `desktop_updater` Linux es preview y solo ZIP
  directo. No prometer paridad con Windows/macOS.

## 7. Android

### Build

```bash
flutter build appbundle --release --target-platform android-arm64
flutter build apk --release --target-platform android-arm64
```

- `android/key.properties` fuera del repo; keystore en secretos de CI.
- `minSdk 24`, `targetSdk` actual; `compileSdk` actual.
- `android:extractNativeLibs` según necesidad; 16 KB page size en ONNX/FFmpeg.
- Proguard/R8: reglas para ONNX Runtime (`-keep class ai.onnxruntime.**`).
- Permisos mínimos; foreground service declarado.

### Distribución

- **Play Store**: AAB, listing, privacy policy, data safety, content rating.
- **Sideload**: APK firmado, checksum, instrucciones de “instalar apps
  desconocidas”.
- **Actualización**: Play Store; sideload manual. No se promete auto-update
  fuera de la tienda.
- Modelos TTS: descarga interna con checksum; no se incluyen en el AAB.

## 8. iOS

### Build

```bash
flutter build ipa --release
```

- macOS + Xcode + Apple Developer; certificados y provisioning profiles.
- `Info.plist`: background audio, file sharing si aplica, privacy strings.
- CocoaPods/SPM; `flutter_onnxruntime` requiere iOS 16 si se usa; confirmar
  `sherpa_onnx`/FFmpeg.
- App Store: sandbox, privacy nutrition labels, review notes; justificar
  descarga de modelos y contenido generado.

### Distribución

- TestFlight para beta; App Store para público.
- SinApple Developer: no hay IPA instalable; se documenta como no soportado.

## 9. Web

- `flutter build web --wasm --release`.
- Hosting estático con HTTPS, Brotli, cache de assets con hash.
- PWA: manifest, icons, service worker para shell; no para biblioteca grande.
- Limitaciones visibles: sin FFmpeg/M4B, sin filesystem, background limitado.
- Deploy: GitHub Pages/Netlify/Cloudflare; headers CSP.
- No se promete paridad; se marca “beta”.

## 10. CI/CD

### Jobs

```text
analyze (ubuntu)
test (ubuntu, windows, macos)
golden (ubuntu)
integration-desktop (windows, linux, macos)
integration-android (ubuntu + emulator)
build-linux (ubuntu x64, arm64 si hay runner)
build-windows (windows x64, arm64 si hay runner)
build-macos (macos-15 arm64, macos-15-intel x64)
build-ios (macos-15)
build-web (ubuntu)
release (solo tag aprobado)
```

- Cache de Flutter/pub, Gradle, CocoaPods.
- Secretos: keystore Android, certificados macOS/iOS, Authenticode, claves
  Ed25519 del updater.
- Artifacts por job con checksums.
- Release workflow: descarga artefactos, verifica, genera `SHA256SUMS`, crea
  GitHub Release solo con tag aprobado.
- No se publica si falta un artefacto o un checksum no coincide.

### Comandos de verificación

```bash
flutter analyze
dart format --set-exit-if-changed .
flutter test --coverage
flutter test integration_test
flutter build windows --release
flutter build macos --release
flutter build linux --release
flutter build appbundle --release --target-platform android-arm64
flutter build ipa --release
flutter build web --wasm --release
```

## 11. Checklist de release

- [ ] Aprobación explícita del usuario.
- [ ] `CHANGELOG.md` actualizado.
- [ ] Versión/build en `pubspec.yaml` y `package_info_plus`.
- [ ] Tests, analyze, goldens, integración y e2e en verde.
- [ ] Benchmarks contra presupuestos.
- [ ] Instalar cada artefacto en una máquina/VM limpia.
- [ ] Importar → convertir → leer → karaoke → exportar.
- [ ] Probar migración de una biblioteca legacy.
- [ ] Probar actualización desde la versión anterior.
- [ ] Verificar firma/notarización/Gatekeeper/SmartScreen.
- [ ] Revisar `THIRD_PARTY_NOTICES.md` y licencias (FFmpeg, modelos, fuentes).
- [ ] Verificar checksums SHA-256 contra los assets publicados.
- [ ] Confirmar que desinstalar no borra la biblioteca del usuario.
- [ ] Confirmar que no quedan procesos/servicios vivos.
- [ ] Publicar solo después de la aprobación.

## 12. Licencias y avisos

- App: AGPL-3.0-only.
- Flutter/Dart: BSD.
- Riverpod/Drift/Dio/Freezed: MIT/BSD/Apache según paquete.
- sherpa-onnx: Apache-2.0.
- FFmpegKit audio: LGPL-3.0; FFmpeg y códecs con sus licencias; incluir
  `LICENSES/` y oferta de fuente cuando corresponda.
- Modelos Piper/Kokoro: verificar licencia de cada modelo; no se bundlean sin
  permiso.
- Fuentes: OFL; incluir avisos.
- `epub_plus` fork: MIT; conservar copyright.
- `desktop_updater`: MIT.
- `THIRD_PARTY_NOTICES.md` generado/actualizado por release; no se publica sin
  revisión legal básica.

## 13. Rollback

- Guardar el artefacto anterior y su checksum.
- `desktop_updater` permite fijar una versión anterior en el feed (fresh
  install) si una release sale mal.
- Android/iOS: despublicar la versión en la tienda; no se puede downgrade
  automático.
- Web: rollback del deploy anterior.
- Nunca borrar la biblioteca del usuario en un rollback; la migración de DB
  debe ser compatible hacia atrás o restaurar backup.
