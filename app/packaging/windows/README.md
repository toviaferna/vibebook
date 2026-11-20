# Instalador de Windows

El instalador usa [Inno Setup](https://jrsoftware.org/isinfo.php). No está
firmado: Windows SmartScreen puede mostrar una advertencia.

## Requisitos

- Flutter 3.50+ y Visual Studio Build Tools.
- Inno Setup 6 (`winget install JRSoftware.InnoSetup` o `choco install innosetup`).

## Construir

```powershell
cd app
flutter build windows --release
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" packaging\windows\vibebook.iss
```

El resultado queda en `app/dist/Vibebook-Setup-0.1.0.exe`.

Para cambiar la versión:

```powershell
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" /DMyAppVersion=0.2.0 packaging\windows\vibebook.iss
```

## Qué incluye

- La app Flutter completa (`build/windows/x64/runner/Release`).
- Los DLL de Piper, sherpa-onnx, FFmpegKit y los plugins.
- Accesos en el menú Inicio y, opcionalmente, en el escritorio.
- Desinstalador estándar.

Los libros, la biblioteca y los modelos de voz se guardan en el perfil del
usuario y no se eliminan al desinstalar.
