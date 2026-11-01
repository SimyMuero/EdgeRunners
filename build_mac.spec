# -*- mode: python ; coding: utf-8 -*-
"""macOS 打包設定（在 Mac 上執行）

用法：
    pyinstaller build_mac.spec --noconfirm --clean

產出：dist/EdgeRunners.app

和 Windows 的 build.spec 差異：
  · 產物是 .app bundle（用 BUNDLE 包裝）
  · 圖標用 .icns 而不是 .ico
  · 不需要 pytun_pmd3 的 wintun.dll（macOS 用 utun 核心介面）
  · 加入 NSLocalNetworkUsageDescription（iOS 17+ 的 tunnel 會用到本機網路）
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
ICON = os.path.join(HERE, 'assets', 'icon.icns')

datas = [(WEB, 'web')]
binaries = []
hiddenimports = []

datas += collect_data_files('pymobiledevice3')
hiddenimports += collect_submodules('pymobiledevice3')

# developer 指令需要 trace.codes，少了它定位與模擬會直接失敗
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
    upx=False,                 # macOS 上 UPX 容易讓簽章與公證失敗
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,          # 想同時支援 Intel 與 Apple Silicon 可改成 'universal2'
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='EdgeRunners',
)

app = BUNDLE(
    coll,
    name='EdgeRunners.app',
    icon=ICON if os.path.exists(ICON) else None,
    bundle_identifier='studio.muerosimy.edgerunners',
    info_plist={
        'CFBundleName': 'EdgeRunners',
        'CFBundleDisplayName': 'EdgeRunners',
        'CFBundleShortVersionString': '0.5.2',
        'CFBundleVersion': '0.5.2',
        'NSHighResolutionCapable': True,
        'LSMinimumSystemVersion': '12.0',
        'NSLocalNetworkUsageDescription':
            'EdgeRunners 需要本機網路權限，才能與連接的 iPhone 建立開發者通道。',
    },
)
