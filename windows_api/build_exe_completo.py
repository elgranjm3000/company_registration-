"""
Script para crear ejecutable .exe del sistema de sincronización API
Método explícito para asegurar que todos los módulos se incluyan
"""

import PyInstaller.__main__
import os
import sys
import shutil

def limpiar_build():
    """Limpiar archivos de compilación anterior"""
    carpetas = ['build', 'dist']
    for carpeta in carpetas:
        if os.path.exists(carpeta):
            print(f"🗑️  Borrando {carpeta}...")
            shutil.rmtree(carpeta)

    archivos_spec = [f for f in os.listdir('.') if f.endswith('.spec')]
    for archivo in archivos_spec:
        print(f"🗑️  Borrando {archivo}...")
        os.remove(archivo)

def build_exe():
    """Construye el ejecutable .exe"""

    print("=" * 70)
    print("  CREANDO EJECUTABLE .EXE - SYNC API SYSTEM")
    print("=" * 70)
    print()

    # Limpiar compilación anterior
    print("🧹 Limpiando compilación anterior...")
    limpiar_build()
    print()

    # Obtener lista de archivos en api_client
    api_client_files = []
    if os.path.exists('api_client'):
        for f in os.listdir('api_client'):
            if f.endswith('.py'):
                api_client_files.append(f'api_client/{f}')

    # Obtener lista de archivos en sync
    sync_files = []
    if os.path.exists('sync'):
        for f in os.listdir('sync'):
            if f.endswith('.py'):
                sync_files.append(f'sync/{f}')

    print(f"📁 Archivos en api_client/: {len(api_client_files)}")
    print(f"📁 Archivos en sync/: {len(sync_files)}")
    print()

    # Opciones de PyInstaller
    pyinstaller_opts = [
        # Archivo principal
        'sync_system_api.py',

        # Nombre del ejecutable
        '--name=SyncAPISystem',

        # Modo una sola carpeta
        '--onedir',

        # Mantener consola para ver logs
        '--console',

        # Limpiar archivos temporales
        '--clean',

        # Confirmación automática
        '--noconfirm',

        # Mostrar progreso
        '--log-level=INFO',

        # ===== DATOS: Incluir módulos =====
        # api_client
        *[f'--add-data={f};api_client' for f in api_client_files],
        # sync
        *[f'--add-data={f};sync' for f in sync_files],
        # config_encryption
        '--add-data=config_encryption.py;.',
    ]

    # ===== HIDDEN IMPORTS =====
    hidden_imports = [
        # api_client
        '--hidden-import=api_client',
        '--hidden-import=api_client.base',
        '--hidden-import=api_client.categories',
        '--hidden-import=api_client.company',
        '--hidden-import=api_client.customers',
        '--hidden-import=api_client.products',
        '--hidden-import=api_client.quotes',
        '--hidden-import=api_client.sellers',
        # sync
        '--hidden-import=sync',
        '--hidden-import=sync.base',
        '--hidden-import=sync.categories_sync',
        '--hidden-import=sync.customers_sync',
        '--hidden-import=sync.products_sync',
        '--hidden-import=sync.quotes_sync',
        '--hidden-import=sync.sellers_sync',
        # config_encryption
        '--hidden-import=config_encryption',
        # PostgreSQL
        '--hidden-import=psycopg2',
        '--hidden-import=psycopg2.extensions',
        '--hidden-import=psycopg2.extras',
        # Requests
        '--hidden-import=requests',
        '--hidden-import=urllib3',
        # System Tray
        '--hidden-import=pystray',
        '--hidden-import=PIL',
        # Tkinter
        '--hidden-import=tkinter',
        # Cryptography
        '--hidden-import=cryptography',
        '--hidden-import=cryptography.fernet',
        # Winreg
        '--hidden-import=winreg',
    ]

    pyinstaller_opts.extend(hidden_imports)

    # ===== COLLECT ALL =====
    collect_all = [
        '--collect-all=psycopg2',
        '--collect-all=pystray',
        '--collect-all=Pillow',
    ]

    pyinstaller_opts.extend(collect_all)

    print("Opciones de PyInstaller:")
    for opt in pyinstaller_opts[:10]:
        print(f"  {opt}")
    print(f"  ... y {len(pyinstaller_opts) - 10} opciones más")
    print()

    print("Iniciando compilación...")
    print("Esto puede tomar varios minutos...")
    print()

    # Ejecutar PyInstaller
    try:
        PyInstaller.__main__.run(pyinstaller_opts)

        print()
        print("=" * 70)
        print("  ¡COMPILACIÓN COMPLETADA!")
        print("=" * 70)
        print()

        # Verificar que se creó el ejecutable
        exe_path = 'dist/SyncAPISystem/SyncAPISystem.exe'
        if os.path.exists(exe_path):
            print(f"✅ Ejecutable creado: {exe_path}")
            print(f"   Tamaño: {os.path.getsize(exe_path) / (1024*1024):.1f} MB")
            print()

            # Verificar que se incluyeron las carpetas
            internal_path = 'dist/SyncAPISystem/_internal'
            if os.path.exists(internal_path):
                api_client_included = os.path.exists(os.path.join(internal_path, 'api_client'))
                sync_included = os.path.exists(os.path.join(internal_path, 'sync'))

                print(f"📂 api_client incluida: {'✅ SÍ' if api_client_included else '❌ NO'}")
                print(f"📂 sync incluida: {'✅ SÍ' if sync_included else '❌ NO'}")
                print()

            print("Para ejecutar:")
            print("  dist\\SyncAPISystem\\SyncAPISystem.exe --mode help")
            print()
            print("Para entregar al cliente:")
            print("  1. Copiar TODO el contenido de dist\\SyncAPISystem\\")
            print("  2. Incluir los archivos .bat (CONFIGURAR, MANAGER, etc)")
            print("  3. Incluir README.md y otros documentos .md")
            print()
        else:
            print("❌ ERROR: No se creó el ejecutable")
            return 1

    except Exception as e:
        print(f"❌ ERROR: {e}")
        print()
        print("Asegúrate de tener instalado:")
        print("  pip install pyinstaller")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    try:
        exit_code = build_exe()
        sys.exit(exit_code if exit_code else 0)
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrumpido por el usuario")
        sys.exit(0)
