#!/usr/bin/env python3
"""
Test completo de mapeo de status y sincronización de seller → user
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

import psycopg2
import pymysql

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

print('='*80)
print('TEST COMPLETO DE MAPEO DE STATUS Y SINCRONIZACIÓN')
print('='*80)
print()

# 1. VERIFICAR ESTADO ANTES
print('1. ESTADO ANTES DE SINCRONIZACIÓN')
print('-'*80)

pg_conn = psycopg2.connect(**postgresql_config)
pg_cursor = pg_conn.cursor()

mysql_conn = pymysql.connect(**mysql_config)
mysql_cursor = mysql_conn.cursor()

# Obtener sellers de PostgreSQL
pg_cursor.execute("""
    SELECT s.code, s.description, s.status
    FROM sellers s
    WHERE s.code IN ('02', '04')
    ORDER BY s.code
""")
pg_sellers = pg_cursor.fetchall()

# Obtener sellers de MySQL
mysql_cursor.execute("""
    SELECT s.code, s.description, s.seller_status, u.name, u.email
    FROM sellers s
    LEFT JOIN users u ON s.user_id = u.id
    WHERE s.code IN ('02', '04')
    ORDER BY s.code
""")
mysql_sellers = mysql_cursor.fetchall()

print(f"{'Code':<6} {'PostgreSQL':<35} {'MySQL':<45}")
print('-'*80)

for pg_s in pg_sellers:
    code = pg_s[0]
    desc_pg = pg_s[1]
    status_pg = pg_s[2]

    mysql_s = next((s for s in mysql_sellers if s[0] == code), None)

    if mysql_s:
        desc_mysql = mysql_s[1]
        status_mysql = mysql_s[2]
        user_name = mysql_s[3]
        email = mysql_s[4]

        esperado = 'active' if status_pg == '01' else 'inactive'
        status_ok = '✅' if status_mysql == esperado else '❌'
        name_ok = '✅' if user_name == desc_pg else '❌'

        print(f"{code:<6} {status_ok} status={status_pg} ({desc_pg[:20]})    "
              f"{name_ok} seller_status={status_mysql} | name={user_name[:15]} | {email}")

print()

# 2. SIMULAR CAMBIO DE DESCRIPCIÓN Y STATUS
print('2. SIMULANDO CAMBIOS EN POSTGRESQL')
print('-'*80)

# Cambiar descripción del seller 02
pg_cursor.execute("UPDATE sellers SET description = 'EDGAR BLANCO MODIFICADO' WHERE code = '02'")
pg_conn.commit()
print("✅ Actualizado seller 02: description = 'EDGAR BLANCO MODIFICADO'")

# Cambiar status del seller 04
pg_cursor.execute("UPDATE sellers SET status = '01' WHERE code = '04'")
pg_conn.commit()
print("✅ Actualizado seller 04: status = '01' (de '02')")

print()

# 3. LIMPIAR HASHES Y SINCRONIZAR
print('3. SINCRONIZANDO')
print('-'*80)

from smart_sellers_sync_module import SmartSellersSyncModule

class MockApp:
    def __init__(self):
        self.company_id = 69

    def log_message(self, mensaje, nivel='info'):
        print(f'[{nivel.upper()}] {mensaje}')

app = MockApp()
sellers_sync = SmartSellersSyncModule(app)

sellers_sync.conectar_postgresql(postgresql_config)
sellers_sync.conectar_mysql(mysql_config)

resultado = sellers_sync.ejecutar_sync()

print()
print(f"Resultado: exito={resultado['exito']}, nuevos={resultado['nuevos']}, "
      f"modificados={resultado['actualizados']}, errores={resultado['errores']}")

print()

# 4. VERIFICAR ESTADO DESPUÉS
print('4. ESTADO DESPUÉS DE SINCRONIZACIÓN')
print('-'*80)

# Recargar datos de PostgreSQL y MySQL
pg_cursor.execute("""
    SELECT s.code, s.description, s.status
    FROM sellers s
    WHERE s.code IN ('02', '04')
    ORDER BY s.code
""")
pg_sellers_after = pg_cursor.fetchall()

mysql_cursor.execute("""
    SELECT s.code, s.description, s.seller_status, u.name, u.email
    FROM sellers s
    LEFT JOIN users u ON s.user_id = u.id
    WHERE s.code IN ('02', '04')
    ORDER BY s.code
""")
mysql_sellers = mysql_cursor.fetchall()

print(f"{'Code':<6} {'PostgreSQL':<35} {'MySQL':<45}")
print('-'*80)

for pg_s in pg_sellers_after:
    code = pg_s[0]
    desc_pg = pg_s[1]
    status_pg = pg_s[2]

    mysql_s = next((s for s in mysql_sellers if s[0] == code), None)

    if mysql_s:
        desc_mysql = mysql_s[1]
        status_mysql = mysql_s[2]
        user_name = mysql_s[3]
        email = mysql_s[4]

        esperado = 'active' if status_pg == '01' else 'inactive'
        status_ok = '✅' if status_mysql == esperado else '❌'
        name_ok = '✅' if user_name == desc_pg else '❌'
        desc_ok = '✅' if desc_mysql == desc_pg else '❌'

        print(f"{code:<6} {desc_ok} {desc_pg[:25]:<25} → {desc_mysql[:25]:<25}")
        print(f"       {status_ok} status={status_pg} → seller_status={status_mysql} (esperado: {esperado})")
        print(f"       {name_ok} name={user_name}")

print()

# 5. REVERTIR CAMBIOS
print('5. REVERTIENDO CAMBIOS DE TEST')
print('-'*80)

pg_cursor.execute("UPDATE sellers SET description = 'EDGAR BLANCO' WHERE code = '02'")
pg_conn.commit()
print("✅ Revertido seller 02: description = 'EDGAR BLANCO'")

pg_cursor.execute("UPDATE sellers SET status = '02' WHERE code = '04'")
pg_conn.commit()
print("✅ Revertido seller 04: status = '02'")

# Limpiar hashes
pg_cursor.execute("DELETE FROM sync_hashes WHERE table_name = 'sellers'")
pg_conn.commit()
print("✅ Limpiados hashes de sellers")

sellers_sync.cerrar()
pg_cursor.close()
pg_conn.close()
mysql_cursor.close()
mysql_conn.close()

print()
print('='*80)
print('TEST FINALIZADO')
print('='*80)
