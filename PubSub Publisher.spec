# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

BASE_DIR = Path(globals().get("SPECPATH", Path.cwd())).resolve()
ASSETS_DIR = BASE_DIR / "pubsub_publisher" / "assets"
ICON_FILE = ASSETS_DIR / "AppIcon.icns"
ICON = str(ICON_FILE) if ICON_FILE.exists() else None
APP_VERSION = "1.0.1"

hiddenimports = []
hiddenimports += collect_submodules("google.cloud.pubsub_v1")
hiddenimports += collect_submodules("google.auth")
hiddenimports += collect_submodules("google.api_core")
hiddenimports += collect_submodules("opentelemetry")

a = Analysis(
    [str(BASE_DIR / "pubsub_publisher" / "main.py")],
    pathex=[str(BASE_DIR)],
    binaries=[],
    datas=[(str(ASSETS_DIR), "pubsub_publisher/assets")],
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
    name='PubSub Publisher',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=True,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=ICON,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='PubSub Publisher',
)
app = BUNDLE(
    coll,
    name="PubSub Publisher.app",
    icon=ICON,
    bundle_identifier="com.pubsubpublisher.app",
    info_plist={
        "CFBundleShortVersionString": APP_VERSION,
        "CFBundleVersion": APP_VERSION,
    },
)
