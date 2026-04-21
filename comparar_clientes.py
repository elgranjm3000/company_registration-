#!/usr/bin/env python3
"""
Obtener clientes del API y comparar con sync_hashes
"""

import json
import os
import requests

def main():
    # Cargar configuración
    config_file = os.path.expanduser('~/.chrystal_sync_config.json')
    with open(config_file, 'r') as f:
        config = json.load(f)

    api_url = config['api_url']
    company_id = 95

    # 1. Login para obtener token
    print("🔐 Haciendo login...")
    login_response = requests.post(
        f"{api_url}/auth/login",
        json={
            'email': 'admin@test.com',
            'password': 'password'
        },
        headers={
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0'
        },
        timeout=10
    )

    if login_response.status_code == 409:
        # Sesión activa existe, intentar logout
        print("⚠️  Sesión activa detectada, intentando logout...")

        # Necesitamos hacer logout pero no tenemos el token
        # Intentar login con force=true o parámetro similar
        print("❌ No se puede cerrar la sesión sin el token")
        print("💡 Solución: Espera a que expire la sesión o ciérrala manualmente")
        return

    if login_response.status_code != 200:
        print(f"❌ Error en login: {login_response.status_code}")
        print(f"Respuesta: {login_response.text[:500]}")
        return

    token_data = login_response.json()
    api_token = token_data.get('token')

    if not api_token:
        print("❌ No se recibió token en login")
        return

    print(f"✅ Token obtenido: {api_token[:20]}...")

    # 2. Obtener clientes del API
    print(f"\n📥 Obteniendo clientes del API (company_id={company_id})...")

    headers = {
        'Authorization': f'Bearer {api_token}',
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0'
    }

    customers_response = requests.get(
        f"{api_url}/customers",
        params={'company_id': company_id},
        headers=headers,
        timeout=30
    )

    if customers_response.status_code != 200:
        print(f"❌ Error obteniendo clientes: {customers_response.status_code}")
        print(f"Respuesta: {customers_response.text[:500]}")
        return

    api_data = customers_response.json()
    api_customers = api_data.get('data', [])

    print(f"✅ Clientes en API REST: {len(api_customers)}")

    # Guardar códigos del API
    codigos_api = {c.get('codigo') for c in api_customers if c.get('codigo')}

    # 3. Leer códigos de sync_hashes
    with open('/tmp/clientes_sync_hashes.txt', 'r') as f:
        lines = f.readlines()
        # Skip header and footer
        codigos_sync_hashes = set()
        for line in lines[2:-1]:  # Skip header (2 lines) and footer (1 line)
            code = line.strip()
            if code:
                codigos_sync_hashes.add(code)

    print(f"✅ Clientes en sync_hashes: {len(codigos_sync_hashes)}")

    # 4. Comparar
    en_hashes_no_api = codigos_sync_hashes - codigos_api
    en_api_no_hashes = codigos_api - codigos_sync_hashes

    print(f"\n{'='*70}")
    print(f"📊 RESULTADO DE LA COMPARACIÓN")
    print(f"{'='*70}")

    if en_hashes_no_api:
        print(f"\n❌ Clientes en sync_hashes PERO NO en API ({len(en_hashes_no_api)}):")
        for codigo in sorted(en_hashes_no_api):
            print(f"   - {codigo}")
    else:
        print(f"\n✅ Todos los clientes de sync_hashes están en la API")

    if en_api_no_hashes:
        print(f"\n⚠️  Clientes en API PERO NO en sync_hashes ({len(en_api_no_hashes)}):")
        for codigo in sorted(en_api_no_hashes)[:10]:
            print(f"   - {codigo}")
        if len(en_api_no_hashes) > 10:
            print(f"   ... y {len(en_api_no_hashes) - 10} más")
    else:
        print(f"✅ No hay clientes extra en la API")

    print(f"\n{'='*70}")
    print(f"📊 RESUMEN")
    print(f"{'='*70}")
    print(f"En sync_hashes: {len(codigos_sync_hashes)}")
    print(f"En API REST:    {len(codigos_api)}")
    print(f"Faltan en API:  {len(en_hashes_no_api)}")
    print(f"Sobrantes API:  {len(en_api_no_hashes)}")
    print(f"{'='*70}\n")

if __name__ == '__main__':
    main()
