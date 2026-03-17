#!/usr/bin/env python3
"""
Test REAL: Ejecutar sync_system.py --mode service --once y verificar si elimina
"""

import psycopg2
import pymysql
from dotenv import load_dotenv
import os
import subprocess
import time

load_dotenv()

print("=" * 80)
print("🧪 TEST REAL: sync_system.py --mode service --once")
print("=" * 80)
print()

# Conexiones para verificar
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

# PASO 1: Limpiar productos de prueba anteriores
print("📋 PASO 1: LIMPIAR PRODUCTOS DE PRUEBA")
print("-" * 80)

test_code = 'TEST_SERVICE_MODE'

# Limpiar PostgreSQL
pg_cursor.execute("DELETE FROM products WHERE code LIKE %s", (f'{test_code}%',))
pg_conn.commit()

# Limpiar MySQL
mysql_cursor.execute("DELETE FROM products WHERE code LIKE %s AND company_id = %s",
                    (f'{test_code}%', company_id))
mysql_conn.commit()

# Limpiar sync_hashes
pg_cursor.execute("DELETE FROM sync_hashes WHERE table_name = 'products' AND record_key LIKE %s",
                  (f'{test_code}%',))
pg_conn.commit()

print(f"   ✅ Limpiados productos de prueba anteriores")
print()

# PASO 2: Crear producto de prueba
print("📋 PASO 2: CREAR PRODUCTO DE PRUEBA EN POSTGRESQL")
print("-" * 80)

# Crear en PostgreSQL
pg_cursor.execute("""
    INSERT INTO products (code, description, short_name, department, status)
    VALUES (%s, %s, %s, %s, '01')
    RETURNING code, description
""", (test_code, 'Producto Test Service Mode', 'Test Service', '00'))

result = pg_cursor.fetchone()
pg_conn.commit()

print(f"   ✅ Creado en PostgreSQL: {result[0]} - {result[1]}")
print()

# Esperar a que se sincronice (si ya hubiera sido sincronizado antes)
time.sleep(2)

# Verificar si existe en MySQL (por sincronización previa)
mysql_cursor.execute("SELECT id, code FROM products WHERE code = %s AND company_id = %s",
                    (test_code, company_id))
existe_en_mysql = mysql_cursor.fetchone()

if existe_en_mysql:
    print(f"   ℹ️  Ya existía en MySQL: id={existe_en_mysql[0]}")
else:
    print(f"   ℹ️  No existe en MySQL todavía (normal si es primera vez)")

print()

# PASO 3: Eliminar producto de PostgreSQL
print("📋 PASO 3: ELIMINAR PRODUCTO DE POSTGRESQL")
print("-" * 80)

pg_cursor.execute("DELETE FROM products WHERE code = %s", (test_code,))
pg_conn.commit()
print(f"   ✅ Eliminado de PostgreSQL: {test_code}")
print()

# Verificar que sync_hashes lo marcó como eliminado
time.sleep(1)

pg_cursor.execute("""
    SELECT deleted_at FROM sync_hashes
    WHERE table_name = 'products' AND record_key = %s
""", (test_code,))

hash_deleted = pg_cursor.fetchone()
if hash_deleted and hash_deleted[0]:
    print(f"   ✅ sync_hashes lo marcó como eliminado: {hash_deleted[0]}")
else:
    print(f"   ❌ sync_hashes NO lo marcó - PROBLEMA CON EL TRIGGER")
    exit(1)

print()

# PASO 4: Crear el producto en MySQL manualmente (simulando que ya existía)
print("📋 PASO 4: CREAR PRODUCTO EN MYSQL (SIMULANDO QUE YA EXISTÍA)")
print("-" * 80)

mysql_cursor.execute("""
    INSERT INTO products (company_id, code, name, description, price, cost, stock, status, category_id, created_at, updated_at)
    VALUES (%s, %s, %s, %s, 100, 50, 10, 'active', 6250, NOW(), NOW())
""", (company_id, test_code, 'Test Service Mode', 'Producto para test'))
mysql_conn.commit()

mysql_cursor.execute("SELECT id, code, name FROM products WHERE code = %s AND company_id = %s",
                    (test_code, company_id))
antes = mysql_cursor.fetchone()

print(f"   ✅ Creado en MySQL: id={antes[0]}, code={antes[1]}, name={antes[2]}")
print()

# PASO 5: Verificar estado ANTES de sincronizar
print("📋 PASO 5: ESTADO ANTES DE SINCRONIZAR")
print("-" * 80)

print(f"   PostgreSQL: NO existe {test_code}")
print(f"   MySQL: SÍ existe {test_code} (id={antes[0]})")
print(f"   sync_hashes: Marcado como eliminado (deleted_at={hash_deleted[0]})")
print()

# PASO 6: Ejecutar sync_system.py --mode service --once
print("📋 PASO 6: EJECUTAR SINCRONIZADOR")
print("-" * 80)
print("   Comando: python3 sync_system.py --mode service --once")
print()

try:
    result = subprocess.run(
        ['python3', 'sync_system.py', '--mode', 'service', '--once'],
        capture_output=True,
        text=True,
        timeout=120,
        cwd='/home/muentes/company_registration'
    )

    # Mostrar salida (primera parte)
    print("   Salida del sincronizador:")
    print("   " + "-" * 76)
    output_lines = result.stdout.split('\n')[:50]  # Primeras 50 líneas
    for line in output_lines:
        if line.strip():
            print(f"   {line}")

    if result.stderr:
        print("   Errores:")
        print("   " + "-" * 76)
        err_lines = result.stderr.split('\n')[:20]
        for line in err_lines:
            if line.strip():
                print(f"   {line}")

    print()
    if result.returncode == 0:
        print("   ✅ Sincronizador terminó correctamente (exit code 0)")
    else:
        print(f"   ⚠️  Sincronizador terminó con exit code {result.returncode}")

except subprocess.TimeoutExpired:
    print("   ❌ TIMEOUT después de 120 segundos")
except Exception as e:
    print(f"   ❌ Error ejecutando: {e}")

print()

# PASO 7: Verificar estado DESPUÉS de sincronizar
print("📋 PASO 7: ESTADO DESPUÉS DE SINCRONIZAR")
print("-" * 80)

# IMPORTANTE: Usar nueva conexión para evitar problemas de transacción
mysql_conn_check = pymysql.connect(
    host='91.238.160.176',
    port=3306,
    database='chrystal_movil',
    user='chrystal_app',
    password='muentes123.',
    charset='utf8mb4'
)
mysql_cursor_check = mysql_conn_check.cursor()

mysql_cursor_check.execute("SELECT id, code, name FROM products WHERE code = %s AND company_id = %s",
                          (test_code, company_id))
despues = mysql_cursor_check.fetchone()

mysql_cursor_check.close()
mysql_conn_check.close()

if despues:
    print(f"   ❌ {test_code} AÚN EXISTE EN MYSQL")
    print(f"      ID: {despues[0]}, Name: {despues[2]}")
    print()
    print("   ❌❌❌ EL SINCRONIZADOR NO ELIMINÓ EL PRODUCTO ❌❌❌")
else:
    print(f"   ✅ {test_code} FUE ELIMINADO DE MYSQL")
    print()
    print("   ✅✅✅ EL SINCRONIZADOR FUNCIONA CORRECTAMENTE ✅✅✅")

print()
print("=" * 80)
print("✅ TEST COMPLETADO")
print("=" * 80)

pg_cursor.close()
pg_conn.close()
mysql_cursor.close()
mysql_conn.close()
