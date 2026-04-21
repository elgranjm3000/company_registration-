#!/usr/bin/env python3
"""
Script para verificar inserción en sales_operation_coins
"""

import psycopg2
from datetime import datetime

# Configuración de PostgreSQL
PG_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'nuevaprueba',
    'user': 'postgres',
    'password': 'muentes123.'
}

def verificar_sales_operation_coins():
    """Verificar si hay registros en sales_operation_coins"""
    try:
        conn = psycopg2.connect(**PG_CONFIG)
        cursor = conn.cursor()

        print("=" * 80)
        print("VERIFICANDO sales_operation_coins")
        print("=" * 80)

        # 1. Verificar si existe la tabla
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'sales_operation_coins'
            )
        """)
        existe_tabla = cursor.fetchone()[0]

        if not existe_tabla:
            print("❌ La tabla 'sales_operation_coins' NO EXISTE")
            return

        print("✅ La tabla 'sales_operation_coins' existe\n")

        # 2. Contar registros
        cursor.execute("SELECT COUNT(*) FROM sales_operation_coins")
        total = cursor.fetchone()[0]
        print(f"📊 Total registros en sales_operation_coins: {total}\n")

        # 3. Mostrar últimos registros (si hay)
        if total > 0:
            cursor.execute("""
                SELECT main_correlative, coin_code, buy_aliquot, sales_aliquot,
                       total_net_details, total_details
                FROM sales_operation_coins
                ORDER BY main_correlative DESC
                LIMIT 5
            """)

            print("Últimos 5 registros:")
            for row in cursor.fetchall():
                correlative, coin_code, buy_aliquot, sales_aliquot, net, total = row
                print(f"  - Correlative: {correlative}, Coin: {coin_code}, "
                      f"Buy: {buy_aliquot}, Sales: {sales_aliquot}, Net: {net}, Total: {total}")
        else:
            print("⚠️  No hay registros en sales_operation_coins\n")

        # 4. Verificar si hay quotes en sales_operation
        cursor.execute("SELECT COUNT(*) FROM sales_operation")
        total_sales = cursor.fetchone()[0]
        print(f"📊 Total ventas en sales_operation: {total}\n")

        if total_sales > 0:
            cursor.execute("""
                SELECT correlative, document_no, total_details
                FROM sales_operation
                ORDER BY correlative DESC
                LIMIT 3
            """)

            print("Últimas 3 ventas en sales_operation:")
            for row in cursor.fetchall():
                correlative, doc_no, total = row
                print(f"  - Correlative: {correlative}, Documento: {doc_no}, Total: {total}")

                # Verificar si tiene monedas en sales_operation_coins
                cursor.execute("""
                    SELECT COUNT(*) FROM sales_operation_coins
                    WHERE main_correlative = %s
                """, (correlative,))

                count_coins = cursor.fetchone()[0]
                if count_coins > 0:
                    print(f"    ✅ Tiene {count_coins} monedas en sales_operation_coins")
                else:
                    print(f"    ❌ NO tiene monedas en sales_operation_coins")

        # 5. Verificar tabla coin
        print("\n" + "=" * 80)
        print("Monedas en tabla 'coin':")
        print("=" * 80)

        cursor.execute("""
            SELECT code, description, buy_aliquot, sales_aliquot, factor_type
            FROM coin
            WHERE code IN ('01', '02')
            ORDER BY code
        """)

        for row in cursor.fetchall():
            code, description, buy, sales, factor = row
            print(f"  - Code: {code}, Descripción: {description}")
            print(f"    Buy_aliquot: {buy}, Sales_aliquot: {sales}, Factor_type: {factor}")

        cursor.close()
        conn.close()

        print("\n" + "=" * 80)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    verificar_sales_operation_coins()
