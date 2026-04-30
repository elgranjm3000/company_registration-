#!/usr/bin/env python3
import sys
sys.path.insert(0, 'windows_api')

# Importar dependencias
import psycopg2
from config_encryption import decrypt_config
import json
import os
from sync.quotes_sync import QuotesSync

# Cargar configuración
CONFIG_FILE = os.path.join(os.path.expanduser('~'), '.chrystal_sync_config.json')
with open(CONFIG_FILE, 'r') as f:
    config = json.load(f)
config = decrypt_config(config)

# Conectar a PostgreSQL
pg_conn = psycopg2.connect(
    host=config['postgres_host'],
    port=config['postgres_port'],
    database=config['postgres_database'],
    user=config['postgres_user'],
    password=config['postgres_password']
)
pg_cursor = pg_conn.cursor()

company_id = config.get('company_rif', '')

# Importar y crear QuotesClient
from api_client.quotes import QuotesClient
quotes_client = QuotesClient(
    base_url=config['api_url'],
    api_key='test_key',  # Placeholder
    logger=lambda msg, level: print(f'[{level.upper()}] {msg}')
)

# Crear QuotesSync
quote_sync = QuotesSync(pg_conn, pg_cursor, company_id, quotes_client)

# Obtener cotización #58 de la API
print('Obteniendo cotización #58 de la API...')
import requests
api_url = config['api_url']
url = f"{api_url}/sync-batch/quotes/58"
response = requests.get(
    url,
    headers={'Authorization': 'Bearer test'},
    timeout=10
)

if response.status_code == 200:
    quote = response.json()
    print(f"Cotización obtenida: {quote.get('id')}")
    print(f"Items: {len(quote.get('items', []))}")

    # Intentar sincronizar
    print('\nIntentando sincronizar...')
    try:
        quote_sync._sync_quote_to_postgres(quote)
        print('✅ Sincronización exitosa')
    except Exception as e:
        print(f'❌ Error: {e}')
        import traceback
        traceback.print_exc()
else:
    print(f"Error obteniendo cotización: {response.status_code}")

pg_cursor.close()
pg_conn.close()
