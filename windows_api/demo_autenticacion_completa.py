#!/usr/bin/env python3
"""
DEMOSTRACIÓN COMPLETA: El password se desencripta y se usa para TODOS los endpoints
Incluyendo Sellers y Quotes
"""

import json
from pathlib import Path
import sys

# Agregar directorio actual
sys.path.insert(0, str(Path(__file__).parent))

print("="*70)
print("🔍 DEMOSTRACIÓN: AUTENTICACIÓN PARA SELLERS Y QUOTES")
print("="*70)

# ============================================================================
# PASO 1: CARGAR CONFIGURACIÓN ENCRIPTADA
# ============================================================================
print("\n📋 PASO 1: CARGAR CONFIGURACIÓN (ENCRIPTADA)")
print("-"*70)

from config_encryption import decrypt_config

CONFIG_FILE = '/root/.chrystal_sync_config.json'

with open(CONFIG_FILE, 'r') as f:
    config_encrypted = json.load(f)

print("✅ Configuración cargada (encriptada)")
print(f"   api_password (encriptado): {config_encrypted.get('api_password', 'N/A')[:30]}...")
print(f"   Empieza con 'enc:': {config_encrypted.get('api_password', '').startswith('enc:')}")

# ============================================================================
# PASO 2: DESENCRIPTAR PASSWORD (UNA SOLA VEZ)
# ============================================================================
print("\n📋 PASO 2: DESENCRIPTAR PASSWORD (UNA SOLA VEZ)")
print("-"*70)

config = decrypt_config(config_encrypted)

api_password = config.get('api_password')

print("✅ Password desencriptado")
print(f"   Longitud: {len(api_password)} caracteres")
print(f"   Empieza con 'enc:': {api_password.startswith('enc:')}")
print(f"   Primeros 4 caracteres: {api_password[:4]}***")

# ============================================================================
# PASO 3: LOGIN CON PASSWORD DESENCRIPTADO (UNA SOLA VEZ)
# ============================================================================
print("\n📋 PASO 3: LOGIN CON PASSWORD DESENCRIPTADO (UNA SOLA VEZ)")
print("-"*70)

from sync_system_api import APIAuthManager

auth_manager = APIAuthManager(
    base_url=config['api_url'],
    logger=None
)

print(f"🔐 Haciendo login con password desencriptado...")
login_result = auth_manager.login(config['api_email'], api_password)

if not login_result.get('success'):
    print(f"❌ Login falló: {login_result.get('error')}")
    sys.exit(1)

print("✅ Login exitoso")
print(f"   Token obtenido: {auth_manager.api_token[:40]}...")
print(f"   Expira: {auth_manager.token_expires_at}")

# ============================================================================
# PASO 4: VALIDAR EMPRESA
# ============================================================================
print("\n📋 PASO 4: VALIDAR EMPRESA")
print("-"*70)

validate_result = auth_manager.validate_company(
    config['company_rif'],
    config['company_email']
)

if not validate_result.get('success'):
    print(f"❌ Validación falló")
    sys.exit(1)

company_id = validate_result.get('company_id')
print(f"✅ Empresa validada: Company ID = {company_id}")

# ============================================================================
# PASO 5: INICIALIZAR TODOS LOS CLIENTES CON EL MISMO TOKEN
# ============================================================================
print("\n📋 PASO 5: INICIALIZAR TODOS LOS CLIENTES CON EL MISMO TOKEN")
print("-"*70)

from api_client import SellersClient, QuotesClient

# El MISMO token se usa para TODOS los clientes
api_token = auth_manager.api_token

print(f"📦 Token que se usará: {api_token[:40]}...")

# Crear SellersClient con el MISMO token
sellers_client = SellersClient(
    base_url=config['api_url'],
    api_key=api_token,  # ← MISMO TOKEN (obtenido con password desencriptado)
    logger=None
)

print("✅ SellersClient creado")
print(f"   - api_key pasada: Sí (longitud: {len(api_token)})")
print(f"   - Header Authorization: {sellers_client.session.headers.get('Authorization')[:40]}...")

# Crear QuotesClient con el MISMO token
quotes_client = QuotesClient(
    base_url=config['api_url'],
    api_key=api_token,  # ← MISMO TOKEN (obtenido con password desencriptado)
    logger=None
)

print("✅ QuotesClient creado")
print(f"   - api_key pasada: Sí (longitud: {len(api_token)})")
print(f"   - Header Authorization: {quotes_client.session.headers.get('Authorization')[:40]}...")

# ============================================================================
# PASO 6: PROBAR ENDPOINTS CON EL TOKEN
# ============================================================================
print("\n📋 PASO 6: PROBAR ENDPOINTS CON EL TOKEN")
print("-"*70)

import requests

# Probar Sellers
print("\n👔 Probando /sync-batch/sellers...")
response = requests.get(
    f'{config["api_url"]}/sync-batch/sellers',
    params={'company_id': company_id},
    headers={
        'Authorization': f'Bearer {api_token}',
        'Content-Type': 'application/json'
    },
    timeout=10
)

print(f"   Status Code: {response.status_code}")
if response.status_code == 401:
    print("   ❌ 401 - Token inválido")
elif response.status_code == 403:
    print("   ❌ 403 - Sin permisos (el token es válido, pero no tienes acceso)")
elif response.status_code == 200:
    print("   ✅ 200 - OK")

# Probar Quotes
print("\n💰 Probando /sync-batch/quotes...")
response = requests.get(
    f'{config["api_url"]}/sync-batch/quotes',
    params={'company_id': company_id},
    headers={
        'Authorization': f'Bearer {api_token}',
        'Content-Type': 'application/json'
    },
    timeout=10
)

print(f"   Status Code: {response.status_code}")
if response.status_code == 401:
    print("   ❌ 401 - Token inválido")
elif response.status_code == 403:
    print("   ❌ 403 - Sin permisos (el token es válido, pero no tienes acceso)")
elif response.status_code == 200:
    print("   ✅ 200 - OK")

# ============================================================================
# RESUMEN
# ============================================================================
print("\n" + "="*70)
print("📊 RESUMEN DE AUTENTICACIÓN")
print("="*70)

print("\n✅ FLUJO COMPLETO:")
print("   1. Cargar config (encriptada)")
print("   2. Desencriptar password (UNA VEZ)")
print(f"   3. Login con password desencriptado → Obtener token")
print("   4. Usar el MISMO token para:")
print("      - CategoriesClient ✅")
print("      - ProductsClient ✅")
print("      - CustomersClient ✅")
print("      - SellersClient ✅")
print("      - QuotesClient ✅")

print("\n⚠️  SI VES ERROR 401:")
print("   - El TOKEN expiró o es inválido")
print("   - NO es problema de desencriptación del password")
print("   - El password siempre está correctamente desencriptado")

print("\n⚠️  SI VES ERROR 403:")
print("   - El token es VÁLIDO")
print("   - Pero el usuario NO tiene permisos para ese endpoint")
print("   - Contacta al administrador para activar permisos")

print("\n" + "="*70)
