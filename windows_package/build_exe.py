"""
Script para crear ejecutable .exe del sistema de sincronización
Usa PyInstaller con todas las dependencias necesarias
"""

import PyInstaller.__main__
import os
import sys

def build_exe():
    """Construye el ejecutable .exe"""

    print("=" * 70)
    print("  CREANDO EJECUTABLE .EXE - SYNC SYSTEM")
    print("=" * 70)
    print()

    # Archivo principal
    script_main = "sync_system.py"

    # Opciones de PyInstaller
    pyinstaller_opts = [
        # Archivo principal
        script_main,

        # Nombre del ejecutable
        '--name=SyncSystem',

        # Modo una sola carpeta (más fácil de debugguear)
        '--onedir',

        # Ventana (porque usa tkinter)
        '--windowed',

        # Icono (opcional - puedes agregar un .ico después)
        # '--icon=icon.ico',

        # Agregar todos los datos necesarios
        '--add-data=smart_sync_complete.py;.',
        '--add-data=smart_sellers_sync_module.py;.',

        # Ocultar consola (excepto en errores)
        '--noconsole',

        # Limpiar archivos temporales
        '--clean',

        # Confirmación automática
        '--noconfirm',

        # Mostrar progreso
        '--log-level=INFO',

        # ===== IMPORTANTE: Hidden imports para pymysql =====
        # pymysql es 100% Python puro - funciona perfectamente con PyInstaller
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
        '--hidden-import=tkinter',
        '--hidden-import=tkinter.scrolledtext',

        # Incluir paquetes completos
        '--collect-all=psycopg2',
        '--collect-all=pystray',
        '--collect-all=Pillow',
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
    print("  dist/SyncSystem/sync_system.exe")
    print()
    print("Para ejecutar:")
    print("  dist/SyncSystem/sync_system.exe --mode tray")
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
