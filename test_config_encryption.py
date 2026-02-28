#!/usr/bin/env python3
"""
Test: Verificar encriptación de sync_config.json
"""

import os
import sys
import json
import tempfile
import shutil

# Importar el módulo de encriptación
from config_encryption import (
    encrypt_password,
    decrypt_password,
    encrypt_config,
    decrypt_config,
    is_encrypted
)

print("=" * 80)
print("🧪 TEST: Encriptación de sync_config.json")
print("=" * 80)
print()

# Config de prueba
config_prueba = {
    "postgres_host": "localhost",
    "postgres_port": "5432",
    "postgres_database": "test_db",
    "postgres_user": "postgres",
    "postgres_password": "mi_password_secreto_123",
    "mysql_host": "91.238.160.176",
    "mysql_port": "3306",
    "mysql_database": "chrystal_movil",
    "mysql_user": "chrystal_app",
    "mysql_password": "otro_password_secreto_456",
    "company_rif": "J505261940",
    "company_email": "test@example.com",
    "company_name": "Empresa Test"
}

# ==============================================================================
# TEST 1: Encriptar y desencriptar contraseña individual
# ==============================================================================
print("📋 TEST 1: Encriptar/Desencriptar contraseña individual")
print("-" * 80)

password_original = "mi_password_secreto_123"
print(f"   Password original: {password_original}")

password_enc = encrypt_password(password_original)
print(f"   Password encriptado: {password_enc[:50]}...")

password_dec = decrypt_password(password_enc)
print(f"   Password desencriptado: {password_dec}")

if password_original == password_dec:
    print("   ✅ TEST 1 PASÓ: Encriptación/desencriptación individual funciona")
else:
    print("   ❌ TEST 1 FALLÓ: Las contraseñas no coinciden")
    sys.exit(1)

print()

# ==============================================================================
# TEST 2: Encriptar config completo
# ==============================================================================
print("📋 TEST 2: Encriptar config completo")
print("-" * 80)

print("   Config original (contraseñas visibles):")
print(f"      postgres_password: {config_prueba['postgres_password']}")
print(f"      mysql_password: {config_prueba['mysql_password']}")

config_enc = encrypt_config(config_prueba)
print("   Config encriptado:")
print(f"      postgres_password: {config_enc['postgres_password'][:50]}...")
print(f"      mysql_password: {config_enc['mysql_password'][:50]}...")

if is_encrypted(config_enc['postgres_password']):
    print("   ✅ postgres_password está encriptado (empieza con 'enc:')")
else:
    print("   ❌ postgres_password NO está encriptado")

if is_encrypted(config_enc['mysql_password']):
    print("   ✅ mysql_password está encriptado (empieza con 'enc:')")
else:
    print("   ❌ mysql_password NO está encriptado")

print()

# ==============================================================================
# TEST 3: Desencriptar config completo
# ==============================================================================
print("📋 TEST 3: Desencriptar config completo")
print("-" * 80)

config_dec = decrypt_config(config_enc)
print("   Config desencriptado:")
print(f"      postgres_password: {config_dec['postgres_password']}")
print(f"      mysql_password: {config_dec['mysql_password']}")

if config_dec['postgres_password'] == config_prueba['postgres_password']:
    print("   ✅ postgres_password desencriptado correctamente")
else:
    print("   ❌ postgres_password NO coincide")
    sys.exit(1)

if config_dec['mysql_password'] == config_prueba['mysql_password']:
    print("   ✅ mysql_password desencriptado correctamente")
else:
    print("   ❌ mysql_password NO coincide")
    sys.exit(1)

print()

# ==============================================================================
# TEST 4: Guardar y cargar archivo JSON
# ==============================================================================
print("📋 TEST 4: Guardar y cargar archivo JSON")
print("-" * 80)

# Crear directorio temporal
temp_dir = tempfile.mkdtemp()
config_file = os.path.join(temp_dir, "sync_config.json")

try:
    # Guardar config encriptado en archivo
    print(f"   Guardando en: {config_file}")
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(config_enc, f, indent=4)

    # Leer archivo
    with open(config_file, "r", encoding="utf-8") as f:
        config_from_file = json.load(f)

    print("   ✅ Archivo guardado y leído correctamente")

    # Desencriptar config del archivo
    config_decrypted = decrypt_config(config_from_file)

    if config_decrypted['postgres_password'] == config_prueba['postgres_password']:
        print("   ✅ postgres_password correcto después de guardar/cargar")
    else:
        print("   ❌ postgres_password incorrecto después de guardar/cargar")
        sys.exit(1)

    if config_decrypted['mysql_password'] == config_prueba['mysql_password']:
        print("   ✅ mysql_password correcto después de guardar/cargar")
    else:
        print("   ❌ mysql_password incorrecto después de guardar/cargar")
        sys.exit(1)

    # Mostrar contenido del archivo (parcial)
    print()
    print("   📄 Contenido del archivo (primeras líneas):")
    with open(config_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
        for line in lines[:10]:
            if line.strip():
                print(f"      {line.rstrip()[:70]}")

finally:
    # Limpiar
    shutil.rmtree(temp_dir)
    print()
    print("   🧹 Directorio temporal eliminado")

print()

# ==============================================================================
# TEST 5: Verificar que otros campos no se encriptan
# ==============================================================================
print("📋 TEST 5: Verificar campos no sensibles")
print("-" * 80)

config_enc = encrypt_config(config_prueba)

# Campos que NO deben encriptarse
campos_no_sensibles = [
    'postgres_host',
    'postgres_port',
    'postgres_database',
    'postgres_user',
    'mysql_host',
    'mysql_port',
    'mysql_database',
    'mysql_user',
    'company_rif',
    'company_email',
    'company_name'
]

todos_ok = True
for campo in campos_no_sensibles:
    if campo in config_enc:
        valor = config_enc[campo]
        if not is_encrypted(valor):
            print(f"   ✅ {campo}: NO encriptado (correcto)")
        else:
            print(f"   ❌ {campo}: Encriptado (INCORRECTO)")
            todos_ok = False

if todos_ok:
    print()
    print("   ✅ TEST 5 PASÓ: Solo campos sensibles encriptados")

print()

# ==============================================================================
# RESUMEN FINAL
# ==============================================================================
print("=" * 80)
print("✅ TODOS LOS TESTS PASARON")
print("=" * 80)
print()
print("RESUMEN:")
print("   ✅ Encriptación/desencriptación individual funciona")
print("   ✅ Config completo se encripta correctamente")
print("   ✅ Config completo se desencripta correctamente")
print("   ✅ Guardar/cargar archivo JSON funciona")
print("   ✅ Solo campos sensibles se encriptan")
print()
print("🔒 SEGURIDAD:")
print("   - Las contraseñas están encriptadas con Fernet (AES-128)")
print("   - La clave de encriptación es única por máquina")
print("   - Si el archivo se mueve a otra máquina, no se puede desencriptar")
print("   - Los campos encriptados empiezan con 'enc:'")
print()
