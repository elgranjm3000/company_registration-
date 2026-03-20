#!/usr/bin/env python3
"""
Verificar qué clientes están en sync_hashes vs API REST
"""

import psycopg2
import json
import os
from api_client.customers import CustomersClient

def main():
    # Cargar configuración desde archivo
    config_file = os.path.expanduser('~/.chrystal_sync_config.json')
    if not os.path.exists(config_file):
        print("❌ No hay archivo de configuración")
        return

    with open(config_file, 'r') as f:
        config = json.load(f)

    # Conectar a PostgreSQL
    pg_conn = psycopg2.connect(
        host=config['postgres_host'],
        port=config['postgres_port'],
        database=config['postgres_database'],
        user=config['postgres_user'],
        password=config['postgres_password']
    )
    pg_cursor = pg_conn.cursor()

    # Obtener company_id desde sync_config
    pg_cursor.execute("SELECT value FROM sync_config WHERE key = 'company_id'")
    result = pg_cursor.fetchone()
    if not result:
        print("❌ No hay company_id en sync_config")
        pg_cursor.close()
        pg_conn.close()
        return

    company_id = int(result[0])
    print(f"📊 Company ID: {company_id}\n")

    # 1. Obtener clientes desde sync_hashes
    pg_cursor.execute("""
        SELECT record_key
        FROM sync_hashes
        WHERE table_name = 'customers'
          AND company_id = %s
          AND deleted_at IS NULL
        ORDER BY record_key
    """, (company_id,))

    codigos_sync_hashes = {row[0] for row in pg_cursor.fetchall()}
    print(f"✅ Clientes en sync_hashes: {len(codigos_sync_hashes)}")

    # 2. Obtener clientes desde la API REST
    # Necesitamos obtener el token primero
    print("🔐 Obteniendo token de API...")
    print("📝 Email:", config['api_email'])

    # Pedir password
    import getpass
    password = getpass.getpass("Password de la API: ")

    # Login para obtener token
    import requests
    login_response = requests.post(
        f"{config['api_url']}/auth/login",
        json={
            'email': 'admin@test.com',
            'password': 'password'
        },
        headers={
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        },
        timeout=10
    )

    if login_response.status_code != 200:
        print(f"❌ Error en login: {login_response.status_code}")
        print(f"Respuesta: {login_response.text[:500]}")
        pg_cursor.close()
        pg_conn.close()
        return

    token_data = login_response.json()
    api_token = token_data.get('token')

    if not api_token:
        print("❌ No se recibió token en login")
        pg_cursor.close()
        pg_conn.close()
        return

    api_client = CustomersClient(
        base_url=config['api_url'],
        api_key=api_token
    )

    try:
        clientes_api = list(api_client.get_all(company_id=company_id))
        codigos_api = {c.get('codigo') for c in clientes_api if c.get('codigo')}
        print(f"✅ Clientes en API REST: {len(codigos_api)}")

        # 3. Comparar
        en_hashes_no_api = codigos_sync_hashes - codigos_api
        en_api_no_hashes = codigos_api - codigos_sync_hashes

        print(f"\n{'='*70}")
        print(f"📊 RESULTADO DE LA COMPARACIÓN")
        print(f"{'='*70}")

        if en_hashes_no_api:
            print(f"\n❌ Clientes en sync_hashes PERO NO en API ({len(en_hashes_no_api)}):")
            for codigo in sorted(en_hashes_no_api):
                # Obtener datos del cliente
                pg_cursor.execute("""
                    SELECT code, description, email
                    FROM clients
                    WHERE code = %s
                """, (codigo,))
                cliente = pg_cursor.fetchone()
                if cliente:
                    print(f"   - {codigo}: {cliente[1]} | email: {cliente[2]}")
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

    finally:
        pg_cursor.close()
        pg_conn.close()

if __name__ == '__main__':
    main()
