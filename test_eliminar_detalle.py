#!/usr/bin/env python3
"""
Test detallado: Verificar qué pasa con el DELETE
"""

import psycopg2
import pymysql
from dotenv import load_dotenv
import os

load_dotenv()

print("=" * 80)
print("🔍 TEST DETALLADO: ELIMINACIÓN DE PRODUCTOS")
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
    charset='utf8mb4',
    autocommit=False  # Importante: controlar commits manualmente
)
mysql_cursor = mysql_conn.cursor()

# Obtener company_id
mysql_cursor.execute("SELECT id FROM companies WHERE rif = %s AND email = %s LIMIT 1",
                     ('J505261940', 'elgranjm3000@gmail.com'))
result = mysql_cursor.fetchone()
company_id = result[0]
print(f"✅ Company ID: {company_id}")
print()

# Buscar un producto eliminado en sync_hashes
print("🔍 PASO 1: BUSCAR PRODUCTO ELIMINADO EN SYNC_HASHES")
print("-" * 80)

pg_cursor.execute("""
    SELECT record_key, deleted_at
    FROM sync_hashes
    WHERE table_name = 'products'
    AND deleted_at IS NOT NULL
    LIMIT 1
""")
hash_data = pg_cursor.fetchone()

if not hash_data:
    print("❌ No hay productos eliminados en sync_hashes")
    print("📋 Creando uno para probar...")

    # Crear producto
    pg_cursor.execute("""
        INSERT INTO products (code, description, short_name, department, status)
        VALUES (%s, %s, %s, %s, '01')
    """, ('TEST_DELETE_001', 'Test Delete', 'Test', '001'))
    pg_conn.commit()
    print("   ✅ Creado: TEST_DELETE_001")

    # Eliminarlo
    pg_cursor.execute("DELETE FROM products WHERE code = %s", ('TEST_DELETE_001',))
    pg_conn.commit()
    print("   ✅ Eliminado: TEST_DELETE_001")

    # Verificar sync_hashes
    pg_cursor.execute("""
        SELECT record_key, deleted_at
        FROM sync_hashes
        WHERE table_name = 'products' AND record_key = %s
    """, ('TEST_DELETE_001',))
    hash_data = pg_cursor.fetchone()

if hash_data:
    code, deleted_at = hash_data
    print(f"   ✅ Producto en sync_hashes: {code}, deleted_at: {deleted_at}")
else:
    print("   ❌ ERROR: No se marcó en sync_hashes")
    exit(1)

print()

# Verificar si existe en MySQL
print("🔍 PASO 2: VERIFICAR SI EXISTE EN MYSQL")
print("-" * 80)

mysql_cursor.execute("SELECT id, code, name FROM products WHERE code = %s AND company_id = %s",
                    (code, company_id))
producto = mysql_cursor.fetchone()

if not producto:
    print(f"   ℹ️  {code} NO existe en MySQL")
    print("   📋 Creándolo para probar eliminación...")

    mysql_cursor.execute("""
        INSERT INTO products (company_id, code, name, description, price, cost, stock, status, category_id, created_at, updated_at)
        VALUES (%s, %s, %s, %s, 100, 50, 10, 'active', 1, NOW(), NOW())
    """, (company_id, code, f'Producto {code}', f'Descripción {code}'))
    mysql_conn.commit()
    print(f"   ✅ Creado en MySQL: {code}")

    mysql_cursor.execute("SELECT id, code, name FROM products WHERE code = %s AND company_id = %s",
                        (code, company_id))
    producto = mysql_cursor.fetchone()

if producto:
    pid, pcode, pname = producto
    print(f"   ✅ EXISTE en MySQL: id={pid}, code={pcode}, name={pname}")
else:
    print(f"   ❌ NO existe en MySQL")
    exit(1)

print()

# Ejecutar DELETE
print("🔍 PASO 3: EJECUTAR DELETE")
print("-" * 80)

try:
    delete_query = """
    DELETE FROM products
    WHERE id = %s AND company_id = %s
    """
    mysql_cursor.execute(delete_query, (pid, company_id))

    affected_rows = mysql_cursor.rowcount
    print(f"   Rowcount (filas afectadas): {affected_rows}")

    if affected_rows > 0:
        print("   ✅ DELETE afectó filas - haciendo commit...")
        mysql_conn.commit()
        print("   ✅ Commit ejecutado")
    else:
        print("   ❌ DELETE NO afectó ninguna fila - haciendo rollback")
        mysql_conn.rollback()
        print("   ❌ Rollback ejecutado")

except Exception as e:
    print(f"   ❌ Error en DELETE: {e}")
    mysql_conn.rollback()
    print("   ❌ Rollback por error")
    import traceback
    print(f"   TRACEBACK: {traceback.format_exc()}")

print()

# Verificar resultado
print("🔍 PASO 4: VERIFICAR RESULTADO")
print("-" * 80)

mysql_cursor.execute("SELECT id, code, name FROM products WHERE id = %s", (pid,))
resultado = mysql_cursor.fetchone()

if resultado:
    print(f"   ❌ PRODUCTO AÚN EXISTE: id={resultado[0]}, code={resultado[1]}")
    print(f"   ❌ EL DELETE NO FUNCIONÓ")
else:
    print(f"   ✅ PRODUCTO FUE ELIMINADO: id={pid}")
    print(f"   ✅ EL DELETE SÍ FUNCIONÓ")

print()
print("=" * 80)
print("✅ TEST COMPLETADO")
print("=" * 80)

pg_cursor.close()
pg_conn.close()
mysql_cursor.close()
mysql_conn.close()
