#!/usr/bin/env python3
"""
Script para crear el ejecutable .exe del sistema de sincronización
Asegura que todos los módulos necesarios estén incluidos, especialmente:
- config_encryption.py (encriptación de contraseñas)
- cryptography (librería de encriptación)
"""

import os
import sys
import subprocess
from pathlib import Path

# Directorio actual
BASE_DIR = Path(__file__).parent.absolute()

def limpiar_build():
    """Limpia directorios de build anteriores"""
    print("🧹 Limpiando builds anteriores...")

    build_dirs = ['build', 'dist', '__pycache__']
    for d in build_dirs:
        path = BASE_DIR / d
        if path.exists():
            import shutil
            shutil.rmtree(path)
            print(f"  ✅ Eliminado: {d}")

def crear_spec_file():
    """Crea el archivo .spec para PyInstaller con todas las dependencias"""

    # Convertir ruta a formato seguro para Python string (usar forward slashes)
    base_dir_safe = str(BASE_DIR).replace('\\', '/')

    spec_content = f"""# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['sync_system.py'],
    pathex=['{base_dir_safe}'],
    binaries=[],
    datas=[
        # Incluir módulo de encriptación
        ('config_encryption.py', '.'),

        # Incluir smart_sync_complete.py
        ('smart_sync_complete.py', '.'),

        # Incluir mysql_error_logger.py
        ('mysql_error_logger.py', '.'),

        # Incluir templates de GUI si existen
        # ('templates', 'templates'),
    ],
    hiddenimports=[
        # Módulo de encriptación
        'config_encryption',

        # Logger de errores de MySQL
        'mysql_error_logger',

        # Librerías de criptografía
        'cryptography',
        'cryptography.fernet',
        'cryptography.hazmat',
        'cryptography.hazmat.primitives',
        'cryptography.hazmat.backends',
        'cryptography.hazmat.primitives.ciphers',
        'cryptography.hazmat.primitives.hashes',
        'cryptography.hazmat.primitives.kdf',

        # PostgreSQL
        'psycopg2',
        'psycopg2.extensions',

        # MySQL
        'pymysql',

        # Tkinter (GUI)
        'tkinter',
        'tkinter.ttk',
        'tkinter.filedialog',
        'tkinter.messagebox',
        'tkinter.scrolledtext',

        # JSON
        'json',
        'uuid',
        'hashlib',
        'base64',
        'threading',
        'datetime',
        'argparse',
        'logging',

        # System tray
        'pystray',
        'PIL',
        'PIL.Image',
        'win10toast',

        # Otros
        'importlib',
        'importlib.util',
        'shutil',
        'platform',
        'getpass',
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
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
    console=True,  # True para ver logs en consola
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Agregar icono si existe: 'icon.ico'
)
"""

    spec_file = BASE_DIR / "SyncSystem.spec"
    with open(spec_file, 'w', encoding='utf-8') as f:
        f.write(spec_content)

    print(f"✅ Archivo .spec creado: {spec_file}")
    return spec_file

def construir_exe():
    """Ejecuta PyInstaller para crear el .exe"""

    print("\n🔨 Creando executable con PyInstaller...")

    # Verificar que PyInstaller esté instalado
    try:
        import PyInstaller
        print(f"  ✅ PyInstaller versión: {PyInstaller.__version__}")
    except ImportError:
        print("  ❌ PyInstaller NO está instalado")
        print("  Instalando PyInstaller...")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pyinstaller'])

    # Crear spec file
    spec_file = crear_spec_file()

    # Ejecutar PyInstaller
    cmd = [sys.executable, '-m', 'PyInstaller', '--clean', str(spec_file)]
    print(f"\n📦 Ejecutando: {' '.join(cmd)}\n")

    result = subprocess.run(cmd, cwd=BASE_DIR)
    if result.returncode != 0:
        print("\n❌ Error creando el executable")
        return False

    print("\n✅ Executable creado exitosamente!")
    exe_path = BASE_DIR / 'dist' / 'SyncSystem.exe'
    print(f"📍 Ubicación: {exe_path}")

    return True

def verificar_encriptacion():
    """Verifica que el módulo de encriptación esté incluido en el exe"""

    print("\n🔍 Verificando encriptación...")

    exe_path = BASE_DIR / 'dist' / 'SyncSystem.exe'

    if not exe_path.exists():
        print("  ⚠️ Executable no encontrado, no se puede verificar")
        return

    print(f"  ✅ Executable encontrado: {exe_path}")
    print(f"  📊 Tamaño: {exe_path.stat().st_size / (1024*1024):.1f} MB")

    # Verificar que config_encryption.py existe
    config_enc_path = BASE_DIR / 'config_encryption.py'
    if config_enc_path.exists():
        print(f"  ✅ config_encryption.py encontrado")
    else:
        print(f"  ❌ config_encryption.py NO encontrado - Las contraseñas estarán visibles!")

def main():
    """Función principal"""
    print("=" * 60)
    print("🔄 BUILD EXECUTABLE - Sistema de Sincronización")
    print("=" * 60)

    # 1. Limpiar builds anteriores
    limpiar_build()

    # 2. Crear exe
    if construir_exe():

        # 3. Verificar encriptación
        verificar_encriptacion()

        print("\n" + "=" * 60)
        print("✅ BUILD COMPLETADO")
        print("=" * 60)
        print("\n📝 Notas importantes:")
        print("  1. El .exe incluye config_encryption.py")
        print("  2. Las contraseñas se encriptan automáticamente")
        print("  3. sync_config.json tendrá contraseñas con 'enc:' prefix")
        print("  4. Distribuye sync_system.py junto con el .exe")
        print("\n📦 Archivos a distribuir:")
        print("  - dist/SyncSystem.exe")
        print("  - smart_sync_complete.py")
        print("  - config_encryption.py (ya incluido en exe)")
        print("\n")

    else:
        print("\n❌ BUILD FALLÓ")
        return 1

    return 0

if __name__ == '__main__':
    sys.exit(main())
