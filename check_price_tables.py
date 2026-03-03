#!/usr/bin/env python3
import psycopg2
import json

with open('.sync_config.json', 'r') as f:
    config = json.load(f)

conn = psycopg2.connect(
    host=config['postgres_host'],
    database=config['postgres_database'],
    user=config['postgres_user'],
    password=config['postgres_password']
)
cursor = conn.cursor()

# Buscar tablas que tengan 'price' o 'cost' en el nombre
cursor.execute("""
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = 'public'
    AND (table_name LIKE '%price%' OR table_name LIKE '%cost%' OR table_name LIKE '%unit%')
    ORDER BY table_name
""")

print('Tablas relacionadas con precios/costos/unidades:')
for (table,) in cursor.fetchall():
    print(f'  - {table}')

# Ver estructura de products_units
print('\nEstructura de products_units:')
cursor.execute("""
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_name = 'products_units'
    ORDER BY ordinal_position
""")
for col, type_ in cursor.fetchall():
    print(f'  - {col}: {type_}')

# Ver un producto de ejemplo con sus precios
print('\nEjemplo: Producto con coin=01')
cursor.execute("""
    SELECT p.code, p.description, p.coin
    FROM products p
    WHERE p.coin = '01'
    LIMIT 1
""")
ejemplo = cursor.fetchone()
if ejemplo:
    code, desc, coin = ejemplo
    print(f'Producto: {code} - {desc} (coin={coin})')

    # Buscar sus precios en products_units
    cursor.execute("""
        SELECT unit, price, cost
        FROM products_units
        WHERE product_code = %s
    """, (code,))
    print('Precios en products_units:')
    for unit, price, cost in cursor.fetchall():
        print(f'  Unit {unit}: price={price}, cost={cost}')
else:
    print('No hay productos con coin=01')

cursor.close()
conn.close()
