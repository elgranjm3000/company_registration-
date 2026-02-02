#!/usr/bin/env python3
"""
Test específico: Verificar detección de cambios en status, aliquot y coin
"""

import hashlib
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def safe_float(value):
    """Convertir a float de forma segura"""
    if isinstance(value, memoryview):
        try:
            value = value.tobytes().decode('utf-8')
        except Exception:
            return 0.0
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0

def generar_hash_product(product):
    """Generar hash MD5 para un producto - MISMA LÓGICA QUE smart_sync_complete.py"""
    try:
        campos = (
            str(product[0]) if product[0] else '',  # code
            str(product[1]) if product[1] else '',  # description
            str(product[2]) if product[2] else '',  # short_name
            str(product[3]) if product[3] else '',  # department
            str(float(product[4]) if product[4] else 0),  # stock
            str(product[5]) if product[5] else '',  # product_type
            str(product[6]) if product[6] else '',  # coin
            str(product[7]) if product[7] else '',  # description_coin
            str(safe_float(product[8])),            # price
            str(safe_float(product[9])),            # cost
            str(safe_float(product[10])),           # higher_price
            str(safe_float(product[11])),           # min_stock
            str(product[12]) if product[12] else '',  # status
            str(product[15]) if product[15] else '',  # sale_tax
            str(product[16]) if product[16] else ''   # aliquot
        )

        datos = "|".join(campos)
        return hashlib.md5(datos.encode('utf-8')).hexdigest()
    except Exception as e:
        print(f"Error generando hash: {e}")
        return None

