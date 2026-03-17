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

# Ver estructura completa de products_units
cursor.execute("""
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_name = 'products_units'
    ORDER BY ordinal_position
""")

print('Estructura de products_units:')
for idx, (col, type_) in enumerate(cursor.fetchall(), 1):
    print(f'  {idx}. {col}: {type_}')

# Ver datos de TESTVES
print('\nDatos de TESTVES en products_units:')
cursor.execute("""
    SELECT * FROM products_units WHERE product_code = 'TESTVES'
""")
row = cursor.fetchone()
if row:
    columnas = [
        'correlative', 'unit', 'product_code', 'main_unit', 'conversion_factor',
        'unit_type', 'show_in_screen', 'is_for_buy', 'is_for_sale',
        'unitary_cost', 'calculated_cost', 'average_cost',
        'perc_waste_cost', 'perc_handling_cost', 'perc_operating_cost',
        'perc_additional_cost', 'maximum_price', 'offer_price', 'higher_price',
        'minimum_price'
    ]
    print('\nCampos de precio:')
    for i, col in enumerate(columnas):
        if 'price' in col.lower() or 'cost' in col.lower():
            valor = row[i]
            print(f'  {col}: {valor}')

# Ver datos de productos que SÍ tienen maximum_price
print('\n\nProductos que tienen maximum_price (ejemplos):')
cursor.execute("""
    SELECT pu.product_code, pu.maximum_price, pu.higher_price, pu.offer_price
    FROM products_units pu
    WHERE pu.maximum_price IS NOT NULL
    LIMIT 5
""")
print('product_code | maximum_price | higher_price | offer_price')
for row in cursor.fetchall():
    print(f'{row[0]:12} | {row[1]:13} | {row[2]:12} | {row[3]:11}')

cursor.close()
conn.close()
