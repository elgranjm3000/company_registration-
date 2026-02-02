#!/usr/bin/env python3
"""
Test de Diagnóstico Completo: ¿Por qué no sincronizan los quotes?

Este test verifica PASO A PASO todo el flujo de sincronización
para identificar exactamente dónde está el problema.
"""

import sys
import json
import hashlib
from datetime import datetime
import psycopg2
import mysql.connector

print("=" * 80)
print("🔍 TEST DE DIAGNÓSTICO: SINCRONIZACIÓN DE QUOTES")
print("=" * 80)
print()

# Cargar configuración
try:
    with open('sync_config.json', 'r') as f:
        config = json.load(f)
except Exception as e:
    print(f"❌ Error cargando configuración: {e}")
    sys.exit(1)

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

# ===================================================================
# PASO 1: CONEXIÓN A MYSQL
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
# PASO 2: OBTENER COMPANY_ID
# ===================================================================

print()
print("🏢 PASO 2: Obteniendo company_id desde MySQL...")
try:
    mysql_cursor.execute(
        "SELECT id FROM companies WHERE rif = %s",
        (company_rif,)
    )
    company_result = mysql_cursor.fetchone()

    if not company_result:
        print(f"   ❌ No existe empresa con RIF: {company_rif}")
        mysql_cursor.close()
        mysql_conn.close()
        sys.exit(1)

    company_id = company_result['id']
    print(f"   ✅ Company ID encontrado: {company_id}")
except Exception as e:
    print(f"   ❌ Error obteniendo company_id: {e}")
    mysql_cursor.close()
    mysql_conn.close()
    sys.exit(1)

# ===================================================================
# PASO 3: VERIFICAR QUOTES EN MYSQL
# ===================================================================

print()
print("📋 PASO 3: Verificando quotes en MySQL...")
print()

try:
    mysql_cursor.execute(
        "SELECT COUNT(*) as total FROM quotes WHERE company_id = %s",
        (company_id,)
    )
    total_quotes = mysql_cursor.fetchone()['total']

    print(f"   📊 Total de quotes en MySQL: {total_quotes}")

    if total_quotes == 0:
        print("   ⚠️ NO HAY QUOTES EN MYSQL")
        print("   💡 Esto explica por qué no sincroniza nada")
        mysql_cursor.close()
        mysql_conn.close()
        sys.exit(0)

    # Obtener los quotes (últimos 5)
    mysql_cursor.execute(
        """SELECT id, quote_number, customer_id, subtotal, total, status, created_at
        FROM quotes WHERE company_id = %s ORDER BY id DESC LIMIT 5""",
        (company_id,)
    )
    quotes = mysql_cursor.fetchall()

    print(f"   ✅ Últimos {len(quotes)} quotes:")
    for idx, q in enumerate(quotes, 1):
        print(f"      {idx}. ID={q['id']} | {q['quote_number']} | "
              f"Total: ${q['total']:.2f} | Status: {q['status']}")

except Exception as e:
    print(f"   ❌ Error verificando quotes: {e}")
    mysql_cursor.close()
    mysql_conn.close()
    sys.exit(1)

# ===================================================================
# PASO 4: CONEXIÓN A POSTGRESQL
# ===================================================================

print()
print("🔌 PASO 4: Conectando a PostgreSQL...")
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
# PASO 5: VERIFICAR sync_hashes
# ===================================================================

print()
print("🔍 PASO 5: Verificando sync_hashes en PostgreSQL...")
print()

# Verificar si existe la tabla
pg_cursor.execute("""
    SELECT EXISTS (
        SELECT FROM information_schema.tables
        WHERE table_name = 'sync_hashes'
    )
""")

if not pg_cursor.fetchone()[0]:
    print("   ❌ La tabla 'sync_hashes' NO existe en PostgreSQL")
    print("   💡 Debes ejecutar la inicialización primero")
    pg_cursor.close()
    pg_conn.close()
    mysql_cursor.close()
    mysql_conn.close()
    sys.exit(1)

print("   ✅ Tabla 'sync_hashes' existe")

# Verificar hashes de quotes
pg_cursor.execute(
    """SELECT COUNT(*) FROM sync_hashes WHERE table_name = 'quotes'"""
)
total_hashes = pg_cursor.fetchone()[0]

print(f"   📊 Total de hashes de quotes: {total_hashes}")

# Mostrar algunos hashes
pg_cursor.execute(
    """SELECT record_key, record_hash, updated_at
    FROM sync_hashes
    WHERE table_name = 'quotes'
    ORDER BY updated_at DESC
    LIMIT 5"""
)

hashes = pg_cursor.fetchall()
if hashes:
    print(f"   ✅ Últimos {len(hashes)} hashes:")
    for idx, (key, hash_val, updated) in enumerate(hashes, 1):
        print(f"      {idx}. Quote #{key} | Hash: {hash_val[:16]}... | {updated}")

# ===================================================================
# PASO 6: SIMULAR DETECCIÓN DE CAMBIOS
# ===================================================================

print()
print("🔍 PASO 6: Simulando detección de cambios...")
print()

def generar_hash_quote(quote):
    """Generar hash MD5 de un quote"""
    datos = f"{quote['id']}|{quote['quote_number']}|{quote['subtotal']}|{quote['total']}|{quote['status']}"
    return hashlib.md5(datos.encode()).hexdigest()

cambios_detectados = {'nuevos': 0, 'modificados': 0, 'sin_cambios': 0}

