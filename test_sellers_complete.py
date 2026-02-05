#!/usr/bin/env python3
"""
Test completo de sincronización de sellers con el módulo SmartSellersSyncModule
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

# Importar el módulo
from smart_sellers_sync_module import SmartSellersSyncModule

print('=' * 80)
print('TEST COMPLETO DE SINCRONIZACIÓN DE SELLERS')
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
        # Usar company_id que existe en MySQL (ID 69: Pruebas Nathaly)
        self.company_id = 69

    def log_message(self, mensaje, nivel="info"):
        """Simula el método de logging del app"""
        print(f"[{nivel.upper()}] {mensaje}")

# Crear app mock
app = MockApp()

# Crear módulo de sellers
sellers_sync = SmartSellersSyncModule(app)

print('1. CONFIGURACIÓN')
print('-' * 80)
print(f"PostgreSQL: {postgresql_config['host']}:{postgresql_config['port']}/{postgresql_config['database']}")
print(f"MySQL: {mysql_config['host']}:{mysql_config.get('port', 'por defecto')}/{mysql_config['database']}")
print()

print('2. CONECTANDO A POSTGRESQL')
print('-' * 80)
if not sellers_sync.conectar_postgresql(postgresql_config):
    print("❌ No se pudo conectar a PostgreSQL")
    sys.exit(1)
print()

print('3. CONECTANDO A MYSQL')
print('-' * 80)
if not sellers_sync.conectar_mysql(mysql_config):
    print("❌ No se pudo conectar a MySQL")
    sellers_sync.cerrar()
    sys.exit(1)
print()

print('4. EJECUTANDO SINCRONIZACIÓN')
print('-' * 80)
print()

resultado = sellers_sync.ejecutar_sync()

print()
print('5. RESULTADO')
print('-' * 80)
print(f"Éxito: {resultado['exito']}")
print(f"Nuevos: {resultado['nuevos']}")
print(f"Actualizados: {resultado['actualizados']}")
print(f"Errores: {resultado['errores']}")
print()

# Cerrar conexiones
sellers_sync.cerrar()

print('6. VERIFICACIÓN FINAL EN MYSQL')
print('-' * 80)

import pymysql

mysql_conn = pymysql.connect(
    host=mysql_config['host'],
    user=mysql_config['user'],
    password=mysql_config['password'],
    database=mysql_config['database']
)
mysql_cursor = mysql_conn.cursor()

# Ver usuarios sellers
mysql_cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'seller'")
users_count = mysql_cursor.fetchone()[0]
print(f"Usuarios sellers en MySQL.users: {users_count}")

if users_count > 0:
    mysql_cursor.execute("""
        SELECT id, email, name, status
        FROM users WHERE role = 'seller'
        ORDER BY id
    """)
    users = mysql_cursor.fetchall()
    print(f"\nUsuarios creados:")
    for u in users:
        print(f"   ID {u[0]}: {u[1]} - {u[2]} ({u[3]})")

print()

# Ver sellers
mysql_cursor.execute("SELECT COUNT(*) FROM sellers")
sellers_count = mysql_cursor.fetchone()[0]
print(f"Sellers en MySQL.sellers: {sellers_count}")

if sellers_count > 0:
    mysql_cursor.execute("""
        SELECT s.id, s.code, s.description, s.status,
               u.email, s.percent_sales
        FROM sellers s
        JOIN users u ON s.user_id = u.id
        ORDER BY s.code
    """)
    sellers = mysql_cursor.fetchall()
    print(f"\nSellers creados:")
    for s in sellers:
        print(f"   Code {s[1]}: {s[2]} | Email: {s[4]} | Status: {s[3]} | Percent: {s[5]}%")

mysql_cursor.close()
mysql_conn.close()

print()
print('=' * 80)
print('TEST FINALIZADO')
print('=' * 80)
