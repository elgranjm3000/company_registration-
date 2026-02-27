#!/usr/bin/env python3
"""
Diagnóstico: Identificar productos que no se sincronizan
"""

import psycopg2
import pymysql
from dotenv import load_dotenv
import os

load_dotenv()

pg_conn = psycopg2.connect(
    host=os.getenv('DB_HOST'),
    database=os.getenv('DB_DATABASE'),
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

company_id = 87

print('🔍 PRODUCTOS EN POSTGRESQL PERO NO EN MYSQL')
print('=' * 80)

# Obtener productos que están en PostgreSQL pero no en MySQL
query = """
    SELECT DISTINCT ON (a.code)
        a.code,
        a.description,
        a.short_name,
        a.department,
        COALESCE(c.total_stock, 0) AS stock
    FROM products a
    LEFT JOIN (
        SELECT product_code, SUM(stock) as total_stock
        FROM products_stock
        GROUP BY product_code
    ) c ON a.code = c.product_code
    WHERE a.code IS NOT NULL AND a.code != ''
    AND a.status = '01'
    ORDER BY a.code
"""

pg_cursor.execute(query)
todos_pg = pg_cursor.fetchall()

# Productos en MySQL
mysql_cursor.execute('SELECT code FROM products WHERE company_id = %s', (company_id,))
codes_mysql = set(row[0] for row in mysql_cursor.fetchall())

# Encontrar los que faltan
faltantes = [p for p in todos_pg if p[0] not in codes_mysql]

print(f'Total encontrados: {len(faltantes)} productos')
print()

if faltantes:
    print('Lista de productos que faltan en MySQL:')
    for i, p in enumerate(faltantes, 1):
        code, description, short_name, department, stock = p
        dept = department if department else 'NULL'
        desc = description if description else 'NULL'
        print(f'{i:2}. Code: {code:12} | Dept: {dept:10} | Desc: {desc[:40]}')

    print()
    print('Verificando si tienen categoría válida...')
    print()

    for i, p in enumerate(faltantes[:10], 1):
        code, description, short_name, department, stock = p

        # Verificar si la categoría existe
        mysql_cursor.execute(
            'SELECT id FROM categories WHERE company_id = %s AND name = %s',
            (company_id, department)
        )
        cat = mysql_cursor.fetchone()

        if cat:
            print(f'✅ {code}: Categoría "{department}" EXISTE (ID: {cat[0]})')
        else:
            print(f'❌ {code}: Categoría "{department}" NO EXISTE - ESTE ES EL PROBLEMA')

else:
    print('✅ Todos los productos están sincronizados')

pg_cursor.close()
pg_conn.close()
mysql_cursor.close()
