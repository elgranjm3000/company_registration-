#!/usr/bin/env python3
"""
Script de diagnóstico para verificar conversión de VES a USD
"""
import sys
import os
import json

# Cargar configuración directamente
config_file = '.sync_config.json'
if not os.path.exists(config_file):
    print(f"❌ No existe archivo de configuración: {config_file}")
    sys.exit(1)

with open(config_file, 'r') as f:
    config = json.load(f)

print("✅ Configuración cargada")

# Conectar a PostgreSQL
import psycopg2
try:
    pg_conn = psycopg2.connect(
        host=config['postgres_host'],
        database=config['postgres_database'],
        user=config['postgres_user'],
        password=config['postgres_password']
    )
    pg_cursor = pg_conn.cursor()
    print("✅ Conectado a PostgreSQL")
except Exception as e:
    print(f"❌ Error conectando a PostgreSQL: {e}")
    sys.exit(1)

# Conectar a MySQL
import pymysql
try:
    mysql_conn = pymysql.connect(
        host=config['mysql_host'],
        user=config['mysql_user'],
        password=config['mysql_password'],
        database=config['mysql_database']
    )
    mysql_cursor = mysql_conn.cursor()
    print("✅ Conectado a MySQL")
except Exception as e:
    print(f"❌ Error conectando a MySQL: {e}")
    sys.exit(1)

# Obtener company
if 'company_rif' not in config or not config['company_rif']:
    print("❌ No hay company_rif en configuración")
    # Buscar una empresa en MySQL
    mysql_cursor.execute("SELECT id FROM companies LIMIT 1")
    company = mysql_cursor.fetchone()
    if company:
        company_id = company[0]
        print(f"💡 Usando company ID: {company_id}")
    else:
        print("❌ No hay empresas en MySQL")
        sys.exit(1)
else:
    company_id = config['company_rif']

print(f"\n📋 Company ID: {company_id}")

# Buscar productos con coin='01' en PostgreSQL
print("\n🔍 Buscando productos con coin='01' en PostgreSQL...")
pg_cursor.execute("""
    SELECT code, description, coin, price, cost
    FROM products
    WHERE coin = '01'
    ORDER BY code DESC
    LIMIT 5
""")
productos_ves = pg_cursor.fetchall()

if not productos_ves:
    print("   ❌ No hay productos con coin='01' en PostgreSQL")
    print("\n💡 Sugerencia: Verifica que el campo 'coin' tenga el valor '01'")
    print("   - Puedes ejecutar: UPDATE products SET coin='01' WHERE code='TU_CODIGO';")
else:
    print(f"   ✅ Encontrados {len(productos_ves)} productos con coin='01':")
    for code, desc, coin, price, cost in productos_ves:
        print(f"\n      📦 {code}: {desc}")
        print(f"         coin={coin}, price={price}, cost={cost}")

        # Verificar si existe en MySQL
        mysql_cursor.execute(
            "SELECT code, price, cost FROM products WHERE code = %s AND company_id = %s",
            (code, company_id)
        )
        prod_mysql = mysql_cursor.fetchone()

        if prod_mysql:
            mysql_code, mysql_price, mysql_cost = prod_mysql
            print(f"         💾 MySQL: price={mysql_price}, cost={mysql_cost}")

            # Verificar si se convirtió
            if price and mysql_price:
                if abs(float(price) - float(mysql_price)) < 0.01:
                    print(f"         ⚠️  NO SE CONVIRTIÓ: MySQL tiene mismo valor que PostgreSQL (VES)")
                    print(f"         💡 Debería tener: {float(price)/36:.4f} USD (aprox, con tasa 36)")
                else:
                    tasa = float(price) / float(mysql_price) if mysql_price > 0 else 0
                    print(f"         ✅ CONVERSIÓN APLICADA: Tasa {tasa:.2f} VES/USD")
        else:
            print(f"         ⚠️  NO EXISTE EN MYSQL - Debe sincronizarse primero")

# Probar obtener tipo de cambio
print("\n💰 Probando obtener tipo de cambio VES→USD...")
try:
    import requests
    url = "https://api.exchangerate-api.com/v4/latest/USD"
    print(f"   📡 Consultando API: {url}")
    response = requests.get(url, timeout=10)

    if response.status_code == 200:
        data = response.json()
        if 'rates' in data and 'VES' in data['rates']:
            tasa = data['rates']['VES']
            print(f"   ✅ Tipo de cambio actual: {tasa:.2f} VES/USD")
            print(f"   📊 Ejemplo de conversión:")
            print(f"      1000 VES = {1000/tasa:.4f} USD")
            print(f"      5000 VES = {5000/tasa:.4f} USD")
        else:
            print(f"   ❌ La API no devolvió tasa VES")
            print(f"   Respuesta: {data}")
    else:
        print(f"   ❌ Error en API: status {response.status_code}")
except Exception as e:
    print(f"   ❌ Error obteniendo tipo de cambio: {e}")

# Cerrar conexiones
pg_cursor.close()
pg_conn.close()
mysql_cursor.close()
mysql_conn.close()

print("\n" + "="*70)
print("DIAGNÓSTICO COMPLETADO")
print("="*70)
