#!/usr/bin/env python3
"""
Test: Obtener Facturas (Invoices) de MySQL a PostgreSQL

Este test muestra:
1. Conexión a MySQL y PostgreSQL
2. Extracción de facturas de MySQL
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
print("TEST: Obtener Facturas de MySQL → PostgreSQL")
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
# PASO 2: VERIFICAR QUÉ TABLAS EXISTEN EN MYSQL
# ===================================================================

print()
print("🔍 PASO 2: Verificando tablas en MySQL...")
print()

mysql_cursor.execute("SHOW TABLES")
tablas_mysql = [tabla[f'Tables_in_{mysql_config["database"]}'] for tabla in mysql_cursor.fetchall()]

# Buscar tablas relacionadas con facturas
posibles_tablas_facturas = [
    'invoices', 'invoice', 'sales', 'sale',
    'facturas', 'factura', 'ventas', 'venta'
]

tablas_facturas_encontradas = [t for t in posibles_tablas_facturas if t in tablas_mysql]

if tablas_facturas_encontradas:
    print(f"   ✅ Tablas de facturas encontradas: {', '.join(tablas_facturas_encontradas)}")
    tabla_facturas = tablas_facturas_encontradas[0]
else:
    print(f"   ⚠️ No se encontraron tablas de facturas")
    print(f"   Tablas disponibles: {', '.join(tablas_mysql[:20])}")

    # Buscar si hay tabla de quotes para usar como referencia
    if 'quotes' in tablas_mysql:
        print(f"   📋 Usando 'quotes' como referencia para la estructura")
        print()
        print("   ⚠️ Este test adaptará el proceso de QUOTES como si fueran FACTURAS")
        tabla_facturas = 'quotes'
    else:
        mysql_cursor.close()
        mysql_conn.close()
        print("\n❌ No hay tablas disponibles para el test")
        sys.exit(1)

print(f"   📋 Tabla a usar: {tabla_facturas}")
print()

# ===================================================================
# PASO 3: EXPLORAR ESTRUCTURA DE LA TABLA
# ===================================================================

print("🔍 PASO 3: Explorando estructura de la tabla...")
print()

mysql_cursor.execute(f"DESCRIBE {tabla_facturas}")
columnas = mysql_cursor.fetchall()

print(f"   Columnas de '{tabla_facturas}':")
for col in columnas[:15]:  # Mostrar primeras 15 columnas
    print(f"      - {col['Field']}: {col['Type']}")

if len(columnas) > 15:
    print(f"      ... y {len(columnas) - 15} columnas más")

print()

# ===================================================================
# PASO 4: OBTENER FACTURAS DE MYSQL
# ===================================================================

print("📋 PASO 4: Obteniendo facturas de MySQL...")
print()

# Query genérico que se adapta a diferentes estructuras
query = f"""
SELECT
    id,
    quote_number,
    customer_id,
    company_id,
    subtotal,
    tax_amount,
    total,
    status,
    created_at
