#!/usr/bin/env python3
"""
Test: Ejecutar sync_system.py --mode service --once
"""

import psycopg2
import pymysql
from dotenv import load_dotenv
import os
import subprocess

load_dotenv()

print("=" * 80)
print("🧪 TEST: python3 sync_system.py --mode service --once")
print("=" * 80)
print()

# Conexiones
pg_conn = psycopg2.connect(
    host=os.getenv('DB_HOST'),
    database='nuevaprueba',
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD')
)
pg_cursor = pg_conn.cursor()

mysql_conn = pymysql.connect(
    host='91.238.160.176',
    port=3306,
    database='chrystal_movil',
    user='chrystal_app',
    password='muentes123.',
    charset='utf8mb4'
)
mysql_cursor = mysql_conn.cursor()

# Obtener company_id
mysql_cursor.execute("SELECT id FROM companies WHERE rif = %s AND email = %s LIMIT 1",
                     ('J505261940', 'elgranjm3000@gmail.com'))
result = mysql_cursor.fetchone()
if not result:
    print("❌ No se encontró company_id")
    exit(1)

company_id = result[0]
print(f"✅ Company ID: {company_id}")
print()

# PASO 1: Crear producto de prueba en PostgreSQL y eliminarlo
print("📋 PASO 1: CREAR Y ELIMINAR PRODUCTO DE PRUEBA")
print("-" * 80)

test_code = 'TEST_SERVICE_001'

# Verificar que no exista
pg_cursor.execute("SELECT code FROM products WHERE code = %s", (test_code,))
if pg_cursor.fetchone():
    pg_cursor.execute("DELETE FROM products WHERE code = %s", (test_code,))
    pg_conn.commit()
    print(f"   ℹ️  Eliminado residual de {test_code}")

# Crear producto
pg_cursor.execute("""
    INSERT INTO products (code, description, short_name, department, status, coin)
    VALUES (%s, %s, %s, %s, '01', '01')
""", (test_code, 'Producto Test Service', 'Test Service', '001'))
pg_conn.commit()
print(f"   ✅ Creado en PostgreSQL: {test_code}")

# Esperar a que se guarde en sync_hashes
import time
time.sleep(1)

# Eliminar el producto
pg_cursor.execute("DELETE FROM products WHERE code = %s", (test_code,))
pg_conn.commit()
print(f"   ✅ Eliminado de PostgreSQL: {test_code}")

# Verificar que esté marcado en sync_hashes
pg_cursor.execute("SELECT deleted_at FROM sync_hashes WHERE table_name = %s AND record_key = %s",
                 ('products', test_code))
hash_data = pg_cursor.fetchone()
if hash_data and hash_data[0]:
    print(f"   ✅ sync_hashes: MARCADO (deleted_at={hash_data[0]})")
else:
    print(f"   ❌ sync_hashes: NO MARCADO")

# Crear el mismo producto en MySQL para verificar que se elimine
mysql_cursor.execute("""
    INSERT INTO products (company_id, code, name, description, price, cost, stock, status, category_id, created_at, updated_at)
    VALUES (%s, %s, %s, %s, 100, 50, 10, 'active', 1, NOW(), NOW())
""", (company_id, test_code, 'Test Service', 'Producto para probar service mode'))
mysql_conn.commit()
print(f"   ✅ Creado en MySQL: {test_code}")

print()

# PASO 2: Verificar estado ANTES
print("📋 PASO 2: ESTADO ANTES DE SINCRONIZAR")
print("-" * 80)

mysql_cursor.execute("SELECT id, code, name FROM products WHERE code = %s AND company_id = %s",
                    (test_code, company_id))
producto = mysql_cursor.fetchone()
if producto:
    print(f"   ✅ {test_code} EXISTE en MySQL antes de sincronizar")
else:
    print(f"   ❌ {test_code} NO EXISTE en MySQL")

print()

# PASO 3: Ejecutar sincronizador
print("📋 PASO 3: EJECUTANDO python3 sync_system.py --mode service --once")
print("-" * 80)

try:
    result = subprocess.run(
        ['python3', 'sync_system.py', '--mode', 'service', '--once'],
        capture_output=True,
        text=True,
        timeout=120
    )

    print(result.stdout[:1000])
    if result.stderr:
        print("STDERR:", result.stderr[:500])

    if result.returncode == 0:
        print("   ✅ Sincronizador ejecutado correctamente")
    else:
        print(f"   ⚠️  Exit code: {result.returncode}")

except subprocess.TimeoutExpired:
    print("   ❌ Timeout después de 120 segundos")
except Exception as e:
    print(f"   ❌ Error: {e}")

print()

# PASO 4: Verificar estado DESPUÉS
print("📋 PASO 4: ESTADO DESPUÉS DE SINCRONIZAR")
print("-" * 80)

mysql_cursor.execute("SELECT id, code, name FROM products WHERE code = %s AND company_id = %s",
                    (test_code, company_id))
producto = mysql_cursor.fetchone()
if producto:
    print(f"   ❌ {test_code} AÚN EXISTE en MySQL - NO SE ELIMINÓ")
    print(f"      ID: {producto[0]}, Name: {producto[2]}")
else:
    print(f"   ✅ {test_code} FUE ELIMINADO de MySQL - ¡FUNCIONA!")

print()
print("=" * 80)
print("✅ TEST COMPLETADO")
print("=" * 80)

pg_cursor.close()
pg_conn.close()
mysql_cursor.close()
mysql_conn.close()
