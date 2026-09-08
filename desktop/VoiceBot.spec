# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for building VoiceBot OS as a native desktop executable.
#
# Usage:
#   pyinstaller desktop/VoiceBot.spec
#
# Output:
#   dist/VoiceBotOS/  (Linux/macOS)
#   dist/VoiceBotOS.exe  (Windows)
#
# Build a standalone binary that launches the voicebot web server and
# auto-opens a native app window.

import os

block_cipher = None

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))

a = Analysis(
    [os.path.join(ROOT, "main.py")],
    pathex=[ROOT],
    binaries=[],
    datas=[
        (os.path.join(ROOT, "templates"), "templates"),
        (os.path.join(ROOT, "static"), "static"),
        (os.path.join(ROOT, "config"), "config"),
        (os.path.join(ROOT, "src"), "src"),
        (os.path.join(ROOT, "hand_landmarker.task"), "."),
        (os.path.join(ROOT, "requirements.txt"), "."),
    ],
    hiddenimports=[
        "edge_tts",
        "pynput",
        "pyperclip",
        "pyttsx3",
        "sounddevice",
        "speech_recognition",
        "mediapipe",
        "google.genai",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="VoiceBotOS",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,   # Windowless native app
    disable_windowed_traceback=False,
    icon=os.path.join(ROOT, "static", "icons", "icon-192.png") if os.path.exists(os.path.join(ROOT, "static", "icons", "icon-192.png")) else None,
)
