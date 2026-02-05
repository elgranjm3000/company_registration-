#!/usr/bin/env python3
"""
Test de conexión para el módulo de sellers
"""
import pymysql
import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()

print('=' * 80)
print('TEST DE CONEXIÓN PARA SELLERS')
print('=' * 80)
print()

# Configuración de PostgreSQL
postgresql_config = {
    'host': os.getenv('DB_HOST'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'database': os.getenv('DB_DATABASE'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD')
}

print('1. CONFIGURACIÓN POSTGRESQL')
print('-' * 80)
for key, value in postgresql_config.items():
    if key == 'password':
        print(f'   {key}: {"*" * len(str(value))}')
    else:
        print(f'   {key}: {value}')
print()

# Configuración de MySQL
mysql_config = {
    'host': os.getenv('DB_HOST_MYSQL'),
    'port': os.getenv('REMOTE_DB_PORT', 3306),  # Puede ser None o string
    'database': os.getenv('DB_PORT_DATABASE_MYSQL'),
    'user': os.getenv('DB_USER_MYSQL'),
    'password': os.getenv('DB_PASSWORD_MYSQL')
}

print('2. CONFIGURACIÓN MYSQL (ANTES DE LIMPIAR)')
print('-' * 80)
for key, value in mysql_config.items():
    if key == 'password':
        print(f'   {key}: {"*" * len(str(value))}')
    else:
        print(f'   {key}: {value} (tipo: {type(value).__name__})')
print()

# Limpiar puerto (igual que el código del módulo)
connect_params = mysql_config.copy()
if 'port' in connect_params and (connect_params['port'] is None or connect_params['port'] == 0):
    del connect_params['port']
    print('   ℹ️  Puerto eliminado (es None o 0)')
elif 'port' in connect_params and isinstance(connect_params['port'], str):
    try:
        connect_params['port'] = int(connect_params['port'])
        print(f'   ℹ️  Puerto convertido a int: {connect_params["port"]}')
    except:
        del connect_params['port']
        print('   ℹ️  Puerto eliminado (no convertible a int)')

print()
print('3. CONFIGURACIÓN MYSQL (DESPUÉS DE LIMPIAR)')
print('-' * 80)
for key, value in connect_params.items():
    if key == 'password':
        print(f'   {key}: {"*" * len(str(value))}')
    else:
        print(f'   {key}: {value} (tipo: {type(value).__name__})')
print()

# Probar conexión PostgreSQL
print('4. PROBAR CONEXIÓN POSTGRESQL')
print('-' * 80)
try:
    pg_conn = psycopg2.connect(**postgresql_config)
    pg_cursor = pg_conn.cursor()
    pg_cursor.execute("SELECT version()")
    version = pg_cursor.fetchone()[0]
    print(f'✅ Conectado a PostgreSQL')
    print(f'   Versión: {version[:50]}...')
    pg_cursor.close()
    pg_conn.close()
except Exception as e:
    print(f'❌ Error conectando PostgreSQL: {e}')

print()

# Probar conexión MySQL
print('5. PROBAR CONEXIÓN MYSQL')
print('-' * 80)
try:
    mysql_conn = pymysql.connect(**connect_params)
    mysql_cursor = mysql_conn.cursor()
    mysql_cursor.execute("SELECT VERSION()")
    version = mysql_cursor.fetchone()[0]
    print(f'✅ Conectado a MySQL')
    print(f'   Versión: {version}')
    mysql_cursor.close()
    mysql_conn.close()
except Exception as e:
    print(f'❌ Error conectando MySQL: {e}')
    print(f'   Tipo de error: {type(e).__name__}')

print()
print('=' * 80)
print('TEST FINALIZADO')
print('=' * 80)
