#!/usr/bin/env python3
"""
Test completo: Cambiar un producto en PostgreSQL y verificar si se detecta
"""

import hashlib
import psycopg2
import os
from dotenv import load_dotenv
from datetime import datetime

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
    """Generar hash MD5 para un producto"""
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

def obtener_producto(cursor, code):
    """Obtener un producto específico"""
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
    print("🧪 TEST: DETECCIÓN DE CAMBIOS EN PRODUCTOS")
    print("=" * 80)

    try:
        # Conectar a PostgreSQL
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST'),
            database=os.getenv('DB_DATABASE'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD')
        )
        cursor = conn.cursor()

        # PASO 1: Obtener un producto de prueba
        print("\n📌 PASO 1: Obtener producto de prueba")
        print("-" * 80)

        cursor.execute("""
            SELECT code FROM products
            WHERE code IS NOT NULL AND code != ''
            ORDER BY random()
            LIMIT 1
        """)
        result = cursor.fetchone()

        if not result:
            print("❌ No se encontraron productos")
            return

        test_code = result[0]
        print(f"✅ Producto seleccionado: {test_code}")

        # Obtener producto completo
        producto_antes = obtener_producto(cursor, test_code)
        hash_antes = generar_hash_product(producto_antes)

        print(f"\nProducto ANTES del cambio:")
        print(f"   Código:        {producto_antes[0]}")
        print(f"   Descripción:   {producto_antes[1][:40]}...")
        print(f"   Precio:        ${producto_antes[8]}")
        print(f"   Stock:         {producto_antes[4]}")
        print(f"   Departamento:  {producto_antes[3]}")
        print(f"\n   Hash ANTES:    {hash_antes}")

        # PASO 2: Obtener hash guardado en sync_hashes
        print("\n📌 PASO 2: Verificar hash guardado en sync_hashes")
        print("-" * 80)

        cursor.execute("""
            SELECT record_hash, last_sync_data, updated_at
            FROM sync_hashes
            WHERE table_name = 'products'
              AND record_key = %s
        """, (test_code,))

        hash_guardado_info = cursor.fetchone()
        if hash_guardado_info:
            hash_guardado, last_sync_data, updated_at = hash_guardado_info
            print(f"✅ Hash guardado:     {hash_guardado}")
            print(f"   Última sync:      {updated_at}")

            if hash_guardado == hash_antes:
                print(f"   Estado:           ✅ HASH IGUAL (sin cambios detectados)")
            else:
                print(f"   Estado:           ⚠️  HASH DIFERENTE (ya hay cambios pendientes)")
        else:
            hash_guardado = None
            print(f"⚠️  No hay hash guardado (producto nuevo)")

        # PASO 3: Cambiar el precio del producto
        print("\n📌 PASO 3: Cambiar precio en PostgreSQL")
        print("-" * 80)

        precio_actual = float(producto_antes[8]) if producto_antes[8] else 0
        nuevo_precio = precio_actual + 1.0

        print(f"   Precio actual:    ${precio_actual}")
        print(f"   Nuevo precio:     ${nuevo_precio}")

        # Hacer el cambio
        cursor.execute("""
            UPDATE PRODUCTS_UNITS
            SET maximum_price = %s
            WHERE product_code = %s
        """, (nuevo_precio, test_code))

        conn.commit()
        print(f"✅ Precio actualizado en PostgreSQL")

        # PASO 4: Obtener el producto nuevamente
        print("\n📌 PASO 4: Obtener producto después del cambio")
        print("-" * 80)

        producto_despues = obtener_producto(cursor, test_code)
        hash_despues = generar_hash_product(producto_despues)

        print(f"\nProducto DESPUÉS del cambio:")
        print(f"   Código:        {producto_despues[0]}")
        print(f"   Descripción:   {producto_despues[1][:40]}...")
        print(f"   Precio:        ${producto_despues[8]} ✅ CAMBIÓ")
        print(f"   Stock:         {producto_despues[4]}")
        print(f"   Departamento:  {producto_despues[3]}")
        print(f"\n   Hash DESPUÉS:   {hash_despues}")

        # PASO 5: Comparar hashes
        print("\n📌 PASO 5: Comparar hashes")
        print("=" * 80)

        print(f"\n{'Comparación':<20} | {'Hash':<33} | {'Resultado'}")
        print("-" * 80)

        if hash_guardado:
            iguales_guardado = hash_despues == hash_guardado
            print(f"{'Hash DESPUÉS vs Guardado':<20} | {hash_despues[:16]}... vs {hash_guardado[:16]}... | {'❌ IGUAL ❌' if iguales_guardado else '✅ DIFERENTE ✅'}")

        iguales_antes_despues = hash_antes == hash_despues
        print(f"{'Hash ANTES vs DESPUÉS':<20} | {hash_antes[:16]}... vs {hash_despues[:16]}... | {'❌ IGUAL ❌' if iguales_antes_despues else '✅ DIFERENTE ✅'}")

        # PASO 6: Simular detección de cambios
        print("\n📌 PASO 6: Simular detección de cambios")
        print("-" * 80)

        if hash_guardado:
            if hash_despues != hash_guardado:
                print(f"✅ ¡CAMBIO DETECTADO!")
                print(f"   El producto '{test_code}' sería agregado a la lista de MODIFICADOS")
                print(f"   Se sincronizaría a MySQL en la próxima sincronización")
            else:
                print(f"❌ NO SE DETECTÓ EL CAMBIO")
                print(f"   El producto NO sería sincronizado")
        else:
            print(f"✅ PRODUCTO NUEVO")
            print(f"   El producto sería agregado a la lista de NUEVOS")

        # PASO 7: Restaurar precio original
        print("\n📌 PASO 7: Restaurar precio original")
        print("-" * 80)

        cursor.execute("""
            UPDATE PRODUCTS_UNITS
            SET maximum_price = %s
            WHERE product_code = %s
        """, (precio_actual, test_code))

        conn.commit()
        print(f"✅ Precio restaurado a ${precio_actual}")

        # RESUMEN FINAL
        print("\n" + "=" * 80)
        print("📊 RESUMEN DEL TEST")
        print("=" * 80)

        if hash_guardado:
            if hash_despues != hash_guardado:
                print("\n✅ RESULTADO: El sistema DETECTA correctamente los cambios")
                print("\n   Si tu sincronización NO está actualizando productos cuando")
                print("   cambian campos que no son stock, el problema NO está en la")
                print("   detección de cambios, sino en:")
                print("\n   1. La sincronización a MySQL (¿falla silenciosamente?)")
                print("   2. El guardado del hash después de sincronizar")
                print("   3. Algún filtro que esté excluyendo los productos")
            else:
                print("\n❌ RESULTADO: El sistema NO detectó el cambio")
                print("\n   Esto indica un problema con la generación del hash")
        else:
            print("\n⚠️  No había hash guardado - producto nunca sincronizado antes")

        print("\n" + "=" * 80)

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
