#!/usr/bin/env python3
"""
Test para verificar sales_operation_coins
"""

import psycopg2
from decimal import Decimal

# Configuración de PostgreSQL
PG_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'chrystal',
    'user': 'postgres',
    'password': 'muentes123.'
}

def test_sales_operation_coins():
    """Verificar la lógica de sales_operation_coins"""

    print("=" * 80)
    print("TEST: sales_operation_coins - Verificación de conversión")
    print("=" * 80)

    try:
        # Conectar a PostgreSQL
        conn = psycopg2.connect(**PG_CONFIG)
        cursor = conn.cursor()

        # 1. Obtener datos de la tabla coin
        print("\n📊 PASO 1: Datos de la tabla coin")
        print("-" * 80)

        cursor.execute("""
            SELECT code, description, buy_aliquot, sales_aliquot, factor_type
            FROM coin
            WHERE code IN ('01', '02')
            ORDER BY code
        """)

        coins = {}
        for row in cursor.fetchall():
            code, description, buy_aliquot, sales_aliquot, factor_type = row
            coins[code] = {
                'description': description,
                'buy_aliquot': float(buy_aliquot),
                'sales_aliquot': float(sales_aliquot),
                'factor_type': int(factor_type)
            }
            print(f"  Coin {code} ({description}):")
            print(f"    - buy_aliquot:   {coins[code]['buy_aliquot']}")
            print(f"    - sales_aliquot: {coins[code]['sales_aliquot']}")
            print(f"    - factor_type:   {coins[code]['factor_type']}")

        # 2. Buscar un quote reciente
        print("\n📋 PASO 2: Buscar un quote reciente")
        print("-" * 80)

        cursor.execute("""
            SELECT q.id, q.quote_number, q.subtotal, q.tax_amount, q.total, q.bcv_rate
            FROM quotes q
            ORDER BY q.id DESC
            LIMIT 1
        """)

        quote = cursor.fetchone()
        if not quote:
            print("  ❌ No hay quotes en la base de datos")
            return

        quote_id, quote_number, subtotal, tax_amount, total, bcv_rate = quote
        print(f"  Quote ID: {quote_id}")
        print(f"  Quote Number: {quote_number}")
        print(f"  Subtotal: {float(subtotal)} USD")
        print(f"  Tax Amount: {float(tax_amount)} USD")
        print(f"  Total: {float(total)} USD")
        print(f"  BCV Rate (antiguo): {float(bcv_rate)}")

        # 3. Calcular qué se debería guardar
        print("\n💰 PASO 3: Cálculo de sales_operation_coins")
        print("-" * 80)

        # Valores del quote (en USD)
        total_net_details = float(subtotal)
        total_tax_details = float(tax_amount)
        total_details = float(total)
        discount_amount = 0.0

        # USD (coin_code='02')
        print("\n  🇺🇸 USD (coin_code='02'):")
        print(f"    - buy_aliquot:   {coins['02']['buy_aliquot']} (de coin code='02')")
        print(f"    - sales_aliquot: {coins['02']['sales_aliquot']} (de coin code='02')")
        print(f"    - factor_type:   {coins['02']['factor_type']} (de coin code='02')")
        print(f"    - total_net_details: {total_net_details} (directo del quote)")
        print(f"    - total_tax_details: {total_tax_details} (directo del quote)")
        print(f"    - total_details: {total_details} (directo del quote)")

        # Bs (coin_code='01')
        print("\n  🇻🇪 Bs (coin_code='01'):")

        # Obtener sales_aliquot de USD para conversión
        sales_aliquot_usd = coins['02']['sales_aliquot']

        # Calcular montos en Bs
        total_net_details_bs = round(total_net_details * sales_aliquot_usd, 2)
        total_tax_details_bs = round(total_tax_details * sales_aliquot_usd, 2)
        total_details_bs = round(total_details * sales_aliquot_usd, 2)
        discount_amount_bs = round(discount_amount * sales_aliquot_usd, 2)

        print(f"    - buy_aliquot:   {coins['01']['buy_aliquot']} (de coin code='01' - TAL CUAL)")
        print(f"    - sales_aliquot: {coins['01']['sales_aliquot']} (de coin code='01' - TAL CUAL)")
        print(f"    - factor_type:   {coins['01']['factor_type']} (de coin code='01')")
        print(f"    - Tasa de conversión: {sales_aliquot_usd} (sales_aliquot de USD)")
        print(f"    - total_net_details: {total_net_details_bs} = {total_net_details} × {sales_aliquot_usd}")
        print(f"    - total_tax_details: {total_tax_details_bs} = {total_tax_details} × {sales_aliquot_usd}")
        print(f"    - total_details: {total_details_bs} = {total_details} × {sales_aliquot_usd}")
        print(f"    - discount: {discount_amount_bs} = {discount_amount} × {sales_aliquot_usd}")

        # 4. Verificar en la base de datos si existe
        print("\n🔍 PASO 4: Verificar en base de datos")
        print("-" * 80)

        cursor.execute("""
            SELECT main_correlative, coin_code, buy_aliquot, sales_aliquot,
                   total_net_details, total_tax_details, total_details
            FROM sales_operation_coins
            WHERE main_correlative = (
                SELECT correlative FROM quotes WHERE id = %s
            )
            ORDER BY coin_code
        """, (quote_id,))

        results = cursor.fetchall()
        if results:
            print(f"  ✅ Encontrados {len(results)} registros en sales_operation_coins:\n")

            for row in results:
                main_correlative, coin_code, buy_aliquot, sales_aliquot, total_net, total_tax, total_val = row
                coin_desc = 'USD' if coin_code == '02' else 'Bs'

                print(f"  📌 Registro {coin_desc} (coin_code='{coin_code}'):")
                print(f"     - buy_aliquot:   {float(buy_aliquot)}")
                print(f"     - sales_aliquot: {float(sales_aliquot)}")
                print(f"     - total_net_details: {float(total_net)}")
                print(f"     - total_tax_details: {float(total_tax)}")
                print(f"     - total_details: {float(total_val)}")

                # Verificar si es correcto
                if coin_code == '02':  # USD
                    expected_buy = coins['02']['buy_aliquot']
                    expected_sales = coins['02']['sales_aliquot']
                    expected_total_net = total_net_details
                    expected_total_tax = total_tax_details
                    expected_total = total_details
                else:  # Bs
                    expected_buy = coins['01']['buy_aliquot']
                    expected_sales = coins['01']['sales_aliquot']
                    expected_total_net = total_net_details_bs
                    expected_total_tax = total_tax_details_bs
                    expected_total = total_details_bs

                buy_ok = abs(float(buy_aliquot) - expected_buy) < 0.01
                sales_ok = abs(float(sales_aliquot) - expected_sales) < 0.01
                total_net_ok = abs(float(total_net) - expected_total_net) < 0.01
                total_tax_ok = abs(float(total_tax) - expected_total_tax) < 0.01
                total_ok = abs(float(total_val) - expected_total) < 0.01

                if buy_ok and sales_ok and total_net_ok and total_tax_ok and total_ok:
                    print(f"     ✅ TODOS LOS VALORES SON CORRECTOS")
                else:
                    print(f"     ❌ ERRORES DETECTADOS:")
                    if not buy_ok:
                        print(f"        ❌ buy_aliquot: esperado {expected_buy}, encontrado {float(buy_aliquot)}")
                    if not sales_ok:
                        print(f"        ❌ sales_aliquot: esperado {expected_sales}, encontrado {float(sales_aliquot)}")
                    if not total_net_ok:
                        print(f"        ❌ total_net_details: esperado {expected_total_net}, encontrado {float(total_net)}")
                    if not total_tax_ok:
                        print(f"        ❌ total_tax_details: esperado {expected_total_tax}, encontrado {float(total_tax)}")
                    if not total_ok:
                        print(f"        ❌ total_details: esperado {expected_total}, encontrado {float(total_val)}")
                print()
        else:
            print(f"  ⚠️ No hay registros en sales_operation_coins para este quote")

        print("\n" + "=" * 80)
        print("✅ TEST COMPLETADO")
        print("=" * 80)

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_sales_operation_coins()