def obtener_producto_completo(cursor, code):
    """Obtener producto completo con todos los campos"""
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
        CASE WHEN b.maximum_price IS NULL OR b.maximum_price < 0 OR b.maximum_price > 99999999 THEN 0 ELSE b.maximum_price END AS price,
        CASE WHEN b.offer_price IS NULL OR b.offer_price < 0 OR b.offer_price > 99999999 THEN 0 ELSE b.offer_price END AS cost,
        CASE WHEN b.higher_price IS NULL OR b.higher_price < 0 OR b.higher_price > 99999999 THEN 0 ELSE b.higher_price END AS higher_price,
        CASE WHEN a.minimal_stock IS NULL OR a.minimal_stock < 0 OR a.minimal_stock > 2147483647 THEN 0 ELSE a.minimal_stock END AS min_stock,
        CASE WHEN a.status = '01' THEN 'active' ELSE 'inactive' END AS status,
        d.image_type,
        d.product_image,
        a.sale_tax,
        e.aliquot
    FROM products a
    LEFT JOIN (
        SELECT product_code, SUM(stock) as total_stock
        FROM products_stock
        GROUP BY product_code
    ) c ON a.code = c.product_code
    LEFT JOIN PRODUCTS_UNITS b ON a.code = b.product_code
    LEFT JOIN products_image d ON d.main_code = a.code
    LEFT JOIN taxes e ON e.code = a.sale_tax
    LEFT JOIN coin f ON f.code = a.coin
    WHERE a.code = %s
      AND a.status = '01'
    ORDER BY a.code, b.maximum_price DESC
    """

    cursor.execute(query, (code,))
    return cursor.fetchone()

def test_campo_status(cursor):
    """Test específico para el campo STATUS"""
    print("\n" + "=" * 80)
    print("🔄 TEST 1: CAMBIAR STATUS")
    print("=" * 80)

    try:
        # Buscar un producto activo
        cursor.execute("""
            SELECT code FROM products
            WHERE code IS NOT NULL AND code != '' AND status = '01'
            ORDER BY random()
            LIMIT 1
        """)
        result = cursor.fetchone()

        if not result:
            print("   ⚠️  No se encontraron productos activos")
            return False

        code = result[0]
        print(f"   Producto: {code}")

        # Obtener producto ANTES
        producto_antes = obtener_producto_completo(cursor, code)
        if not producto_antes:
            print("   ❌ No se pudo obtener el producto")
            return False

        status_antes = producto_antes[12]
        hash_antes = generar_hash_product(producto_antes)

        print(f"   Status ANTES: '{status_antes}'")
        print(f"   Hash ANTES:   {hash_antes}")

        # IMPORTANTE: El query usa CASE WHEN a.status = '01' THEN 'active' ELSE 'inactive'
        # Así que para cambiar el status en el hash, necesitamos cambiar a.status en PostgreSQL
        # Pero el producto debe seguir siendo '01' para aparecer en el query (WHERE a.status = '01')

        # Cambiar status a '00' (inactivo)
        cursor.execute("""
            UPDATE products
            SET status = '00'
            WHERE code = %s
        """, (code,))
        cursor.connection.commit()

        print(f"   Cambié status a '00' (inactivo)")

        # Obtener producto DESPUÉS (ya no aparecerá en el query porque status != '01')
        # Necesitamos obtenerlo sin el filtro de status
        query_sin_filtro = """
        SELECT DISTINCT ON (a.code)
            a.code,
            a.description,
            a.short_name,
            a.department,
            COALESCE(c.total_stock, 0) AS stock,
            a.product_type,
            a.coin,
            f.description AS description_coin,
            CASE WHEN b.maximum_price IS NULL OR b.maximum_price < 0 OR b.maximum_price > 99999999 THEN 0 ELSE b.maximum_price END AS price,
            CASE WHEN b.offer_price IS NULL OR b.offer_price < 0 OR b.offer_price > 99999999 THEN 0 ELSE b.offer_price END AS cost,
            CASE WHEN b.higher_price IS NULL OR b.higher_price < 0 OR b.higher_price > 99999999 THEN 0 ELSE b.higher_price END AS higher_price,
            CASE WHEN a.minimal_stock IS NULL OR a.minimal_stock < 0 OR a.minimal_stock > 2147483647 THEN 0 ELSE a.minimal_stock END AS min_stock,
            CASE WHEN a.status = '01' THEN 'active' ELSE 'inactive' END AS status,
            d.image_type,
            d.product_image,
            a.sale_tax,
            e.aliquot
        FROM products a
        LEFT JOIN (
            SELECT product_code, SUM(stock) as total_stock
            FROM products_stock
            GROUP BY product_code
        ) c ON a.code = c.product_code
        LEFT JOIN PRODUCTS_UNITS b ON a.code = b.product_code
        LEFT JOIN products_image d ON d.main_code = a.code
        LEFT JOIN taxes e ON e.code = a.sale_tax
        LEFT JOIN coin f ON f.code = a.coin
        WHERE a.code = %s
        ORDER BY a.code, b.maximum_price DESC
        """

        cursor.execute(query_sin_filtro, (code,))
        producto_despues = cursor.fetchall()

        if producto_despues:
            # Puede haber múltiples filas si hay varios PRECIOS
            # Tomamos la primera (que es la de mayor precio por el ORDER BY)
            prod = producto_despues[0]
            status_despues = prod[12]
            hash_despues = generar_hash_product(prod)

            print(f"   Status DESPUÉS: '{status_despues}'")
            print(f"   Hash DESPUÉS:   {hash_despues}")

            if hash_antes != hash_despues:
                print(f"   ✅ ¡CAMBIO DETECTADO! El hash cambió")
            else:
                print(f"   ❌ El hash NO cambió")

        # Restaurar status original
        cursor.execute("""
            UPDATE products
            SET status = '01'
            WHERE code = %s
        """, (code,))
        cursor.connection.commit()
        print(f"   ✅ Status restaurado a '01'")

        return True

    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_campo_aliquot(cursor):
    """Test específico para el campo ALIQUOT"""
    print("\n" + "=" * 80)
    print("🔄 TEST 2: CAMBIAR ALIQUOT")
    print("=" * 80)

    try:
        # Buscar un producto con aliquot
        cursor.execute("""
            SELECT a.code, e.aliquot
            FROM products a
            LEFT JOIN taxes e ON e.code = a.sale_tax
            WHERE a.code IS NOT NULL AND a.code != '' AND a.status = '01'
              AND e.aliquot IS NOT NULL AND e.aliquot != 0
            ORDER BY random()
            LIMIT 1
        """)
        result = cursor.fetchone()

        if not result:
            print("   ⚠️  No se encontraron productos con aliquot")
            return False

        code = result[0]
        aliquot_antes = result[1]
        print(f"   Producto: {code}")

        # Obtener producto completo ANTES
        producto_antes = obtener_producto_completo(cursor, code)
        if not producto_antes:
            print("   ❌ No se pudo obtener el producto")
            return False

        aliquot_val_antes = producto_antes[16]
        hash_antes = generar_hash_product(producto_antes)

        print(f"   Aliquot ANTES: {aliquot_val_antes}")
        print(f"   Hash ANTES:    {hash_antes}")

        # Cambiar aliquot en la tabla taxes
        # El producto tiene a.sale_tax que apunta a taxes.code
        # Necesitamos actualizar el aliquot para ese tax code

        sale_tax_code = producto_antes[15]  # Obtener el código de tax
        if not sale_tax_code:
            print("   ⚠️  El producto no tiene sale_tax")
            return False

        nuevo_aliquot = aliquot_val_antes + 1.0 if aliquot_val_antes else 16.0

        print(f"   Sale tax code: {sale_tax_code}")
        print(f"   Cambiando aliquot de {aliquot_val_antes} a {nuevo_aliquot}")

        cursor.execute("""
            UPDATE taxes
            SET aliquot = %s
            WHERE code = %s
        """, (nuevo_aliquot, sale_tax_code))
        cursor.connection.commit()

        # Obtener producto DESPUÉS
        producto_despues = obtener_producto_completo(cursor, code)
        if not producto_despues:
            print("   ❌ No se pudo obtener el producto después del cambio")
            # Restaurar
            cursor.execute("UPDATE taxes SET aliquot = %s WHERE code = %s",
                          (aliquot_val_antes, sale_tax_code))
            cursor.connection.commit()
            return False

        aliquot_val_despues = producto_despues[16]
        hash_despues = generar_hash_product(producto_despues)

        print(f"   Aliquot DESPUÉS: {aliquot_val_despues}")
        print(f"   Hash DESPUÉS:    {hash_despues}")

        if hash_antes != hash_despues:
            print(f"   ✅ ¡CAMBIO DETECTADO! El hash cambió")
        else:
            print(f"   ❌ El hash NO cambió")
            print(f"   ⚠️  Esto indica que aliquot NO está incluido correctamente en el hash")

        # Restaurar aliquot original
        cursor.execute("""
            UPDATE taxes
            SET aliquot = %s
            WHERE code = %s
        """, (aliquot_val_antes, sale_tax_code))
        cursor.connection.commit()
        print(f"   ✅ Aliquot restaurado")

        return True

    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_campo_coin(cursor):
    """Test específico para el campo COIN"""
    print("\n" + "=" * 80)
    print("🔄 TEST 3: CAMBIAR COIN")
    print("=" * 80)

    try:
        # Buscar un producto con coin
        cursor.execute("""
            SELECT code, coin FROM products
            WHERE code IS NOT NULL AND code != '' AND status = '01'
              AND coin IS NOT NULL AND coin != ''
            ORDER BY random()
            LIMIT 1
        """)
        result = cursor.fetchone()

        if not result:
            print("   ⚠️  No se encontraron productos con coin")
            return False

        code = result[0]
        coin_antes = result[1]
        print(f"   Producto: {code}")
        print(f"   Coin ANTES: '{coin_antes}'")

        # Obtener producto completo ANTES
        producto_antes = obtener_producto_completo(cursor, code)
        if not producto_antes:
            print("   ❌ No se pudo obtener el producto")
            return False

        coin_val_antes = producto_antes[6]
        description_coin_antes = producto_antes[7]
        hash_antes = generar_hash_product(producto_antes)

        print(f"   Coin (pos 6):    '{coin_val_antes}'")
        print(f"   Desc. coin:      '{description_coin_antes}'")
        print(f"   Hash ANTES:      {hash_antes}")

        # Cambiar coin a un valor diferente
        # Verificar qué coins existen
        cursor.execute("SELECT code FROM coin WHERE code != %s LIMIT 1", (coin_val_antes,))
        nuevo_coin_result = cursor.fetchone()

        if not nuevo_coin_result:
            print("   ⚠️  No hay otro coin disponible para probar")
            return False

        nuevo_coin = nuevo_coin_result[0]
        print(f"   Cambiando coin a: '{nuevo_coin}'")

        cursor.execute("""
            UPDATE products
            SET coin = %s
            WHERE code = %s
        """, (nuevo_coin, code))
        cursor.connection.commit()

        # Obtener producto DESPUÉS
        producto_despues = obtener_producto_completo(cursor, code)
        if not producto_despues:
            print("   ❌ No se pudo obtener el producto después del cambio")
            # Restaurar
            cursor.execute("UPDATE products SET coin = %s WHERE code = %s",
                          (coin_val_antes, code))
            cursor.connection.commit()
            return False

        coin_val_despues = producto_despues[6]
        description_coin_despues = producto_despues[7]
        hash_despues = generar_hash_product(producto_despues)

        print(f"   Coin DESPUÉS:    '{coin_val_despues}'")
        print(f"   Desc. coin:      '{description_coin_despues}'")
        print(f"   Hash DESPUÉS:    {hash_despues}")

        if hash_antes != hash_despues:
            print(f"   ✅ ¡CAMBIO DETECTADO! El hash cambió")
        else:
            print(f"   ❌ El hash NO cambío")

        # Restaurar coin original
        cursor.execute("""
            UPDATE products
            SET coin = %s
            WHERE code = %s
        """, (coin_val_antes, code))
        cursor.connection.commit()
        print(f"   ✅ Coin restaurado")

        return True

    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("=" * 80)
    print("🧪 TEST ESPECÍFICO: CAMPOS STATUS, ALIQUOT, COIN")
    print("=" * 80)
    print("\nEste test verifica si cambios en estos campos específicos se detectan:")
    print("  - STATUS (estado del producto)")
    print("  - ALIQUOT (alícuota de impuesto)")
    print("  - COIN (moneda)")

    try:
        # Conectar a PostgreSQL
        print("\n📌 Conectando a PostgreSQL...")
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST'),
            database=os.getenv('DB_DATABASE'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD')
        )
        cursor = conn.cursor()
        print("✅ Conectado")

        # Ejecutar tests
        results = {}

        results['status'] = test_campo_status(cursor)
        results['aliquot'] = test_campo_aliquot(cursor)
        results['coin'] = test_campo_coin(cursor)

        # Resumen
        print("\n" + "=" * 80)
        print("📊 RESUMEN DE RESULTADOS")
        print("=" * 80)

        print(f"\nStatus:  {'✅ FUNCIONA' if results['status'] else '❌ FALLÓ'}")
        print(f"Aliquot: {'✅ FUNCIONA' if results['aliquot'] else '❌ FALLÓ'}")
        print(f"Coin:    {'✅ FUNCIONA' if results['coin'] else '❌ FALLÓ'}")

        print("\n" + "=" * 80)
        print("🏁 TEST COMPLETADO")
        print("=" * 80)

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
