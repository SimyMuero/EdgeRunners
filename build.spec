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
ICON = os.path.join(HERE, 'assets', 'icon.ico')

datas = [(WEB, 'web')]
binaries = []
hiddenimports = []

datas += collect_data_files('pymobiledevice3')
hiddenimports += collect_submodules('pymobiledevice3')

datas += collect_data_files('pykdebugparser')

# 把所有已安裝套件的 dist-info 一起打包。
# pymobiledevice3 會在執行時用 importlib.metadata.version() 查套件版本
# （pyimg4、apple_compress、pmd_* 等），少任何一個就 PackageNotFoundError。
# 而且這類套件是平台相依的：apple_compress 只在 macOS 上安裝，
# 所以逐個補會補不完 —— 直接全部打包最保險。
from importlib.metadata import distributions as _distributions

_seen_meta = set()
for _dist in _distributions():
    try:
        _name = _dist.metadata['Name']
    except Exception:
        continue
    if not _name or _name.lower() in _seen_meta:
        continue
    _seen_meta.add(_name.lower())
    try:
        datas += copy_metadata(_name)
    except Exception:
        pass

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
    icon=ICON if os.path.exists(ICON) else None,
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

