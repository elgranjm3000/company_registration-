@echo off
title Crear Ejecutable Auto - Sync API System

cd /d "%~dp0"

echo ========================================
echo   CREAR EJECUTABLE .EXE (AUTOMATICO)
echo   Sync API System
echo ========================================
echo.

REM Verificar dependencias
python -c "import PyInstaller" >nul 2>&1
if %errorlevel% neq 0 (
    echo Instalando PyInstaller...
    pip install pyinstaller
)

REM Verificar si existe el spec, si no, crearlo
if not exist sync_system_api.spec (
    echo.
    echo Creando archivo sync_system_api.spec...
    python -c "import os; open('sync_system_api.spec', 'w', encoding='utf-8').write('# -*- mode: python ; coding: utf-8 -*-\n# Spec file para compilar sync_system_api.py con PyInstaller\n\ndatas_list = [\n    ('api_client', 'api_client'),\n    ('sync', 'sync'),\n    ('config_encryption.py', '.'),\n]\n\nif os.path.exists('icon.ico'):\n    datas_list.append(('icon.ico', '.'))\n\na = Analysis(\n    ['sync_system_api.py'],\n    pathex=[],\n    binaries=[],\n    datas=datas_list,\n    hiddenimports=[\n        'api_client', 'api_client.base', 'api_client.categories', 'api_client.company',\n        'api_client.customers', 'api_client.products', 'api_client.quotes', 'api_client.sellers',\n        'sync', 'sync.base', 'sync.categories_sync', 'sync.customers_sync',\n        'sync.products_sync', 'sync.quotes_sync', 'sync.sellers_sync',\n        'config_encryption',\n        'psycopg2', 'psycopg2.extensions', 'psycopg2.extras', 'psycopg2.pool',\n        'pystray', 'pystray._appindicator', 'pystray._darwin', 'pystray._util', 'pystray._win32',\n        'PIL', 'PIL.Image', 'PIL.ImageDraw', 'PIL.ImageFont',\n        'requests', 'requests.adapters', 'requests.auth', 'requests.models', 'requests.sessions',\n        'urllib3', 'urllib3.poolmanager', 'urllib3.response', 'urllib3.util',\n        'cryptography', 'cryptography.fernet', 'cryptography.hazmat',\n        'cryptography.hazmat.primitives', 'cryptography.hazmat.backends',\n        'tkinter', 'tkinter.ttk', 'tkinter.scrolledtext', 'tkinter.messagebox', 'tkinter.filedialog',\n        'threading', 'queue', 'json', 'datetime', 'os', 'sys', 'time', 'logging', 'hashlib', 'base64', 'winreg',\n    ],\n    hookspath=[], hooksconfig={}, runtime_hooks=[],\n    excludes=['test', 'unittest', 'pytest', 'matplotlib', 'numpy', 'pandas'],\n    win_no_prefer_redirects=False, win_private_assemblies=False, noarchive=False,\n)\n\npyz = PYZ(a.pure, a.zipped_data)\n\nexe = EXE(\n    pyz, a.scripts, a.binaries, a.zipfiles, a.datas, [],\n    name='SyncAPISystem', debug=False, bootloader_ignore_signals=False,\n    strip=False, upx=True, upx_exclude=[], runtime_tmpdir=None,\n    console=True, disable_windowed_traceback=False, target_arch=None,\n    codesign_identity=None, entitlements_file=None,\n    icon='icon.ico' if os.path.exists('icon.ico') else None,\n    version='version_info.txt' if os.path.exists('version_info.txt') else None,\n)\n')"
    echo Espec file creado.
)

echo.
echo Creando ejecutable...
echo.

pyinstaller --clean sync_system_api.spec

if %errorlevel% neq 0 (
    echo.
    echo ERROR: La compilacion fallo
    pause
    exit /b 1
)

echo.
echo ========================================
echo   ¡EJECUTABLE CREADO!
echo ========================================
echo.
echo Ubicacion: dist\SyncAPISystem\
echo.
pause
