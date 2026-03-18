#!/usr/bin/env python3
"""
Script rápido para ejecutar sincronización
Uso: python3 sync_now.py
"""

import sys
import os

# Cargar configuración
import json
with open('sync_config_api.json', 'r') as f:
    config = json.load(f)

print("SINCRONIZACIÓN - SISTEMA API")
print(f"Email: {config['company_email']}")
print()

# Pedir password
import getpass
api_password = getpass.getpass("Password: ")

# Logger simple
def log(msg, level="info"):
    print(msg)

# Ejecutar sincronización
from sync_system_api import APIAuthManager, APISyncManager

auth = APIAuthManager(config['api_url'], log)
auth.login(config['company_email'], api_password)
auth.validate_company(config['company_rif'], config['company_email'])

pg_config = {
    'host': config['postgres_host'],
    'port': int(config['postgres_port']),
    'database': config['postgres_database'],
    'user': config['postgres_user'],
    'password': config['postgres_password']
}

sync = APISyncManager(pg_config, auth, log)
sync.connect_postgresql()
sync._initialize_api_clients(config['api_url'], auth.api_token)

print("\n" + "="*70)
print("EJECUTANDO SINCRONIZACIÓN...")
print("="*70 + "\n")

result = sync.sync_all()

print("\n" + "="*70)
print("RESULTADO:")
print("="*70)
stats = result.get('stats', {})
for entity, s in stats.items():
    if s.get('created', 0) + s.get('updated', 0) + s.get('errors', 0) > 0:
        print(f"{entity}: C={s.get('created',0)} U={s.get('updated',0)} E={s.get('errors',0)}")

sync.close_postgresql_connection()
print("\n✅ Listo")
