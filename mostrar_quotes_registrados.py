"""
Script para mostrar cómo se registran los quotes en la base de datos
"""

import sys
import os
import json
import psycopg2
from datetime import datetime


def mostrar_quotes_registrados():
    """Muestra cómo se registran los quotes en sales_operation"""

    print("="*70)
    print("MOSTRANDO QUOTES REGISTRADOS EN POSTGRESQL")
    print("="*70)

    # Leer configuración
    config_file = "sync_config_api.json"
    if not os.path.exists(config_file):
        print(f"\n❌ ERROR: No existe el archivo {config_file}")
        return False

    with open(config_file, 'r') as f:
        config = json.load(f)

    # Conectar a PostgreSQL
    try:
        print("\n📡 Conectando a PostgreSQL...")
        conn = psycopg2.connect(
            host=config['postgres_host'],
            port=config['postgres_port'],
            database=config['postgres_database'],
            user=config['postgres_user'],
            password=config['postgres_password']
        )
        cursor = conn.cursor()
        print("✅ Conectado a PostgreSQL")

        # Buscar quotes recientes (BUDGET)
        print("\n" + "="*70)
        print("BUSCANDO QUOTES EN SALES_OPERATION")
        print("="*70)

        query = """
            SELECT
                correlative,
                operation_type,
                document_no,
                emission_date,
                register_date,
                client_code,
                client_name,
                seller,
                total_amount,
                total_tax,
                discount,
                total,
                coin_code,
                pending,
                canceled
            FROM sales_operation
            WHERE operation_type = 'BUDGET'
            ORDER BY register_date DESC
            LIMIT 5
        """

        cursor.execute(query)
        results = cursor.fetchall()

        if not results:
            print("\n⚠️ No se encontraron quotes registrados")
            return True

        print(f"\n✅ Se encontraron {len(results)} quotes recientes:\n")

        for i, row in enumerate(results, 1):
            print(f"{'='*70}")
            print(f"QUOTE #{i}")
            print(f"{'='*70}")

            print(f"📋 Correlative:        {row[0]}")
            print(f"📋 Operation Type:     {row[1]}")
            print(f"📋 Document No:        {row[2]}")
            print(f"📅 Emission Date:      {row[3]}")
            print(f"📅 Register Date:      {row[4]}")
            print(f"\n👤 Cliente:")
            print(f"   Code:               '{row[5]}'")
            print(f"   Name:               '{row[6]}'")
            print(f"\n👨‍💼 Vendedor:")
            print(f"   Seller Code:        {row[7] if row[7] else 'NULL'}")

            # Buscar nombre del vendedor si existe
            if row[7]:
                cursor.execute("SELECT description FROM sellers WHERE code = %s", (row[7],))
                seller_result = cursor.fetchone()
                if seller_result:
                    print(f"   Seller Name:        '{seller_result[0]}'")
                else:
                    print(f"   ⚠️ Vendedor no encontrado en tabla sellers")

            print(f"\n💰 Montos:")
            print(f"   Subtotal:           {row[8]:.2f}")
            print(f"   Tax:                {row[9]:.2f}")
            print(f"   Discount:           {row[10]:.2f}")
            print(f"   Total:              {row[11]:.2f}")
            print(f"   Coin Code:          '{row[12]}'")

            # Buscar nombre de la moneda
            cursor.execute("SELECT description FROM coin WHERE code = %s", (row[12],))
            coin_result = cursor.fetchone()
            if coin_result:
                print(f"   Coin Name:          '{coin_result[0]}'")

            print(f"\n📊 Estado:")
            print(f"   Pending:            {row[13]}")
            print(f"   Canceled:           {row[14]}")

            # Mostrar items
            print(f"\n📦 Items:")
            cursor.execute("""
                SELECT
                    product_code,
                    description,
                    quantity,
                    unit_price,
                    discount,
                    tax,
                    total
                FROM sales_operation_details
                WHERE correlative = %s
                ORDER BY correlative_detail
            """, (row[0],))

            items = cursor.fetchall()
            if items:
                for j, item in enumerate(items, 1):
                    print(f"   {j}. Producto: {item[0]}")
                    print(f"      Descripción:  {item[1]}")
                    print(f"      Cantidad:     {item[2]}")
                    print(f"      Precio Unit:  {item[3]:.2f}")
                    print(f"      Descuento:    {item[4]:.2f}")
                    print(f"      Tax:          {item[5]:.2f}")
                    print(f"      Total:        {item[6]:.2f}")
            else:
                print("   ⚠️ No hay items")

            print()

        # Mostrar información de sync_hashes
        print("="*70)
        print("SYNC_HASHES - QUOTES")
        print("="*70)

        cursor.execute("""
            SELECT
                record_key,
                record_hash,
                pending_sync,
                deleted_at,
                last_sync_date
            FROM sync_hashes
            WHERE table_name = 'quotes'
            ORDER BY last_sync_date DESC
            LIMIT 5
        """)

        sync_results = cursor.fetchall()

        if sync_results:
            print(f"\n✅ Se encontraron {len(sync_results)} registros en sync_hashes:\n")
            for i, row in enumerate(sync_results, 1):
                print(f"{i}. Quote ID (record_key): {row[0]}")
                print(f"   Hash: {row[1][:32]}...")
                print(f"   Pending Sync: {row[2]}")
                print(f"   Deleted At: {row[3]}")
                print(f"   Last Sync: {row[4]}")
                print()
        else:
            print("\n⚠️ No hay registros en sync_hashes para quotes")

        # Verificar vendedores disponibles
        print("="*70)
        print("VENDEDORES DISPONIBLES EN TABLA SELLERS")
        print("="*70)

        cursor.execute("""
            SELECT code, description
            FROM sellers
            WHERE code IS NOT NULL AND code != ''
            ORDER BY code
            LIMIT 10
        """)

        sellers = cursor.fetchall()
        if sellers:
            print(f"\n✅ Primeros {len(sellers)} vendedores:\n")
            for code, description in sellers:
                print(f"   Code: {code:10s} | Name: {description}")
        else:
            print("\n⚠️ No hay vendedores registrados")

        print("\n" + "="*70)
        print("✅ ANÁLISIS COMPLETADO")
        print("="*70)

        cursor.close()
        conn.close()

        return True

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = mostrar_quotes_registrados()
    sys.exit(0 if success else 1)
