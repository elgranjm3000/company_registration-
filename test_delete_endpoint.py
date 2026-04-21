#!/usr/bin/env python3
"""
Test directo del endpoint DELETE de customers
"""

import requests
import json

API_URL = "https://chrystal.com.ve/mobile/public/api"
API_EMAIL = "admin@test.com"
API_PASSWORD = "admin12345"  # ¿Cuál es el password correcto?
COMPANY_ID = 107

# Login
session = requests.Session()
login_response = session.post(
    f"{API_URL}/auth/login",
    json={
        'email': API_EMAIL,
        'password': API_PASSWORD,
        'device_name': 'test_delete'
    },
    timeout=30
)

if login_response.status_code != 200:
    print(f"❌ Error de login: {login_response.status_code}")
    print(f"Respuesta: {login_response.text}")
    exit(1)

login_data = login_response.json()
if not login_data.get('success'):
    print(f"❌ Login falló: {login_data.get('message')}")
    exit(1)

token = login_data['data']['token']

print("="*70)
print("TEST DEL ENDPOINT DELETE /api/sync-batch/customers")
print("="*70)

# Test DELETE con V54544554
print("\n📋 Enviando DELETE request...")

delete_response = session.delete(
    f"{API_URL}/sync-batch/customers",
    headers={
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    },
    json={
        'company_id': COMPANY_ID,
        'documents': ['V54544554']
    },
    timeout=30
)

print(f"\nStatus Code: {delete_response.status_code}")
print(f"Response Headers:")
for key, value in delete_response.headers.items():
    print(f"  {key}: {value}")

print(f"\nResponse Body:")
try:
    response_json = delete_response.json()
    print(json.dumps(response_json, indent=2, ensure_ascii=False))
    
    if delete_response.status_code == 200:
        print(f"\n✅ Cliente eliminado: {response_json.get('deleted', 0)}")
    else:
        print(f"\n❌ Error al eliminar cliente")
        
except Exception as e:
    print(f"  {delete_response.text}")

