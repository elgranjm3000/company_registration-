#!/usr/bin/env python3
"""
Test de detección de cambios en sellers con hash (sin password)
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from smart_sellers_sync_module import SmartSellersSyncModule

print('=' * 80)
print('TEST DE DETECCIÓN DE CAMBIOS EN SELLERS')
print('=' * 80)
print()

# Configuraciones
postgresql_config = {
    'host': os.getenv('DB_HOST'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'database': os.getenv('DB_DATABASE'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD')
}

mysql_config = {
    'host': os.getenv('DB_HOST_MYSQL'),
    'port': os.getenv('REMOTE_DB_PORT', 3306),
    'database': os.getenv('DB_PORT_DATABASE_MYSQL'),
    'user': os.getenv('DB_USER_MYSQL'),
    'password': os.getenv('DB_PASSWORD_MYSQL')
}

# Clase mock para simular el app
class MockApp:
    def __init__(self):
        self.company_id = 69

    def log_message(self, mensaje, nivel="info"):
        """Simula el método de logging del app"""
        print(f"[{nivel.upper()}] {mensaje}")

# Crear app mock
app = MockApp()

# Crear módulo de sellers
sellers_sync = SmartSellersSyncModule(app)

print('1. PRIMERA SINCRONIZACIÓN (sin hashes previos)')
print('-' * 80)

if not sellers_sync.conectar_postgresql(postgresql_config):
    print("❌ No se pudo conectar a PostgreSQL")
    sys.exit(1)

if not sellers_sync.conectar_mysql(mysql_config):
    print("❌ No se pudo conectar a MySQL")
    sellers_sync.cerrar()
    sys.exit(1)

resultado1 = sellers_sync.ejecutar_sync()
print()
print(f"Resultado 1ª sincronización: Nuevos={resultado1['nuevos']}, Modificados={resultado1['actualizados']}")

print()
print('2. SEGUNDA SINCRONIZACIÓN (con hashes - debe omitir todos)')
print('-' * 80)

resultado2 = sellers_sync.ejecutar_sync()
print()
print(f"Resultado 2ª sincronización: Nuevos={resultado2['nuevos']}, Modificados={resultado2['actualizados']}, Omitidos (deben ser todos)")

print()
print('3. VERIFICANDO HASHES EN sync_hashes')
print('-' * 80)

import psycopg2
from dotenv import load_dotenv
load_dotenv()

pg_conn = psycopg2.connect(
    host=os.getenv('DB_HOST'),
    database=os.getenv('DB_DATABASE'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD')
)
pg_cursor = pg_conn.cursor()

pg_cursor.execute("""
    SELECT table_name, record_key, record_hash
    FROM sync_hashes
    WHERE table_name = 'sellers'
    ORDER BY record_key
""")

hashes = pg_cursor.fetchall()

if hashes:
    print(f"Hashes encontrados: {len(hashes)}")
    for h in hashes:
        print(f"   {h[1]}: {h[2][:16]}...")
else:
    print("No se encontraron hashes")

pg_cursor.close()
pg_conn.close()

sellers_sync.cerrar()

print()
print('=' * 80)
print('TEST FINALIZADO')
print('=' * 80)
