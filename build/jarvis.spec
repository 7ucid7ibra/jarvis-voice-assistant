# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from pathlib import Path

# Get the project root directory
spec_dir = Path(SPECPATH)
PROJECT_ROOT = spec_dir.parent.parent

# Add the project root to Python path for imports
sys.path.insert(0, str(PROJECT_ROOT))

print(f"PROJECT_ROOT: {PROJECT_ROOT}")
print(f"Main script: {PROJECT_ROOT / 'jarvis_assistant' / 'main.py'}")

block_cipher = None

# Define data files to include
data_files = [
    # Include the entire jarvis_assistant package
    ('../jarvis_assistant', 'jarvis_assistant'),
    # Include settings and memory files if they exist
    ('../memory.json', '.'),
]

a = Analysis(
    ['../jarvis_assistant/main.py'],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=data_files,
    hiddenimports=[
        # PyQt6 modules
        'PyQt6',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'PyQt6.QtMultimedia',
        'PyQt6.QtDBus',
        'PyQt6.QtNetwork',
        'PyQt6.QtOpenGL',
        'PyQt6.QtPrintSupport',
        'PyQt6.QtSql',
        'PyQt6.QtTest',
        'PyQt6.QtXml',
        'PyQt6.QtQuick',
        'PyQt6.QtQml',
        'PyQt6.QtWebEngine',
        'PyQt6.QtWebEngineCore',
        'PyQt6.QtWebEngineWidgets',
        # Standard library
        'json',
        'threading',
        'time',
        'typing',
        'pathlib',
        'os',
        'sys',
        'logging',
        'subprocess',
        'multiprocessing',
        'queue',
        'urllib',
        'urllib.request',
        'urllib.parse',
        'http',
        'http.client',
        'ssl',
        'socket',
        'select',
        'fcntl',
        # Third-party
        'numpy',
        'numpy.core',
        'numpy.lib',
        'sounddevice',
        'cffi',
        '_cffi_backend',
        'pyttsx3',
        'pyttsx3.drivers',
        'pyttsx3.drivers.nsspeech',
        'requests',
        'urllib3',
        'certifi',
        'charset_normalizer',
        'idna',
        'whisper',
        'torch',
        'torch.nn',
        'torch.nn.functional',
        'torch.optim',
        'torchvision',
        'torchaudio',
        'tqdm',
        'tiktoken',
        'more_itertools',
        'numba',
        # Local modules
        'jarvis_assistant.agents',
        'jarvis_assistant.audio_io',
        'jarvis_assistant.config',
        'jarvis_assistant.conversation',
        'jarvis_assistant.gui',
        'jarvis_assistant.ha_client',
        'jarvis_assistant.llm_client',
        'jarvis_assistant.memory',
        'jarvis_assistant.stt',
        'jarvis_assistant.tts',
        'jarvis_assistant.ui_framework',
        'jarvis_assistant.utils',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude unnecessary modules to reduce size
        'tkinter',
        'matplotlib',
        'PIL',
        'IPython',
        'jupyter',
        'notebook',
        'ipykernel',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

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
    console=False,  # No console window for GUI app
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.icns',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Jarvis Assistant',
)

app = BUNDLE(
    coll,
    name='Jarvis Assistant.app',
    icon='icon.icns',
    bundle_identifier='com.jarvis.assistant',
    version='1.0.0',
    info_plist={
        'CFBundleDisplayName': 'Jarvis Assistant',
        'CFBundleName': 'Jarvis Assistant',
        'CFBundleIdentifier': 'com.jarvis.assistant',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleExecutable': 'Jarvis Assistant',
        'CFBundleIconFile': 'icon.icns',
        'CFBundlePackageType': 'APPL',
        'CFBundleSignature': '????',
        'LSMinimumSystemVersion': '12.0',
        'NSHighResolutionCapable': True,
        'NSRequiresAquaSystemAppearance': False,
        'LSApplicationCategoryType': 'public.app-category.productivity',
        'NSHumanReadableCopyright': '© 2026 Jarvis Project. Built for the locally-hosted future.',
        'CFBundleURLTypes': [],
        'CFBundleDocumentTypes': [],
        'NSMicrophoneUsageDescription': 'Jarvis Assistant needs microphone access to listen to your voice commands.',
        'NSSpeechRecognitionUsageDescription': 'Jarvis Assistant uses speech recognition to understand your voice commands.',
        'NSAppTransportSecurity': {
            'NSAllowsArbitraryLoads': True,
        },
        # Fix Qt library loading issues and enable Rosetta on Apple Silicon
        'LSPrefersPPC': False,
        'LSRequiresNativeExecution': False,
    },
)