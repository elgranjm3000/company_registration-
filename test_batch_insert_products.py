#!/usr/bin/env python3
"""
Test: Verificar que el batch insert de productos PostgreSQL → MySQL funciona
"""

import sys
import os
import psycopg2
import pymysql
from dotenv import load_dotenv
from importlib.util import spec_from_file_location, module_from_spec

load_dotenv()

print("=" * 80)
print("🧪 TEST: Batch Insert PostgreSQL → MySQL")
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
    autocommit=False
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
test_prefix = 'BATCH_TEST_'

pg_cursor.execute("DELETE FROM products WHERE code LIKE %s", (f'{test_prefix}%',))
pg_conn.commit()

mysql_cursor.execute("DELETE FROM products WHERE code LIKE %s AND company_id = %s",
                    (f'{test_prefix}%', company_id))
mysql_conn.commit()

pg_cursor.execute("DELETE FROM sync_hashes WHERE table_name = 'products' AND record_key LIKE %s",
                 (f'{test_prefix}%',))
pg_conn.commit()
print("   ✅ Limpiado")
print()

# PASO 2: Crear 5 productos de prueba en PostgreSQL
print("📋 PASO 2: CREAR PRODUCTOS EN POSTGRESQL")
print("-" * 80)

test_products = []
for i in range(1, 6):
    code = f'{test_prefix}{i:03d}'
    # Obtener department válido
    pg_cursor.execute("SELECT code FROM department WHERE code != '00' LIMIT 1")
    dept_row = pg_cursor.fetchone()
    department = dept_row[0] if dept_row else '001'

    # Insertar producto
    pg_cursor.execute("""
        INSERT INTO products (code, description, short_name, department, status, product_type)
        VALUES (%s, %s, %s, %s, '01', 'finished')
        RETURNING code, description
    """, (code, f'Producto Batch Test {i}', f'Batch {i}'))

    result = pg_cursor.fetchone()
    test_products.append(result[0])
    print(f"   ✅ Creado: {result[0]} - {result[1]}")

pg_conn.commit()
print()

# PASO 3: Verificar que NO existen en MySQL
print("📋 PASO 3: VERIFICAR QUE NO EXISTEN EN MYSQL")
print("-" * 80)

mysql_cursor.execute(f"""
    SELECT COUNT(*)
    FROM products
    WHERE code LIKE %s AND company_id = %s
""", (f'{test_prefix}%', company_id))
count = mysql_cursor.fetchone()[0]
print(f"   Productos en MySQL: {count}")
if count == 0:
    print("   ✅ Correcto - no existen en MySQL aún")
else:
    print(f"   ⚠️  Advertencia - ya existen {count} productos en MySQL")
print()

# PASO 4: Detectar cambios
print("📋 PASO 4: DETECTAR CAMBIOS")
print("-" * 80)

try:
    # Importar SmartSyncComplete
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
                'info': 'ℹ️',
                'success': '✅',
                'warning': '⚠️',
                'error': '❌',
                'debug': '🔍'
            }
            prefijo = prefijos.get(tipo, 'ℹ️')
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
        'database': 'chrystal_movil'',
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

    print("   Detectando cambios...")
    cambios = sync_instance.detectar_cambios_products()

    nuevos = len(cambios['nuevos'])
    modificados = len(cambios['modificados'])

    print(f"   ✅ Nuevos: {nuevos}")
    print(f"   ✅ Modificados: {modificados}")

    # Verificar que nuestros productos están en 'nuevos'
    nuevos_codes = [p[0] for p in cambios['nuevos']]
    nuestros_nuevos = [c for c in test_products if c in nuevos_codes]
    print(f"   ✅ Nuestros productos detectados: {len(nuestros_nuevos)}/{len(test_products)}")

except Exception as e:
    print(f"   ❌ Error: {e}")
    import traceback
    print(f"   TRACEBACK:\n{traceback.format_exc()}")
    exit(1)

print()

# PASO 5: Ejecutar sincronización
print("📋 PASO 5: SINCRONIZAR A MYSQL")
print("-" * 80)

try:
    if nuevos > 0:
        sync_instance.sincronizar_products_mysql(cambios)
        print("   ✅ Sincronización completada")
    else:
        print("   ⚠️  No hay productos nuevos para sincronizar")
except Exception as e:
    print(f"   ❌ Error en sincronización: {e}")
    import traceback
    print(f"   TRACEBACK:\n{traceback.format_exc()}")
    exit(1)

print()

# PASO 6: Verificar resultado con nueva conexión
print("📋 PASO 6: VERIFICAR RESULTADO")
print("-" * 80)

mysql_conn_check = pymysql.connect(
    host='91.238.160.176',
    port=3306,
    database='chrystal_movil',
    user='chrystal_app',
    password='muentes123.',
    charset='utf8mb4'
)
mysql_cursor_check = mysql_conn_check.cursor()

mysql_cursor_check.execute(f"""
    SELECT code, name
    FROM products
    WHERE code LIKE %s AND company_id = %s
    ORDER BY code
""", (f'{test_prefix}%', company_id))

resultados = mysql_cursor_check.fetchall()

if len(resultados) == len(test_products):
    print(f"   ✅ ÉXITO: {len(resultados)} productos insertados en MySQL")
    print()
    for code, name in resultados:
        print(f"      - {code}: {name}")
    print()
    print("   ✅✅✅ EL BATCH INSERT FUNCIONA CORRECTAMENTE ✅✅✅")
elif len(resultados) > 0:
    print(f"   ⚠️  PARCIAL: {len(resultados)}/{len(test_products)} productos insertados")
    for code, name in resultados:
        print(f"      - {code}")
else:
    print(f"   ❌❌❌ ERROR: Ningún producto insertado en MySQL ❌❌❌")

mysql_cursor_check.close()
mysql_conn_check.close()

print()
print("=" * 80)
print("✅ TEST COMPLETADO")
print("=" * 80)

# Limpiar
pg_cursor.execute("DELETE FROM products WHERE code LIKE %s", (f'{test_prefix}%',))
pg_conn.commit()
mysql_cursor.execute("DELETE FROM products WHERE code LIKE %s AND company_id = %s",
                    (f'{test_prefix}%', company_id))
mysql_conn.commit()
pg_cursor.execute("DELETE FROM sync_hashes WHERE table_name = 'products' AND record_key LIKE %s",
                 (f'{test_prefix}%',))
pg_conn.commit()
print("✅ Productos de prueba eliminados")

pg_cursor.close()
pg_conn.close()
mysql_cursor.close()
mysql_conn.close()
