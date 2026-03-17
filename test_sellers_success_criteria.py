#!/usr/bin/env python3
"""
Test del criterio de éxito en sincronización de sellers
Verifica que errores individuales no marquen toda la sync como fallida
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from smart_sellers_sync_module import SmartSellersSyncModule

# Clase mock para simular el app
class MockApp:
    def __init__(self):
        self.company_id = 69

    def log_message(self, mensaje, nivel='info'):
        print(f'[{nivel.upper()}] {mensaje}')

app = MockApp()
sellers_sync = SmartSellersSyncModule(app)

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

print('='*80)
print('TEST DE CRITERIO DE ÉXITO CON ERRORES INDIVIDUALES')
print('='*80)
print()

if not sellers_sync.conectar_postgresql(postgresql_config):
    print('❌ No se pudo conectar a PostgreSQL')
    sys.exit(1)

if not sellers_sync.conectar_mysql(mysql_config):
    print('❌ No se pudo conectar a MySQL')
    sellers_sync.cerrar()
    sys.exit(1)

print('1. PRIMERA SYNC (debe crear sellers y marcar como exitoso)')
print('-'*80)
resultado1 = sellers_sync.ejecutar_sync()
print()
print(f'Resultado: exito={resultado1["exito"]}, nuevos={resultado1["nuevos"]}, modificados={resultado1["actualizados"]}, errores={resultado1["errores"]}')
print(f'✅ Éxito: {resultado1["exito"]} (debe ser True)')
print()

print('2. SEGUNDA SYNC (debe omitir todos y marcar como exitoso)')
print('-'*80)
resultado2 = sellers_sync.ejecutar_sync()
print()
print(f'Resultado: exito={resultado2["exito"]}, nuevos={resultado2["nuevos"]}, modificados={resultado2["actualizados"]}, errores={resultado2["errores"]}')
print(f'✅ Éxito: {resultado2["exito"]} (debe ser True aunque no hubo cambios)')
print()

sellers_sync.cerrar()

print('='*80)
print('TEST FINALIZADO')
print('='*80)
