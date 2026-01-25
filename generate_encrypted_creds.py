#!/usr/bin/env python3
"""
UTILIDAD PARA GENERAR CREDENCIALES ENCRIPTADAS
===============================================
Este script genera credenciales encriptadas para MySQL
que se pueden usar en sync_system.py

Uso:
    python generate_encrypted_creds.py

Autor: Sistema de Sincronización
Versión: 1.0
"""

import base64
import hashlib

def generar_key():
    """Genera la key usada en sync_system.py"""
    secreto = "SyncSystem2024-KeyFija-MySQL-Creds".encode()
    return base64.urlsafe_b64encode(hashlib.sha256(secreto).digest())

def encriptar_credencial(texto_plano):
    """Encripta usando base64 (mismo método que sync_system.py)"""
    return base64.b64encode(texto_plano.encode()).decode()

def main():
    print("=" * 60)
    print("GENERADOR DE CREDENCIALES ENCRIPTADAS PARA MYSQL")
    print("=" * 60)
    print()

    # Obtener credenciales del usuario
    print("Ingrese las credenciales de MySQL:")
    host = input("Host [ej: 91.238.160.176]: ").strip() or "91.238.160.176"
    port = input("Puerto [ej: 3306]: ").strip() or "3306"
    database = input("Base de datos [ej: chrystal_movil]: ").strip() or "chrystal_movil"
    user = input("Usuario [ej: chrystal_app]: ").strip() or "chrystal_app"
    password = input("Password: ").strip()

    if not password:
        print("\n❌ Error: El password es obligatorio")
        return

    print()
    print("=" * 60)
    print("CREDENCIALES ENCRIPTADAS (copiar en sync_system.py)")
    print("=" * 60)
    print()

    print(f"'host': desencriptar_credencial(\"{encriptar_credencial(host)}\"),")
    print(f"'port': desencriptar_credencial(\"{encriptar_credencial(port)}\"),")
    print(f"'database': desencriptar_credencial(\"{encriptar_credencial(database)}\"),")
    print(f"'user': desencriptar_credencial(\"{encriptar_credencial(user)}\"),")
    print(f"'password': desencriptar_credencial(\"{encriptar_credencial(password)}\")")
    print()

    # Verificación
    print("=" * 60)
    print("VERIFICACIÓN (desencriptado):")
    print("=" * 60)
    print(f"Host: {host}")
    print(f"Puerto: {port}")
    print(f"Database: {database}")
    print(f"User: {user}")
    print(f"Password: {password}")
    print()

if __name__ == "__main__":
    main()
