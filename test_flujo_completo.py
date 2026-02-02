#!/usr/bin/env python3
"""
Test del flujo completo: Detectar cambio → Sincronizar a MySQL
Este test simula EXACTAMENTE lo que hace smart_sync_complete.py
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

def _generar_hash_product(product):
    """Misma función que smart_sync_complete.py"""
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
        return None

def main():
    print("=" * 80)
    print("🧪 TEST: SIMULAR FLUJO COMPLETO DE DETECCIÓN Y SINCRONIZACIÓN")
    print("=" * 80)

    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST'),
            database=os.getenv('DB_DATABASE'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD')
        )
        cursor = conn.cursor()
        print("✅ Conectado a PostgreSQL\n")

        # PASO 1: Obtener un producto
        print("📌 PASO 1: Obtener producto de prueba")
        print("-" * 80)

        cursor.execute("""
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
            WHERE a.code IS NOT NULL AND a.code != '' AND a.status = '01'
            ORDER BY a.code, b.maximum_price DESC
            LIMIT 1
        """)

        producto = cursor.fetchone()
        if not producto:
            print("❌ No se encontraron productos")
            return

        (code, description, short_name, department, stock, product_type,
         coin, description_coin, price, cost, higher_price, min_stock, status,
         image_type, product_image, sale_tax, aliquot) = producto

        print(f"Producto: {code}")
        print(f"  Coin:    {coin}")
        print(f"  Status:  {status}")
        print(f"  Aliquot: {aliquot}")
        print(f"  Sale_tax code: {sale_tax}")

        # PASO 2: Generar hash ANTES
        print("\n📌 PASO 2: Generar hash ANTES")
        print("-" * 80)
        hash_antes = _generar_hash_product(producto)
        print(f"Hash ANTES: {hash_antes}")

        # PASO 3: Obtener hash guardado en sync_hashes
        print("\n📌 PASO 3: Verificar hash guardado en sync_hashes")
        print("-" * 80)

        cursor.execute("""
            SELECT record_hash FROM sync_hashes
            WHERE table_name = 'products' AND record_key = %s
        """, (code,))
        resultado = cursor.fetchone()

        if resultado:
            hash_guardado = resultado[0]
            print(f"Hash guardado: {hash_guardado}")

            if hash_antes == hash_guardado:
                print("Estado: ✅ IGUAL (sin cambios detectados)")
            else:
                print("Estado: ⚠️  DIFERENTE (ya hay cambios pendientes)")
        else:
            hash_guardado = None
            print("Hash guardado: None (producto nunca sincronizado)")

        # PASO 4: SIMULAR CAMBIO DE ALIQUOT
        print("\n📌 PASO 4: Cambiar ALIQUOT en PostgreSQL")
        print("-" * 80)

        aliquot_antes = aliquot
        nuevo_aliquot = float(aliquot) + 1.0 if aliquot else 16.0

        print(f"Aliquot ANTES: {aliquot_antes}")
        print(f"Cambiando a: {nuevo_aliquot}")

        cursor.execute("""
            UPDATE taxes
            SET aliquot = %s
            WHERE code = %s
        """, (nuevo_aliquot, sale_tax))
        conn.commit()
        print("✅ Aliquot actualizado en PostgreSQL")

        # PASO 5: Obtener producto NUEVO con el aliquot cambiado
        print("\n📌 PASO 5: Obtener producto DESPUÉS del cambio")
        print("-" * 80)

        cursor.execute("""
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
            WHERE a.code = %s AND a.status = '01'
            ORDER BY a.code, b.maximum_price DESC
        """, (code,))

        producto_nuevo = cursor.fetchone()
        aliquot_despues = producto_nuevo[16]

        print(f"Producto DESPUÉS:")
        print(f"  Aliquot: {aliquot_despues}")

        # PASO 6: Generar hash DESPUÉS
        print("\n📌 PASO 6: Generar hash DESPUÉS")
        print("-" * 80)
        hash_despues = _generar_hash_product(producto_nuevo)
        print(f"Hash DESPUÉS: {hash_despues}")

        # PASO 7: Comparar hashes
        print("\n📌 PASO 7: ¿Se detectaría el cambio?")
        print("-" * 80)

        if hash_guardado:
            if hash_despues != hash_guardado:
                print("✅ ¡SÍ! El producto se agregaría a 'modificados'")
                print(f"   Hash guardado: {hash_guardado[:16]}...")
                print(f"   Hash nuevo:    {hash_despues[:16]}...")
            else:
                print("❌ NO. El hash es igual, no se detectaría cambio")
        else:
            print("✅ SÍ. Producto nuevo, se agregaría a 'nuevos'")

        # PASO 8: Restaurar aliquot original
        print("\n📌 PASO 8: Restaurar aliquot original")
        print("-" * 80)

        cursor.execute("""
            UPDATE taxes
            SET aliquot = %s
            WHERE code = %s
        """, (aliquot_antes, sale_tax))
        conn.commit()
        print(f"✅ Aliquot restaurado a {aliquot_antes}")

        # CONCLUSIÓN
        print("\n" + "=" * 80)
        print("📊 RESULTADO")
        print("=" * 80)

        if hash_guardado and hash_despues != hash_guardado:
            print("\n✅ El cambio SÍ se detecta")
            print("✅ El producto SÍ se agregaría a la lista de modificados")
            print("✅ El producto SÍ se sincronizaría a MySQL")
            print("\n❌ Si el cambio NO se refleja en MySQL, el problema está en:")
            print("   1. La sincronización a MySQL (¿hay errores?)")
            print("   2. El UPDATE en MySQL no funciona para aliquot")
            print("   3. El producto se filtra por alguna razón")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
