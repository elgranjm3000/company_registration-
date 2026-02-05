#!/usr/bin/env python3
"""
Demostración: Guardado de hashes en sync_hashes
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

import psycopg2
from smart_sellers_sync_module import SmartSellersSyncModule

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
    'port': int(os.getenv('REMOTE_DB_PORT', 3306)),
    'database': os.getenv('DB_PORT_DATABASE_MYSQL'),
    'user': os.getenv('DB_USER_MYSQL'),
    'password': os.getenv('DB_PASSWORD_MYSQL')
}

class MockApp:
    def __init__(self):
        self.company_id = 69

    def log_message(self, mensaje, nivel='info'):
        if nivel == 'debug':
            return
        print(f'[{nivel.upper()}] {mensaje}')

print('='*80)
print('DEMOSTRACIÓN: GUARDADO EN SYNC_HASHES')
print('='*80)
print()

# Conectar a PostgreSQL
conn = psycopg2.connect(**postgresql_config)
cursor = conn.cursor()

print('1. ESTADO INICIAL: Limpiar hashes')
print('-'*80)
cursor.execute("DELETE FROM sync_hashes WHERE table_name = 'sellers'")
conn.commit()
print('✅ Hashes limpiados')
print()

print('2. PRIMERA SINCRONIZACIÓN')
print('-'*80)
app = MockApp()
sellers_sync = SmartSellersSyncModule(app)
sellers_sync.conectar_postgresql(postgresql_config)
sellers_sync.conectar_mysql(mysql_config)

resultado1 = sellers_sync.ejecutar_sync()
print(f'Resultado: nuevos={resultado1["nuevos"]}, modificados={resultado1["actualizados"]}')
print()

print('3. VERIFICAR HASHES GUARDADOS')
print('-'*80)
cursor.execute("""
    SELECT table_name, record_key, record_hash, updated_at
    FROM sync_hashes
    WHERE table_name = 'sellers'
    ORDER BY record_key
""")
hashes = cursor.fetchall()

if hashes:
    print(f'✅ Se guardaron {len(hashes)} hashes en sync_hashes:')
    for h in hashes:
        print(f'   - Table: {h[0]}, Key: {h[1]}, Hash: {h[2][:16]}..., Updated: {h[3]}')
else:
    print('❌ No se encontraron hashes')
print()

print('4. SEGUNDA SINCRONIZACIÓN (debe omitir todos)')
print('-'*80)
resultado2 = sellers_sync.ejecutar_sync()
print(f'Resultado: nuevos={resultado2["nuevos"]}, modificados={resultado2["actualizados"]}, omitidos (sin cambios)')
print()

print('5. CAMBIAR UN SELLER Y VOLVER A SINCRONIZAR')
print('-'*80)
cursor.execute("UPDATE sellers SET description = 'EDGAR BLANCO TEST' WHERE code = '02'")
conn.commit()
print('✅ Seller 02 modificado')

resultado3 = sellers_sync.ejecutar_sync()
print(f'Resultado: nuevos={resultado3["nuevos"]}, modificados={resultado3["actualizados"]}')

# Revertir cambio
cursor.execute("UPDATE sellers SET description = 'EDGAR BLANCO' WHERE code = '02'")
conn.commit()
print('✅ Cambio revertido')
print()

print('6. VERIFICAR QUE EL HASH SE ACTUALIZÓ')
print('-'*80)
cursor.execute("""
    SELECT table_name, record_key, record_hash, updated_at
    FROM sync_hashes
    WHERE table_name = 'sellers' AND record_key = '02'
""")
hash_02 = cursor.fetchone()

if hash_02:
    print(f'✅ Hash del seller 02 actualizado:')
    print(f'   - Key: {hash_02[1]}')
    print(f'   - Hash: {hash_02[2][:16]}...')
    print(f'   - Updated: {hash_02[3]}')
print()

sellers_sync.cerrar()
cursor.close()
conn.close()

print('='*80)
print('DEMOSTRACIÓN COMPLETADA')
print('='*80)
