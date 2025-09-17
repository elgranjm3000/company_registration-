# -*- mode: python ; coding: utf-8 -*-

import sys
import os

block_cipher = None

# Configuración específica para generar .exe desde Linux
a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('assets', 'assets') if os.path.exists('assets') else [],
    ],
    hiddenimports=[
        'mysql.connector',
        'mysql.connector.pooling',
        'mysql.connector.constants',
        'mysql.connector.abstracts',
        'mysql.connector.conversion',
        'mysql.connector.cursor',
        'mysql.connector.errorcode',
        'mysql.connector.errors',
        'tkinter',
        'tkinter.ttk',
        'tkinter.messagebox',
        'tkinter.scrolledtext',
        'tkinter.filedialog',
        'tkinter.font',
        'tkinter.constants',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'test',
        'unittest',
        'doctest',
        'pydoc',
        'xml',
        'email',
        'http',
        'urllib',
        'json',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyd = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyd,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='CompanyRegistration.exe',  # Forzar extensión .exe
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico' if os.path.exists('assets/icon.ico') else None,
)
