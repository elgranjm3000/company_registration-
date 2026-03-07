#!/usr/bin/env python3
"""
Script para inicializar hashes de products_mysql y customers_mysql en sync_hashes.
Esto evita que el sincronizador tenga que procesar 52,686 productos cada vez.
"""

import psycopg2
import pymysql
import hashlib
import json
from datetime import datetime

# Configuración PostgreSQL
PG_CONFIG = {
    'host': 'localhost',
    'database': 'databig',
    'user': 'postgres',
    'password': 'muentes123.'
}

# Configuración MySQL
MYSQL_CONFIG = {
    'host': '91.238.160.176',
    'port': 3306,
    'user': 'chrystal_app',
    'password': 'muentes123.',
    'database': 'chrystal_movil',
    'charset': 'utf8mb4'
}

def generar_hash_product_mysql(product):
    """Generar hash MD5 de un producto MySQL"""
    campos = (
        str(product.get('id', '')),
        str(product.get('code', '')),
        str(product.get('name', '')),
        str(product.get('description', '')),
        str(product.get('price', '')),
        str(product.get('cost', '')),
        str(product.get('higher_price', '')),
        str(product.get('coin', '')),
        str(product.get('description_coin', '')),
        str(product.get('min_stock', '')),
        str(product.get('category_id', '')),
        str(product.get('status', '')),
        str(product.get('product_type', '')),
        str(product.get('sale_tax', '')),
        str(product.get('aliquot', '')),
    )
    return hashlib.md5(''.join(campos).encode()).hexdigest()

def generar_hash_customer_mysql(customer):
    """Generar hash MD5 de un cliente MySQL"""
    campos = (
        str(customer.get('id', '')),
        str(customer.get('document_number', '')),
        str(customer.get('name', '')),
        str(customer.get('address', '')),
        str(customer.get('email', '')),
        str(customer.get('phone', '')),
        str(customer.get('contact', '')),
        str(customer.get('status', '')),
    )
    return hashlib.md5(''.join(campos).encode()).hexdigest()

