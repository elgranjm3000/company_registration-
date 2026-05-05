#!/usr/bin/env python3
"""
Verificar si el token está actualizado para sellers y quotes
"""

from config_encryption import decrypt_config
import json

with open('/root/.chrystal_sync_config.json', 'r') as f:
    config_encrypted = json.load(f)

config = decrypt_config(config_encrypted)

# Verificar password
api_password = config.get('api_password')
print('✅ Password desencriptado:')
print(f'   Longitud: {len(api_password)} caracteres')
print(f'   Empieza con "enc:": {api_password.startswith("enc:")}')

# Hacer login para obtener un token nuevo
from sync_system_api import APIAuthManager

auth_manager = APIAuthManager(base_url=config['api_url'], logger=None)

print('\n🔐 Haciendo login...')
login_result = auth_manager.login(config['api_email'], api_password)

if not login_result.get('success'):
    print(f'❌ Login falló: {login_result.get("error")}')
    exit(1)

token = auth_manager.api_token
print(f'\n✅ Token obtenido:')
print(f'   Token: {token[:50]}...')
print(f'   Longitud: {len(token)} caracteres')

# Verificar si el token cambia cada vez
token_anterior = '21282|6oOhntjpyJIBXfW9c0zD9IGPpvOJQNaLMvQqeyxGbbfb1639'
son_diferentes = token_anterior != token[:50]
print(f'\n⚠️  IMPORTANTE: El token cambia cada vez que haces login')
print(f'   Token anterior: {token_anterior}')
print(f'   Token actual:   {token[:50]}...')
print(f'   ¿Son diferentes? {son_diferentes}')

# Validar empresa
print('\n🏢 Validando empresa...')
validate_result = auth_manager.validate_company(config['company_rif'], config['company_email'])

if not validate_result.get('success'):
    print(f'❌ Validación falló: {validate_result.get("error")}')
    exit(1)

company_id = validate_result.get('company_id')
print(f'✅ Company ID: {company_id}')

# Probar endpoint de sellers
print('\n👔 Probando endpoint /sync-batch/sellers...')
import requests

response = requests.get(
    f'{config["api_url"]}/sync-batch/sellers',
    params={'company_id': company_id},
    headers={
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    },
    timeout=10
)

print(f'Status Code: {response.status_code}')

if response.status_code == 401:
    print('❌ 401 Unauthorized - Token inválido o expirado')
    print('⚠️  Esto significa que el token NO es válido')
elif response.status_code == 403:
    print('❌ 403 Forbidden - Sin permisos')
    print('⚠️  El token es válido pero no tienes permisos para este endpoint')
elif response.status_code == 200:
    print('✅ 200 OK - Endpoint funciona')
else:
    print(f'⚠️  Código inesperado: {response.status_code}')
    print(f'Response: {response.text[:200]}')
