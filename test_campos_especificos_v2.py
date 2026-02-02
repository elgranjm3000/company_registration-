#!/usr/bin/env python3
"""
Test específico: Verificar que status, aliquot y coin están en el hash
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

def generar_hash_con_valores(product, status=None, aliquot=None, coin=None):
    """Generar hash con valores específicos para campos"""
    try:
        # Si se especifica un valor, usarlo, si no, usar el original
        p_status = status if status is not None else (str(product[12]) if product[12] else '')
        p_aliquot = aliquot if aliquot is not None else (str(product[16]) if product[16] else '')
        p_coin = coin if coin is not None else (str(product[6]) if product[6] else '')

        campos = (
            str(product[0]) if product[0] else '',  # code
            str(product[1]) if product[1] else '',  # description
            str(product[2]) if product[2] else '',  # short_name
            str(product[3]) if product[3] else '',  # department
            str(float(product[4]) if product[4] else 0),  # stock
            str(product[5]) if product[5] else '',  # product_type
            p_coin,  # coin (puede ser modificado)
            str(product[7]) if product[7] else '',  # description_coin
            str(safe_float(product[8])),            # price
            str(safe_float(product[9])),            # cost
            str(safe_float(product[10])),           # higher_price
            str(safe_float(product[11])),           # min_stock
            p_status,  # status (puede ser modificado)
            str(product[15]) if product[15] else '',  # sale_tax
            p_aliquot  # aliquot (puede ser modificado)
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

def main():
    print("=" * 80)
    print("🧪 TEST: VERIFICAR QUE STATUS, ALIQUOT Y COIN ESTÁN EN EL HASH")
    print("=" * 80)

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

        # TEST 1: Verificar que STATUS está en el hash
        print("\n" + "=" * 80)
        print("🔄 TEST 1: ¿STATUS ESTÁ EN EL HASH?")
        print("=" * 80)

        cursor.execute("""
            SELECT code FROM products
            WHERE code IS NOT NULL AND code != '' AND status = '01'
            ORDER BY random()
            LIMIT 1
        """)
        result = cursor.fetchone()

        if result:
            code = result[0]
            producto = obtener_producto_completo(cursor, code)

            if producto:
                hash_original = generar_hash_con_valores(producto)
                hash_status_cambiado = generar_hash_con_valores(producto, status='inactive')

                print(f"\n   Producto: {code}")
                print(f"   Status actual: '{producto[12]}'")
                print(f"   Hash original:     {hash_original}")
                print(f"   Hash si status='inactive': {hash_status_cambiado}")

                if hash_original != hash_status_cambiado:
                    print(f"   ✅ ¡STATUS SÍ ESTÁ en el hash!")
                    print(f"   ✅ Cambios en status DEBERÍAN detectarse")
                else:
                    print(f"   ❌ STATUS NO ESTÁ en el hash")
                    print(f"   ❌ Cambios en status NO se detectarán")

        # TEST 2: Verificar que ALIQUOT está en el hash
        print("\n" + "=" * 80)
        print("🔄 TEST 2: ¿ALIQUOT ESTÁ EN EL HASH?")
        print("=" * 80)

        cursor.execute("""
            SELECT a.code, e.aliquot
            FROM products a
            LEFT JOIN taxes e ON e.code = a.sale_tax
            WHERE a.code IS NOT NULL AND a.code != '' AND a.status = '01'
              AND e.aliquot IS NOT NULL
            ORDER BY random()
            LIMIT 1
        """)
        result = cursor.fetchone()

        if result:
            code = result[0]
            aliquot_actual = result[1]
            producto = obtener_producto_completo(cursor, code)

            if producto:
                hash_original = generar_hash_con_valores(producto)
                aliquot_nuevo = float(aliquot_actual) + 1.0 if aliquot_actual else 16.0
                hash_aliquot_cambiado = generar_hash_con_valores(producto, aliquot=str(aliquot_nuevo))

                print(f"\n   Producto: {code}")
                print(f"   Aliquot actual: {producto[16]}")
                print(f"   Hash original:       {hash_original}")
                print(f"   Hash si aliquot cambia: {hash_aliquot_cambiado}")

                if hash_original != hash_aliquot_cambiado:
                    print(f"   ✅ ¡ALIQUOT SÍ ESTÁ en el hash!")
                    print(f"   ✅ Cambios en aliquot DEBERÍAN detectarse")
                else:
                    print(f"   ❌ ALIQUOT NO ESTÁ en el hash")
                    print(f"   ❌ Cambios en aliquot NO se detectarán")

        # TEST 3: Verificar que COIN está en el hash
        print("\n" + "=" * 80)
        print("🔄 TEST 3: ¿COIN ESTÁ EN EL HASH?")
        print("=" * 80)

        cursor.execute("""
            SELECT code, coin FROM products
            WHERE code IS NOT NULL AND code != '' AND status = '01'
              AND coin IS NOT NULL AND coin != ''
            ORDER BY random()
            LIMIT 1
        """)
        result = cursor.fetchone()

        if result:
            code = result[0]
            coin_actual = result[1]
            producto = obtener_producto_completo(cursor, code)

            if producto:
                hash_original = generar_hash_con_valores(producto)
                hash_coin_cambiado = generar_hash_con_valores(producto, coin='99')

                print(f"\n   Producto: {code}")
                print(f"   Coin actual: '{producto[6]}'")
                print(f"   Desc. coin:  '{producto[7]}'")
                print(f"   Hash original:    {hash_original}")
                print(f"   Hash si coin='99': {hash_coin_cambiado}")

                if hash_original != hash_coin_cambiado:
                    print(f"   ✅ ¡COIN SÍ ESTÁ en el hash!")
                    print(f"   ✅ Cambios en coin DEBERÍAN detectarse")
                else:
                    print(f"   ❌ COIN NO ESTÁ en el hash")
                    print(f"   ❌ Cambios en coin NO se detectarán")

        # TEST 4: Verificar todos los campos juntos
        print("\n" + "=" * 80)
        print("🔄 TEST 4: CAMBIO MÚLTIPLES CAMPOS SIMULTÁNEAMENTE")
        print("=" * 80)

        cursor.execute("""
            SELECT a.code, a.coin, e.aliquot
            FROM products a
            LEFT JOIN taxes e ON e.code = a.sale_tax
            WHERE a.code IS NOT NULL AND a.code != '' AND a.status = '01'
            ORDER BY random()
            LIMIT 1
        """)
        result = cursor.fetchone()

        if result:
            code = result[0]
            producto = obtener_producto_completo(cursor, code)

            if producto:
                hash_original = generar_hash_con_valores(producto)
                hash_todos_cambiados = generar_hash_con_valores(
                    producto,
                    status='inactive',
                    aliquot='99.99',
                    coin='99'
                )

                print(f"\n   Producto: {code}")
                print(f"   Hash original:           {hash_original}")
                print(f"   Hash con todos cambiados: {hash_todos_cambiados}")

                if hash_original != hash_todos_cambiados:
                    print(f"   ✅ ¡TODOS LOS CAMPOS están en el hash!")
                    print(f"   ✅ El hash cambia cuando se modifica status, aliquot o coin")
                else:
                    print(f"   ❌ PROBLEMA: El hash no cambia")

        # Resumen
        print("\n" + "=" * 80)
        print("📊 CONCLUSIÓN")
        print("=" * 80)

        print("\n✅ Si TODOS los tests muestran que los campos SÍ están en el hash,")
        print("   entonces el problema NO está en la detección de cambios.")
        print("\n❌ Si algún test muestra que el campo NO está en el hash,")
        print("   entonces ese campo necesita ser agregado.")

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
