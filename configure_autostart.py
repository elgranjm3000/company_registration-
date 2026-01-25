#!/usr/bin/env python3
"""
UTILIDAD PARA CONFIGURAR AUTO-INICIO DEL SINCRONIZADOR
========================================================
Este script permite habilitar o deshabilitar el inicio automático
del sincronizador al encender el equipo.

Uso:
    python configure_autostart.py --enable
    python configure_autostart.py --disable
    python configure_autostart.py --status

Autor: Sistema de Sincronización
Versión: 1.0
"""

import sys
import os
import argparse
import winreg


def get_app_path():
    """Obtiene la ruta de la aplicación"""
    if getattr(sys, 'frozen', False):
        # Si está empaquetado como exe
        return sys.executable
    else:
        # Si es script Python
        script_path = os.path.abspath(__file__)
        script_dir = os.path.dirname(script_path)
        sync_system_path = os.path.join(script_dir, "sync_system.py")
        return f'"{sys.executable}" "{sync_system_path}" --mode tray'


def enable_autostart():
    """Habilita el auto-inicio"""
    try:
        app_path = get_app_path()
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        key_name = "SyncSystemTray"

        # Verificar que el archivo existe
        if os.path.exists(sys.executable):
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, key_name, 0, winreg.REG_SZ, app_path)
            winreg.CloseKey(key)

            print("✅ Auto-inicio HABILITADO correctamente")
            print(f"   Ruta: {app_path}")
            print(f"   Registry: HKCU\\{key_path}\\{key_name}")
            return True
        else:
            print(f"❌ Error: El archivo no existe: {sys.executable}")
            print("   No se puede configurar auto-inicio para un archivo inexistente")
            return False
    except Exception as e:
        print(f"❌ Error habilitando auto-inicio: {e}")
        return False


def disable_autostart():
    """Deshabilita el auto-inicio"""
    try:
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        key_name = "SyncSystemTray"

        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
            winreg.DeleteValue(key, key_name)
            winreg.CloseKey(key)
            print("✅ Auto-inicio DESHABILITADO correctamente")
            return True
        except FileNotFoundError:
            print("ℹ️  El auto-inicio no estaba configurado")
            return True
    except Exception as e:
        print(f"❌ Error deshabilitando auto-inicio: {e}")
        return False


def check_status():
    """Verifica el estado del auto-inicio"""
    try:
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        key_name = "SyncSystemTray"

        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ)
        try:
            value, _ = winreg.QueryValueEx(key, key_name)
            winreg.CloseKey(key)
            print("✅ Estado: Auto-inicio HABILITADO")
            print(f"   Ruta: {value}")
            return True
        except FileNotFoundError:
            winreg.CloseKey(key)
            print("ℹ️  Estado: Auto-inicio DESHABILITADO")
            return False
    except Exception as e:
        print(f"❌ Error verificando estado: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Configurar auto-inicio del sincronizador")
    parser.add_argument("--enable", action="store_true", help="Habilitar auto-inicio")
    parser.add_argument("--disable", action="store_true", help="Deshabilitar auto-inicio")
    parser.add_argument("--status", action="store_true", help="Verificar estado actual")

    args = parser.parse_args()

    if args.enable:
        enable_autostart()
    elif args.disable:
        disable_autostart()
    elif args.status:
        check_status()
    else:
        # Mostrar estado por defecto
        print("=" * 60)
        print("CONFIGURACIÓN DE AUTO-INICIO - SINCRONIZADOR")
        print("=" * 60)
        print()
        check_status()
        print()
        print("Comandos disponibles:")
        print("  python configure_autostart.py --enable   Habilitar auto-inicio")
        print("  python configure_autostart.py --disable  Deshabilitar auto-inicio")
        print("  python configure_autostart.py --status   Verificar estado")
        print()


if __name__ == "__main__":
    main()
