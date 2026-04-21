#!/usr/bin/env python3
"""
Guardar password de la API encriptado en el config
"""
import json
from config_encryption import encrypt_password

# Leer config actual
with open('sync_config_api.json', 'r') as f:
    config = json.load(f)

# Solicitar password
password = input("Password de la API: ")

# Encriptar usando el sistema correcto
encrypted_password = encrypt_password(password)

# Guardar en config
config['api_password_encrypted'] = encrypted_password

# Escribir config
with open('sync_config_api.json', 'w') as f:
    json.dump(config, f, indent=2)

print("\n✅ Password guardado encriptado en sync_config_api.json")
print("Ahora puedes ejecutar: python3 sync_system_api.py --mode sync\n")
