# -*- mode: python ; coding: utf-8 -*-
# Spec file para compilar sync_system_api.py CON CONSOLA
# Incluye todas las dependencias para System Tray y API REST

from PyInstaller.utils.hooks import collect_all

# Collect all plyer data (notificaciones)
plyer_datas, plyer_binaries, plyer_hiddenimports = collect_all('plyer')

# Collect all win10toast data (incluye metadatos .egg-info/.dist-info)
win10toast_datas, win10toast_binaries, win10toast_hiddenimports = collect_all('win10toast')

# Collect all pywin32 data
pywin32_datas, pywin32_binaries, pywin32_hiddenimports = collect_all('pywin32')

# Collect all requests data (HTTP client)
requests_datas, requests_binaries, requests_hiddenimports = collect_all('requests')

# Collect all urllib3 data (dependencia de requests)
urllib3_datas, urllib3_binaries, urllib3_hiddenimports = collect_all('urllib3')

# Collect all certifi data (certificados SSL para requests)
certifi_datas, certifi_binaries, certifi_hiddenimports = collect_all('certifi')

# Collect all psycopg2 data (PostgreSQL)
# Nota: Usar 'psycopg2' no 'psycopg2-binary' porque collect_all busca el módulo importado
psycopg2_datas, psycopg2_binaries, psycopg2_hiddenimports = collect_all('psycopg2')

# Collect all cryptography data (encriptación)
cryptography_datas, cryptography_binaries, cryptography_hiddenimports = collect_all('cryptography')

# Collect all cffi data (dependencia de cryptography)
cffi_datas, cffi_binaries, cffi_hiddenimports = collect_all('cffi')

# Construir lista de datas
datas_list = [
    # Agregar módulos del sistema
    ('api_client', 'api_client'),
    ('sync', 'sync'),
    ('config_encryption.py', '.'),
] + plyer_datas + win10toast_datas + pywin32_datas + requests_datas + urllib3_datas + certifi_datas + psycopg2_datas + cryptography_datas + cffi_datas

# Agregar icono solo si existe
if os.path.exists('icon.ico'):
    datas_list.append(('icon.ico', '.'))

a = Analysis(
    ['sync_system_api.py'],
    pathex=[],
    binaries=plyer_binaries + win10toast_binaries + pywin32_binaries + requests_binaries + urllib3_binaries + certifi_binaries + psycopg2_binaries + cryptography_binaries + cffi_binaries,
    datas=datas_list,
    hiddenimports=[
        # Hidden imports de collect_all
        *plyer_hiddenimports,
        *win10toast_hiddenimports,
        *pywin32_hiddenimports,
        *requests_hiddenimports,
        *urllib3_hiddenimports,
        *certifi_hiddenimports,
        *psycopg2_hiddenimports,
        *cryptography_hiddenimports,
        *cffi_hiddenimports,
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
        # PostgreSQL (psycopg2)
        'psycopg2',
        'psycopg2.extensions',
        'psycopg2.extras',
        'psycopg2.pool',
        'psycopg2._psycopg',
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
        # Cryptography (encriptación) - hiddenimports manuales adicionales
        'cryptography',
        'cryptography.fernet',
        'cryptography.hazmat',
        'cryptography.hazmat.primitives',
        'cryptography.hazmat.primitives.ciphers',
        'cryptography.hazmat.primitives.hashes',
        'cryptography.hazmat.primitives.kdf',
        'cryptography.hazmat.backends',
        'cryptography.hazmat.backends.default_backend',
        'cffi',  # Dependencia de cryptography
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
        # Notificaciones Windows (plyer - más estable)
        'plyer',
        'plyer.platform',
        'plyer.platforms',
        'plyer.platforms.win.notification',
        'plyer.platforms.win.libs',
        'plyer.platforms.win.libs.win10toast',
        # Notificaciones Windows (win10toast - backup, mantener compatibilidad)
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
    ] + plyer_hiddenimports + win10toast_hiddenimports + pywin32_hiddenimports,
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
