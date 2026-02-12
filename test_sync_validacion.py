#!/usr/bin/env python3
"""
Test del método _obtener_company_id() de smart_sync_complete.py
Verifica la validación cruzada:
1. acceso (MySQL): RIF y email coincidentes
2. company (PostgreSQL): email existe
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

# Importar clase SmartSyncComplete
from smart_sync_complete import SmartSyncComplete

# Configuración PostgreSQL
postgresql_config = {
    'host': os.getenv('DB_HOST'),
    'database': os.getenv('DB_DATABASE'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD')
}

# Configuración MySQL
mysql_config = {
    'host': os.getenv('DB_HOST_MYSQL'),
    'port': 3306,
    'database': os.getenv('DB_PORT_DATABASE_MYSQL'),
    'user': os.getenv('DB_USER_MYSQL'),
    'password': os.getenv('DB_PASSWORD_MYSQL')
}

# Datos de empresa (del .env)
company_rif = os.getenv('RIF')
company_email = os.getenv('EMAIL')
company_name = os.getenv('COMPANY_NOMBRE')

print("=" * 70)
print("🧪 TEST: _obtener_company_id() de SmartSyncComplete")
print("=" * 70)
print(f"📋 RIF: {company_rif}")
print(f"📧 Email: {company_email}")
print(f"🏢 Nombre: {company_name}")
print()

# Clase mock para el callback
class MockApp:
    def __init__(self):
        self.logs = []

    def log_callback(self, message, level="info"):
        self.logs.append((level, message))
        print(f"[{level.upper()}] {message}")

try:
    # Crear instancia de SmartSyncComplete
    app = MockApp()

    print("🔦 Creando instancia de SmartSyncComplete...")
    sync = SmartSyncComplete(
        app=app,
        postgresql_config=postgresql_config,
        mysql_config=mysql_config,
        company_rif=company_rif,
        company_email=company_email,
        company_name=company_name,
        progress_callback=None
    )

    print("✅ Instancia creada")
    print()

    # Conectar a bases de datos
    print("🔌 Conectando a bases de datos...")
    if not sync._conectar_bases_datos():
        print("❌ Error conectando a bases de datos")
        sys.exit(1)

    print("✅ Conexiones establecidas")
    print()

    # Ejecutar método _obtener_company_id
    print("=" * 70)
    print("🔍 Ejecutando _obtener_company_id()...")
    print("=" * 70)
    print()

    resultado = sync._obtener_company_id()

    print()
    print("=" * 70)
    if resultado:
        print("✅ ÉXITO: company_id obtenido correctamente")
        print("=" * 70)
        print(f"   Company ID: {sync.company_id}")
        print()
        print("Validaciones realizadas:")
        for level, msg in app.logs:
            if "acceso" in msg.lower() or "company" in msg.lower():
                print(f"   [{level}] {msg}")
    else:
        print("❌ ERROR: No se pudo obtener company_id")
        print("=" * 70)
        print()
        print("Logs de error:")
        for level, msg in app.logs:
            if level in ["error", "warning"]:
                print(f"   [{level}] {msg}")

    # Cerrar conexiones
    sync._cerrar_conexiones()

except Exception as e:
    print()
    print("=" * 70)
    print(f"❌ EXCEPCIÓN: {type(e).__name__}")
    print(f"   {str(e)}")
    print("=" * 70)
    import traceback
    traceback.print_exc()
    sys.exit(1)
