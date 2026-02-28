#!/usr/bin/env python3
"""
Test COMPLETO: Verificar sincronización de productos PostgreSQL → MySQL
- Crear producto en PostgreSQL
- Ejecutar sincronización
- Verificar que aparezca en MySQL
- Editar producto en PostgreSQL
- Ejecutar sincronización nuevamente
- Verificar que se actualice en MySQL
"""

import sys
import os
import psycopg2
import pymysql
import time
from dotenv import load_dotenv
from importlib.util import spec_from_file_location, module_from_spec

load_dotenv()

print("=" * 80)
print("🧪 TEST COMPLETO: Sincronización PostgreSQL → MySQL")
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

# ==============================================================================
# PARTE 1: CREAR NUEVO PRODUCTO
# ==============================================================================

print("📋 PARTE 1: CREAR NUEVO PRODUCTO EN POSTGRESQL")
print("-" * 80)

test_code = 'SYNC_TEST_001'

# Limpiar si existe
pg_cursor.execute("DELETE FROM products WHERE code = %s", (test_code,))
pg_conn.commit()
mysql_cursor.execute("DELETE FROM products WHERE code = %s AND company_id = %s",
                    (test_code, company_id))
mysql_conn.commit()
pg_cursor.execute("DELETE FROM sync_hashes WHERE table_name = 'products' AND record_key = %s",
                 (test_code,))
pg_conn.commit()

# Obtener department válido
pg_cursor.execute("SELECT code FROM department WHERE code != '00' LIMIT 1")
dept_row = pg_cursor.fetchone()
department = dept_row[0] if dept_row else '001'

print(f"   Creando producto: {test_code}")
print(f"   Department: {department}")

# Crear producto
pg_cursor.execute("""
    INSERT INTO products (
        code, description, short_name, department, status,
        product_type, minimal_stock, sale_tax
    ) VALUES (%s, %s, %s, %s, '01', 'finished', 10, '01')
    RETURNING code, description, short_name
""", (test_code, 'Producto Sync Test', 'Sync Test', department))

result = pg_cursor.fetchone()
pg_conn.commit()

print(f"   ✅ Creado en PostgreSQL: {result[0]} - {result[1]}")
print()

# Esperar un momento para que se procese
time.sleep(1)

# ==============================================================================
# PARTE 2: VERIFICAR ANTES DE SINCRONIZAR
# ==============================================================================

print("📋 PARTE 2: ESTADO ANTES DE SINCRONIZAR")
print("-" * 80)

# Verificar PostgreSQL
pg_cursor.execute("SELECT code, description FROM products WHERE code = %s", (test_code,))
pg_producto = pg_cursor.fetchone()
print(f"   PostgreSQL: ✅ EXISTE - {pg_producto[0]}: {pg_producto[1]}")

# Verificar MySQL (con nueva conexión)
mysql_conn_check = pymysql.connect(
    host='91.238.160.176',
    port=3306,
    database='chrystal_movil',
    user='chrystal_app',
    password='muentes123.',
    charset='utf8mb4'
)
mysql_cursor_check = mysql_conn_check.cursor()

mysql_cursor_check.execute("SELECT code, name FROM products WHERE code = %s AND company_id = %s",
                          (test_code, company_id))
mysql_producto = mysql_cursor_check.fetchone()

if mysql_producto:
    print(f"   MySQL: ⚠️  YA EXISTE - {mysql_producto[0]}: {mysql_producto[1]}")
else:
    print(f"   MySQL: ❌ NO EXISTE (esperado antes de sincronizar)")

mysql_cursor_check.close()
mysql_conn_check.close()
print()

# ==============================================================================
# PARTE 3: DETECTAR CAMBIOS
# ==============================================================================

