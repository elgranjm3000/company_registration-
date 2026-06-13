# -*- mode: python ; coding: utf-8 -*-
# Spec file para compilar sync_system.py con PyInstaller
# Incluye todas las dependencias para System Tray y Notificaciones Banner

# Clave de encriptación para proteger el código
# Generar nueva clave con: python -c "import secrets; print(secrets.token_hex(16))"
block_cipher = bytes.fromhex('1c99a2c513420a908c50aa6bea5d914a')

a = Analysis(
    ['sync_system.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Agregar aquí cualquier archivo de datos necesario
        ('icon.ico', '.'),  # Icono personalizado si existe
    ],
    hiddenimports=[
        # Módulos principales de la aplicación
        'smart_sync_complete',
        # MySQL
        'mysql.connector',
        'mysql.connector.pooling',
        'mysql.connector.constants',
        'mysql.connector.errors',
        # PostgreSQL
        'psycopg2',
        'psycopg2.extensions',
        'psycopg2.extras',
        'psycopg2.pool',
        # System Tray (pystray)
        'pystray',
        'pystray._appindicator',
        'pystray._darwin',
        'pystray._util',
        'pystray._win32',
        # PIL/Pillow para pystray
        'PIL',
        'PIL.Image',
        'PIL.ImageDraw',
        'PIL.ImageFont',
        # Notificaciones Banner (win10toast)
        'win10toast',
        'win10toast.toast',
        # Windows-specific (pypiwin32, pywin32)
        'pypiwin32',
        'pypiwin32.pywin32',
        'pywin32',
        'pywin32.win32api',
        'pywin32.win32con',
        'pywin32.win32gui',
        'pywin32.win32clipboard',
        'pywin32.win32process',
        'pywin32.win32event',
        'pywin32.win32service',
        'pythoncom',
        'pywintypes',
        # Tkinter
        'tkinter',
        'tkinter.ttk',
        'tkinter.scrolledtext',
        'tkinter.messagebox',
        'tkinter.filedialog',
        # PySide6 (diálogo de autenticación)
        'PySide6',
        'PySide6.QtCore',
        'PySide6.QtWidgets',
        'PySide6.QtGui',
        # Otras dependencias
        'dotenv',
        'requests',
        'threading',
        'queue',
        'json',
        'datetime',
        'os',
        'sys',
        'time',
        'logging',
        'hashlib',
        'base64',
        'cryptography',
        'cryptography.fernet',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['test', 'unittest', 'pytest', 'matplotlib', 'numpy', 'pandas'],
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
    name='SyncSystem',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Mantener consola para ver logs
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico' if os.path.exists('icon.ico') else None,
    version='version_info.txt' if os.path.exists('version_info.txt') else None,
)
