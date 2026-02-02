#!/usr/bin/env python3
"""
Test: Obtener Presupuestos (Quotes) de MySQL a PostgreSQL

Este test muestra:
1. Conexión a MySQL y PostgreSQL
2. Extracción de quotes de MySQL
3. Detección de cambios usando sync_hashes
4. Proceso de inserción en PostgreSQL
"""

import sys
import json
from datetime import datetime
import psycopg2
import mysql.connector

def safe_float(value):
    """Conversión segura a float"""
    try:
        return float(value) if value is not None else 0.0
    except:
        return 0.0

# ===================================================================
# CONFIGURACIÓN DE CONEXIONES
# ===================================================================

print("=" * 80)
print("TEST: Obtener Quotes de MySQL → PostgreSQL")
print("=" * 80)
print()

# Cargar configuración desde sync_config.json
try:
    with open('sync_config.json', 'r') as f:
        config = json.load(f)

    # Configuración PostgreSQL
    pg_config = {
        'host': config['postgres_host'],
        'database': config['postgres_database'],
        'user': config['postgres_user'],
        'password': config['postgres_password']
    }

    # Configuración MySQL
    mysql_config = {
        'host': config['mysql_host'],
        'database': config['mysql_database'],
        'user': config['mysql_user'],
        'password': config['mysql_password'],
        'port': int(config.get('mysql_port', 3306))
    }

    company_rif = config['company_rif']

    print(f"📊 PostgreSQL: {pg_config['host']}:{pg_config['database']}")
    print(f"📊 MySQL: {mysql_config['host']}:{mysql_config['database']}")
    print(f"🏢 Company RIF: {company_rif}")
    print()

except Exception as e:
    print(f"❌ Error cargando configuración: {e}")
    print("   Asegúrate de que sync_config.json existe")
    sys.exit(1)

# ===================================================================
# PASO 1: CONECTAR A MYSQL
# ===================================================================

print("🔌 PASO 1: Conectando a MySQL...")
try:
    mysql_conn = mysql.connector.connect(**mysql_config)
    mysql_cursor = mysql_conn.cursor(dictionary=True)
    print("   ✅ Conexión MySQL exitosa")
except Exception as e:
    print(f"   ❌ Error conectando a MySQL: {e}")
    sys.exit(1)

# ===================================================================
# PASO 2: OBTENER QUOTES DE MYSQL
# ===================================================================

print()
print("📋 PASO 2: Obteniendo quotes de MySQL...")
print()

query = """
SELECT
    id,
    quote_number,
    customer_id,
    company_id,
    user_seller_id,
    subtotal,
    tax,
    tax_amount,
    discount,
    discount_amount,
    total,
    bcv_rate,
    status,
    created_at,
    updated_at
FROM quotes
ORDER BY id
LIMIT 5
"""

try:
    mysql_cursor.execute(query)
    quotes_mysql = mysql_cursor.fetchall()

    if not quotes_mysql:
        print("   ⚠️ No hay quotes en MySQL")
        mysql_cursor.close()
        mysql_conn.close()
        sys.exit(0)

    print(f"   ✅ Obtenidos {len(quotes_mysql)} quotes de MySQL")
    print()

except Exception as e:
    print(f"   ❌ Error obteniendo quotes: {e}")
    mysql_cursor.close()
    mysql_conn.close()
    sys.exit(1)

# ===================================================================
# PASO 3: MOSTRAR DETALLES DE CADA QUOTE
# ===================================================================

print("📄 PASO 3: Detalles de los Quotes")
print("-" * 80)
print()

for idx, quote in enumerate(quotes_mysql, 1):
    print(f"Quote #{idx}:")
    print(f"  ID            : {quote['id']}")
    print(f"  Quote Number  : {quote['quote_number']}")
    print(f"  Customer ID   : {quote['customer_id']}")
    print(f"  Subtotal      : ${safe_float(quote['subtotal']):.2f}")
    print(f"  Tax Amount    : ${safe_float(quote['tax_amount']):.2f}")
    print(f"  Discount      : ${safe_float(quote['discount_amount']):.2f}")
    print(f"  Total         : ${safe_float(quote['total']):.2f}")
    print(f"  BCV Rate      : {safe_float(quote['bcv_rate']):.2f}")
    print(f"  Status        : {quote['status']}")
    print(f"  Created At    : {quote['created_at']}")
    print()