print("📋 PARTE 3: DETECTAR CAMBIOS")
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

    print("   Detectando cambios...")
    cambios = sync_instance.detectar_cambios_products()

    nuevos = len(cambios['nuevos'])
    modificados = len(cambios['modificados'])
    eliminados = len(cambios['eliminados'])

    print(f"   ✅ Nuevos: {nuevos}")
    print(f"   ✅ Modificados: {modificados}")
    print(f"   ✅ Eliminados: {eliminados}")
    print()

    # Verificar si nuestro producto está en 'nuevos'
    nuevos_codes = [p[0] for p in cambios['nuevos']]
    if test_code in nuevos_codes:
        print(f"   ✅ Nuestro producto '{test_code}' fue detectado como NUEVO")
    else:
        print(f"   ❌ Nuestro producto '{test_code}' NO fue detectado")
        print(f"   ℹ️  Productos detectados como nuevos: {nuevos_codes[:5]}")  # Primeros 5

except Exception as e:
    print(f"   ❌ Error detectando cambios: {e}")
    import traceback
    print(f"   TRACEBACK:\n{traceback.format_exc()}")
    pg_cursor.close()
    pg_conn.close()
    mysql_cursor.close()
    mysql_conn.close()
    sys.exit(1)

print()

# ==============================================================================
# PARTE 4: SINCRONIZAR A MYSQL
# ==============================================================================

print("📋 PARTE 4: SINCRONIZAR A MYSQL")
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
    pg_cursor.close()
    pg_conn.close()
    mysql_cursor.close()
    mysql_conn.close()
    sys.exit(1)

print()

# ==============================================================================
# PARTE 5: VERIFICAR DESPUÉS DE SINCRONIZAR
# ==============================================================================

print("📋 PARTE 5: ESTADO DESPUÉS DE SINCRONIZAR")
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

mysql_cursor_check.execute("""
    SELECT code, name, description, price, cost
    FROM products
    WHERE code = %s AND company_id = %s
""", (test_code, company_id))

mysql_producto = mysql_cursor_check.fetchone()

if mysql_producto:
    print(f"   ✅ PRODUCTO EXISTE EN MYSQL:")
    print(f"      Code: {mysql_producto[0]}")
    print(f"      Name: {mysql_producto[1]}")
    print(f"      Description: {mysql_producto[2]}")
    print(f"      Price: {mysql_producto[3]}")
    print(f"      Cost: {mysql_producto[4]}")
    print()
    print("   ✅✅✅ PARTE 1 COMPLETADA: Producto sincronizado correctamente ✅✅✅")
else:
    print(f"   ❌❌❌ PRODUCTO NO EXISTE EN MYSQL ❌❌❌")
    print()
    print("   🔍 DIAGNÓSTICO:")
    print("   Verificando hash en sync_hashes...")

    pg_cursor.execute("""
        SELECT hash_value, updated_at
        FROM sync_hashes
        WHERE table_name = 'products' AND record_key = %s
    """, (test_code,))
    hash_data = pg_cursor.fetchone()

    if hash_data:
        print(f"   ✅ Hash existe en sync_hashes:")
        print(f"      Hash: {hash_data[0]}")
        print(f"      Updated: {hash_data[1]}")
    else:
        print(f"   ❌ Hash NO existe en sync_hashes")

    mysql_cursor_check.close()
    mysql_conn_check.close()
    pg_cursor.close()
    pg_conn.close()
    mysql_cursor.close()
    mysql_conn.close()
    sys.exit(1)

mysql_cursor_check.close()
mysql_conn_check.close()
print()

# ==============================================================================
# PARTE 6: EDITAR PRODUCTO EN POSTGRESQL
# ==============================================================================

print("📋 PARTE 6: EDITAR PRODUCTO EN POSTGRESQL")
print("-" * 80)

print("   Modificando descripción y precios...")

pg_cursor.execute("""
    UPDATE products
    SET description = %s,
        short_name = %s
    WHERE code = %s
    RETURNING code, description, short_name
""", ('Producto MODIFICADO', 'Modificado', test_code))

result = pg_cursor.fetchone()
pg_conn.commit()

