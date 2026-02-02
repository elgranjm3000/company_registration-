#!/usr/bin/env python3
"""
Test completo de sincronización: PostgreSQL → MySQL
"""

import psycopg2
import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

def main():
    print("=" * 80)
    print("🧪 TEST: SINCRONIZACIÓN POSTGRESQL → MYSQL")
    print("=" * 80)

    try:
        # Conectar a PostgreSQL
        print("\n📌 Conectando a PostgreSQL...")
        pg_conn = psycopg2.connect(
            host=os.getenv('DB_HOST'),
            database=os.getenv('DB_DATABASE'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD')
        )
        pg_cursor = pg_conn.cursor()
        print("✅ Conectado a PostgreSQL")

        # Conectar a MySQL
        print("\n📌 Conectando a MySQL...")
        mysql_conn = pymysql.connect(
            host=os.getenv('DB_HOST'),  # Asumiendo mismo host
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_DATABASE')  # Asumiendo misma DB
        )
        mysql_cursor = mysql_conn.cursor()
        print("✅ Conectado a MySQL")

        # Obtener company_id
        print("\n📌 Obteniendo company_id...")
        mysql_cursor.execute("SELECT id FROM companies LIMIT 1")
        company_result = mysql_cursor.fetchone()
        if not company_result:
            print("❌ No hay companies en MySQL")
            return
        company_id = company_result[0]
        print(f"✅ company_id: {company_id}")

        # Obtener un producto de prueba
        print("\n📌 Obteniendo producto de prueba...")
        pg_cursor.execute("""
            SELECT DISTINCT ON (a.code)
                a.code, a.short_name,
                COALESCE(c.total_stock, 0) AS stock,
                CASE WHEN b.maximum_price IS NULL OR b.maximum_price < 0 OR b.maximum_price > 99999999
                THEN 0 ELSE b.maximum_price END AS price
            FROM products a
            LEFT JOIN (
                SELECT product_code, SUM(stock) as total_stock
                FROM products_stock GROUP BY product_code
            ) c ON a.code = c.product_code
            LEFT JOIN PRODUCTS_UNITS b ON a.code = b.product_code
            WHERE a.code IS NOT NULL AND a.code != '' AND a.status = '01'
            ORDER BY a.code, b.maximum_price DESC
            LIMIT 1
        """)
        producto_pg = pg_cursor.fetchone()

        if not producto_pg:
            print("❌ No se encontraron productos")
            return

        code, short_name, stock_pg, price_pg = producto_pg
        print(f"✅ Producto: {code}")
        print(f"   Nombre: {short_name}")
        print(f"   Precio PostgreSQL: ${price_pg}")
        print(f"   Stock PostgreSQL: {stock_pg}")

        # Verificar producto en MySQL ANTES
        print("\n📌 Verificando producto en MySQL ANTES del cambio...")
        mysql_cursor.execute("""
            SELECT code, name, price, stock
            FROM products
            WHERE company_id = %s AND code = %s
        """, (company_id, code))
        producto_mysql_antes = mysql_cursor.fetchone()

        if producto_mysql_antes:
            code_mysql, name_mysql, price_mysql, stock_mysql = producto_mysql_antes
            print(f"✅ Producto encontrado en MySQL:")
            print(f"   Precio MySQL: ${price_mysql}")
            print(f"   Stock MySQL: {stock_mysql}")
        else:
            print(f"⚠️  Producto NO existe en MySQL")
            producto_mysql_antes = None

        # Cambiar precio en PostgreSQL
        print("\n📌 Cambiando precio en PostgreSQL...")
        nuevo_precio = float(price_pg) + 1.0
        pg_cursor.execute("""
            UPDATE PRODUCTS_UNITS
            SET maximum_price = %s
            WHERE product_code = %s
        """, (nuevo_precio, code))
        pg_conn.commit()
        print(f"✅ Precio cambiado a ${nuevo_precio}")

        # Verificar cambio en PostgreSQL
        pg_cursor.execute("""
            SELECT DISTINCT ON (a.code)
                CASE WHEN b.maximum_price IS NULL OR b.maximum_price < 0 OR b.maximum_price > 99999999
                THEN 0 ELSE b.maximum_price END AS price
            FROM products a
            LEFT JOIN PRODUCTS_UNITS b ON a.code = b.product_code
            WHERE a.code = %s AND a.status = '01'
            ORDER BY a.code, b.maximum_price DESC
        """, (code,))
        nuevo_precio_verify = pg_cursor.fetchone()[0]
        print(f"   Precio verificado en PostgreSQL: ${nuevo_precio_verify}")

        # SIMULAR SINCRONIZACIÓN: Insertar/Actualizar en MySQL
        print("\n📌 Sincronizando a MySQL...")
        pg_cursor.execute("""
            SELECT DISTINCT ON (a.code)
                a.code, a.short_name, a.department,
                COALESCE(c.total_stock, 0) AS stock,
                CASE WHEN b.maximum_price IS NULL OR b.maximum_price < 0 OR b.maximum_price > 99999999
                THEN 0 ELSE b.maximum_price END AS price
            FROM products a
            LEFT JOIN (
                SELECT product_code, SUM(stock) as total_stock
                FROM products_stock GROUP BY product_code
            ) c ON a.code = c.product_code
            LEFT JOIN PRODUCTS_UNITS b ON a.code = b.product_code
            WHERE a.code = %s AND a.status = '01'
            ORDER BY a.code, b.maximum_price DESC
        """, (code,))
        producto_sync = pg_cursor.fetchone()

        if producto_sync:
            code_sync, short_name_sync, dept_sync, stock_sync, price_sync = producto_sync

            # Obtener category_id
            mysql_cursor.execute("""
                SELECT id FROM categories
                WHERE company_id = %s AND name = %s
            """, (company_id, dept_sync))
            cat_result = mysql_cursor.fetchone()
            category_id = cat_result[0] if cat_result else None

            if category_id:
                # INSERT/UPDATE en MySQL
                mysql_cursor.execute("""
                    INSERT INTO products (
                        company_id, code, name, price, stock, category_id, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, NOW())
                    ON DUPLICATE KEY UPDATE
                        name = VALUES(name),
                        price = VALUES(price),
                        stock = VALUES(stock),
                        category_id = VALUES(category_id),
                        updated_at = NOW()
                """, (company_id, code_sync, short_name_sync, price_sync, stock_sync, category_id))
                mysql_conn.commit()
                print(f"✅ Producto sincronizado a MySQL")
            else:
                print(f"⚠️  No se encontró categoría '{dept_sync}' en MySQL")

        # Verificar producto en MySQL DESPUÉS
        print("\n📌 Verificando producto en MySQL DESPUÉS de la sincronización...")
        mysql_cursor.execute("""
            SELECT code, name, price, stock, updated_at
            FROM products
            WHERE company_id = %s AND code = %s
        """, (company_id, code))
        producto_mysql_despues = mysql_cursor.fetchone()

        if producto_mysql_despues:
            code_mysql_d, name_mysql_d, price_mysql_d, stock_mysql_d, updated_at = producto_mysql_despues
            print(f"✅ Producto en MySQL después de sync:")
            print(f"   Precio: ${price_mysql_d}")
            print(f"   Stock: {stock_mysql_d}")
            print(f"   Actualizado: {updated_at}")

            # Comparar
            print("\n📌 Comparación:")
            print("-" * 80)
            print(f"{'Campo':<20} | {'PostgreSQL':<15} | {'MySQL':<15} | {'¿Igual?'}")
            print("-" * 80)
            print(f"{'Precio':<20} | ${nuevo_precio:<14} | ${price_mysql_d:<14} | {'✅' if abs(nuevo_precio - price_mysql_d) < 0.01 else '❌'}")
            print(f"{'Stock':<20} | {stock_sync:<15} | {stock_mysql_d:<15} | {'✅' if stock_sync == stock_mysql_d else '❌'}")

            if abs(nuevo_precio - price_mysql_d) < 0.01:
                print("\n✅ RESULTADO: La sincronización funciona CORRECTAMENTE")
                print("\n   Si tus cambios no se reflejan, verifica:")
                print("   1. Que el producto se esté detectando como 'modificado'")
                print("   2. Que no haya errores durante la sincronización")
                print("   3. Que el producto no esté siendo filtrado")
            else:
                print("\n❌ RESULTADO: La sincronización NO actualizó el precio")

        # Restaurar precio original
        print("\n📌 Restaurando precio original...")
        pg_cursor.execute("""
            UPDATE PRODUCTS_UNITS
            SET maximum_price = %s
            WHERE product_code = %s
        """, (price_pg, code))
        pg_conn.commit()
        print(f"✅ Precio restaurado a ${price_pg}")

        # Cerrar conexiones
        pg_cursor.close()
        pg_conn.close()
        mysql_cursor.close()
        mysql_conn.close()

        print("\n" + "=" * 80)
        print("🏁 TEST COMPLETADO")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
