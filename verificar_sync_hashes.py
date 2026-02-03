#!/usr/bin/env python3
"""
Verificar si los cambios se detectan correctamente en sync_hashes
"""

import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def main():
    print("=" * 80)
    print("🔍 DIAGNÓSTICO: ¿SE ESTÁN GUARDANDO LOS HASHES?")
    print("=" * 80)

    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST'),
            database=os.getenv('DB_DATABASE'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD')
        )
        cursor = conn.cursor()

        # Verificar último sync
        print("\n📌 ÚLTIMA SINCRONIZACIÓN REGISTRADA:")
        print("-" * 80)

        cursor.execute("""
            SELECT table_name, COUNT(*) as total,
                   MIN(updated_at) as primer_sync,
                   MAX(updated_at) as ultimo_sync
            FROM sync_hashes
            GROUP BY table_name
            ORDER BY MAX(updated_at) DESC
        """)

        for row in cursor.fetchall():
            table, total, primero, ultimo = row
            print(f"\n{table.upper():15} | Registros: {total:5} | Último sync: {ultimo}")

        # Verificar si hay productos recientes que no se han sincronizado
        print("\n📌 PRODUCTOS QUE CAMBIARON PERO NO ESTÁN EN SYNC_HASHES:")
        print("-" * 80)

        cursor.execute("""
            SELECT COUNT(*) as total
            FROM products a
            WHERE a.code IS NOT NULL AND a.code != '' AND a.status = '01'
              AND NOT EXISTS (
                  SELECT 1 FROM sync_hashes
                  WHERE table_name = 'products'
                    AND record_key = a.code
              )
        """)

        no_sync = cursor.fetchone()[0]
        print(f"\n   Productos sin sincronizar: {no_sync}")

        if no_sync > 0:
            print(f"\n   ⚠️  Hay {no_sync} productos que nunca se han sincronizado")

            cursor.execute("""
                SELECT a.code, a.description, a.status
                FROM products a
                WHERE a.code IS NOT NULL AND a.code != '' AND a.status = '01'
                  AND NOT EXISTS (
                      SELECT 1 FROM sync_hashes
                      WHERE table_name = 'products'
                        AND record_key = a.code
                  )
                LIMIT 5
            """)

            print("\n   Ejemplos:")
            for row in cursor.fetchall():
                code, desc, status = row
                print(f"   - {code}: {desc[:40]}")

        cursor.close()
        conn.close()

        print("\n" + "=" * 80)
        print("✅ Si todos los productos están en sync_hashes, la detección funciona")
        print("❌ Si hay productos sin sincronizar, pueden ser nuevos o haber fallado")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
