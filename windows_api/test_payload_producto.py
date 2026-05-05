#!/usr/bin/env python3
"""
Script para probar el payload que se envía a la API para productos
"""

import json
import psycopg2
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

def safe_float(value) -> float:
    """Convertir valor a float de forma segura."""
    try:
        return float(value) if value is not None else 0.0
    except (ValueError, TypeError):
        return 0.0

# Cargar config
from config_encryption import decrypt_config

with open('/root/.chrystal_sync_config.json', 'r') as f:
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

print('='*70)
print('🔄 SIMULANDO TRANSFORMACIÓN DE PRODUCTOS A FORMATO API')
print('='*70)

# Obtener un producto de ejemplo
pg_cursor.execute('''
    SELECT DISTINCT ON (a.code)
        a.code,
        b.unit,
        a.description,
        a.short_name,
        a.department,
        i.description as department_name,
        b.product_code,
        h.description as unidad,
        COALESCE(c.total_stock, 0) AS stock,
        a.product_type,
        a.coin,
        f.description AS description_coin,
        COALESCE(b.maximum_price, b.higher_price, 0) AS price,
        CASE WHEN b.offer_price IS NULL THEN 0 ELSE b.offer_price END AS cost,
        CASE WHEN b.higher_price IS NULL THEN 0 ELSE b.higher_price END AS higher_price,
        CASE WHEN a.minimal_stock IS NULL THEN 0 ELSE a.minimal_stock END AS min_stock,
        CASE WHEN a.status = '01' THEN 'active' ELSE 'inactive' END AS status,
        b.unitary_cost,
        a.allow_decimal
    FROM products a
    LEFT JOIN (
        SELECT product_code, SUM(stock) as total_stock
        FROM products_stock
        GROUP BY product_code
    ) c ON a.code = c.product_code
    LEFT JOIN products_units b ON a.code = b.product_code
    LEFT JOIN units h ON h.code = b.unit
    LEFT JOIN department i ON a.department = i.code
    LEFT JOIN coin f ON f.code = a.coin
    WHERE a.code = '01'
      AND a.code IS NOT NULL
      AND b.main_unit = true
    LIMIT 1
''')

producto = pg_cursor.fetchone()

