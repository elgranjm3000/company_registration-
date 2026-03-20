# -*- mode: python ; coding: utf-8 -*-
# Spec file para compilar sync_system_api.py CON CONSOLA
# Incluye todas las dependencias para System Tray y API REST

# Construir lista de datas (sin None)
datas_list = [
    # Agregar módulos del sistema
    ('api_client', 'api_client'),
    ('sync', 'sync'),
    ('config_encryption.py', '.'),
]

# Agregar icono solo si existe
if os.path.exists('icon.ico'):
    datas_list.append(('icon.ico', '.'))

a = Analysis(
    ['sync_system_api.py'],
    pathex=[],
    binaries=[],
    datas=datas_list,
    hiddenimports=[
        # Módulos principales de la aplicación
        'api_client',
        'api_client.base',
        'api_client.categories',
        'api_client.company',
        'api_client.customers',
        'api_client.products',
        'api_client.quotes',
        'api_client.sellers',
        'sync',
        'sync.base',
        'sync.categories_sync',
        'sync.customers_sync',
        'sync.products_sync',
        'sync.quotes_sync',
        'sync.sellers_sync',
        'config_encryption',
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
        # Requests (HTTP Client)
        'requests',
        'requests.adapters',
        'requests.auth',
        'requests.models',
        'requests.sessions',
        'urllib3',
        'urllib3.poolmanager',
        'urllib3.response',
        'urllib3.util',
        # Cryptography (encriptación)
        'cryptography',
        'cryptography.fernet',
        'cryptography.hazmat',
        'cryptography.hazmat.primitives',
        'cryptography.hazmat.backends',
        # Tkinter
        'tkinter',
        'tkinter.ttk',
        'tkinter.scrolledtext',
        'tkinter.messagebox',
        'tkinter.filedialog',
        # Otras dependencias
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
        'winreg',  # Windows Registry para auto-inicio
        # Notificaciones Windows - IMPORTANTES
        'win10toast',
        'win10toast.toast',
        'pkg_resources',
        'pkg_resources.extern',
        'pkg_resources.extern.packaging',
        'packaging',
        'packaging.version',
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
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['test', 'unittest', 'pytest', 'matplotlib', 'numpy', 'pandas'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='SyncAPISystem',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # CON CONSOLA - Para debug
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico' if os.path.exists('icon.ico') else None,
    version='version_info.txt' if os.path.exists('version_info.txt') else None,
)
