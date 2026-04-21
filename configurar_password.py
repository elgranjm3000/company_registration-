#!/usr/bin/env python3
"""
Configurar password de la API encriptado
"""
import json
import base64
import os

# Leer config actual
with open('sync_config_api.json', 'r') as f:
    config = json.load(f)

# Solicitar password
password = input("Password de la API: ")

# Encriptar (simple base64 por ahora - el sistema usa un método más seguro)
encoded_password = base64.b64encode(password.encode()).decode()

# Guardar en config
config['api_password_encrypted'] = encoded_password

# Escribir config
with open('sync_config_api.json', 'w') as f:
    json.dump(config, f, indent=2)

print("✅ Password guardado en sync_config_api.json")
