"""
Script para crear ejecutable .exe del sistema de sincronización
VERSION DEBUG - CON CONSOLA VISIBLE
"""

import PyInstaller.__main__
import os
import sys

def build_exe_debug():
    """Construye el ejecutable .exe CON CONSOLA para debug"""

    print("=" * 70)
    print("  CREANDO EJECUTABLE .EXE - SYNC SYSTEM (DEBUG CON CONSOLA)")
    print("=" * 70)
    print()

    # Archivo principal
    script_main = "sync_system.py"

    # Opciones de PyInstaller
    pyinstaller_opts = [
        # Archivo principal
        script_main,

        # Nombre del ejecutable
        '--name=SyncSystem_DEBUG',

        # Modo una sola carpeta
        '--onedir',

        # CONSOLA VISIBLE (para debug)
        '--console',

        # Agregar todos los datos necesarios
        '--add-data=smart_sync_complete.py;.',
        '--add-data=smart_sellers_sync_module.py;.',
        '--add-data=config_encryption.py;.',
        '--add-data=mysql_error_logger.py;.',

        # Limpiar archivos temporales
        '--clean',

        # Confirmación automática
        '--noconfirm',

        # Mostrar progreso
        '--log-level=INFO',

        # Hidden imports
        '--hidden-import=pymysql',
        '--hidden-import=pymysql.connections',
        '--hidden-import=pymysql.cursors',
        '--hidden-import=psycopg2',
        '--hidden-import=psycopg2.extensions',
        '--hidden-import=psycopg2.pool',
        '--hidden-import=pystray',
        '--hidden-import=PIL',
        '--hidden-import=PIL.Image',
        '--hidden-import=win10toast',
        '--hidden-import=win10toast.toast',
        '--hidden-import=pywin32',
        '--hidden-import=win32gui',
        '--hidden-import=win32con',
        '--hidden-import=win32api',
        '--hidden-import=tkinter',
        '--hidden-import=tkinter.scrolledtext',
        '--hidden-import=bcrypt',
        '--hidden-import=hashlib',
        '--hidden-import=config_encryption',
        '--hidden-import=cryptography',
        '--hidden-import=cryptography.fernet',
        '--hidden-import=cryptography.hazmat',
        '--hidden-import=cryptography.hazmat.primitives',
        '--hidden-import=cryptography.hazmat.backends',
        '--hidden-import=mysql_error_logger',
        # Para obtener tipo de cambio VES/USD
        '--hidden-import=requests',
        '--hidden-import=urllib3',

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

    print("Iniciando compilación con CONSOLA...")
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
    print("  dist/SyncSystem_DEBUG/sync_system_debug.exe")
    print()
    print("Para ejecutar en modo config y ver errores:")
    print("  dist\\SyncSystem_DEBUG\\sync_system_debug.exe --mode config")
    print()
    print("⚠️ MIRA LA CONSOLA cuando des click en Guardar")
    print("   Aparecerá el error que está ocurriendo")
    print()

if __name__ == "__main__":
    try:
        build_exe_debug()
    except Exception as e:
        print(f"ERROR: {e}")
        print()
        print("Asegúrate de tener instalado:")
        print("  pip install pyinstaller")
        sys.exit(1)
