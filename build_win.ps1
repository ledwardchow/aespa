# Build AESPA.exe for Windows. Output: dist\AESPA\AESPA.exe
# Chromium is NOT bundled - it downloads into %LOCALAPPDATA%\aespa on first launch.
# Needs the Edge WebView2 runtime (preinstalled on Windows 11 and most Windows 10).
# Run from an x64 "Developer PowerShell" or any PowerShell with uv on PATH:
#   .\build_win.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$IconSrc = "src\aespa\web\icon.png"
$Ico     = "build\AESPA.ico"

Write-Host "==> Building isolated build env (non-editable install)"
# Build against a NON-editable install so PyInstaller collects complete dist-info
# (mirrors build_mac.sh). pywebview gives the native WebView2 window; pillow makes
# the .ico.
$BuildVenv = "build\venv"
if (Test-Path $BuildVenv) { Remove-Item -Recurse -Force $BuildVenv }
uv venv $BuildVenv | Out-Null
$env:VIRTUAL_ENV = (Resolve-Path $BuildVenv).Path
uv pip install --quiet . pyinstaller pywebview pystray pillow

$Py = "$BuildVenv\Scripts\python.exe"

Write-Host "==> Generating $Ico from $IconSrc"
New-Item -ItemType Directory -Force -Path build | Out-Null
& $Py -c "from PIL import Image; Image.open(r'$IconSrc').save(r'$Ico', sizes=[(16,16),(32,32),(48,48),(128,128),(256,256)])"

Write-Host "==> Building exe with PyInstaller"
# --collect-all playwright pulls in its node driver so first-run install works in
# the bundle; AESPA_BUNDLED is read at runtime (frozen sets sys.frozen too).
& "$BuildVenv\Scripts\pyinstaller.exe" `
    --noconfirm `
    --windowed `
    --name AESPA `
    --icon $Ico `
    --add-data "src\aespa\web;aespa\web" `
    --collect-all playwright `
    --collect-all webview `
    --collect-submodules pystray `
    --collect-submodules aespa `
    src\aespa\desktop_win.py

Write-Host "==> Done: dist\AESPA\AESPA.exe"
Write-Host "    Unsigned - SmartScreen may warn on first run (More info > Run anyway)."
Write-Host "    Distribute the whole dist\AESPA\ folder (zip it)."
