#!/usr/bin/env python3
"""
Crear Quotes de Prueba en MySQL y Sincronizar a PostgreSQL

Este script:
1. Crea customers de prueba en MySQL
2. Crea products de prueba en MySQL (si no existen)
3. Crea quotes de prueba en MySQL
4. Ejecuta la sincronización completa
5. Verifica que los quotes llegaron a PostgreSQL
"""

import sys
import json
from datetime import datetime, timedelta
import mysql.connector
import psycopg2

print("=" * 80)
print("🚀 CREAR QUOTES Y SINCRONIZAR")
print("=" * 80)
print()

# Cargar configuración
with open('sync_config.json', 'r') as f:
    config = json.load(f)

# Configuración MySQL
mysql_config = {
    'host': config['mysql_host'],
    'database': config['mysql_database'],
    'user': config['mysql_user'],
    'password': config['mysql_password'],
    'port': int(config.get('mysql_port', 3306))
}

# Configuración PostgreSQL
pg_config = {
    'host': config['postgres_host'],
    'database': config['postgres_database'],
    'user': config['postgres_user'],
    'password': config['postgres_password']
}

company_rif = config['company_rif']

print(f"📊 MySQL: {mysql_config['host']}:{mysql_config['database']}")
print(f"📊 PostgreSQL: {pg_config['host']}:{pg_config['database']}")
print(f"🏢 Company RIF: {company_rif}")
print()

# ===================================================================
# PASO 1: CONECTAR A MYSQL
# ===================================================================

print("🔌 PASO 1: Conectando a MySQL...")
try:
    mysql_conn = mysql.connector.connect(**mysql_config)
    mysql_cursor = mysql_conn.cursor(dictionary=True)
    print("   ✅ Conexión exitosa")
except Exception as e:
    print(f"   ❌ Error: {e}")
    sys.exit(1)

# ===================================================================
# PASO 2: OBTENER COMPANY_ID
# ===================================================================

print()
print("🏢 PASO 2: Obteniendo company_id...")
mysql_cursor.execute(
    "SELECT id, name FROM companies WHERE rif = %s",
    (company_rif,)
)
company = mysql_cursor.fetchone()

if not company:
    print(f"   ❌ No existe empresa con RIF: {company_rif}")
    mysql_cursor.close()
    mysql_conn.close()
    sys.exit(1)

company_id = company['id']
company_name = company['name']
print(f"   ✅ Company ID: {company_id} - {company_name}")

# ===================================================================
# PASO 3: CREAR CUSTOMER DE PRUEBA
# ===================================================================

print()
print("👤 PASO 3: Creando customer de prueba...")

# Verificar si ya existe
mysql_cursor.execute(
    "SELECT id FROM customers WHERE company_id = %s AND document_number = 'TEST001'",
    (company_id,)
)
customer_existente = mysql_cursor.fetchone()

if customer_existente:
    customer_id = customer_existente['id']
    print(f"   ✅ Customer ya existe: ID {customer_id}")
else:
    # Insertar customer de prueba
    mysql_cursor.execute("""
        INSERT INTO customers (
            company_id, name, email, phone, document_number,
            document_type, address, city, status
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        company_id,
        'Cliente de Prueba Sincronización',
        'test@prueba.com',
        '0414-1234567',
        'TEST001',
        'RIF',
        'Dirección de Prueba',
        'Caracas',
        'active'
    ))

    mysql_conn.commit()
    customer_id = mysql_cursor.lastrowid
    print(f"   ✅ Customer creado: ID {customer_id}")

# ===================================================================
# PASO 4: VERIFICAR PRODUCTS
# ===================================================================

print()
print("📦 PASO 4: Verificando products en MySQL...")

mysql_cursor.execute(
    """SELECT id, code, name, cost FROM products
    WHERE company_id = %s LIMIT 5""",
    (company_id,)
)

products = mysql_cursor.fetchall()

if not products:
    print("   ⚠️ No hay products. Creando uno de prueba...")

    # Obtener categoría por defecto
    mysql_cursor.execute(
        "SELECT id FROM categories WHERE company_id = %s LIMIT 1",
        (company_id,)
    )
    category = mysql_cursor.fetchone()

    if not category:
        print("   ❌ No hay categorías. Creando una...")
        mysql_cursor.execute("""
            INSERT INTO categories (company_id, name, description)
            VALUES (%s, %s, %s)
        """, (company_id, 'General', 'Categoría general'))
        mysql_conn.commit()
        category_id = mysql_cursor.lastrowid
    else:
        category_id = category['id']

    # Crear product de prueba
    mysql_cursor.execute("""
        INSERT INTO products (
            company_id, code, name, description, price, cost,
            category_id, status, product_type
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        company_id,
        'TEST-PROD-001',
        'Producto de Prueba',
        'Producto para probar sincronización',
        25.00,
        15.00,
        category_id,
        'active',
        'finished'
    ))

    mysql_conn.commit()
    product_id = mysql_cursor.lastrowid
    print(f"   ✅ Product creado: ID {product_id}")

    products = [{'id': product_id, 'code': 'TEST-PROD-001', 'name': 'Producto de Prueba', 'cost': 15.00}]

else:
    print(f"   ✅ Encontrados {len(products)} products:")
    for p in products:
        print(f"      - {p['code']}: {p['name']} (${p['cost']:.2f})")

# ===================================================================
# PASO 5: CREAR QUOTES DE PRUEBA
# ===================================================================

print()
print("💰 PASO 5: Creando quotes de prueba...")

quotes_creados = []

