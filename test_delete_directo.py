#!/usr/bin/env python3
"""
Test DIRECTO: Llamar a la función de eliminación sin pasar por todo el sync
"""

import sys
import os
import psycopg2
import pymysql
from dotenv import load_dotenv

load_dotenv()

print("=" * 80)
print("🧪 TEST DIRECTO: _eliminar_productos_mysql_cuando_faltan_en_postgresql()")
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

# PASO 1: Limpiar
print("📋 PASO 1: LIMPIAR")
print("-" * 80)
test_code = 'TEST_DELETE_DIRECTO'
pg_cursor.execute("DELETE FROM products WHERE code = %s", (test_code,))
pg_conn.commit()
mysql_cursor.execute("DELETE FROM products WHERE code = %s AND company_id = %s",
                    (test_code, company_id))
mysql_conn.commit()
pg_cursor.execute("DELETE FROM sync_hashes WHERE table_name = 'products' AND record_key = %s",
                 (test_code,))
pg_conn.commit()
print("   ✅ Limpiado")
print()

# PASO 2: Crear producto en PostgreSQL
print("📋 PASO 2: CREAR PRODUCTO EN POSTGRESQL")
print("-" * 80)
pg_cursor.execute("""
    INSERT INTO products (code, description, short_name, department, status)
    VALUES (%s, %s, %s, %s, '01')
    RETURNING code, description
""", (test_code, 'Producto Test Directo', 'Test Directo', '00'))
result = pg_cursor.fetchone()
pg_conn.commit()
print(f"   ✅ Creado en PostgreSQL: {result[0]} - {result[1]}")
print()

# PASO 3: Eliminar de PostgreSQL (trigger marca en sync_hashes)
print("📋 PASO 3: ELIMINAR DE POSTGRESQL")
print("-" * 80)
pg_cursor.execute("DELETE FROM products WHERE code = %s", (test_code,))
pg_conn.commit()
print(f"   ✅ Eliminado de PostgreSQL: {test_code}")

# Verificar sync_hashes
pg_cursor.execute("""
    SELECT record_key, deleted_at
    FROM sync_hashes
    WHERE table_name = 'products' AND record_key = %s
""", (test_code,))
hash_data = pg_cursor.fetchone()
if hash_data and hash_data[1]:
    print(f"   ✅ sync_hashes marcó como eliminado: {hash_data[1]}")
else:
    print(f"   ❌ ERROR: sync_hashes NO lo marcó")
    exit(1)
print()

# PASO 4: Crear en MySQL
print("📋 PASO 4: CREAR EN MYSQL")
print("-" * 80)
mysql_cursor.execute("""
    INSERT INTO products (company_id, code, name, description, price, cost, stock, status, category_id, created_at, updated_at)
    VALUES (%s, %s, %s, %s, 100, 50, 10, 'active', 6250, NOW(), NOW())
""", (company_id, test_code, 'Test Directo', 'Producto para test'))
mysql_conn.commit()

mysql_cursor.execute("SELECT id, code, name FROM products WHERE code = %s AND company_id = %s",
                    (test_code, company_id))
antes = mysql_cursor.fetchone()
print(f"   ✅ Creado en MySQL: id={antes[0]}, code={antes[1]}, name={antes[2]}")
print()

# PASO 5: Importar y llamar a la función de eliminación DIRECTAMENTE
print("📋 PASO 5: LLAMAR FUNCIÓN DE ELIMINACIÓN DIRECTAMENTE")
print("-" * 80)

try:
    # Importar SmartSyncComplete
    from importlib.util import spec_from_file_location, module_from_spec
    spec = spec_from_file_location("smart_sync_complete",
                                   "/home/muentes/company_registration/smart_sync_complete.py")
    sync_module = module_from_spec(spec)
    spec.loader.exec_module(sync_module)

    # Crear instancia minimal
    class MinimalApp:
        def __init__(self):
            self.sync_running = True

        def log_message(self, mensaje, tipo="info"):
            prefijos = {
                'info': 'ℹ️ INFO',
                'success': '✅ SUCCESS',
                'warning': '⚠️ WARNING',
                'error': '❌ ERROR',
                'debug': '🔍 DEBUG'
            }
            prefijo = prefijos.get(tipo, 'ℹ️ INFO')
            print(f"   [{prefijo}] {mensaje}")

    app = MinimalApp()

    postgresql_config = {
        'host': os.getenv('DB_HOST'),
        'port': 5432,
        'database': 'nuevaprueba',
        'user': os.getenv('DB_USER'),
        'password': os.getenv('DB_PASSWORD')
    }

    mysql_config = {
        'host': '91.238.160.176',
        'port': 3306,
        'database': 'chrystal_movil',
        'user': 'chrystal_app',
        'password': 'muentes123.'
    }

    sync_instance = sync_module.SmartSyncComplete(
        app=app,
        postgresql_config=postgresql_config,
        mysql_config=mysql_config,
        company_rif='J505261940',
        company_email='elgranjm3000@gmail.com',
        company_name='empresa prueba'
    )

    # Usar las conexiones existentes
    sync_instance.pg_conn = pg_conn
    sync_instance.pg_cursor = pg_cursor
    sync_instance.mysql_conn = mysql_conn
    sync_instance.mysql_cursor = mysql_cursor
    sync_instance.sync_running = True

    print("   📋 Llamando a _eliminar_productos_mysql_cuando_faltan_en_postgresql()...")
    sync_instance._eliminar_productos_mysql_cuando_faltan_en_postgresql()
    print("   ✅ Función ejecutada")

except Exception as e:
    print(f"   ❌ Error: {e}")
    import traceback
    print(f"   TRACEBACK:\n{traceback.format_exc()}")
    exit(1)

print()

# PASO 6: Verificar resultado
print("📋 PASO 6: VERIFICAR RESULTADO")
print("-" * 80)

mysql_cursor.execute("SELECT id, code, name FROM products WHERE code = %s AND company_id = %s",
                    (test_code, company_id))
despues = mysql_cursor.fetchone()

if despues:
    print(f"   ❌ {test_code} AÚN EXISTE EN MYSQL")
    print(f"      ID: {despues[0]}, Name: {despues[2]}")
    print()
    print("   ❌❌❌ LA FUNCIÓN DE ELIMINACIÓN NO FUNCIONÓ ❌❌❌")
else:
    print(f"   ✅ {test_code} FUE ELIMINADO DE MYSQL")
    print()
    print("   ✅✅✅ LA FUNCIÓN DE ELIMINACIÓN SÍ FUNCIONA ✅✅✅")

print()
print("=" * 80)
print("✅ TEST COMPLETADO")
print("=" * 80)

pg_cursor.close()
pg_conn.close()
mysql_cursor.close()
mysql_conn.close()
