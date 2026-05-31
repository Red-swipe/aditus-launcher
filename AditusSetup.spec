# -*- mode: python ; coding: utf-8 -*-

import os
import site
from PyInstaller.building.datastruct import Tree

_site_packages = site.getusersitepackages()


a = Analysis(
    ['installer\\installer_ui.pyw'],
    pathex=['app'],
    binaries=[
        (os.path.join(_site_packages, '_sounddevice_data', 'portaudio-binaries', 'libportaudio64bit.dll'),
         '_sounddevice_data\\portaudio-binaries'),
        (os.path.join(_site_packages, '_sounddevice_data', 'portaudio-binaries', 'libportaudio64bit-asio.dll'),
         '_sounddevice_data\\portaudio-binaries'),
        (os.path.join(_site_packages, '_cffi_backend.cp312-win_amd64.pyd'), '.'),
    ],
    datas=[(src, os.path.dirname(dest)) for (dest, src, _) in Tree('app', prefix='app')] + [
        ('app\\Aditus.exe', '.'),
        ('assets\\aditus.ico', 'assets'),
    ],
    hiddenimports=[
        'sounddevice',
        'numpy',
        '_sounddevice',
        '_sounddevice_data',
        'cffi',
        'pycparser',
        'version',
    ],
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
    a.binaries,
    a.datas,
    [],
    name='AditusSetup',
    icon='assets\\aditus.ico',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=True,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
