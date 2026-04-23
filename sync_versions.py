#!/usr/bin/env python3
"""
Script para sincronizar las versiones de quotes_sync.py
 entre root y windows_api
"""

import shutil
import os
from datetime import datetime

BASE_DIR = "/home/muentes/devs/sincronizadorchrystal"
ROOT_QUOTE = f"{BASE_DIR}/sync/quotes_sync.py"
WIN_API_QUOTE = f"{BASE_DIR}/windows_api/sync/quotes_sync.py"

def sync_to_root():
    """Copiar desde windows_api hacia root"""
    print("🔄 Sincronizando windows_api → root")
    shutil.copy2(WIN_API_QUOTE, ROOT_QUOTE)
    print(f"✅ Copiado: {WIN_API_QUOTE}")
    print(f"   → {ROOT_QUOTE}")

def sync_to_windows_api():
    """Copiar desde root hacia windows_api"""
    print("🔄 Sincronizando root → windows_api")
    shutil.copy2(ROOT_QUOTE, WIN_API_QUOTE)
    print(f"✅ Copiado: {ROOT_QUOTE}")
    print(f"   → {WIN_API_QUOTE}")

def check_status():
    """Verificar estado de sincronización"""
    root_size = os.path.getsize(ROOT_QUOTE)
    win_size = os.path.getsize(WIN_API_QUOTE)
    root_time = os.path.getmtime(ROOT_QUOTE)
    win_time = os.path.getmtime(WIN_API_QUOTE)

    print("📊 ESTADO DE SINCRONIZACIÓN")
    print("=" * 60)
    print(f"Root (sync/quotes_sync.py):")
    print(f"  - Tamaño: {root_size:,} bytes")
    print(f"  - Modificado: {datetime.fromtimestamp(root_time)}")
    print()
    print(f"Windows API (windows_api/sync/quotes_sync.py):")
    print(f"  - Tamaño: {win_size:,} bytes")
    print(f"  - Modificado: {datetime.fromtimestamp(win_time)}")
    print()

    if root_size == win_size and abs(root_time - win_time) < 1:
        print("✅ AMBAS VERSIONES ESTÁN SINCRONIZADAS")
    else:
        print("⚠️ LAS VERSIONES DIFIEREN:")
        if root_size != win_size:
            diff = abs(root_size - win_size)
            print(f"  - Diferencia de tamaño: {diff:,} bytes")
        if abs(root_time - win_time) > 1:
            print(f"  - Diferencia de tiempo: {abs(root_time - win_time):.0f} segundos")

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == "to-root":
            sync_to_root()
        elif sys.argv[1] == "to-win":
            sync_to_windows_api()
        elif sys.argv[1] == "status":
            check_status()
        else:
            print("Uso:")
            print("  python sync_versions.py status    - Ver estado")
            print("  python sync_versions.py to-root   - Win → Root")
            print("  python sync_versions.py to-win    - Root → Win")
    else:
        # Por defecto, mostrar estado
        check_status()
