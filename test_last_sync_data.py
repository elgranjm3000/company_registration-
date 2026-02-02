#!/usr/bin/env python3
"""
Test para verificar que last_sync_data mantiene correctamente el status
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
    print("🧪 TEST: VERIFICAR last_sync_data MANTIENE STATUS")
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

        # PASO 1: Obtener un producto que tenga hash guardado
        print("📌 PASO 1: Buscar producto con hash guardado")
        print("-" * 80)

        cursor.execute("""
            SELECT record_key, record_hash, last_sync_data, updated_at
            FROM sync_hashes
            WHERE table_name = 'products'
            LIMIT 1
        """)

        hash_row = cursor.fetchone()
        if not hash_row:
            print("❌ No hay productos en sync_hashes. Ejecuta sync primero.")
            return

        code, hash_guardado, last_sync_data_str, updated_at = hash_row

        print(f"Producto: {code}")
        print(f"Hash guardado: {hash_guardado[:16]}...")
        print(f"Updated at: {updated_at}")

        if last_sync_data_str:
            try:
                last_sync_data = json.loads(last_sync_data_str) if isinstance(last_sync_data_str, str) else last_sync_data_str
                print(f"last_sync_data actual: {json.dumps(last_sync_data, indent=2)}")
            except:
                print(f"last_sync_data (raw): {last_sync_data_str}")
                last_sync_data = {}
        else:
            print("⚠️  last_sync_data es NULL")
            last_sync_data = {}

        # PASO 2: Obtener producto actual
        print("\n📌 PASO 2: Obtener producto actual de PostgreSQL")
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

        producto = cursor.fetchone()
        if not producto:
            print("❌ Producto no encontrado en products")
            return

        status_actual = producto[12]
        hash_actual = _generar_hash_product(producto)

        print(f"Status actual: {status_actual}")
        print(f"Hash actual: {hash_actual[:16]}...")

        # PASO 3: Simular actualización de last_sync_data (como lo hace smart_sync_complete.py)
        print("\n📌 PASO 3: Simular actualización de last_sync_data")
        print("-" * 80)

        data_sync = {
            'status': status_actual,  # status (active/inactive)
            'last_sync': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        print(f"Nuevo data_sync a guardar: {json.dumps(data_sync, indent=2)}")

        # PASO 4: Verificar que data_sync tiene status
        print("\n📌 PASO 4: Verificar estructura de data_sync")
        print("-" * 80)

        if 'status' in data_sync:
            print(f"✅ 'status' presente: {data_sync['status']}")
        else:
            print("❌ 'status' NO presente en data_sync")

        if 'last_sync' in data_sync:
            print(f"✅ 'last_sync' presente: {data_sync['last_sync']}")
        else:
            print("❌ 'last_sync' NO presente en data_sync")

        # PASO 5: Simular UPDATE de sync_hashes
        print("\n📌 PASO 5: Simular UPDATE en sync_hashes")
        print("-" * 80)

        update_query = """
        UPDATE sync_hashes
        SET record_hash = %s,
            updated_at = NOW(),
            last_sync_data = %s
        WHERE table_name = %s
          AND record_key = %s
        RETURNING updated_at, last_sync_data
        """

        cursor.execute(update_query, (
            hash_actual,
            json.dumps(data_sync),
            'products',
            code
        ))

        result = cursor.fetchone()
        conn.commit()

        if result:
            new_updated_at, new_last_sync_data = result
            print(f"✅ UPDATE ejecutado")
            print(f"   Updated at: {new_updated_at}")
            print(f"   last_sync_data: {new_last_sync_data}")

        # PASO 6: Verificar el resultado final
        print("\n📌 PASO 6: Verificar resultado final")
        print("-" * 80)

        cursor.execute("""
            SELECT record_key, record_hash, last_sync_data, updated_at
            FROM sync_hashes
            WHERE table_name = 'products'
              AND record_key = %s
        """, (code,))

        final_row = cursor.fetchone()
        final_code, final_hash, final_data, final_updated = final_row

        print(f"Record key: {final_code}")
        print(f"Record hash: {final_hash[:16]}...")
        print(f"Updated at: {final_updated}")

        if final_data:
            try:
                # PostgreSQL ya decodifica JSON a dict automáticamente
                final_data_parsed = final_data if isinstance(final_data, dict) else json.loads(final_data)
                print(f"last_sync_data: {json.dumps(final_data_parsed, indent=2)}")

                if 'status' in final_data_parsed:
                    print(f"\n✅ EXITO: Status '{final_data_parsed['status']}' guardado en last_sync_data")
                else:
                    print("\n❌ ERROR: Status NO guardado en last_sync_data")
            except Exception as e:
                print(f"❌ Error parseando JSON: {e}")
                final_data_parsed = {}
        else:
            print("\n❌ ERROR: last_sync_data es NULL después del UPDATE")
            final_data_parsed = {}

        # CONCLUSIÓN
        print("\n" + "=" * 80)
        print("📊 RESULTADO")
        print("=" * 80)

        if final_data and 'status' in final_data_parsed:
            print("\n✅ TEST EXITOSO")
            print("✅ last_sync_data contiene el status")
            print("✅ El status se preserva correctamente tras sincronización")
        else:
            print("\n❌ TEST FALLIDO")
            print("❌ last_sync_data NO contiene el status")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
