# -*- mode: python ; coding: utf-8 -*-
"""
Aditus.spec — builds app\Aditus.exe from app\main.pyw
Run: python -m PyInstaller Aditus.spec --distpath app --workpath build\Aditus_app --clean
"""

import os
import site

_site_packages = site.getusersitepackages()

block_cipher = None

a = Analysis(
    ['app\\main.pyw'],
    pathex=['app'],
    binaries=[
        (os.path.join(_site_packages, '_sounddevice_data', 'portaudio-binaries', 'libportaudio64bit.dll'),
         '_sounddevice_data\\portaudio-binaries'),
        (os.path.join(_site_packages, '_sounddevice_data', 'portaudio-binaries', 'libportaudio64bit-asio.dll'),
         '_sounddevice_data\\portaudio-binaries'),
        (os.path.join(_site_packages, '_cffi_backend.cp312-win_amd64.pyd'), '.'),
    ],
    datas=[
        ('app\\config\\aditus_config.json', 'config'),
        ('assets\\aditus.ico', 'assets'),
    ],
    hiddenimports=[
        'sounddevice',
        'numpy',
        'customtkinter',
        'keyboard',
        '_sounddevice',
        '_sounddevice_data',
        'cffi',
        'pycparser',
        'pystray',
        'PIL',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['_bootlocale'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Aditus',
    icon='assets\\aditus.ico',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    uac_admin=False,
    disable_windowed_traceback=True,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
