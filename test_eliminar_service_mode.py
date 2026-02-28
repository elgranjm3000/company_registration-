#!/usr/bin/env python3
"""
Test: Verificar que sync_system.py --mode service elimina productos de MySQL
"""

import psycopg2
import pymysql
from dotenv import load_dotenv
import os
import time
import subprocess

load_dotenv()

print("=" * 80)
print("🧪 TEST: ELIMINACIÓN DE PRODUCTOS EN MODO SERVICE")
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

# PASO 1: Verificar estado actual del producto code=03
print("📋 PASO 1: VERIFICAR ESTADO ACTUAL DE CODE=03")
print("-" * 80)

# En PostgreSQL
pg_cursor.execute("SELECT code, description FROM products WHERE code = %s", ('03',))
pg_product = pg_cursor.fetchone()
if pg_product:
    print(f"   ❌ PostgreSQL: AÚN EXISTE (code={pg_product[0]}, desc={pg_product[1]})")
else:
    print(f"   ✅ PostgreSQL: NO EXISTE (fue eliminado)")

# En sync_hashes
pg_cursor.execute("SELECT deleted_at FROM sync_hashes WHERE table_name = %s AND record_key = %s",
                 ('products', '03'))
hash_data = pg_cursor.fetchone()
if hash_data and hash_data[0]:
    print(f"   ✅ sync_hashes: MARCADO COMO ELIMINADO (deleted_at={hash_data[0]})")
elif hash_data:
    print(f"   ⚠️  sync_hashes: EXISTE PERO NO MARCADO COMO ELIMINADO")
else:
    print(f"   ❌ sync_hashes: NO EXISTE")

# En MySQL
mysql_cursor.execute("SELECT id, code, name FROM products WHERE code = %s AND company_id = %s",
                    ('03', company_id))
mysql_product = mysql_cursor.fetchone()
if mysql_product:
    print(f"   ❌ MySQL: AÚN EXISTE (id={mysql_product[0]}, code={mysql_product[1]}, name={mysql_product[2]})")
else:
    print(f"   ✅ MySQL: NO EXISTE (fue eliminado)")

print()

# PASO 2: Si el producto no está marcado en sync_hashes, crear producto de prueba
if not hash_data or not hash_data[0]:
    print("📋 PASO 2: CREAR PRODUCTO DE PRUEBA")
    print("-" * 80)

    # Crear producto en PostgreSQL
    pg_cursor.execute("""
        INSERT INTO products (code, description, short_name, department, status, coin)
        VALUES (%s, %s, %s, %s, '01', '01')
    """, ('TEST_ELIMINAR_001', 'Producto Test Eliminar', 'Test Eliminar', '001'))
    pg_conn.commit()
    print(f"   ✅ Creado en PostgreSQL: TEST_ELIMINAR_001")

    # Esperar a que el trigger lo marque en sync_hashes
    time.sleep(2)

    # Eliminar el producto
    pg_cursor.execute("DELETE FROM products WHERE code = %s", ('TEST_ELIMINAR_001',))
    pg_conn.commit()
    print(f"   ✅ Eliminado de PostgreSQL: TEST_ELIMINAR_001")

    # Verificar que esté marcado en sync_hashes
    pg_cursor.execute("SELECT deleted_at FROM sync_hashes WHERE table_name = %s AND record_key = %s",
                     ('products', 'TEST_ELIMINAR_001'))
    hash_data = pg_cursor.fetchone()
    if hash_data and hash_data[0]:
        print(f"   ✅ sync_hashes: MARCADO (deleted_at={hash_data[0]})")
    else:
        print(f"   ❌ sync_hashes: NO MARCADO - el trigger no funcionó")

    # Crear el mismo producto en MySQL para verificar que se elimine
    mysql_cursor.execute("""
        INSERT INTO products (company_id, code, name, description, price, cost, stock, status, category_id, created_at, updated_at)
        VALUES (%s, %s, %s, %s, 100, 50, 10, 'active', 1, NOW(), NOW())
    """, (company_id, 'TEST_ELIMINAR_001', 'Test Eliminar', 'Producto para probar eliminación'))
    mysql_conn.commit()
    print(f"   ✅ Creado en MySQL: TEST_ELIMINAR_001")

    print()

# PASO 3: Ejecutar sincronizador
print("📋 PASO 3: EJECUTAR SINCRONIZADOR EN MODO SERVICE")
print("-" * 80)
print("   Ejecutando: python3 sync_system.py --mode service")
print()

try:
    result = subprocess.run(
        ['python3', 'sync_system.py', '--mode', 'service'],
        capture_output=True,
        text=True,
        timeout=60
    )

    if result.returncode == 0:
        print("   ✅ Sincronizador ejecutado correctamente")
    else:
        print(f"   ❌ Error en sincronizador (exit code: {result.returncode})")
        if result.stderr:
            print(f"   Error: {result.stderr[:500]}")
except subprocess.TimeoutExpired:
    print("   ⚠️  Timeout después de 60 segundos (esto es normal en modo service)")
except Exception as e:
    print(f"   ❌ Error ejecutando: {e}")

print()

# PASO 4: Verificar resultado
print("📋 PASO 4: VERIFICAR RESULTADO")
print("-" * 80)

# Verificar TEST_ELIMINAR_001 en MySQL
mysql_cursor.execute("SELECT id, code, name FROM products WHERE code = %s AND company_id = %s",
                    ('TEST_ELIMINAR_001', company_id))
mysql_product = mysql_cursor.fetchone()
if mysql_product:
    print(f"   ❌ TEST_ELIMINAR_001 AÚN EXISTE EN MYSQL - NO SE ELIMINÓ")
    print(f"      ID: {mysql_product[0]}, Name: {mysql_product[2]}")
else:
    print(f"   ✅ TEST_ELIMINAR_001 FUE ELIMINADO DE MYSQL")

# Verificar code=03 si existe
mysql_cursor.execute("SELECT id, code, name FROM products WHERE code = %s AND company_id = %s",
                    ('03', company_id))
mysql_product = mysql_cursor.fetchone()
if mysql_product:
    print(f"   ❌ CODE=03 AÚN EXISTE EN MYSQL - NO SE ELIMINÓ")
    print(f"      ID: {mysql_product[0]}, Name: {mysql_product[2]}")
else:
    print(f"   ✅ CODE=03 NO EXISTE EN MYSQL")

print()
print("=" * 80)
print("✅ TEST COMPLETADO")
print("=" * 80)

pg_cursor.close()
pg_conn.close()
mysql_cursor.close()
mysql_conn.close()
