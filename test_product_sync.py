#!/usr/bin/env python3
"""
Test de diagnóstico de sincronización de productos
Para identificar por qué no se insertan productos en MySQL
"""

import sys
sys.path.insert(0, '/home/muentes/company_registration')

import psycopg2
import pymysql
from dotenv import load_dotenv
import os

load_dotenv()

print("=" * 80)
print("🔍 TEST DE DIAGNÓSTICO - SINCRONIZACIÓN DE PRODUCTOS")
print("=" * 80)
print()

# Conexiones
print("1️⃣  CONECTANDO A BASES DE DATOS...")
print("-" * 80)

try:
    pg_conn = psycopg2.connect(
        host=os.getenv('DB_HOST'),
        database=os.getenv('DB_DATABASE'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD')
    )
    pg_cursor = pg_conn.cursor()
    print("   ✅ PostgreSQL conectado")
except Exception as e:
    print(f"   ❌ Error PostgreSQL: {e}")
    sys.exit(1)

try:
    mysql_conn = pymysql.connect(
        host='91.238.160.176',
        port=3306,
        database='chrystal_movil',
        user='chrystal_app',
        password='muentes123.',
        charset='utf8mb4'
    )
    mysql_cursor = mysql_conn.cursor()
    print("   ✅ MySQL conectado")
except Exception as e:
    print(f"   ❌ Error MySQL: {e}")
    sys.exit(1)

print()

# Obtener company_id
print("2️⃣  OBTENIENDO COMPANY_ID...")
print("-" * 80)

mysql_cursor.execute(
    "SELECT company_id FROM acceso WHERE id_fiscal = %s AND correo_electronico = %s LIMIT 1",
    ('J502741283', 'multiserviciosleblanc@gmail.com')
)
company_result = mysql_cursor.fetchone()

if not company_result:
    print("   ❌ No se encontró company_id")
    sys.exit(1)

company_id = company_result[0]
print(f"   ✅ Company ID: {company_id}")
print()

# Contar productos en PostgreSQL
print("3️⃣  CONTANDO PRODUCTOS EN POSTGRESQL...")
print("-" * 80)

pg_cursor.execute("""
    SELECT COUNT(*)
    FROM products a
    WHERE a.code IS NOT NULL AND a.code != ''
    AND a.status = '01'
""")
pg_products_count = pg_cursor.fetchone()[0]
print(f"   ✅ Total productos activos en PostgreSQL: {pg_products_count}")
print()

# Obtener algunos productos de muestra
print("4️⃣  OBTENIENDO MUESTRA DE PRODUCTOS...")
print("-" * 80)

pg_cursor.execute("""
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
    WHERE a.code IS NOT NULL AND a.code != ''
    AND a.status = '01'
    ORDER BY a.code
    LIMIT 5
""")

productos_muestra = pg_cursor.fetchall()
print(f"   ✅ Muestra de {len(productos_muestra)} productos:")

for i, p in enumerate(productos_muestra, 1):
    code, description, short_name, department, stock, product_type, coin, description_coin, price, cost, min_stock, status = p
    print(f"   {i}. Code: {code:10} | Desc: {description[:30]:30} | Dept: {department} | Coin: {coin} | Price: {price}")

print()

# Verificar categorías en MySQL
print("5️⃣  VERIFICANDO CATEGORÍAS EN MYSQL...")
print("-" * 80)

mysql_cursor.execute("""
    SELECT id, name, description
    FROM categories
    WHERE company_id = %s
    LIMIT 10
""", (company_id,))

categories_mysql = mysql_cursor.fetchall()
print(f"   ✅ Categorías en MySQL para company_id={company_id}: {len(categories_mysql)}")

for cat in categories_mysql[:5]:
    print(f"   - ID: {cat[0]:5} | Name: {cat[1]:10} | Desc: {cat[2]}")

print()

# Verificar productos en MySQL
print("6️⃣  VERIFICANDO PRODUCTOS EN MYSQL...")
print("-" * 80)

mysql_cursor.execute("""
    SELECT COUNT(*)
    FROM products
    WHERE company_id = %s
""", (company_id,))

mysql_products_count = mysql_cursor.fetchone()[0]
print(f"   ✅ Productos en MySQL para company_id={company_id}: {mysql_products_count}")
print()

# Intentar insertar UN producto de prueba
print("7️⃣  TEST DE INSERCIÓN DE UN PRODUCTO...")
print("-" * 80)

if productos_muestra:
    test_product = productos_muestra[0]
    code, description, short_name, department, stock, product_type, coin, description_coin, price, cost, min_stock, status = test_product

    print(f"   📦 Producto de prueba: {code}")
    print(f"   - Description: {description}")
    print(f"   - Short name: {short_name}")
    print(f"   - Department: {department}")
    print(f"   - Stock: {stock}")
    print(f"   - Price: {price}")
    print(f"   - Cost: {cost}")
    print(f"   - Status: {status}")

    # Verificar si la categoría existe
    print()
    print(f"   🔍 Verificando si categoría '{department}' existe en MySQL...")
    mysql_cursor.execute(
        "SELECT id FROM categories WHERE company_id = %s AND name = %s",
        (company_id, department)
    )
    category_result = mysql_cursor.fetchone()

    if not category_result:
        print(f"   ❌ Categoría '{department}' NO existe en MySQL")
        print(f"   ⚠️  Este es el PROBLEMA: los productos no se insertan porque su categoría no existe")

        # Intentar crear la categoría
        print()
        print(f"   🔧 Intentando crear categoría '{department}'...")
        try:
            mysql_cursor.execute("""
                INSERT INTO categories (company_id, name, description, status, created_at, updated_at)
                VALUES (%s, %s, %s, 'active', NOW(), NOW())
            """, (company_id, department, f"Categoría {department}"))
            mysql_conn.commit()
            print(f"   ✅ Categoría creada")

            # Obtener el ID
            mysql_cursor.execute(
                "SELECT id FROM categories WHERE company_id = %s AND name = %s",
                (company_id, department)
            )
            category_result = mysql_cursor.fetchone()
            category_id = category_result[0]
            print(f"   ✅ Category ID: {category_id}")
        except Exception as e:
            print(f"   ❌ Error creando categoría: {e}")
            category_id = None
    else:
        category_id = category_result[0]
        print(f"   ✅ Categoría existe: ID={category_id}")

    # Si tenemos categoría, intentar insertar el producto
    if category_id:
        print()
        print(f"   🔧 Intentando insertar producto '{code}'...")

        # Verificar si ya existe
        mysql_cursor.execute(
            "SELECT id FROM products WHERE code = %s AND company_id = %s",
            (code, company_id)
        )
        existing = mysql_cursor.fetchone()

        if existing:
            print(f"   ⚠️  Producto ya existe en MySQL (ID: {existing[0]})")
            print(f"   🔧 Intentando actualizar...")

            try:
                mysql_cursor.execute("""
                    UPDATE products SET
                        name = %s,
                        description = %s,
                        price = %s,
                        cost = %s,
                        stock = %s,
                        status = %s,
                        category_id = %s,
                        updated_at = NOW()
                    WHERE id = %s
                """, (
                    short_name or description,
                    description,
                    price,
                    cost,
                    stock,
                    status,
                    category_id,
                    existing[0]
                ))
                mysql_conn.commit()
                print(f"   ✅ Producto actualizado")
            except Exception as e:
                print(f"   ❌ Error actualizando: {e}")
                mysql_conn.rollback()
        else:
            print(f"   🔧 Producto no existe, intentando insertar...")

            try:
                mysql_cursor.execute("""
                    INSERT INTO products (
                        company_id, code, name, description, price, cost,
                        stock, status, category_id, sale_tax, created_at, updated_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW()
                    )
                """, (
                    company_id,
                    code,
                    short_name or description,
                    description,
                    price,
                    cost,
                    stock,
                    status,
                    category_id,
                    16  # sale_tax
                ))
                mysql_conn.commit()
                print(f"   ✅ Producto insertado correctamente")
                print(f"   ✅ Last row ID: {mysql_cursor.lastrowid}")
            except Exception as e:
                print(f"   ❌ Error insertando: {e}")
                print(f"   ❌ Error type: {type(e).__name__}")
                mysql_conn.rollback()

        # Verificar que se haya insertado
        print()
        print(f"   🔍 Verificando inserción...")
        mysql_cursor.execute(
            "SELECT id, code, name FROM products WHERE code = %s AND company_id = %s",
            (code, company_id)
        )
        verify = mysql_cursor.fetchone()
        if verify:
            print(f"   ✅ Producto verificado en MySQL:")
            print(f"   - ID: {verify[0]}")
            print(f"   - Code: {verify[1]}")
            print(f"   - Name: {verify[2]}")
        else:
            print(f"   ❌ Producto NO encontrado en MySQL después de insertar")

print()
print("=" * 80)
print("✅ TEST COMPLETADO")
print("=" * 80)

pg_cursor.close()
pg_conn.close()
mysql_cursor.close()
mysql_conn.close()
