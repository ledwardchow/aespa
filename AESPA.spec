# -*- mode: python ; coding: utf-8 -*-
import subprocess
import sys

from PyInstaller.utils.hooks import collect_submodules
from PyInstaller.utils.hooks import collect_all

# Reproduce third-party license/NOTICE text next to the app (attribution
# obligation for the bundled MIT/BSD/Apache/MPL deps). Generated against the
# interpreter PyInstaller runs under, so it matches exactly what gets bundled.
subprocess.run(
    [sys.executable, 'scripts/generate_third_party_licenses.py', 'build/THIRD_PARTY_LICENSES.txt'],
    check=True,
)

datas = [('src/aespa/web', 'aespa/web'), ('LICENSE', '.'), ('build/THIRD_PARTY_LICENSES.txt', '.')]
binaries = []
hiddenimports = []
hiddenimports += collect_submodules('aespa')
tmp_ret = collect_all('playwright')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['src/aespa/desktop.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AESPA',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['build/AESPA.icns'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AESPA',
)
app = BUNDLE(
    coll,
    name='AESPA.app',
    icon='build/AESPA.icns',
    bundle_identifier='com.aespa.app',
)
