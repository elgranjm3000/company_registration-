#!/usr/bin/env python3
import psycopg2
import pymysql
from dotenv import load_dotenv
import os

load_dotenv()

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
    user=os.getenv('DB_USER_MYSQL'),
    password=os.getenv('DB_PASSWORD_MYSQL'),
    database=os.getenv('DB_PORT_DATABASE_MYSQL')
)
mysql_cursor = mysql_conn.cursor()

print('=' * 80)
print('TEST DE SINCRONIZACIÓN DE ESTADOS DE QUOTES')
print('=' * 80)
print()

# 1. Obtener sales_operation BUDGET de PostgreSQL
print('1. OBTENIENDO BUDGETS DE POSTGRESQL')
print('-' * 80)

query_pg = """
SELECT
    so.document_no,
    so.pending,
    so.correlative
FROM public.sales_operation so
WHERE so.operation_type = %s
ORDER BY so.correlative
LIMIT 10
"""

pg_cursor.execute(query_pg, ('BUDGET',))
operations = pg_cursor.fetchall()

if not operations:
    print('❌ No se encontraron budgets en PostgreSQL')
else:
    print(f'✅ Se encontraron budgets (mostrando primeros 10):')
    print()
    for op in operations:
        document_no, pending, correlative = op
        status_str = 'APPROVED' if not pending else 'REJECTED'
        print(f'   Doc: {str(document_no):12} | Pending: {str(pending):5} | Status MySQL debería ser: {status_str}')

print()
print('2. VERIFICANDO ESTADO ACTUAL EN MYSQL')
print('-' * 80)

quotes_en_mysql = 0
quotes_desincronizados = 0

for op in operations:
    document_no, pending, correlative = op

    # Buscar el quote en MySQL
    query_mysql = 'SELECT id, quote_number, status FROM quotes WHERE quote_number = %s LIMIT 1'
    mysql_cursor.execute(query_mysql, (str(document_no),))
    quote = mysql_cursor.fetchone()

    if quote:
        quotes_en_mysql += 1
        quote_id, quote_number, current_status = quote
        expected_status = 'approved' if not pending else 'rejected'
        match = '✅' if current_status == expected_status else '❌'
        if current_status != expected_status:
            quotes_desincronizados += 1
        print(f'   {match} Quote #{document_no}: status="{current_status:10}" | esperado="{expected_status:10}"')
    else:
        print(f'   ⚠️  Quote #{document_no}: NO EXISTE EN MYSQL')

print()
print('3. SIMULANDO ACTUALIZACIÓN')
print('-' * 80)

# Tomar el primer budget como ejemplo
if operations:
    test_op = operations[0]
    document_no, pending, correlative = test_op

    new_status = 'approved' if not pending else 'rejected'

    print(f'   Probando con quote #{document_no}')
    print(f'   Pending en PostgreSQL: {pending}')
    print(f'   Status a establecer en MySQL: "{new_status}"')
    print()

    update_mysql = """
    UPDATE quotes
    SET status = %s, updated_at = NOW()
    WHERE quote_number = %s
    """

    mysql_cursor.execute(update_mysql, (new_status, str(document_no)))
    affected_rows = mysql_cursor.rowcount
    mysql_conn.commit()

    print(f'   Filas afectadas: {affected_rows}')

    if affected_rows > 0:
        print('   ✅ ACTUALIZACIÓN EXITOSA')

        # Verificar el nuevo estado
        mysql_cursor.execute(query_mysql, (str(document_no),))
        updated = mysql_cursor.fetchone()
        if updated:
            _, _, new_status_db = updated
            print(f'   Nuevo estado en MySQL: "{new_status_db}"')
    else:
        print('   ❌ NO SE ACTUALIZÓ (el quote no existe en MySQL o ya tenía ese status)')

print()
print('RESUMEN')
print('-' * 80)
print(f'Total de budgets en PostgreSQL: {len(operations)} (mostrados)')
print(f'Total de quotes en MySQL: {quotes_en_mysql}')
print(f'Quotes desincronizados: {quotes_desincronizados}')

pg_cursor.close()
pg_conn.close()
mysql_cursor.close()
mysql_conn.close()

print()
print('=' * 80)
