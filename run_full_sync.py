#!/usr/bin/env python3
"""
Script para ejecutar sincronización completa
"""

import sys
import os
import getpass

# Cargar configuración
import json
with open('sync_config_api.json', 'r') as f:
    config = json.load(f)

print("="*70)
print("SINCRONIZACIÓN COMPLETA - SISTEMA API")
print("="*70)
print(f"API URL: {config['api_url']}")
print(f"Email: {config['company_email']}")
print(f"Empresa RIF: {config['company_rif']}")
print()

# Pedir password
api_password = getpass.getpass("Password de la API: ")

if not api_password:
    print("❌ Password no proporcionado")
    sys.exit(1)

# Crear logger simple
def log_func(msg, level="info"):
    if level == "error":
        print(f"❌ {msg}")
    elif level == "warning":
        print(f"⚠️  {msg}")
    else:
        print(f"ℹ️  {msg}")

# Importar módulos
from sync_system_api import APIAuthManager, APISyncManager

try:
    # Crear auth manager
    auth_manager = APIAuthManager(config['api_url'], log_func)

    # Hacer login
    print("\n🔐 Haciendo login a la API...")
    login_result = auth_manager.login(config['company_email'], api_password)

    if not login_result.get('success'):
        print(f"❌ Login falló: {login_result.get('error')}")
        sys.exit(1)

    print("✅ Login exitoso")
    print(f"   Token: {auth_manager.api_token[:20]}...")
    print(f"   Expira: {auth_manager.token_expires_at}")

    # Validar empresa
    print(f"\n🏢 Validando empresa: {config['company_rif']}")
    validation_result = auth_manager.validate_company(config['company_rif'], config['company_email'])

    if not validation_result.get('success'):
        print(f"❌ Validación falló: {validation_result.get('error')}")
        sys.exit(1)

    print("✅ Empresa validada")
    print(f"   Company ID: {auth_manager.company_id}")
    print(f"   Nombre: {validation_result.get('company', {}).get('name', 'N/A')}")

    # Crear sync manager
    postgres_config = {
        'host': config['postgres_host'],
        'port': int(config['postgres_port']),
        'database': config['postgres_database'],
        'user': config['postgres_user'],
        'password': config['postgres_password']
    }

    sync_manager = APISyncManager(postgres_config, auth_manager, log_func)

    # Conectar a PostgreSQL
    print("\n📊 Conectando a PostgreSQL...")
    if not sync_manager.connect_postgresql():
        print("❌ No se pudo conectar a PostgreSQL")
        sys.exit(1)

    print("✅ Conectado a PostgreSQL")

    # Inicializar clientes API
    print("\n🔧 Inicializando clientes API...")
    base_url = config['api_url']
    api_token = auth_manager.api_token

    if not sync_manager._initialize_api_clients(base_url, api_token):
        print("❌ No se pudieron inicializar los clientes API")
        sys.exit(1)

    print("✅ Clientes API inicializados")

    # Ejecutar sincronización completa
    print("\n" + "="*70)
    print("🔄 INICIANDO SINCRONIZACIÓN COMPLETA")
    print("="*70)

    result = sync_manager.sync_all()

    print("\n" + "="*70)
    print("📊 RESULTADO DE SINCRONIZACIÓN")
    print("="*70)

    if result.get('success'):
        print("✅ Sincronización completada exitosamente")
        stats = result.get('stats', {})
        total_created = sum(s.get('created', 0) for s in stats.values())
        total_updated = sum(s.get('updated', 0) for s in stats.values())
        total_deleted = sum(s.get('deleted', 0) for s in stats.values())
        total_errors = sum(s.get('errors', 0) for s in stats.values())

        print(f"\n📊 TOTALES:")
        print(f"   Created: {total_created}")
        print(f"   Updated: {total_updated}")
        print(f"   Deleted: {total_deleted}")
        print(f"   Errors: {total_errors}")

        print(f"\n📋 DETALLE POR ENTIDAD:")
        for entity, entity_stats in stats.items():
            if entity_stats.get('created', 0) > 0 or entity_stats.get('updated', 0) > 0 or entity_stats.get('errors', 0) > 0:
                print(f"\n{entity.upper()}:")
                print(f"   Created: {entity_stats.get('created', 0)}")
                print(f"   Updated: {entity_stats.get('updated', 0)}")
                print(f"   Deleted: {entity_stats.get('deleted', 0)}")
                print(f"   Errors: {entity_stats.get('errors', 0)}")
    else:
        print(f"❌ Sincronización falló: {result.get('error')}")

    # Cerrar conexión
    sync_manager.close_postgresql_connection()

    print("\n" + "="*70)
    if total_errors == 0:
        print("✅ SINCRONIZACIÓN COMPLETADA SIN ERRORES")
    else:
        print(f"⚠️  SINCRONIZACIÓN COMPLETADA CON {total_errors} ERRORES")
    print("="*70)

except KeyboardInterrupt:
    print("\n\n⚠️  Proceso interrumpido por el usuario")
    sys.exit(1)
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