# ===================================================================
# PASO 4: OBTENER ITEMS DE CADA QUOTE
# ===================================================================

print("📦 PASO 4: Items de los Quotes")
print("-" * 80)
print()

for idx, quote in enumerate(quotes_mysql, 1):
    quote_id = quote['id']

    query_items = """
    SELECT
        description,
        name,
        subtotal,
        unit,
        unit_price,
        total,
        tax_amount,
        discount_amount,
        discount_percentage,
        quantity,
        product_id
    FROM quote_items
    WHERE quote_id = %s
    ORDER BY id
    """

    mysql_cursor.execute(query_items, (quote_id,))
    items = mysql_cursor.fetchall()

    print(f"Items del Quote #{quote_id} ({quote['quote_number']}):")

    if not items:
        print("  ⚠️ No tiene items")
    else:
        for item_idx, item in enumerate(items, 1):
            print(f"  {item_idx}. {item['name'] or item['description']}")
            print(f"     Cantidad: {item['quantity']} | Precio: ${safe_float(item['unit_price']):.2f} | "
                  f"Total: ${safe_float(item['total']):.2f}")
    print()

# ===================================================================
# PASO 5: CONECTAR A POSTGRESQL
# ===================================================================

print("🔌 PASO 5: Conectando a PostgreSQL...")
try:
    pg_conn = psycopg2.connect(**pg_config)
    pg_cursor = pg_conn.cursor()
    print("   ✅ Conexión PostgreSQL exitosa")
except Exception as e:
    print(f"   ❌ Error conectando a PostgreSQL: {e}")
    mysql_cursor.close()
    mysql_conn.close()
    sys.exit(1)

# ===================================================================
# PASO 6: VERIFICAR sync_hashes
# ===================================================================

print()
print("🔍 PASO 6: Verificando sync_hashes en PostgreSQL...")
print()

for quote in quotes_mysql:
    quote_id = quote['id']

    # Buscar hash guardado
    query_hash = """
    SELECT record_hash, last_sync_data, updated_at
    FROM sync_hashes
    WHERE table_name = 'quotes'
      AND record_key = %s
    """

    pg_cursor.execute(query_hash, (str(quote_id),))
    hash_result = pg_cursor.fetchone()

    if hash_result:
        record_hash, last_sync_data, updated_at = hash_result
        print(f"Quote #{quote_id}:")
        print(f"  ✅ Ya sincronizado anteriormente")
        print(f"  Hash guardado  : {record_hash[:16]}...")
        print(f"  Última sync   : {updated_at}")
    else:
        print(f"Quote #{quote_id}:")
        print(f"  ✨ NUEVO - No sincronizado aún")
    print()

# ===================================================================
# PASO 7: MOSTRAR ESTRUCTURA DE INSERCIÓN
# ===================================================================

print("📥 PASO 7: Estructura de Inserción en PostgreSQL")
print("-" * 80)
print()

print("Cada quote se insertaría en:")
print()
print("1. sales_operation (tabla principal)")
print("   - operation_type: 'BUDGET'")
print("   - document_no: quote_number")
print("   - total_net_cost: COSTO real de productos")
print("   - total_tax_cost: IVA sobre el costo")
print("   - total_cost: Costo total + IVA")
print()

print("2. sales_operation_coins (2 registros: USD y Bs)")
print("   - main_correlative: ID del sales_operation")
print("   - coin_code: '02' (USD) y '01' (Bs)")
print("   - Conversión usando tasa BCV")
print()

print("3. sales_operation_details (N registros, 1 por item)")
print("   - main_correlative: ID del sales_operation")
print("   - code_product: Código del producto")
print("   - total_net_cost: Cantidad × Costo del producto")
print("   - total_tax_cost: 16% del costo neto (si gravado)")
print()

print("4. sales_operation_taxes (1 registro)")
print("   - main_correlative: ID del sales_operation")
print("   - taxe_code: '01' (IVA General)")
print("   - aliquot: Porcentaje de IVA")
print()

