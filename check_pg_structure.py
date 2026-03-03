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

# Ver columnas de la tabla products
cursor.execute("""
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_name = 'products'
    ORDER BY ordinal_position
""")

print('Columnas de la tabla products en PostgreSQL:')
for col, type_ in cursor.fetchall():
    print(f'  - {col}: {type_}')

cursor.close()
conn.close()
