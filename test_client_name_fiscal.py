#!/usr/bin/env python3
"""
Test para verificar que client_name_fiscal se obtiene correctamente
desde clients.name_fiscal y se inserta en sales_operation
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

import psycopg2
import pymysql

print('='*80)
print('TEST: CLIENT_NAME_FISCAL EN SALES_OPERATION')
print('='*80)
print()

# Conectar a PostgreSQL
pg_conn = psycopg2.connect(
    host=os.getenv('DB_HOST'),
    database=os.getenv('DB_DATABASE'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD')
)
pg_cursor = pg_conn.cursor()

# Conectar a MySQL
mysql_conn = pymysql.connect(
    host=os.getenv('DB_HOST_MYSQL'),
    port=int(os.getenv('REMOTE_DB_PORT', 3306)),
    database=os.getenv('DB_PORT_DATABASE_MYSQL'),
    user=os.getenv('DB_USER_MYSQL'),
    password=os.getenv('DB_PASSWORD_MYSQL')
)
mysql_cursor = mysql_conn.cursor()

print('1. VERIFICAR CAMPO name_fiscal EN TABLA clients')
print('-'*80)
pg_cursor.execute("""
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_name = 'clients'
    AND column_name = 'name_fiscal'
""")
result = pg_cursor.fetchone()

if result:
    print(f"✅ Campo EXISTE: name_fiscal ({result[1]})")
else:
    print("❌ Campo name_fiscal NO EXISTE en la tabla clients")
    print("   Se necesita agregar el campo a la tabla:")
    print("   ALTER TABLE clients ADD COLUMN name_fiscal VARCHAR(255)")

print()

print('2. VERIFICAR CAMPO client_name_fiscal EN TABLA sales_operation')
print('-'*80)
pg_cursor.execute("""
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_name = 'sales_operation'
    AND column_name = 'client_name_fiscal'
""")
result = pg_cursor.fetchone()

if result:
    print(f"✅ Campo EXISTE: client_name_fiscal ({result[1]})")
else:
    print("❌ Campo client_name_fiscal NO EXISTE en la tabla sales_operation")
    print("   Se necesita agregar el campo a la tabla:")
    print("   ALTER TABLE sales_operation ADD COLUMN client_name_fiscal VARCHAR(255)")

print()

print('3. OBTENER UN CLIENTE DE MYSQL PARA PROBAR')
print('-'*80)
mysql_cursor.execute("""
    SELECT id, name, document_number
    FROM customers
    WHERE document_number IS NOT NULL
    AND document_number != ''
    LIMIT 1
""")
customer = mysql_cursor.fetchone()

if not customer:
    print("❌ No hay customers en MySQL con document_number")
    pg_cursor.close()
    pg_conn.close()
    mysql_cursor.close()
    mysql_conn.close()
    sys.exit(1)

customer_id, customer_name, customer_doc = customer
print(f"✅ Customer encontrado: ID={customer_id}, Name={customer_name}, Doc={customer_doc}")

print()

print('4. VERIFICAR QUE EL CLIENTE EXISTE EN POSTGRESQL (clients)')
print('-'*80)
pg_cursor.execute(
    "SELECT code, description, name_fiscal FROM clients WHERE code = %s",
    (customer_doc,)
)
client_pg = pg_cursor.fetchone()

if not client_pg:
    print(f"❌ Cliente NO EXISTE en PostgreSQL (code={customer_doc})")
    print(f"   Insertando cliente de prueba...")

    # Insertar cliente de prueba
    pg_cursor.execute("""
        INSERT INTO clients (
            code, description, name_fiscal, address, email, phone, contact,
            country, province, city, client_type, area_sales,
            seller, client_group
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (code) DO NOTHING
    """, (
        customer_doc,
        customer_name,
        f"{customer_name} (Fiscal)",  # name_fiscal de prueba
        'Dirección de prueba',
        'test@test.com',
        '0414-1234567',
        customer_name,
        '00',
        '00',
        '00',
        '01',
        '00',
        '00',
        '00'
    ))
    pg_conn.commit()

    # Recargar
    pg_cursor.execute(
        "SELECT code, description, name_fiscal FROM clients WHERE code = %s",
        (customer_doc,)
    )
    client_pg = pg_cursor.fetchone()

if client_pg:
    code_pg, desc_pg, name_fiscal_pg = client_pg
    print(f"✅ Cliente en PostgreSQL:")
    print(f"   code: {code_pg}")
    print(f"   description: {desc_pg}")
    print(f"   name_fiscal: {name_fiscal_pg}")

print()

print('5. SIMULAR LÓGICA DE OBTENCIÓN DE name_fiscal')
print('-'*80)
# Simular la lógica del código
pg_cursor.execute(
    "SELECT name_fiscal FROM clients WHERE code = %s",
    (customer_doc,)
)
client_fiscal_result = pg_cursor.fetchone()

if client_fiscal_result and client_fiscal_result[0]:
    client_name_fiscal = client_fiscal_result[0]
    print(f"✅ name_fiscal obtenido: {client_name_fiscal}")
else:
    client_name_fiscal = customer_name
    print(f"⚠️ name_fiscal es NULL, usando customer_name: {client_name_fiscal}")

print()

print('6. VERIFICAR sales_operation RECIENTES (si existen)')
print('-'*80)
pg_cursor.execute("""
    SELECT
        correlative,
        client_code,
        client_name,
        client_name_fiscal,
        emission_date
    FROM sales_operation
    WHERE client_code = %s
    ORDER BY emission_date DESC
    LIMIT 3
""")
sales_ops = pg_cursor.fetchall()

if sales_ops:
    print(f"✅ Encontradas {len(sales_ops)} sales_operation para este cliente:")
    for so in sales_ops:
        correlative, client_code, client_name, client_name_fiscal_so, emission_date = so
        fiscal_match = "✅" if client_name_fiscal_so == name_fiscal_pg else "❌"
        print(f"   Correlative: {correlative}")
        print(f"   client_code: {client_code}")
        print(f"   client_name: {client_name}")
        print(f"   client_name_fiscal: {client_name_fiscal_so} {fiscal_match}")
        print(f"   emission_date: {emission_date}")
        print()
else:
    print("ℹ️ No hay sales_operation para este cliente")

print()

print('7. RESUMEN')
print('-'*80)
print(f"Cliente MySQL: {customer_name} ({customer_doc})")
print(f"Cliente PostgreSQL description: {desc_pg if client_pg else 'N/A'}")
print(f"Cliente PostgreSQL name_fiscal: {name_fiscal_pg if client_pg else 'N/A'}")
print(f"Valor que se insertaría en client_name_fiscal: {client_name_fiscal}")

if client_name_fiscal == name_fiscal_pg:
    print("✅ CORRECTO: client_name_fiscal coincide con clients.name_fiscal")
else:
    if name_fiscal_pg:
        print("❌ ERROR: client_name_fiscal NO coincide con clients.name_fiscal")
    else:
        print("⚠️ ADVERTENCIA: name_fiscal es NULL en clients")

print()

pg_cursor.close()
pg_conn.close()
mysql_cursor.close()
mysql_conn.close()

print('='*80)
print('TEST FINALIZADO')
print('='*80)
