$ErrorActionPreference = "Stop"

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $root

$config = Get-Content "src-tauri/tauri.conf.json" -Raw | ConvertFrom-Json
$version = $config.version
$destination = "portable/Vibebook-$version"
$archive = "portable/Vibebook-$version-windows-x64.zip"

if (-not (Test-Path "dist/vibebook-sidecar.exe")) {
    throw "Falta dist/vibebook-sidecar.exe. Ejecutá 'make sidecar' primero."
}

$exe = Get-ChildItem "src-tauri/target/release/*.exe" |
    Where-Object { $_.Name -notlike "*sidecar*" } |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
if (-not $exe) {
    throw "No hay ejecutable de escritorio en src-tauri/target/release."
}

Remove-Item $destination -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path "$destination/sidecar" | Out-Null
Copy-Item $exe.FullName "$destination/Vibebook.exe"
Copy-Item "dist/vibebook-sidecar.exe" "$destination/sidecar/vibebook-sidecar.exe"
New-Item -ItemType File -Path "$destination/portable.flag" | Out-Null
Copy-Item "packaging/THIRD_PARTY_NOTICES.md" "$destination/THIRD_PARTY_NOTICES.md"
Copy-Item "docs/desktop.md" "$destination/LEEME.md"

Compress-Archive -Path "$destination/*" -DestinationPath $archive -Force
Write-Output (Resolve-Path $archive)
