#!/usr/bin/env python3
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
    host=os.getenv('DB_HOST_MYSQL'),
    user=os.getenv('DB_USER_MYSQL'),
    password=os.getenv('DB_PASSWORD_MYSQL'),
    database=os.getenv('DB_PORT_DATABASE_MYSQL')
)
mysql_cursor = mysql_conn.cursor()

print('=' * 80)
print('VERIFICANDO SINCRONIZACIÓN DE ESTADOS MYSQL → POSTGRESQL')
print('=' * 80)
print()

# Obtener quotes de MySQL
mysql_cursor.execute('SELECT quote_number, status FROM quotes')
quotes_mysql = mysql_cursor.fetchall()

print(f'Total de quotes en MySQL: {len(quotes_mysql)}')
print()

sincronizados = 0
desincronizados = 0
no_existen_en_pg = 0

for quote_number, status_mysql in quotes_mysql:
    # Buscar en PostgreSQL
    pg_cursor.execute("""
        SELECT pending, correlative
        FROM public.sales_operation
        WHERE document_no = %s AND operation_type = 'BUDGET'
    """, (quote_number,))
    result = pg_cursor.fetchone()

    if result:
        pending_pg, correlative = result
        expected_status_mysql = 'approved' if not pending_pg else 'rejected'

        # El status en MySQL puede ser diferente (draft, sent, etc.)
        # Solo verificamos si approved/rejected coincide con pending
        if status_mysql in ['approved', 'rejected']:
            match = '✅' if status_mysql == expected_status_mysql else '❌'
            if status_mysql != expected_status_mysql:
                desincronizados += 1
            else:
                sincronizados += 1
            print(f'{match} Quote #{quote_number}: MySQL={status_mysql:10} | PG pending={str(pending_pg):5} | esperado={expected_status_mysql:10}')
        else:
            print(f'ℹ️  Quote #{quote_number}: MySQL={status_mysql:10} | PG pending={str(pending_pg):5} (no es approved/rejected)')
    else:
        no_existen_en_pg += 1
        print(f'⚠️  Quote #{quote_number}: NO EXISTE EN POSTGRESQL')

print()
print('RESUMEN')
print('-' * 80)
print(f'Total de quotes en MySQL: {len(quotes_mysql)}')
print(f'Sincronizados correctamente: {sincronizados}')
print(f'Desincronizados: {desincronizados}')
print(f'No existen en PostgreSQL: {no_existen_en_pg}')

pg_cursor.close()
pg_conn.close()
mysql_cursor.close()
mysql_conn.close()
print()
print('=' * 80)