FROM {tabla_facturas}
ORDER BY id
LIMIT 5
"""

try:
    mysql_cursor.execute(query)
    facturas_mysql = mysql_cursor.fetchall()

    if not facturas_mysql:
        print(f"   ⚠️ No hay registros en {tabla_facturas}")
        mysql_cursor.close()
        mysql_conn.close()
        sys.exit(0)

    print(f"   ✅ Obtenidos {len(facturas_mysql)} registros de MySQL")
    print()

except Exception as e:
    print(f"   ❌ Error obteniendo facturas: {e}")
    print(f"   Query: {query}")
    mysql_cursor.close()
    mysql_conn.close()
    sys.exit(1)

# ===================================================================
# PASO 5: MOSTRAR DETALLES DE CADA FACTURA
# ===================================================================

print("📄 PASO 5: Detalles de las Facturas")
print("-" * 80)
print()

for idx, factura in enumerate(facturas_mysql, 1):
    print(f"Factura #{idx}:")
    print(f"  ID            : {factura['id']}")
    print(f"  Número        : {factura.get('quote_number', 'N/A')}")
    print(f"  Customer ID   : {factura.get('customer_id', 'N/A')}")
    print(f"  Subtotal      : ${safe_float(factura.get('subtotal', 0)):.2f}")
    print(f"  Tax Amount    : ${safe_float(factura.get('tax_amount', 0)):.2f}")
    print(f"  Total         : ${safe_float(factura.get('total', 0)):.2f}")
    print(f"  Status        : {factura.get('status', 'N/A')}")
    print(f"  Created At    : {factura.get('created_at', 'N/A')}")
    print()

# ===================================================================
# PASO 6: BUSCAR TABLA DE ITEMS
# ===================================================================

print("🔍 PASO 6: Buscando tabla de items...")
print()

tablas_items_posibles = [
    f'{tabla_facturas}_items',  # Ej: invoice_items, quote_items
    f'{tabla_facturas[:-1]}_items',  # Ej: invoice_items
    'items', 'line_items', 'sale_items', 'detail_items'
]

tabla_items = None
for posible in tablas_items_posibles:
    if posible in tablas_mysql:
        tabla_items = posible
        print(f"   ✅ Tabla de items encontrada: {tabla_items}")
        break

if not tabla_items:
    print(f"   ⚠️ No se encontró tabla de items")
    tabla_items = None

print()

# ===================================================================
# PASO 7: OBTENER ITEMS DE CADA FACTURA (SI EXISTE LA TABLA)
# ===================================================================

if tabla_items:
    print("📦 PASO 7: Items de las Facturas")
    print("-" * 80)
    print()

    for idx, factura in enumerate(facturas_mysql[:3], 1):  # Solo primeras 3
        factura_id = factura['id']

        # Asumir que la columna se llama igual que la tabla principal + _id
        columna_fk = f'{tabla_facturas}_id' if tabla_facturas.endswith('s') else f'{tabla_facturas}s_id'

        # Intentar diferentes nombres de columna
        for nombre_col in [columna_fk, tabla_facturas + '_id', 'quote_id', 'invoice_id', 'sale_id', 'id']:
            try:
                query_items = f"""
                SELECT
                    description,
                    name,
                    quantity,
                    unit_price,
                    total,
                    tax_amount,
                    product_id
                FROM {tabla_items}
                WHERE {nombre_col} = %s
                ORDER BY id
                LIMIT 5
                """

                mysql_cursor.execute(query_items, (factura_id,))
                items = mysql_cursor.fetchall()

                if items or mysql_cursor.rowcount > 0:
                    print(f"Items del Factura #{factura_id}:")

                    if not items:
                        print("  ⚠️ No tiene items")
                    else:
                        for item_idx, item in enumerate(items, 1):
                            nombre = item.get('name') or item.get('description') or 'Producto'
                            cantidad = item.get('quantity', 0)
                            precio = safe_float(item.get('unit_price', 0))
                            total_item = safe_float(item.get('total', 0))

                            print(f"  {item_idx}. {nombre}")
                            print(f"     Cantidad: {cantidad} | Precio: ${precio:.2f} | Total: ${total_item:.2f}")
                    print()
                    break
            except Exception as e:
                continue  # Intentar con siguiente nombre de columna
        else:
            print(f"Items del Factura #{factura_id}:")
            print("  ⚠️ No se pudieron obtener items (columna desconocida)")
            print()

# ===================================================================
# PASO 8: CONECTAR A POSTGRESQL
# ===================================================================

print("🔌 PASO 8: Conectando a PostgreSQL...")
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
# PASO 9: VERIFICAR sync_hashes
# ===================================================================

print()
print("🔍 PASO 9: Verificando sync_hashes en PostgreSQL...")
print()

for factura in facturas_mysql:
    factura_id = factura['id']

    # Buscar hash guardado
    query_hash = """
    SELECT record_hash, last_sync_data, updated_at
    FROM sync_hashes
    WHERE table_name = %s
      AND record_key = %s
    """

    pg_cursor.execute(query_hash, (tabla_facturas, str(factura_id)))
    hash_result = pg_cursor.fetchone()

    if hash_result:
        record_hash, last_sync_data, updated_at = hash_result
        print(f"{tabla_facturas[:-1].upper()} #{factura_id}:")
        print(f"  ✅ Ya sincronizado anteriormente")
        print(f"  Hash guardado  : {record_hash[:16]}...")
        print(f"  Última sync   : {updated_at}")
    else:
        print(f"{tabla_facturas[:-1].upper()} #{factura_id}:")
        print(f"  ✨ NUEVO - No sincronizado aún")
    print()

# ===================================================================
# PASO 10: MOSTRAR ESTRUCTURA DE INSERCIÓN
# ===================================================================

print("📥 PASO 10: Estructura de Inserción en PostgreSQL")
print("-" * 80)
print()

print("Cada factura se insertaría en:")
print()
print("1. sales_operation (tabla principal)")
print("   - operation_type: 'BUDGET' (mismo tipo que quotes)")
print("   - pending: False (factura aprobada/confirmada)")
print("   - document_no: Número de factura")
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
# PASO 11: COMPARACIÓN: QUOTES VS FACTURAS
# ===================================================================

print("🔄 PASO 11: Diferencias Quotes vs Facturas")
print("-" * 80)
print()

comparacion = [
    ("Operación", "QUOTE (Presupuesto)", "INVOICE (Factura)"),
    ("operation_type", "'BUDGET'", "'BUDGET' (¡MISMO!)"),
    ("pending", "True (requiere aprobación)", "False (ya aprobada)"),
    ("canceled", "False", "False (salvo que esté anulada)"),
    ("Proceso", "Pendiente de confirmación", "Venta confirmada")
]

print(f"{'Concepto':<20} {'Quote':<25} {'Factura':<25}")
print("-" * 70)
for concepto, valor_quote, valor_factura in comparacion:
    print(f"{concepto:<20} {valor_quote:<25} {valor_factura:<25}")
print()

print("Nota: La estructura de inserción es IDÉNTICA")
print("      Solo cambia el operation_type y algunos campos de estado")
print()

# ===================================================================
# PASO 12: RESUMEN
# ===================================================================

print("=" * 80)
print("📊 RESUMEN DEL TEST")
print("=" * 80)
print()

print(f"✅ Conexiones exitosas:")
print(f"   - MySQL: {mysql_config['host']}:{mysql_config['database']}")
print(f"   - PostgreSQL: {pg_config['host']}:{pg_config['database']}")
print()

print(f"📋 Tabla usada: {tabla_facturas}")
print(f"📄 Registros obtenidos: {len(facturas_mysql)}")
print()

if tabla_items:
    total_items = 0
    for factura in facturas_mysql[:3]:
        factura_id = factura['id']
        try:
            mysql_cursor.execute(f"SELECT COUNT(*) as cnt FROM {tabla_items} WHERE quote_id = {factura_id}")
            result = mysql_cursor.fetchone()
            total_items += result['cnt']
        except:
            pass

    print(f"📦 Total items (primeras 3 facturas): {total_items}")
    print()

print("🎯 Diferencias principales en la sincronización:")
print()
print("   QUOTES → PostgreSQL:")
print("   - operation_type = 'BUDGET'")
print("   - pending = True (requiere aprobación)")
print("   - Representa una oferta al cliente")
print()
print("   FACTURAS → PostgreSQL:")
print("   - operation_type = 'BUDGET' (¡MISMO TIPO!)")
print("   - pending = False (venta confirmada)")
print("   - Representa una venta realizada")
print()
print("   El proceso de sincronización es IDENTICO en ambos casos")
print("   Solo cambia el campo 'pending'")
print()

print("🚀 Para implementar sincronización de facturas:")
print("   1. Identificar la tabla correcta en MySQL")
print("   2. Adaptar el query de extracción")
print("   3. Usar el mismo proceso que quotes pero con pending=False")
print("   4. Mantener operation_type='BUDGET' (¡NO cambiar!)")
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
