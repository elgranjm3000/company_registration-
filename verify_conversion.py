#!/usr/bin/env python3
"""
Verificar si los productos VES se convirtieron a USD en MySQL
"""
import psycopg2
import pymysql
import json

# Cargar configuración
with open('.sync_config.json', 'r') as f:
    config = json.load(f)

# Conectar a PostgreSQL
pg_conn = psycopg2.connect(
    host=config['postgres_host'],
    database=config['postgres_database'],
    user=config['postgres_user'],
    password=config['postgres_password']
)
pg_cursor = pg_conn.cursor()

# Conectar a MySQL
mysql_conn = pymysql.connect(
    host=config['mysql_host'],
    user=config['mysql_user'],
    password=config['mysql_password'],
    database=config['mysql_database']
)
mysql_cursor = mysql_conn.cursor()

# Obtener company
company_id = config.get('company_rif')
if not company_id:
    mysql_cursor.execute("SELECT id FROM companies LIMIT 1")
    company = mysql_cursor.fetchone()
    if company:
        company_id = company[0]
    else:
        print("❌ No hay company")
        exit(1)

print("="*70)
print("🔍 VERIFICANDO CONVERSIÓN VES → USD")
print("="*70)

# Obtener productos VES de PostgreSQL
pg_cursor.execute("""
    SELECT p.code, p.description, p.coin,
           COALESCE(pu.higher_price, 0) as price,
           COALESCE(pu.unitary_cost, 0) as cost
    FROM products p
    LEFT JOIN products_units pu ON p.code = pu.product_code AND pu.unit = '00'
    WHERE p.coin = '01'
    ORDER BY p.code
""")

productos_ves = pg_cursor.fetchall()

print(f"\n📊 Encontrados {len(productos_ves)} productos con coin='01'\n")

conversiones_ok = 0
conversiones_fail = 0
no_existe_mysql = 0

for code, desc, coin, price_pg, cost_pg in productos_ves:
    print(f"📦 {code}: {desc}")
    print(f"   PostgreSQL (VES): price={price_pg}, cost={cost_pg}")

    # Buscar en MySQL
    mysql_cursor.execute(
        "SELECT price, cost FROM products WHERE code = %s AND company_id = %s",
        (code, company_id)
    )
    prod_mysql = mysql_cursor.fetchone()

    if not prod_mysql:
        print(f"   ❌ NO EXISTE EN MYSQL")
        no_existe_mysql += 1
    else:
        price_mysql, cost_mysql = prod_mysql
        print(f"   MySQL (USD?):   price={price_mysql}, cost={cost_mysql}")

        # Verificar si se convirtió
        if price_pg and price_mysql:
            if abs(float(price_pg) - float(price_mysql)) < 0.01:
                print(f"   ⚠️  NO SE CONVIRTIÓ (tiene el mismo valor)")
                conversiones_fail += 1
            else:
                tasa = float(price_pg) / float(price_mysql)
                print(f"   ✅ CONVERSIÓN OK (tasa: {tasa:.2f} VES/USD)")
                conversiones_ok += 1
    print()

print("="*70)
print("📋 RESUMEN")
print("="*70)
print(f"✅ Conversiones correctas: {conversiones_ok}")
print(f"⚠️  Sin convertir: {conversiones_fail}")
print(f"❌ No existen en MySQL: {no_existe_mysql}")
print()

if conversiones_fail > 0 or no_existe_mysql > 0:
    print("💡 ACCIONES RECOMENDADAS:")
    if no_existe_mysql > 0:
        print("   - Ejecuta sincronización: python sync_system.py --mode sync")
    if conversiones_fail > 0:
        print("   - Verifica que la API de tipo de cambio esté funcionando")
        print("   - Revisa los logs de sincronización")

# Probar API de tipo de cambio
print("\n" + "="*70)
print("💰 TIPO DE CAMBIO ACTUAL")
print("="*70)
try:
    import requests
    url = "https://api.exchangerate-api.com/v4/latest/USD"
    response = requests.get(url, timeout=10)

    if response.status_code == 200:
        data = response.json()
        if 'rates' in data and 'VES' in data['rates']:
            tasa_actual = data['rates']['VES']
            print(f"✅ Tasa actual: {tasa_actual:.2f} VES/USD")
            print(f"\n📊 Ejemplos de conversión:")
            print(f"   10 VES  = {10/tasa_actual:.4f} USD")
            print(f"   20 VES  = {20/tasa_actual:.4f} USD")
            print(f"   30 VES  = {30/tasa_actual:.4f} USD")
            print(f"   40 VES  = {40/tasa_actual:.4f} USD")
            print(f"   50 VES  = {50/tasa_actual:.4f} USD")
        else:
            print("❌ La API no devolvió tasa VES")
    else:
        print(f"❌ Error API: status {response.status_code}")
except Exception as e:
    print(f"❌ Error: {e}")

pg_cursor.close()
pg_conn.close()
mysql_cursor.close()
mysql_conn.close()
