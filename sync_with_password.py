#!/usr/bin/env python3
"""
Ejecutar sincronización pasando el password como argumento
Uso: python3 sync_with_password.py TU_PASSWORD
"""
import sys
from config_encryption import encrypt_password
import json

if len(sys.argv) < 2:
    print("Uso: python3 sync_with_password.py PASSWORD_API")
    sys.exit(1)

api_password = sys.argv[1]

# Guardar password temporalmente en config
with open('sync_config_api.json', 'r') as f:
    config = json.load(f)

encrypted_password = encrypt_password(api_password)
config['api_password_encrypted'] = encrypted_password

with open('sync_config_api.json', 'w') as f:
    json.dump(config, f, indent=2)

print(f"✅ Password configurado. Ejecutando sincronización...\n")

# Ahora ejecutar el sincronizador
import sync_system_api
sync_system_api.main()

