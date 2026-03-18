"""
Script para crear ejecutable .exe del sistema de sincronización API
Usa PyInstaller con todas las dependencias necesarias
"""

import PyInstaller.__main__
import os
import sys

def build_exe():
    """Construye el ejecutable .exe"""

    print("=" * 70)
    print("  CREANDO EJECUTABLE .EXE - SYNC API SYSTEM")
    print("=" * 70)
    print()

    # Archivo principal
    script_main = "sync_system_api.py"

    # Opciones de PyInstaller
    pyinstaller_opts = [
        # Archivo principal
        script_main,

        # Nombre del ejecutable
        '--name=SyncAPISystem',

        # Modo una sola carpeta (más fácil de debugguear)
        '--onedir',

        # Ventana (porque usa tkinter) - SIN CONSOLA NEGRA
        '--windowed',

        # Ocultar consola completamente (no asusta al usuario)
        '--noconsole',

        # Icono (opcional - puedes agregar un .ico después)
        # '--icon=icon.ico',

        # Agregar todos los datos necesarios
        '--add-data=config_encryption.py;.',
        '--add-data=api_client;base',
        '--add-data=api_client\\base.py;base',
        '--add-data=api_client\\categories.py;base',
        '--add-data=api_client\\company.py;base',
        '--add-data=api_client\\customers.py;base',
        '--add-data=api_client\\products.py;base',
        '--add-data=api_client\\quotes.py;base',
        '--add-data=api_client\\sellers.py;base',
        '--add-data=api_client\\__init__.py;base',
        '--add-data=sync;base',
        '--add-data=sync\\base.py;base',
        '--add-data=sync\\categories_sync.py;base',
        '--add-data=sync\\customers_sync.py;base',
        '--add-data=sync\\products_sync.py;base',
        '--add-data=sync\\quotes_sync.py;base',
        '--add-data=sync\\sellers_sync.py;base',
        '--add-data=sync\\__init__.py;base',

        # Limpiar archivos temporales
        '--clean',

        # Confirmación automática
        '--noconfirm',

        # Mostrar progreso
        '--log-level=INFO',

        # ===== IMPORTANTE: Hidden imports =====
        # PostgreSQL
        '--hidden-import=psycopg2',
        '--hidden-import=psycopg2.extensions',
        '--hidden-import=psycopg2.pool',
        # System Tray
        '--hidden-import=pystray',
        '--hidden-import=PIL',
        '--hidden-import=PIL.Image',
        '--hidden-import=PIL.ImageDraw',
        # Tkinter
        '--hidden-import=tkinter',
        '--hidden-import=tkinter.scrolledtext',
        # API Client
        '--hidden-import=api_client',
        '--hidden-import=api_client.base',
        '--hidden-import=api_client.categories',
        '--hidden-import=api_client.company',
        '--hidden-import=api_client.customers',
        '--hidden-import=api_client.products',
        '--hidden-import=api_client.quotes',
        '--hidden-import=api_client.sellers',
        # Sync
        '--hidden-import=sync',
        '--hidden-import=sync.base',
        '--hidden-import=sync.categories_sync',
        '--hidden-import=sync.customers_sync',
        '--hidden-import=sync.products_sync',
        '--hidden-import=sync.quotes_sync',
        '--hidden-import=sync.sellers_sync',
        # Config encryption
        '--hidden-import=config_encryption',
        # Cryptography
        '--hidden-import=cryptography',
        '--hidden-import=cryptography.fernet',
        '--hidden-import=cryptography.hazmat',
        '--hidden-import=cryptography.hazmat.primitives',
        '--hidden-import=cryptography.hazmat.backends',
        # Requests
        '--hidden-import=requests',
        '--hidden-import=urllib3',
        # Winreg para auto-inicio
        '--hidden-import=winreg',
        # Notificaciones Windows
        '--hidden-import=win10toast',
        '--hidden-import=win10toast.toast',
        '--hidden-import=pywin32',
        '--hidden-import=win32gui',
        '--hidden-import=win32con',
        '--hidden-import=win32api',

        # Incluir paquetes completos
        '--collect-all=psycopg2',
        '--collect-all=pystray',
        '--collect-all=Pillow',
        '--collect-all=win10toast',
        '--collect-all=pywin32',
    ]

    print("Opciones de PyInstaller:")
    for opt in pyinstaller_opts:
        print(f"  {opt}")
    print()

    print("Iniciando compilación...")
    print("Esto puede tomar varios minutos...")
    print()

    # Ejecutar PyInstaller
    PyInstaller.__main__.run(pyinstaller_opts)

    print()
    print("=" * 70)
    print("  ¡COMPILACIÓN COMPLETADA!")
    print("=" * 70)
    print()
    print("El ejecutable se encuentra en:")
    print("  dist/SyncAPISystem/sync_system_api.exe")
    print()
    print("Para ejecutar:")
    print("  dist/SyncAPISystem/sync_system_api.exe --mode tray")
    print()
    print("Para entregar al cliente:")
    print("  1. Copiar TODO el contenido de dist/SyncAPISystem/")
    print("  2. Incluir los archivos .bat (CONFIGURAR.bat, MANAGER.bat, etc)")
    print("  3. Incluir README.md e INICIO_RAPIDO.md")
    print()

if __name__ == "__main__":
    try:
        build_exe()
    except Exception as e:
        print(f"ERROR: {e}")
        print()
        print("Asegúrate de tener instalado:")
        print("  pip install pyinstaller")
        sys.exit(1)