for i in range(1, 4):  # Crear 3 quotes
    quote_number = f"TEST-2026-{i:03d}"

    # Verificar si ya existe
    mysql_cursor.execute(
        "SELECT id FROM quotes WHERE quote_number = %s",
        (quote_number,)
    )

    if mysql_cursor.fetchone():
        print(f"   ⚠️ Quote {quote_number} ya existe, omitiendo...")
        continue

    # Insertar quote
    mysql_cursor.execute("""
        INSERT INTO quotes (
            company_id, quote_number, customer_id, user_seller_id,
            subtotal, tax, tax_amount, discount, discount_amount,
            total, bcv_rate, bcv_date, status, notes, quote_date
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        company_id,
        quote_number,
        customer_id,
        541,  # user_seller_id (usuario válido)
        50.00,  # subtotal
        16.00,  # tax %
        8.00,   # tax_amount
        0.00,   # discount %
        0.00,   # discount_amount
        58.00,  # total
        35.50,  # bcv_rate
        datetime.now().date(),
        'draft',
        'Quote de prueba para sincronización',
        datetime.now()
    ))

    mysql_conn.commit()
    quote_id = mysql_cursor.lastrowid

    # Insertar items del quote
    for j, product in enumerate(products[:2], 1):  # 2 items por quote
        quantity = 2
        unit_price = 25.00
        subtotal = quantity * unit_price
        tax_amount = subtotal * 0.16
        total = subtotal + tax_amount

        mysql_cursor.execute("""
            INSERT INTO quote_items (
                quote_id, product_id, name, description, quantity,
                unit, unit_price, subtotal, tax_amount, total
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            quote_id,
            product['id'],
            product['name'],
            product['name'],
            quantity,
            'unidad',
            unit_price,
            subtotal,
            tax_amount,
            total
        ))

    mysql_conn.commit()
    quotes_creados.append((quote_id, quote_number))
    print(f"   ✅ Quote creado: {quote_number} (ID: {quote_id}) con 2 items")

if not quotes_creados:
    print("   ⚠️ No se crearon quotes (ya existían)")
else:
    print()
    print(f"   📊 Total de quotes creados: {len(quotes_creados)}")

# ===================================================================
# PASO 6: VERIFICAR QUOTES EN MYSQL
# ===================================================================

print()
print("📋 PASO 6: Verificando quotes en MySQL...")

mysql_cursor.execute(
    """SELECT id, quote_number, customer_id, subtotal, total, status
    FROM quotes WHERE company_id = %s ORDER BY id DESC LIMIT 5""",
    (company_id,)
)

quotes_verify = mysql_cursor.fetchall()

print(f"   📊 Total de quotes: {len(quotes_verify)}")
for q in quotes_verify:
    print(f"      - {q['quote_number']}: ${q['total']:.2f} ({q['status']})")

mysql_cursor.close()
mysql_conn.close()

# ===================================================================
# PASO 7: EJECUTAR SINCRONIZACIÓN
# ===================================================================

print()
print("🔄 PASO 7: Ejecutando sincronización completa...")
print()

try:
    # Importar el sistema de sincronización
    from smart_sync_complete import SmartSyncComplete

    # Crear instancia
    sync_system = SmartSyncComplete(
        postgresql_config=pg_config,
        mysql_config=mysql_config,
        company_rif=company_rif,
        company_email=config['company_email'],
        company_name=company_name
    )

    # Ejecutar sincronización
    resultado = sync_system.ejecutar_sync_completa()

    if resultado:
        print()
        print("✅ SINCRONIZACIÓN COMPLETADA EXITOSAMENTE")
    else:
        print()
        print("⚠️ SINCRONIZACIÓN COMPLETADA CON ERRORES")

except Exception as e:
    print(f"❌ Error en sincronización: {e}")
    import traceback
    print(f"TRACEBACK:\n{traceback.format_exc()}")
    sys.exit(1)

# ===================================================================
# PASO 8: VERIFICAR QUOTES EN POSTGRESQL
# ===================================================================

print()
print("📊 PASO 8: Verificando quotes en PostgreSQL...")
print()

try:
    pg_conn = psycopg2.connect(**pg_config)
    pg_cursor = pg_conn.cursor()

    # Buscar los quotes que creamos
    for quote_id, quote_number in quotes_creados:
        pg_cursor.execute(
            """SELECT correlative, document_no, total, pending, canceled
            FROM sales_operation
            WHERE operation_type = 'BUDGET' AND document_no = %s""",
            (quote_number,)
        )

        resultado = pg_cursor.fetchone()

        if resultado:
            correlative, doc_no, total, pending, canceled = resultado
            print(f"   ✅ {quote_number} → Correlative: {correlative}, "
                  f"Total: ${total:.2f}, Pending: {pending}")
        else:
            print(f"   ❌ {quote_number} → NO se encontró en PostgreSQL")

    # Contar todos los budgets
    pg_cursor.execute(
        "SELECT COUNT(*) FROM sales_operation WHERE operation_type = 'BUDGET'"
    )
    total_budgets = pg_cursor.fetchone()[0]

    print()
    print(f"   📊 Total de BUDGET en PostgreSQL: {total_budgets}")

    pg_cursor.close()
    pg_conn.close()

except Exception as e:
    print(f"   ❌ Error verificando PostgreSQL: {e}")

# ===================================================================
# RESUMEN FINAL
# ===================================================================

print()
print("=" * 80)
print("📊 RESUMEN FINAL")
print("=" * 80)
print()

print(f"✅ Quotes creados en MySQL: {len(quotes_creados)}")
print(f"✅ Sincronización ejecutada")
print()
print("🎯 PRÓXIMOS PASOS:")
print("   1. Revisa el log de sincronización arriba")
print("   2. Verifica que los quotes aparezcan en PostgreSQL")
print("   3. Modifica un quote en MySQL y vuelve a sincronizar")
print("   4. Deberías ver el quote como 'MODIFICADO' en el log")
print()

print("✅ Test completado")
