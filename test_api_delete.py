#!/usr/bin/env python3
"""
Test si los clientes eliminados aún existen en la API
"""

import requests

API_URL = "https://chrystal.com.ve/mobile/public/api"
API_EMAIL = "admin@test.com"
API_PASSWORD = "admin12345"
COMPANY_ID = 107

# Clientes a verificar
clientes_codigo = ['V54544554', 'V5454566', 'V5554454', 'V5455655']

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
    exit(1)

login_data = login_response.json()
if not login_data.get('success'):
    print(f"❌ Login falló: {login_data.get('message')}")
    exit(1)

token = login_data['data']['token']

print("="*70)
print("VERIFICANDO SI LOS CLIENTES ELIMINADOS AÚN EXISTEN EN LA API")
print("="*70)

for codigo in clientes_codigo:
    print(f"\n📋 Buscando cliente: {codigo}")
    
    search_response = session.get(
        f"{API_URL}/sync-batch/customers",
        params={
            'company_id': COMPANY_ID,
            'search': codigo
        },
        headers={
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        },
        timeout=30
    )
    
    if search_response.status_code == 200:
        data = search_response.json()
        if data.get('success'):
            customers = data.get('data', {}).get('data', [])
            
            if customers:
                print(f"   ✅ Cliente AÚN EXISTE en la API:")
                for customer in customers:
                    print(f"      - ID: {customer.get('id')}")
                    print(f"      - Código: {customer.get('codigo')}")
                    print(f"      - Documento: {customer.get('document_number')}")
                    print(f"      - Nombre: {customer.get('name')}")
                    print(f"      - Estado: {customer.get('status')}")
            else:
                print(f"   ✅ Cliente NO EXISTE en la API (fue eliminado correctamente)")
        else:
            print(f"   ❌ Error: {data.get('message', 'Error desconocido')}")
    else:
        print(f"   ❌ Error buscando cliente: {search_response.status_code}")
        print(f"      {search_response.text[:200]}")

print("\n" + "="*70)
print("CONCLUSIÓN:")
print("="*70)
print("Si los clientes AÚN EXISTEN en la API, el endpoint DELETE no está funcionando.")
print("Si NO EXISTEN, el problema es otro.")
