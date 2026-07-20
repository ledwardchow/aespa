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
# the .ico. Pin the interpreter and desktop stack so releases are reproducible.
$BuildVenv = "build\venv"
if (Test-Path $BuildVenv) { Remove-Item -Recurse -Force $BuildVenv }
uv venv --python 3.14 $BuildVenv | Out-Null
$env:VIRTUAL_ENV = (Resolve-Path $BuildVenv).Path
uv pip install --quiet . `
    "pyinstaller==6.21.0" `
    "pyinstaller-hooks-contrib==2026.6" `
    "pywebview==6.2.1" `
    "pythonnet==3.1.0" `
    "clr-loader==0.3.1" `
    "pystray==0.19.5" `
    "pillow==12.3.0"

$Py = "$BuildVenv\Scripts\python.exe"

Write-Host "==> Generating $Ico from $IconSrc"
New-Item -ItemType Directory -Force -Path build | Out-Null
& $Py -c "from PIL import Image; Image.open(r'$IconSrc').save(r'$Ico', sizes=[(16,16),(32,32),(48,48),(128,128),(256,256)])"

Write-Host "==> Generating THIRD_PARTY_LICENSES.txt"
# Attribution for the bundled MIT/BSD/Apache/MPL deps. Run against the build venv
# so it lists exactly what gets frozen into the exe.
& $Py scripts\generate_third_party_licenses.py THIRD_PARTY_LICENSES.txt

Write-Host "==> Building exe with PyInstaller"
# --collect-all playwright pulls in its node driver so first-run install works in
# the bundle. A one-file exe is intentional: DLLs extracted from a downloaded ZIP
# inherit its Mark of the Web, which prevents .NET from loading Python.Runtime.dll.
if (Test-Path "dist\AESPA") { Remove-Item -Recurse -Force "dist\AESPA" }
& "$BuildVenv\Scripts\pyinstaller.exe" `
    --noconfirm `
    --clean `
    --onefile `
    --windowed `
    --name AESPA `
    --distpath "dist\AESPA" `
    --icon $Ico `
    --add-data "src\aespa\web;aespa\web" `
    --add-data "THIRD_PARTY_LICENSES.txt;." `
    --add-data "LICENSE;." `
    --collect-all playwright `
    --collect-all webview `
    --collect-submodules pystray `
    --collect-submodules aespa `
    src\aespa\desktop_win.py

Write-Host "==> Smoke-testing frozen WinForms runtime"
$SmokeProcess = Start-Process `
    -FilePath (Resolve-Path "dist\AESPA\AESPA.exe") `
    -ArgumentList "--smoke-test" `
    -PassThru `
    -Wait
if ($SmokeProcess.ExitCode -ne 0) {
    throw "Frozen Windows runtime smoke test failed with exit code $($SmokeProcess.ExitCode)"
}

# Keep attributions directly accessible in the release archive.
Copy-Item "THIRD_PARTY_LICENSES.txt" "dist\AESPA\THIRD_PARTY_LICENSES.txt"
Copy-Item "LICENSE" "dist\AESPA\LICENSE"

Write-Host "==> Done: dist\AESPA\AESPA.exe"
Write-Host "    Unsigned - SmartScreen may warn on first run (More info > Run anyway)."
Write-Host "    Distribute the whole dist\AESPA\ folder (zip it)."
