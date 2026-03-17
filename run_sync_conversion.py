#!/usr/bin/env python3
"""
Script para ejecutar sincronización completa y probar conversión de VES a USD
"""

import sys
sys.path.insert(0, '/home/muentes/company_registration')

from dotenv import load_dotenv
import os
load_dotenv()

from smart_sync_complete import SmartSyncComplete

# Configuración de PostgreSQL
postgresql_config = {
    'host': os.getenv('DB_HOST'),
    'database': os.getenv('DB_DATABASE'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD')
}

# Configuración de MySQL
mysql_config = {
    'host': '91.238.160.176',
    'port': 3306,
    'database': 'chrystal_movil',
    'user': 'chrystal_app',
    'password': 'muentes123.',
    'charset': 'utf8mb4'
}

# Crear un mock app
class MockApp:
    pass

# Crear instancia de SmartSyncComplete
print("🔄 Inicializando SmartSyncComplete...")
sync = SmartSyncComplete(
    app=MockApp(),
    postgresql_config=postgresql_config,
    mysql_config=mysql_config,
    company_rif='J502741283',
    company_email='multiserviciosleblanc@gmail.com',
    company_name='Multiservicios Leblanc'
)

# Ejecutar sincronización completa
print("🚀 Ejecutando sincronización completa...")
print("   Esto sincronizará products, customers, sellers, categories y quotes")
print()

resultado = sync.ejecutar_sync_completa()

if resultado:
    print("\n✅ Sincronización completada exitosamente")
else:
    print("\n❌ Sincronización falló")

sys.exit(0 if resultado else 1)