print(f"   ✅ Modificado en PostgreSQL:")
print(f"      Code: {result[0]}")
print(f"      Description: {result[1]}")
print(f"      Short Name: {result[2]}")
print()

# Esperar un momento
time.sleep(1)

# ==============================================================================
# PARTE 7: DETECTAR CAMBIOS NUEVAMENTE
# ==============================================================================

print("📋 PARTE 7: DETECTAR CAMBIOS NUEVAMENTE")
print("-" * 80)

print("   Detectando cambios después de modificación...")
cambios2 = sync_instance.detectar_cambios_products()

nuevos2 = len(cambios2['nuevos'])
modificados2 = len(cambios2['modificados'])
eliminados2 = len(cambios2['eliminados'])

print(f"   ✅ Nuevos: {nuevos2}")
print(f"   ✅ Modificados: {modificados2}")
print(f"   ✅ Eliminados: {eliminados2}")
print()

# Verificar si nuestro producto está en 'modificados'
modificados_codes = [p[0] for p in cambios2['modificados']]
if test_code in modificados_codes:
    print(f"   ✅ Nuestro producto '{test_code}' fue detectado como MODIFICADO")
else:
    print(f"   ❌ Nuestro producto '{test_code}' NO fue detectado como modificado")
    print(f"   ℹ️  Productos detectados como modificados: {modificados_codes[:5]}")

print()

# ==============================================================================
# PARTE 8: SINCRONIZAR MODIFICACIÓN
# ==============================================================================

print("📋 PARTE 8: SINCRONIZAR MODIFICACIÓN A MYSQL")
print("-" * 80)

try:
    if modificados2 > 0:
        sync_instance.sincronizar_products_mysql(cambios2)
        print("   ✅ Sincronización de modificación completada")
    else:
        print("   ⚠️  No hay productos modificados para sincronizar")
except Exception as e:
    print(f"   ❌ Error en sincronización: {e}")
    import traceback
    print(f"   TRACEBACK:\n{traceback.format_exc()}")

print()

# ==============================================================================
# PARTE 9: VERIFICAR MODIFICACIÓN EN MYSQL
# ==============================================================================

print("📋 PARTE 9: VERIFICAR MODIFICACIÓN EN MYSQL")
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

mysql_cursor_check.execute("""
    SELECT code, name, description
    FROM products
    WHERE code = %s AND company_id = %s
""", (test_code, company_id))

mysql_producto = mysql_cursor_check.fetchone()

if mysql_producto:
    print(f"   ✅ PRODUCTO EN MYSQL:")
    print(f"      Code: {mysql_producto[0]}")
    print(f"      Name: {mysql_producto[1]}")
    print(f"      Description: {mysql_producto[2]}")
    print()

    if mysql_producto[2] == 'Producto MODIFICADO':
        print("   ✅✅✅ PARTE 2 COMPLETADA: Modificación sincronizada correctamente ✅✅✅")
    else:
        print(f"   ⚠️  La descripción NO se actualizó:")
        print(f"      Esperado: 'Producto MODIFICADO'")
        print(f"      Obtenido: '{mysql_producto[2]}'")
else:
    print(f"   ❌ Producto desapareció de MySQL")

mysql_cursor_check.close()
mysql_conn_check.close()

print()
print("=" * 80)
print("🏁 TEST COMPLETADO")
print("=" * 80)

# Limpiar
print()
print("🧹 Limpiando producto de prueba...")
pg_cursor.execute("DELETE FROM products WHERE code = %s", (test_code,))
pg_conn.commit()
mysql_cursor.execute("DELETE FROM products WHERE code = %s AND company_id = %s",
                    (test_code, company_id))
mysql_conn.commit()
pg_cursor.execute("DELETE FROM sync_hashes WHERE table_name = 'products' AND record_key = %s",
                 (test_code,))
pg_conn.commit()
print("✅ Limpieza completada")

pg_cursor.close()
pg_conn.close()
mysql_cursor.close()
mysql_conn.close()
