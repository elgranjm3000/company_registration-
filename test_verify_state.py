#!/usr/bin/env python3
"""
Test para verificar el estado DESPUÉS de la sincronización
"""

import psycopg2
import pymysql
from dotenv import load_dotenv
import os

load_dotenv()

print("=" * 80)
print("🔍 VERIFICANDO ESTADO DESPUÉS DE SINCRONIZACIÓN")
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
company_id = result[0]
print(f"✅ Company ID: {company_id}")
print()

# Verificar TEST_SERVICE_MODE en MySQL
print("📋 VERIFICANDO TEST_SERVICE_MODE EN MYSQL:")
print("-" * 80)
mysql_cursor.execute("""
    SELECT id, code, name, created_at, updated_at
    FROM products
    WHERE code = %s AND company_id = %s
""", ('TEST_SERVICE_MODE', company_id))
producto = mysql_cursor.fetchone()

if producto:
    pid, code, name, created, updated = producto
    print(f"   ✅ EXISTE en MySQL:")
    print(f"      ID: {pid}")
    print(f"      Code: {code}")
    print(f"      Name: {name}")
    print(f"      Created: {created}")
    print(f"      Updated: {updated}")
    print()
    print("   ℹ️  El producto fue RECREADO después de ser eliminado")
    print("   ℹ️  Esto explica por qué el test falla")
else:
    print(f"   ❌ NO EXISTE en MySQL")
    print()
    print("   ✅ La eliminación fue exitosa y PERMANENTE")

print()

# Verificar TEST_SERVICE_MODE en PostgreSQL
print("📋 VERIFICANDO TEST_SERVICE_MODE EN POSTGRESQL:")
print("-" * 80)
pg_cursor.execute("""
    SELECT code, description, short_name
    FROM products
    WHERE code = %s
""", ('TEST_SERVICE_MODE',))
producto = pg_cursor.fetchone()

if producto:
    code, description, short_name = producto
    print(f"   ✅ EXISTE en PostgreSQL:")
    print(f"      Code: {code}")
    print(f"      Description: {description}")
    print(f"      Short Name: {short_name}")
    print()
    print("   ℹ️  Fue recreado por la sincronización MySQL→PostgreSQL")
else:
    print(f"   ❌ NO EXISTE en PostgreSQL")

print()

# Verificar sync_hashes
print("📋 VERIFICANDO SYNC_HASHES:")
print("-" * 80)
pg_cursor.execute("""
    SELECT record_key, deleted_at, hash_value
    FROM sync_hashes
    WHERE table_name = 'products' AND record_key = %s
""", ('TEST_SERVICE_MODE',))
hash_data = pg_cursor.fetchone()

if hash_data:
    key, deleted, hash_val = hash_data
    print(f"   ✅ EXISTE en sync_hashes:")
    print(f"      Key: {key}")
    print(f"      Deleted at: {deleted}")
    print(f"      Hash value: {hash_val}")
else:
    print(f"   ❌ NO EXISTE en sync_hashes")

print()
print("=" * 80)
print("✅ VERIFICACIÓN COMPLETADA")
print("=" * 80)

pg_cursor.close()
pg_conn.close()
mysql_cursor.close()
mysql_conn.close()
