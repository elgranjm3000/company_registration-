"""
Verificar quote sincronizado en PostgreSQL
"""
import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()

pg_config = {
    'host': os.getenv('DB_HOST'),
    'database': os.getenv('DB_DATABASE'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD')
}

conn = psycopg2.connect(**pg_config)
cursor = conn.cursor()

print('🔍 VERIFICANDO QUOTE SINCRONIZADO EN POSTGRESQL')
print('─'*80)

# Buscar el quote de prueba
cursor.execute("""
    SELECT correlative, document_no, client_name, total_amount, pending, emission_date
    FROM sales_operation
    WHERE document_no LIKE 'TEST%'
    ORDER BY emission_date DESC
    LIMIT 1
""")
result = cursor.fetchone()

if result:
    correlative, doc_no, client_name, total_amount, pending, emission_date = result
    print('✅ Quote encontrado en PostgreSQL:')
    print(f'   Correlativo:    {correlative}')
    print(f'   Document No:    {doc_no}')
    print(f'   Cliente:        {client_name}')
    print(f'   Total:          {total_amount:.2f} USD')
    print(f'   Pending:        {pending}')
    print(f'   Fecha Emisión:  {emission_date}')

    # Verificar monedas
    cursor.execute("""
        SELECT coin_code, total_amount, total_net
        FROM sales_operation_coins
        WHERE correlative = %s
    """, (correlative,))
    coins = cursor.fetchall()

    print('\n   💰 Monedas:')
    for coin_code, amount, net in coins:
        print(f'      Moneda {coin_code}: {net:.2f} (Total: {amount:.2f})')

    print('\n✅ SINCRONIZACIÓN COMPLETADA CON ÉXITO')
else:
    print('⚠️ Quote no encontrado en PostgreSQL')

cursor.close()
conn.close()

print('\n' + '─'*80)