for quote in quotes:
    quote_id = str(quote['id'])

    # Generar hash actual
    hash_actual = generar_hash_quote(quote)

    # Buscar en sync_hashes
    pg_cursor.execute(
        """SELECT record_hash FROM sync_hashes
        WHERE table_name = 'quotes' AND record_key = %s""",
        (quote_id,)
    )
    resultado = pg_cursor.fetchone()

    if resultado is None:
        cambios_detectados['nuevos'] += 1
        print(f"   ✨ NUEVO: Quote #{quote_id} ({quote['quote_number']})")
        print(f"      Hash: {hash_actual}")
    elif resultado[0] != hash_actual:
        cambios_detectados['modificados'] += 1
        print(f"   🔄 MODIFICADO: Quote #{quote_id} ({quote['quote_number']})")
        print(f"      Hash anterior: {resultado[0][:16]}...")
        print(f"      Hash actual:   {hash_actual}")
    else:
        cambios_detectados['sin_cambios'] += 1
        print(f"   ✅ Sin cambios: Quote #{quote_id} ({quote['quote_number']})")

print()
print(f"   📊 Resumen:")
print(f"      Nuevos:      {cambios_detectados['nuevos']}")
print(f"      Modificados: {cambios_detectados['modificados']}")
print(f"      Sin cambios: {cambios_detectados['sin_cambios']}")

# ===================================================================
# PASO 7: VERIFICAR sales_operation EN POSTGRESQL
# ===================================================================

print()
print("📊 PASO 7: Verificando sales_operation en PostgreSQL...")
print()

pg_cursor.execute(
    """SELECT COUNT(*) FROM sales_operation WHERE operation_type = 'BUDGET'"""
)

total_sales = pg_cursor.fetchone()[0]
print(f"   📊 Total de BUDGET en PostgreSQL: {total_sales}")

# Mostrar últimos budgets
pg_cursor.execute(
    """SELECT correlative, document_no, total, created_at
    FROM sales_operation
    WHERE operation_type = 'BUDGET'
    ORDER BY correlative DESC
    LIMIT 5"""
)

budgets = pg_cursor.fetchall()
if budgets:
    print(f"   ✅ Últimos {len(budgets)} budgets:")
    for idx, (corr, doc_no, total, created) in enumerate(budgets, 1):
        print(f"      {idx}. Correlative: {corr} | Doc: {doc_no} | "
              f"Total: ${total:.2f} | {created}")

# ===================================================================
# PASO 8: VERIFICAR SI EXISTEN LOS QUOTES EN POSTGRESQL
# ===================================================================

print()
print("🔍 PASO 8: Verificando si los quotes de MySQL están en PostgreSQL...")
print()

for quote in quotes[:3]:  # Solo primeros 3
    quote_id = str(quote['id'])
    quote_number = quote['quote_number']

    pg_cursor.execute(
        """SELECT correlative, document_no, total
        FROM sales_operation
        WHERE operation_type = 'BUDGET' AND document_no = %s""",
        (quote_number,)
    )

    resultado = pg_cursor.fetchone()

    if resultado:
        correlative, doc_no, total = resultado
        print(f"   ✅ Quote #{quote_id} ({quote_number}) está en PostgreSQL")
        print(f"      → Correlative: {correlative} | Total: ${total:.2f}")
    else:
        print(f"   ❌ Quote #{quote_id} ({quote_number}) NO está en PostgreSQL")
        print(f"      💡 Debería sincronizarse")

# ===================================================================
# PASO 9: DIAGNÓSTICO FINAL
# ===================================================================

print()
print("=" * 80)
print("📊 DIAGNÓSTICO FINAL")
print("=" * 80)
print()

problemas = []
recomendaciones = []

if total_quotes == 0:
    problemas.append("❌ NO hay quotes en MySQL")
    recomendaciones.append("💡 Crea quotes en MySQL primero")
elif cambios_detectados['nuevos'] == 0 and cambios_detectados['modificados'] == 0:
    problemas.append("⚠️ Todos los quotes ya están sincronizados")
    recomendaciones.append("💡 Crea o modifica un quote en MySQL para probar")
elif cambios_detectados['nuevos'] > 0:
    problemas.append(f"✅ Hay {cambios_detectados['nuevos']} quotes nuevos que DEBERÍAN sincronizar")
    recomendaciones.append("💡 Ejecuta la sincronización manualmente")

if total_sales == 0:
    problemas.append("❌ NO hay BUDGET en PostgreSQL")
    recomendaciones.append("💡 La sincronización nunca se ha ejecutado o falla")
elif total_sales < total_quotes:
    problemas.append(f"⚠️ Hay menos budgets ({total_sales}) que quotes ({total_quotes})")
    recomendaciones.append("💡 Faltan quotes por sincronizar")

print("PROBLEMAS DETECTADOS:")
if problemas:
    for p in problemas:
        print(f"  {p}")
else:
    print("  ✅ No se detectaron problemas")

print()
print("RECOMENDACIONES:")
if recomendaciones:
    for r in recomendaciones:
        print(f"  {r}")
else:
    print("  ✅ Todo parece funcionar correctamente")

print()
print("🎯 PRÓXIMOS PASOS:")
print()
print("1. Si hay quotes nuevos que NO sincronizan:")
print("   → Revisa el log de sincronización completo")
print("   → Ejecuta: python3 sync_system.py")
print()
print("2. Si NO hay quotes en MySQL:")
print("   → Crea quotes en el sistema MySQL")
print("   → Vuelve a ejecutar este test")
print()
print("3. Si hay errores en el log:")
print("   → Verifica que sync_hashes esté inicializado")
print("   → Verifica conexión a bases de datos")
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
