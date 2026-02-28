#!/usr/bin/env python3
"""
Test directo: Ejecutar solo el método de eliminación de productos
"""

import sys
sys.path.insert(0, '/home/muentes/company_registration')

from dotenv import load_dotenv
import os
import psycopg2
import pymysql

load_dotenv()

print("=" * 80)
print("🧪 TEST DIRECTO: _eliminar_productos_mysql_cuando_faltan_en_postgresql")
print("=" * 80)
print()

# Configuración PostgreSQL
postgresql_config = {
    'host': os.getenv('DB_HOST'),
    'database': 'nuevaprueba',
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD')
}

# Configuración MySQL
mysql_config = {
    'host': '91.238.160.176',
    'port': 3306,
    'database': 'chrystal_movil',
    'user': 'chrystal_app',
    'password': 'muentes123.'
}

# Importar SmartSyncComplete
from smart_sync_complete import SmartSyncComplete

# Crear instancia
class MockApp:
    def log_message(self, msg, tipo):
        print(f"[{tipo.upper()}] {msg}")

app = MockApp()

sync = SmartSyncComplete(
    app=app,
    postgresql_config=postgresql_config,
    mysql_config=mysql_config,
    company_rif='J505261940',
    company_email='elgranjm3000@gmail.com',
    company_name='',
    progress_callback=None,
    log_callback=app.log_message
)

# Conectar
print("📋 Conectando a bases de datos...")
if not sync._conectar_bases_datos():
    print("❌ Error conectando")
    sys.exit(1)

print("✅ Conectado")
print()

# Obtener company_id
print("📋 Obteniendo company_id...")
if not sync._obtener_company_id():
    print("❌ Error obteniendo company_id")
    sys.exit(1)

print(f"✅ Company ID: {sync.company_id}")
print()

# Verificar estado ANTES
print("📋 ESTADO ANTES:")
print("-" * 80)

mysql_conn = pymysql.connect(**mysql_config)
mysql_cursor = mysql_conn.cursor()
mysql_cursor.execute("SELECT id, code, name FROM products WHERE code = %s AND company_id = %s",
                    ('03', sync.company_id))
producto = mysql_cursor.fetchone()
if producto:
    print(f"   ❌ code=03 EXISTE en MySQL (ID={producto[0]}, name={producto[2]})")
else:
    print(f"   ✅ code=03 NO EXISTE en MySQL")

print()

# Ejecutar eliminación
print("📋 EJECUTANDO: _eliminar_productos_mysql_cuando_faltan_en_postgresql()")
print("-" * 80)
sync._eliminar_productos_mysql_cuando_faltan_en_postgresql()
print()

# Verificar estado DESPUÉS
print("📋 ESTADO DESPUÉS:")
print("-" * 80)

mysql_cursor.execute("SELECT id, code, name FROM products WHERE code = %s AND company_id = %s",
                    ('03', sync.company_id))
producto = mysql_cursor.fetchone()
if producto:
    print(f"   ❌ code=03 AÚN EXISTE en MySQL (ID={producto[0]}, name={producto[2]}) - NO SE ELIMINÓ")
else:
    print(f"   ✅ code=03 FUE ELIMINADO de MySQL")

print()
print("=" * 80)
print("✅ TEST COMPLETADO")
print("=" * 80)

mysql_cursor.close()
mysql_conn.close()
