#!/usr/bin/env python3
"""
Script para diagnosticar el error en la cotización #58
"""

import sys
sys.path.insert(0, 'windows_api')

import psycopg2
from config_encryption import decrypt_config
import json
import os

# Cargar configuración
CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".chrystal_sync_config.json")

with open(CONFIG_FILE, 'r') as f:
    config = json.load(f)

config = decrypt_config(config)

# Conectar a PostgreSQL
pg_conn = psycopg2.connect(
    host=config['postgres_host'],
    port=config['postgres_port'],
    database=config['postgres_database'],
    user=config['postgres_user'],
    password=config['postgres_password']
)

pg_cursor = pg_conn.cursor()

company_id = config.get('company_rif', '')

print("=" * 80)
print("DIAGNÓSTICO DE COTIZACIÓN #58")
print("=" * 80)

# 1. Verificar cliente
print("\n1. VERIFICANDO CLIENTE 20418024:")
try:
    pg_cursor.execute("""
        SELECT code, name_fiscal FROM clients WHERE code = %s LIMIT 1
    """, ('20418024',))
    result = pg_cursor.fetchone()
    if result:
        print(f"   ✓ Cliente encontrado")
        print(f"   - result[0] (code): {result[0]}")
        print(f"   - result[1] (name_fiscal): {result[1]}")
        print(f"   - len(result): {len(result)}")

        # Intentar acceder a índices
        try:
            code = result[0]
            name_fiscal = result[1] if len(result) > 1 else 0
            print(f"   ✓ Acceso a índices exitoso: code={code}, name_fiscal={name_fiscal}")
        except IndexError as e:
            print(f"   ✗ ERROR accediendo a índices: {e}")
    else:
        print("   ✗ Cliente NO encontrado")
except Exception as e:
    print(f"   ✗ Error en consulta: {e}")

# 2. Verificar estación
print("\n2. VERIFICANDO ESTACIÓN 91:21:FD:AD:B0:B7:")
try:
    pg_cursor.execute("""
        SELECT code FROM stations WHERE code = %s LIMIT 1
    """, ('91:21:FD:AD:B0:B7',))
    result = pg_cursor.fetchone()
    if result:
        print(f"   ✓ Estación encontrada: {result[0]}")
    else:
        print("   ✗ Estación NO encontrada")
except Exception as e:
    print(f"   ✗ Error: {e}")

# 3. Verificar taxes
print("\n3. VERIFICANDO TAXES:")
try:
    pg_cursor.execute("""
        SELECT code, line FROM taxes WHERE code IN ('EX', '01', '03')
    """)
    results = pg_cursor.fetchall()
    print(f"   ✓ Encontrados {len(results)} taxes")
    for row in results:
        print(f"   - code={row[0]}, line={row[1]}, len={len(row)}")

        # Verificar que cada row tenga 2 elementos
        if len(row) < 2:
            print(f"   ✗ ERROR: Row tiene menos de 2 elementos: {row}")
        else:
            try:
                code = row[0]
                line = row[1]
                print(f"   ✓ Acceso correcto: {code} -> {line}")
            except IndexError as e:
                print(f"   ✗ ERROR accediendo: {e}")

    # Crear diccionario como lo hace el código
    try:
        tax_types_dict = {row[0]: row[1] for row in results}
        print(f"   ✓ Diccionario creado: {tax_types_dict}")
    except IndexError as e:
        print(f"   ✗ ERROR creando diccionario: {e}")
        print("   Intentando con manejo seguro...")
        tax_types_dict = {}
        for row in results:
            if len(row) >= 2:
                tax_types_dict[row[0]] = row[1]
            else:
                print(f"   ✗ Row incompleta: {row}")
        print(f"   ✓ Diccionario seguro: {tax_types_dict}")

except Exception as e:
    print(f"   ✗ Error en consulta: {e}")

# 4. Verificar products_units
print("\n4. VERIFICANDO PRODUCTS_UNITS:")
try:
    pg_cursor.execute("""
        SELECT correlative, conversion_factor FROM products_units LIMIT 5
    """)
    results = pg_cursor.fetchall()
    print(f"   ✓ Encontrados {len(results)} products_units")
    for row in results:
        print(f"   - correlative={row[0]}, conversion_factor={row[1]}, len={len(row)}")
        if len(row) < 2:
            print(f"   ✗ ERROR: Row tiene menos de 2 elementos")
except Exception as e:
    print(f"   ✗ Error: {e}")

print("\n" + "=" * 80)
print("FIN DEL DIAGNÓSTICO")
print("=" * 80)

pg_cursor.close()
pg_conn.close()
