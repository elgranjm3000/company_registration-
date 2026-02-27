#!/usr/bin/env python3
"""
Test específico para verificar la conversión de VES a USD durante la sincronización
"""

import sys
sys.path.insert(0, '/home/muentes/company_registration')

from dotenv import load_dotenv
import os
load_dotenv()

import psycopg2
import pymysql

# Conectar a PostgreSQL
print("1️⃣ Conectando a PostgreSQL...")
pg_conn = psycopg2.connect(
    host=os.getenv('DB_HOST'),
    database=os.getenv('DB_DATABASE'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD')
)
pg_cursor = pg_conn.cursor()
print("   ✅ Conectado")

# Conectar a MySQL
print("\n2️⃣ Conectando a MySQL...")
mysql_conn = pymysql.connect(
    host='91.238.160.176',
    port=3306,
    database='chrystal_movil',
    user='chrystal_app',
    password='muentes123.',
    charset='utf8mb4'
)
mysql_cursor = mysql_conn.cursor()
print("   ✅ Conectado")

# Obtener company_id
print("\n3️⃣ Obteniendo company_id...")
mysql_cursor.execute(
    "SELECT id FROM acceso WHERE id_fiscal = %s AND correo_electronico = %s LIMIT 1",
    ('J502741283', 'multiserviciosleblanc@gmail.com')
)
company = mysql_cursor.fetchone()
if not company:
    print("   ❌ Empresa no encontrada")
    sys.exit(1)
company_id = company[0]
print(f"   ✅ Company ID: {company_id}")

# Obtener UN producto con coin='01' de PostgreSQL
print("\n4️⃣ Obteniendo un producto con coin='01' de PostgreSQL...")
query = """
SELECT DISTINCT ON (a.code)
    a.code,
    a.description,
    a.short_name,
    a.department,
    COALESCE(c.total_stock, 0) AS stock,
    a.product_type,
    a.coin,
    f.description AS description_coin,
    CASE
        WHEN b.maximum_price IS NULL OR b.maximum_price < 0 OR b.maximum_price > 99999999
        THEN 0
        ELSE b.maximum_price
    END AS price,
    CASE
        WHEN b.offer_price IS NULL OR b.offer_price < 0 OR b.offer_price > 99999999
        THEN 0
        ELSE b.offer_price
    END AS cost,
    CASE
        WHEN b.higher_price IS NULL OR b.higher_price < 0 OR b.higher_price > 99999999
        THEN 0
        ELSE b.higher_price
    END AS higher_price,
    a.minimal_stock AS min_stock,
    CASE WHEN a.status = '01' THEN 'active' ELSE 'inactive' END AS status
FROM products a
LEFT JOIN (
    SELECT product_code, SUM(stock) as total_stock
    FROM products_stock
    GROUP BY product_code
) c ON a.code = c.product_code
LEFT JOIN products_units b ON a.code = b.product_code and b.unit = '00'
LEFT JOIN coin f ON f.code = a.coin
WHERE a.code IS NOT NULL
  AND a.code != ''
  AND a.coin = '01'
LIMIT 1
"""
pg_cursor.execute(query)
producto = pg_cursor.fetchone()

if not producto:
    print("   ❌ No hay productos con coin='01'")
    sys.exit(1)

# Desempaquetar
(code, description, short_name, department, stock, product_type,
 coin, description_coin, price, cost, higher_price, min_stock, status) = producto

print(f"   ✅ Producto encontrado:")
print(f"      Code: {code}")
print(f"      Description: {description}")
print(f"      Coin: {coin} (índice 6)")
print(f"      Price: {price} VES")
print(f"      Cost: {cost} VES")
print(f"      Higher Price: {higher_price} VES")

# Verificar el índice correcto
print(f"\n5️⃣ Verificando índices:")
print(f"   producto[6] = {producto[6]} (coin)")
print(f"   producto[7] = {producto[7]} (description_coin)")

# Obtener tipo de cambio
print(f"\n6️⃣ Obteniendo tipo de cambio...")
import requests
url = "https://api.exchangerate-api.com/v4/latest/USD"
response = requests.get(url, timeout=10)
if response.status_code == 200:
    data = response.json()
    tipo_cambio = float(data['rates']['VES'])
    print(f"   ✅ Tipo de cambio: {tipo_cambio:.2f} VES/USD")
else:
    print(f"   ❌ Error obteniendo tipo de cambio")
    tipo_cambio = 417.36

# Convertir a USD
print(f"\n7️⃣ Convirtiendo a USD...")
price_usd = round(price / tipo_cambio, 4) if price else 0
cost_usd = round(cost / tipo_cambio, 4) if cost else 0
higher_price_usd = round(higher_price / tipo_cambio, 4) if higher_price else 0

print(f"   Price: {price} VES → {price_usd} USD")
print(f"   Cost: {cost} VES → {cost_usd} USD")
print(f"   Higher Price: {higher_price} VES → {higher_price_usd} USD")

# Verificar si el producto existe en MySQL
print(f"\n8️⃣ Verificando producto en MySQL...")
mysql_cursor.execute(
    "SELECT price, cost FROM products WHERE code = %s AND company_id = %s",
    (code, company_id)
)
mysql_producto = mysql_cursor.fetchone()

if mysql_producto:
    mysql_price, mysql_cost = mysql_producto
    print(f"   Producto en MySQL:")
    print(f"      Price: {mysql_price}")
    print(f"      Cost: {mysql_cost}")

    if mysql_price == price_usd:
        print(f"   ✅ Price convertido correctamente a USD")
    else:
        print(f"   ⚠️ Price NO coincide (esperaba {price_usd}, tiene {mysql_price})")
        print(f"   Diferencia: {abs(mysql_price - price_usd)}")
else:
    print(f"   ⚠️ Producto no existe en MySQL")

# Cerrar conexiones
pg_cursor.close()
pg_conn.close()
mysql_cursor.close()
mysql_conn.close()

print(f"\n✅ Test completado")