def obtener_company_id():
    """Obtener company_id desde MySQL"""
    conn = pymysql.connect(**MYSQL_CONFIG)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id FROM companies
        WHERE rif = %s AND email = %s
        LIMIT 1
    """, ('J195071884', 'muentes2@hotmail.com'))

    result = cursor.fetchone()
    cursor.close()
    conn.close()

    return result[0] if result else None

def inicializar_products_mysql(company_id):
    """Inicializar hashes de products_mysql"""
    print("\n📦 INICIALIZANDO HASHES DE PRODUCTS_MYSQL...")

    # Conectar a MySQL
    mysql_conn = pymysql.connect(**MYSQL_CONFIG)
    mysql_cursor = mysql_conn.cursor()

    # Obtener todos los productos de MySQL
    mysql_cursor.execute("""
        SELECT
            id, code, name, description, price, cost,
            higher_price, coin, description_coin, min_stock,
            category_id, status, product_type, sale_tax, aliquot
        FROM products
        WHERE company_id = %s
        ORDER BY id
    """, (company_id,))

    products = mysql_cursor.fetchall()
    mysql_cursor.close()
    mysql_conn.close()

    print(f"   📋 Obtenidos {len(products):,} productos de MySQL")

    # Conectar a PostgreSQL
    pg_conn = psycopg2.connect(**PG_CONFIG)
    pg_cursor = pg_conn.cursor()

    # Preparar datos para batch insert
    columnas = [
        'id', 'code', 'name', 'description', 'price', 'cost',
        'higher_price', 'coin', 'description_coin', 'min_stock',
        'category_id', 'status', 'product_type', 'sale_tax', 'aliquot'
    ]

    batch_data = []
    for fila in products:
        product_dict = dict(zip(columnas, fila))
        product_id = str(product_dict['id'])
        product_code = product_dict['code']

        # Generar hash
        hash_value = generar_hash_product_mysql(product_dict)

        # Verificar si ya existe
        pg_cursor.execute("""
            SELECT id FROM sync_hashes
            WHERE table_name = 'products_mysql'
              AND record_key = %s
              AND company_id = %s
        """, (product_id, company_id))

        if pg_cursor.fetchone():
            continue  # Ya existe, saltar

        # Preparar data
        data_sync = {
            'code': product_code,
            'last_sync': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        batch_data.append((
            'products_mysql',
            product_id,
            hash_value,
            json.dumps(data_sync),
            company_id
        ))

    # Batch insert
    if batch_data:
        print(f"   💾 Insertando {len(batch_data):,} hashes en sync_hashes...")
        pg_cursor.executemany("""
            INSERT INTO sync_hashes (table_name, record_key, record_hash, last_sync_data, company_id, synced_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
            ON CONFLICT (table_name, record_key, company_id) DO NOTHING
        """, batch_data)

        pg_conn.commit()
        print(f"   ✅ {len(batch_data):,} hashes de products_mysql inicializados")
    else:
        print(f"   ℹ️ No hay hashes nuevos de products_mysql para insertar")

    pg_cursor.close()
    pg_conn.close()

def inicializar_customers_mysql(company_id):
    """Inicializar hashes de customers_mysql"""
    print("\n👥 INICIALIZANDO HASHES DE CUSTOMERS_MYSQL...")

    # Conectar a MySQL
    mysql_conn = pymysql.connect(**MYSQL_CONFIG)
    mysql_cursor = mysql_conn.cursor()

    # Obtener todos los clientes de MySQL
    mysql_cursor.execute("""
        SELECT
            id, document_number, name, address, email,
            phone, contact, status
        FROM customers
        WHERE company_id = %s
        ORDER BY id
    """, (company_id,))

    customers = mysql_cursor.fetchall()
    mysql_cursor.close()
    mysql_conn.close()

    print(f"   📋 Obtenidos {len(customers):,} clientes de MySQL")

    # Conectar a PostgreSQL
    pg_conn = psycopg2.connect(**PG_CONFIG)
    pg_cursor = pg_conn.cursor()

    # Preparar datos para batch insert
    columnas = [
        'id', 'document_number', 'name', 'address', 'email',
        'phone', 'contact', 'status'
    ]

    batch_data = []
    for fila in customers:
        customer_dict = dict(zip(columnas, fila))
        customer_id = str(customer_dict['id'])
        customer_code = customer_dict['document_number']

        # Generar hash
        hash_value = generar_hash_customer_mysql(customer_dict)

        # Verificar si ya existe
        pg_cursor.execute("""
            SELECT id FROM sync_hashes
            WHERE table_name = 'customers_mysql'
              AND record_key = %s
              AND company_id = %s
        """, (customer_id, company_id))

        if pg_cursor.fetchone():
            continue  # Ya existe, saltar

        # Preparar data
        data_sync = {
            'document_number': customer_code,
            'last_sync': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        batch_data.append((
            'customers_mysql',
            customer_id,
            hash_value,
            json.dumps(data_sync),
            company_id
        ))

    # Batch insert
    if batch_data:
        print(f"   💾 Insertando {len(batch_data):,} hashes en sync_hashes...")
        pg_cursor.executemany("""
            INSERT INTO sync_hashes (table_name, record_key, record_hash, last_sync_data, company_id, synced_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
            ON CONFLICT (table_name, record_key, company_id) DO NOTHING
        """, batch_data)

        pg_conn.commit()
        print(f"   ✅ {len(batch_data):,} hashes de customers_mysql inicializados")
    else:
        print(f"   ℹ️ No hay hashes nuevos de customers_mysql para insertar")

    pg_cursor.close()
    pg_conn.close()

def main():
    """Función principal"""
    print("=" * 60)
    print("🚀 INICIALIZANDO HASHES DE MYSQL → POSTGRESQL")
    print("=" * 60)

    # Obtener company_id
    print("\n🔍 Obteniendo company_id...")
    company_id = obtener_company_id()

    if not company_id:
        print("❌ No se pudo obtener company_id")
        print("   Verifica que la empresa existe en MySQL")
        return

    print(f"✅ company_id: {company_id}")

    # Inicializar hashes
    try:
        inicializar_products_mysql(company_id)
        inicializar_customers_mysql(company_id)

        print("\n" + "=" * 60)
        print("✅ INICIALIZACIÓN COMPLETADA")
        print("=" * 60)
        print("\n💡 Ahora el sincronizador solo procesará los productos/clientes")
        print("   realmente nuevos o modificados, en lugar de procesar todos.")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        print(traceback.format_exc())

if __name__ == '__main__':
    main()
