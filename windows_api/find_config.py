#!/usr/bin/env python3
"""
Script para encontrar y mostrar la ubicación del archivo de configuración
"""

import os
import sys
from pathlib import Path

def find_config_file():
    """Muestra la ubicación del archivo de configuración"""

    # La misma ruta que usa el sistema
    CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".chrystal_sync_config.json")

    print("="*70)
    print("📁 UBICACIÓN DEL ARCHIVO DE CONFIGURACIÓN")
    print("="*70)

    print(f"\n🔍 Ruta del archivo:")
    print(f"   {CONFIG_FILE}")

    print(f"\n📂 Expandido:")
    print(f"   {os.path.abspath(CONFIG_FILE)}")

    # Ver si existe
    if os.path.exists(CONFIG_FILE):
        print(f"\n✅ El archivo EXISTE")

        # Mostrar tamaño
        size = os.path.getsize(CONFIG_FILE)
        print(f"   - Tamaño: {size:,} bytes ({size/1024:.2f} KB)")

        # Mostrar fecha de modificación
        import time
        mtime = os.path.getmtime(CONFIG_FILE)
        mtime_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(mtime))
        print(f"   - Modificado: {mtime_str}")

        # Ver si está encriptado
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                content = f.read()
                if content.strip().startswith('{'):
                    import json
                    data = json.loads(content)

                    # Verificar si hay campos encriptados
                    encrypted_fields = []
                    for key, value in data.items():
                        if isinstance(value, str) and value.startswith('enc:'):
                            encrypted_fields.append(key)

                    if encrypted_fields:
                        print(f"   - Estado: ✅ ENCRIPTADO ({len(encrypted_fields)} campos)")
                        print(f"   - Campos encriptados: {', '.join(encrypted_fields)}")
                    else:
                        print(f"   - Estado: ⚠️  SIN ENCRIPTAR (todos en texto plano)")

                    # Mostrar campos
                    print(f"\n📋 Campos en el archivo:")
                    for key in data.keys():
                        value = data[key]
                        if isinstance(value, str):
                            if value.startswith('enc:'):
                                display = f"{value[:20]}... (encriptado)"
                            else:
                                display = value[:30] if len(value) > 30 else value
                        else:
                            display = str(value)[:30]
                        print(f"   - {key}: {display}")

        except Exception as e:
            print(f"   ⚠️  Error leyendo el archivo: {e}")

    else:
        print(f"\n❌ El archivo NO EXISTE")
        print(f"   \n💡 Esto significa que:")
        print(f"   1. No has configurado el sistema aún, O")
        print(f"   2. El archivo fue borrado o movido")

        # Mostrar cómo crearlo
        print(f"\n   📝 Para crearlo, ejecuta:")
        print(f"   python sync_system_api.py --mode config")

    # Abrir en explorador
    print(f"\n" + "="*70)
    choice = input("¿Quieres abrir la carpeta en el explorador? (s/n): ").lower()

    if choice == 's':
        import subprocess
        import platform

        folder = os.path.dirname(CONFIG_FILE)

        try:
            if platform.system() == 'Windows':
                subprocess.run(['explorer', folder])
            elif platform.system() == 'Darwin':  # macOS
                subprocess.run(['open', folder])
            else:  # Linux
                subprocess.run(['xdg-open', folder])
            print(f"✅ Explorador abierto en: {folder}")
        except Exception as e:
            print(f"❌ Error abriendo explorador: {e}")
            print(f"   Ruta manual: {folder}")

    print("="*70)

if __name__ == '__main__':
    try:
        find_config_file()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n🏁 Presiona Enter para salir...")
        input()