if producto:
    print('\n📦 Producto desde PostgreSQL:')
    print(f'  code: {repr(producto[0])}')
    print(f'  description: {repr(producto[2])}')
    print(f'  department: {repr(producto[4])}')
    print(f'  department_name: {repr(producto[5])}')
    print(f'  coin: {repr(producto[10])}')
    print(f'  price: {producto[12]}')
    print(f'  cost: {producto[13]}')

    # Simular la transformación
    (
        code, unit, description, short_name, department, department_name,
        product_code, unidad, stock, product_type, coin, description_coin,
        price, cost, higher_price, min_stock, status, image_type, product_image,
        sale_tax, aliquot, buy_tax, buy_aliquot, unitary_cost, allow_decimal
    ) = producto

    # Mapeo de moneda
    coin_map = {
        '01': 'VES',
        '02': 'USD',
        'VES': 'VES',
        'USD': 'USD'
    }

    coin_normalizado = coin_map.get(coin, coin) if coin else 'USD'

    print(f'\n💱 Moneda detectada: {coin} -> {coin_normalizado}')

    # Si está en VES, convertir a USD
    if coin_normalizado in ['VES', '01']:
        print(f'⚠️  Producto en VES detectado - Convirtiendo a USD')

        # Obtener tipo de cambio
        pg_cursor.execute('SELECT sales_aliquot FROM coin WHERE code = %s', ('02',))
        tipo_cambio_result = pg_cursor.fetchone()

        if tipo_cambio_result and tipo_cambio_result[0]:
            tipo_cambio = float(tipo_cambio_result[0])
            print(f'   Tipo de cambio: {tipo_cambio}')

            price_usd = round(safe_float(price) / tipo_cambio, 4)
            cost_usd = round(safe_float(cost) / tipo_cambio, 4)
            higher_price_usd = round(safe_float(higher_price) / tipo_cambio, 4)
            unitary_cost_usd = round(safe_float(unitary_cost) / tipo_cambio, 4)

            print(f'   Price: {price} VES -> {price_usd} USD')
            print(f'   Cost: {cost} VES -> {cost_usd} USD')

            price = price_usd
            cost = cost_usd
            higher_price = higher_price_usd
            unitary_cost = unitary_cost_usd
            coin_normalizado = 'USD'
        else:
            print(f'❌ ERROR: No se pudo obtener tipo de cambio')

    # category_id es el código del department
    category_id = department if department else 'GENERAL'

    # Construir name
    name = (short_name[:255] if short_name else '')[:255]
    if not name:
        name = (description[:255] if description else '')[:255]

    # Mapeo de moneda a descripción
    coin_descriptions = {
        'USD': 'Dólares americanos',
        'VES': 'Bolívares',
        '': 'Dólares americanos',
        None: 'Dólares americanos'
    }

    valid_description_coin = description_coin
    if not description_coin or description_coin.strip() in ['', 'N/A', 'N/A']:
        valid_description_coin = coin_descriptions.get(coin, 'Dólares americanos')

    # Construir payload final
    payload = {
        'code': code,
        'name': name,
        'description': description if description else None,
        'price': float(safe_float(price)),
        'cost': float(safe_float(cost)),
        'higher_price': float(safe_float(higher_price)),
        'coin': coin if coin else 'USD',
        'description_coin': valid_description_coin,
        'stock': float(safe_float(stock)),
        'min_stock': float(safe_float(min_stock)),
        'category_id': category_id,
        'status': status,
        'weight': 1.0,
        'unitary_cost': float(safe_float(unitary_cost)),
        'buy_tax': str(buy_tax) if buy_tax else '0',
        'buy_aliquot': float(safe_float(buy_aliquot)),
        'sale_tax': str(sale_tax) if sale_tax else '16',
        'aliquot': float(safe_float(aliquot)),
        'product_type': product_type if product_type else 'P',
        'unidad': unidad if unidad else 'Unidad',
        'allow_decimal': bool(allow_decimal) if allow_decimal is not None else False
    }

    print(f'\n📤 Payload que se enviaría a la API:')
    print('='*70)
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    print('='*70)

    print(f'\n⚠️  POSIBLES PROBLEMAS:')
    print(f'   1. category_id = {repr(category_id)} (puede no existir en la API)')
    print(f'   2. coin = {repr(payload["coin"])} (después de conversión)')
    print(f'   3. Valores numéricos: price={payload["price"]}, cost={payload["cost"]}')

    # Verificar si category_id existe en la API
    print(f'\n🔍 Verificando si category_id existe en la API...')
    import requests

    # Login primero
    from sync_system_api import APIAuthManager
    auth_manager = APIAuthManager(base_url=config['api_url'], logger=None)
    api_password = config.get('api_password')

    login_result = auth_manager.login(config['api_email'], api_password)
    if login_result.get('success'):
        validate_result = auth_manager.validate_company(config['company_rif'], config['company_email'])
        if validate_result.get('success'):
            company_id = validate_result.get('company_id')

            # Obtener categorías
            response = requests.get(
                f'{config["api_url"]}/sync-batch/categories',
                params={'company_id': company_id},
                headers={'Authorization': f'Bearer {auth_manager.api_token}'},
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    categories = data.get('data', {}).get('data', [])

                    print(f'\n📋 Categorías disponibles en la API:')
                    category_found = False
                    for cat in categories:
                        cat_name = cat.get('name', '')
                        cat_id = cat.get('id')
                        print(f'   - ID: {cat_id} | Name: "{cat_name}"')

                        if cat_name == category_id or str(cat_id) == str(category_id):
                            category_found = True
                            print(f'     ✅ ESTA CATEGORÍA CORRESPONDE AL category_id')

                    if not category_found:
                        print(f'\n❌ ERROR: category_id="{category_id}" NO EXISTE en la API')
                        print(f'   Debes usar el ID numérico o el nombre exacto de una categoría existente')
            else:
                print(f'❌ Error obteniendo categorías: {response.status_code}')
        else:
            print(f'❌ Error validando empresa')
    else:
        print(f'❌ Error en login')

pg_conn.close()
