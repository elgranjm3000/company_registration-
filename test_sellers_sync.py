#!/usr/bin/env python3
import psycopg2
import pymysql
import hashlib
from dotenv import load_dotenv
import os

load_dotenv()

def safe_float(value):
    """Convertir valor a float de forma segura"""
    try:
        return float(value) if value is not None else 0.0
    except:
        return 0.0

def generar_hash_seller(seller):
    """Generar hash MD5 para un vendedor"""
    try:
        campos = (
            str(seller[0]) if seller[0] else '',  # seller_code
            str(seller[1]) if seller[1] else '',  # description
            str(seller[2]) if seller[2] else '',  # status
            str(safe_float(seller[3])),           # percent_sales
            str(safe_float(seller[4])),           # percent_receivable
            str(seller[5]) if seller[5] else '',  # inkeeper
            str(seller[6]) if seller[6] else '',  # user_code
            str(safe_float(seller[7])),           # percent_gerencial_debit_note
            str(safe_float(seller[8])),           # percent_gerencial_credit_note
            str(safe_float(seller[9])),           # percent_returned_check
            str(seller[10]) if seller[10] else '' # email
        )
        datos = "|".join(campos)
        return hashlib.md5(datos.encode('utf-8')).hexdigest()
    except Exception as e:
        return hashlib.md5(str(seller[0]).encode()).hexdigest()

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

company_id = 27  # O desde configuración

print('=' * 80)
print('TEST DE SINCRONIZACIÓN DE SELLERS CON sync_hashes')
print('=' * 80)
print()

# 1. Cargar hashes existentes
print('1. CARGANDO HASHES EXISTENTES DE sync_hashes')
print('-' * 80)
pg_cursor.execute("""
    SELECT record_key, record_hash
    FROM sync_hashes
    WHERE table_name = 'sellers'
      AND company_id = %s
""", (company_id,))

hashes_existentes = {}
for row in pg_cursor.fetchall():
    hashes_existentes[row[0]] = row[1]

print(f'✅ Hashes cargados: {len(hashes_existentes)} sellers previos')
print()

# 2. Obtener sellers de PostgreSQL
print('2. OBTENIENDO SELLERS DE POSTGRESQL')
print('-' * 80)
pg_cursor.execute("""
    SELECT
        s.code as seller_code,
        s.description,
        s.status,
        s.percent_sales,
        s.percent_receivable,
        s.inkeeper,
        s.user_code,
        s.percent_gerencial_debit_note,
        s.percent_gerencial_credit_note,
        s.percent_returned_check,
        u.email
    FROM sellers s
    LEFT JOIN users u ON s.user_code = u.code
    WHERE s.user_code IS NOT NULL
      AND u.email IS NOT NULL
      AND u.email != ''
      AND u.email != '@'
    ORDER BY s.code
""")

sellers = pg_cursor.fetchall()

if not sellers:
    print('❌ No se encontraron sellers en PostgreSQL')
else:
    print(f'✅ Se encontraron {len(sellers)} sellers en PostgreSQL')

print()

# 3. Analizar cambios
print('3. ANALIZANDO CAMBIOS')
print('-' * 80)

sellers_nuevos = 0
sellers_modificados = 0
sellers_omitidos = 0

for seller in sellers:
    seller_code = seller[0]

    # Generar hash actual
    hash_actual = generar_hash_seller(seller)
    hash_anterior = hashes_existentes.get(seller_code, '')

    # Analizar
    if not hash_anterior:
        sellers_nuevos += 1
        estado = 'NUEVO'
    elif hash_actual == hash_anterior:
        sellers_omitidos += 1
        estado = 'OMITIDO (sin cambios)'
    else:
        sellers_modificados += 1
        estado = 'MODIFICADO'

    # Mostrar primeros 10 de cada categoría
    if (estado == 'NUEVO' and sellers_nuevos <= 10) or \
       (estado == 'MODIFICADO' and sellers_modificados <= 10) or \
       (estado == 'OMITIDO (sin cambios)' and sellers_omitidos <= 10):
        print(f'   {estado:25} | Seller: {seller_code:15} | Hash: {hash_actual[:16]}...')

# Mostrar resumen si hay más de 10 en alguna categoría
if sellers_nuevos > 10:
    print(f'   ... y {sellers_nuevos - 10} sellers nuevos más')
if sellers_modificados > 10:
    print(f'   ... y {sellers_modificados - 10} sellers modificados más')
if sellers_omitidos > 10:
    print(f'   ... y {sellers_omitidos - 10} sellers omitidos más')

print()
print('4. VERIFICANDO SELLERS EN MYSQL')
print('-' * 80)

mysql_cursor.execute("SELECT code, description FROM sellers LIMIT 10")
sellers_mysql = mysql_cursor.fetchall()

if sellers_mysql:
    print(f'Sellers en MySQL (primeros 10):')
    for s in sellers_mysql:
        print(f'   Code: {s[0]:15} | Description: {s[1]}')
else:
    print('⚠️  No hay sellers en MySQL')

print()
print('RESUMEN')
print('=' * 80)
print(f'Total de sellers en PostgreSQL: {len(sellers)}')
print(f'Sellers nuevos (sin hash previo): {sellers_nuevos}')
print(f'Sellers modificados (hash cambió): {sellers_modificados}')
print(f'Sellers omitidos (sin cambios): {sellers_omitidos}')
print(f'Sellers totales a sincronizar: {sellers_nuevos + sellers_modificados}')
print()
print(f'Eficiencia: {sellers_omitidos} de {len(sellers)} sellers ({100*sellers_omitidos//len(sellers) if sellers else 0}%) no necesitan sincronización')
print('=' * 80)

pg_cursor.close()
pg_conn.close()
mysql_cursor.close()
mysql_conn.close()
