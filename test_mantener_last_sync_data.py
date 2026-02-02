#!/usr/bin/env python3
"""
Test para verificar que last_sync_data se MANTIENE cuando el producto no tiene cambios
"""

import hashlib
import psycopg2
import json
import os
from datetime import datetime
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
    print("🧪 TEST: VERIFICAR QUE last_sync_data SE MANTIENE SIN CAMBIOS")
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

        code = producto[0]
        status = producto[12]
        hash_actual = _generar_hash_product(producto)

        print(f"Producto: {code}")
        print(f"Status: {status}")
        print(f"Hash actual: {hash_actual[:16]}...")

        # PASO 2: Guardar hash CON status en last_sync_data
        print("\n📌 PASO 2: Guardar hash CON status en last_sync_data")
        print("-" * 80)

        data_sync_inicial = {
            'status': status,
            'last_sync': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        cursor.execute("""
            INSERT INTO sync_hashes (table_name, record_key, record_hash, last_sync_data, updated_at, company_id)
            VALUES (%s, %s, %s, %s, NOW(), %s)
            ON CONFLICT (table_name, record_key, company_id) DO UPDATE
            SET record_hash = EXCLUDED.record_hash,
                last_sync_data = EXCLUDED.last_sync_data,
                updated_at = NOW()
        """, ('products', code, hash_actual, json.dumps(data_sync_inicial), 1))

        conn.commit()

        cursor.execute("""
            SELECT last_sync_data, updated_at FROM sync_hashes
            WHERE table_name = 'products' AND record_key = %s AND company_id = %s
        """, (code, 1))

        row = cursor.fetchone()
        last_sync_data_antes = row[0]
        updated_at_antes = row[1]

        print(f"✅ Guardado inicial")
        print(f"   last_sync_data: {json.dumps(last_sync_data_antes, indent=2)}")
        print(f"   updated_at: {updated_at_antes}")

        # PASO 3: Simular sync SIN cambios (mismo hash)
        print("\n📌 PASO 3: Simular sync SIN cambios")
        print("-" * 80)

        # Este es el código de smart_sync_complete.py cuando no hay cambios
        update_query = """
        UPDATE sync_hashes
        SET updated_at = NOW()
        WHERE table_name = %s
          AND record_key = %s
          AND company_id = %s
        """
        company_id = 1  # Usar el company_id correcto
        cursor.execute(update_query, ('products', code, company_id))
        conn.commit()

        print("✅ Ejecutado UPDATE solo de updated_at")

        # PASO 4: Verificar que last_sync_data NO cambió
        print("\n📌 PASO 4: Verificar que last_sync_data se MANTIENE")
        print("-" * 80)

        cursor.execute("""
            SELECT last_sync_data, updated_at FROM sync_hashes
            WHERE table_name = 'products' AND record_key = %s AND company_id = %s
        """, (code, 1))

        row = cursor.fetchone()
        last_sync_data_despues = row[0]
        updated_at_despues = row[1]

        print(f"   last_sync_data: {json.dumps(last_sync_data_despues, indent=2)}")
        print(f"   updated_at: {updated_at_despues}")

        # PASO 5: Comparar
        print("\n📌 PASO 5: Comparar ANTES vs DESPUÉS")
        print("-" * 80)

        last_sync_mismo = (last_sync_data_antes == last_sync_data_despues)
        updated_at_cambio = (updated_at_antes != updated_at_despues)

        if last_sync_mismo:
            print("✅ last_sync_data se MANTIUVO igual")
        else:
            print("❌ last_sync_data CAMBIÓ (no debería)")

        if updated_at_cambio:
            print("✅ updated_at se ACTUALIZÓ")
        else:
            print("⚠️  updated_at NO cambió")

        # CONCLUSIÓN
        print("\n" + "=" * 80)
        print("📊 RESULTADO")
        print("=" * 80)

        if last_sync_mismo and updated_at_cambio:
            print("\n✅ TEST EXITOSO")
            print("✅ last_sync_data se mantiene cuando no hay cambios")
            print("✅ updated_at se actualiza correctamente")
        else:
            print("\n❌ TEST FALLIDO")
            if not last_sync_mismo:
                print("❌ last_sync_data cambió cuando no debía")
            if not updated_at_cambio:
                print("❌ updated_at no se actualizó")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
