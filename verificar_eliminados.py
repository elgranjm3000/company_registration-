#!/usr/bin/env python3
"""
Verificar productos que faltan en MySQL
"""

import psycopg2
import pymysql
from dotenv import load_dotenv
import os

load_dotenv()

# PostgreSQL
pg_conn = psycopg2.connect(
    host=os.getenv('DB_HOST'),
    database=os.getenv('DB_DATABASE'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD')
)
pg_cursor = pg_conn.cursor()

# MySQL
mysql_conn = pymysql.connect(
    host='91.238.160.176',
    port=3306,
    database='chrystal_movil',
    user='chrystal_app',
    password='muentes123.',
    charset='utf8mb4'
)
mysql_cursor = mysql_conn.cursor()

company_id = 87

print('🔍 PRODUCTOS EN POSTGRESQL PERO NO EN MYSQL')
print('=' * 80)

# Productos en PostgreSQL
pg_cursor.execute("SELECT code, description, status FROM products WHERE code IS NOT NULL AND code != '' LIMIT 20")
pg_products = pg_cursor.fetchall()

# Productos en MySQL
mysql_cursor.execute('SELECT code FROM products WHERE company_id = %s', (company_id,))
mysql_codes = set(row[0] for row in mysql_cursor.fetchall())

# Productos que faltan en MySQL
faltantes = [p for p in pg_products if p[0] not in mysql_codes]

print(f'Total productos en PostgreSQL: {len(pg_products)}')
print(f'Total productos en MySQL: {len(mysql_codes)}')
print(f'Productos en PostgreSQL pero NO en MySQL: {len(faltantes)}')

if faltantes:
    print()
    print('Lista:')
    for code, desc, status in faltantes[:10]:
        print(f'   {code:15} | Status: {status} | {desc[:40]}')

print()
print('🔍 SYNC_HASHES DE ESTOS PRODUCTOS:')
print('=' * 80)

if faltantes:
    for code, _, _ in faltantes[:5]:
        pg_cursor.execute('SELECT deleted_at, synced_at FROM sync_hashes WHERE table_name = %s AND record_key = %s', ('products', code))
        hash_data = pg_cursor.fetchone()
        if hash_data:
            deleted, synced = hash_data
            print(f'   {code:15} | deleted_at: {deleted} | synced_at: {synced}')
        else:
            print(f'   {code:15} | ❌ NO ESTÁ EN SYNC_HASHES')
else:
    print('   Todos los productos de PostgreSQL están en MySQL')

pg_cursor.close()
pg_conn.close()
mysql_cursor.close()
mysql_conn.close()
