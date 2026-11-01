# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包設定

用法：
    pyinstaller build.spec --noconfirm --clean

三個關鍵的 collect 對應三個「打包後才會炸」的問題：
  collect_data pykdebugparser → developer 指令需要 trace.codes
  collect_all  pytun_pmd3     → userspace tunnel 需要 wintun.dll
  copy_metadata pyimg4        → pyimg4 用 importlib.metadata 取版本號
"""

import os

from PyInstaller.utils.hooks import (
    collect_all,
    collect_data_files,
    collect_submodules,
    copy_metadata,
)

HERE = os.path.abspath('.')
WEB = os.path.join(HERE, 'web')

datas = [(WEB, 'web')]
binaries = []
hiddenimports = []

datas += collect_data_files('pymobiledevice3')
hiddenimports += collect_submodules('pymobiledevice3')

datas += collect_data_files('pykdebugparser')
datas += copy_metadata('pyimg4')
datas += copy_metadata('pymobiledevice3')

for pkg in ('pytun_pmd3', 'webview'):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

a = Analysis(
    ['app.py'],
    pathex=[HERE],
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
    name='EdgeRunners',
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
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='EdgeRunners',
)

