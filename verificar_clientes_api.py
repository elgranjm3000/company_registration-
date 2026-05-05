#!/usr/bin/env python3
"""
Verificar si los clientes existen en la API REST
"""

import requests
import json

API_URL = "https://chrystal.com.ve/mobile/public/api"
API_EMAIL = "admin@test.com"
API_PASSWORD = "admin12345"  # Reemplaza con tu password real
COMPANY_ID = 107  # O el que corresponda

def verificar_clientes_api(clientes_codigo):
    """Verificar si los clientes existen en la API"""

    # Login
    session = requests.Session()

    login_response = session.post(
        f"{API_URL}/auth/login",
        json={
            'email': API_EMAIL,
            'password': API_PASSWORD,
            'device_name': 'verificar_clientes'
        },
        timeout=30
    )

    if login_response.status_code != 200:
        print(f"❌ Error de login: {login_response.status_code}")
        return

    login_data = login_response.json()
    if not login_data.get('success'):
        print(f"❌ Login falló: {login_data.get('message')}")
        return

    token = login_data['data']['token']

    # Buscar cada cliente
    print("="*70)
    print("VERIFICANDO CLIENTES EN LA API")
    print("="*70)

    for codigo in clientes_codigo:
        print(f"\n📋 Buscando cliente: {codigo}")

        # Buscar por document_number
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
                    print(f"   ✅ Cliente ENCONTRADO en API:")
                    for customer in customers:
                        print(f"      - ID: {customer.get('id')}")
                        print(f"      - Código: {customer.get('codigo')}")
                        print(f"      - Nombre: {customer.get('name')}")
                        print(f"      - Documento: {customer.get('document_number')}")
                        print(f"      - Estado: {customer.get('status')}")
                else:
                    print(f"   ❌ Cliente NO ENCONTRADO en API")
                    print(f"      Respuesta: {data.get('message', 'No encontrado')}")
        else:
            print(f"   ❌ Error buscando cliente: {search_response.status_code}")
            print(f"      {search_response.text[:200]}")

if __name__ == '__main__':
    # Clientes que se intentaron insertar
    clientes_codigo = ['V5455655', 'V5554454']

    verificar_clientes_api(clientes_codigo)