print("5. sales_operation_taxes_coins (2 registros: USD y Bs)")
print("   - Impuestos en ambas monedas")
print()

# ===================================================================
# PASO 8: EJEMPLO DE CÁLCULO DE COSTOS
# ===================================================================

print("💰 PASO 8: Ejemplo de Cálculo de Costos")
print("-" * 80)
print()

if quotes_mysql:
    quote = quotes_mysql[0]
    quote_id = quote['id']

    # Obtener items para calcular costos
    query_items = """
    SELECT
        qi.quantity,
        p.cost,
        qi.product_id,
        p.code
    FROM quote_items qi
    JOIN products p ON p.id = qi.product_id
    WHERE qi.quote_id = %s
    """

    mysql_cursor.execute(query_items, (quote_id,))
    items_costos = mysql_cursor.fetchall()

    if items_costos:
        print(f"Quote #{quote_id} - Cálculo de Costos:")
        print()

        total_net_cost = 0
        total_tax_cost = 0

        for item_idx, item in enumerate(items_costos, 1):
            quantity = safe_float(item['quantity'])
            cost = safe_float(item['cost'])

            item_net_cost = quantity * cost
            item_tax_cost = item_net_cost * 0.16  # 16% IVA

            total_net_cost += item_net_cost
            total_tax_cost += item_tax_cost

            print(f"  {item_idx}. Producto {item['code']}")
            print(f"     Cantidad: {quantity}")
            print(f"     Costo unitario: ${cost:.2f}")
            print(f"     Costo neto: ${item_net_cost:.2f}")
            print(f"     IVA (16%): ${item_tax_cost:.2f}")
            print(f"     Costo total: ${item_net_cost + item_tax_cost:.2f}")
            print()

        total_cost = total_net_cost + total_tax_cost

        print(f"  📊 TOTALES:")
        print(f"     Costo Neto   : ${total_net_cost:.2f}")
        print(f"     IVA Costo    : ${total_tax_cost:.2f}")
        print(f"     Costo Total  : ${total_cost:.2f}")
        print()

        # Comparar con precio de venta
        quote_total = safe_float(quote['total'])
        profit = quote_total - total_cost
        profit_margin = (profit / quote_total * 100) if quote_total > 0 else 0

        print(f"  💵 Comparación Precio vs Costo:")
        print(f"     Precio Venta: ${quote_total:.2f}")
        print(f"     Costo Total : ${total_cost:.2f}")
        print(f"     Ganancia    : ${profit:.2f} ({profit_margin:.1f}%)")
        print()

# ===================================================================
# PASO 9: RESUMEN
# ===================================================================

print("=" * 80)
print("📊 RESUMEN DEL TEST")
print("=" * 80)
print()

print(f"✅ Conexiones exitosas:")
print(f"   - MySQL: {mysql_config['host']}:{mysql_config['database']}")
print(f"   - PostgreSQL: {pg_config['host']}:{pg_config['database']}")
print()

print(f"📋 Quotes obtenidos: {len(quotes_mysql)}")
print()

total_items = 0
for quote in quotes_mysql:
    quote_id = quote['id']
    mysql_cursor.execute(f"SELECT COUNT(*) as cnt FROM quote_items WHERE quote_id = {quote_id}")
    result = mysql_cursor.fetchone()
    total_items += result['cnt']

print(f"📦 Total items: {total_items}")
print()

print("🎯 Próximos pasos para sincronización:")
print("   1. Generar hash MD5 de cada quote")
print("   2. Comparar con sync_hashes")
print("   3. Insertar quotes nuevos/modificados en:")
print("      - sales_operation")
print("      - sales_operation_coins (×2)")
print("      - sales_operation_details (×N items)")
print("      - sales_operation_taxes")
print("      - sales_operation_taxes_coins (×2)")
print("   4. Actualizar sync_hashes")
print("   5. Registrar en system_logs de MySQL")
print()

# ===================================================================
# CERRAR CONEXIONES
# ===================================================================

print("🔌 Cerrando conexiones...")
mysql_cursor.close()
mysql_conn.close()
pg_cursor.close()
pg_conn.close()
print("✅ Test finalizado")
