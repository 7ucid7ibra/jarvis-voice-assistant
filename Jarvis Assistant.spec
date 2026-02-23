# -*- mode: python ; coding: utf-8 -*-

import os
import platform
import subprocess
import sys


def _is_universal_python() -> bool:
    try:
        output = subprocess.check_output(["file", sys.executable], text=True)
        return "x86_64" in output and "arm64" in output
    except Exception:
        return False


REQUESTED_ARCH = os.environ.get("JARVIS_TARGET_ARCH", "universal2")
if REQUESTED_ARCH == "universal2" and not _is_universal_python():
    TARGET_ARCH = "arm64" if platform.machine() == "arm64" else "x86_64"
    print(
        f"[Jarvis build] Universal2 requested but interpreter is single-arch; "
        f"falling back to {TARGET_ARCH}."
    )
else:
    TARGET_ARCH = REQUESTED_ARCH

a = Analysis(
    ['run.py'],
    pathex=['.'],
    binaries=[],
    datas=[('jarvis_assistant/assets', 'jarvis_assistant/assets')],
    hiddenimports=[],
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
    name='Jarvis Assistant',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=TARGET_ARCH,
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
    name='Jarvis Assistant',
)
app = BUNDLE(
    coll,
    name='Jarvis Assistant.app',
    icon='packaging/assets/icons/icon2.icns',
    bundle_identifier=None,
)
