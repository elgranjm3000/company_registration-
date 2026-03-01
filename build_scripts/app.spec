# -*- mode: python ; coding: utf-8 -*-

# Clave de encriptación para proteger el código
# Generar nueva clave con: python -c "import secrets; print(secrets.token_hex(16))"
block_cipher = bytes.fromhex('1c99a2c513420a908c50aa6bea5d914a')

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('assets/icon.ico', 'assets'),  # Incluir icono
    ],
    hiddenimports=[
        # Módulos principales de la aplicación
        'smart_sync_complete',
        # MySQL
        'mysql.connector',
        'mysql.connector.pooling',
        'mysql.connector.constants',
        # PostgreSQL
        'psycopg2',
        'psycopg2.extensions',
        'psycopg2.extras',
        # System Tray (pystray)
        'pystray',
        'pystray._appindicator',
        'pystray._darwin',
        'pystray._util',
        'PIL',
        'PIL.Image',
        # Notificaciones Banner (win10toast)
        'win10toast',
        'win10toast.toast',
        # Windows-specific
        'pypiwin32',
        'pywin32',
        'win32api',
        'win32con',
        'win32gui',
        'win32clipboard',
        'pythoncom',
        'pywintypes',
        # Otras dependencias
        'dotenv',
        'requests',
        'tkinter',
        'tkinter.ttk',
        'tkinter.scrolledtext',
        'threading',
        'queue',
        'json',
        'datetime',
        'os',
        'sys',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['test', 'unittest', 'pytest'],
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
    name='CompanyRegistration',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Sin ventana de consola
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico'  # Icono del ejecutable
)
