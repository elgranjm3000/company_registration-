#!/usr/bin/env python3
"""
Verificar datos completos del producto 01
"""
import psycopg2
import json

with open('.sync_config.json', 'r') as f:
    config = json.load(f)

conn = psycopg2.connect(
    host=config['postgres_host'],
    database=config['postgres_database'],
    user=config['postgres_user'],
    password=config['postgres_password']
)
cursor = conn.cursor()

# Ver el producto completo
print("="*70)
print("📦 PRODUCTO 01 - DATOS COMPLETOS")
print("="*70)

cursor.execute("""
    SELECT p.code, p.description, p.coin, p.product_type, p.department,
           pu.unit, pu.higher_price, pu.offer_price, pu.minimum_price, pu.unitary_cost
    FROM products p
    LEFT JOIN products_units pu ON p.code = pu.product_code
    WHERE p.code = '01'
""")

result = cursor.fetchall()
if result:
    print(f"\n✅ Producto encontrado ({len(result)} registros en products_units):\n")
    for row in result:
        code, desc, coin, ptype, dept, unit, higher, offer, minimum, cost = row
        print(f"code: {code}")
        print(f"description: {desc}")
        print(f"coin: '{coin}' (tipo: {type(coin).__name__})")
        print(f"product_type: {ptype}")
        print(f"department: {dept}")
        print(f"unit: {unit}")
        print(f"higher_price: {higher}")
        print(f"offer_price: {offer}")
        print(f"minimum_price: {minimum}")
        print(f"unitary_cost: {cost}")
        print()

        # Verificar si coin es '01'
        if coin == '01':
            print("✅ coin = '01' (BOLÍVARES)")
            print(f"   Debería convertirse a USD")
            print(f"   Precio esperado en USD: {float(higher)/421.88:.4f}" if higher else "   N/A")
        else:
            print(f"⚠️ coin = '{coin}' (NO es '01')")
else:
    print("❌ Producto 01 NO encontrado")

# Verificar consulta que usa smart_sync_complete
print("\n" + "="*70)
print("🔍 CONSULTA QUE USA SMART_SYNC_COMPLETE")
print("="*70)

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
        b.higher_price,
        b.offer_price,
        b.minimum_price,
        b.unitary_cost,
        a.minimal_stock,
        a.status,
        a.image_type,
        a.product_image,
        a.sale_tax,
        b.aliquot,
        a.buy_tax,
        b.buy_aliquot
    FROM products a
    LEFT JOIN products_units b ON a.code = b.product_code AND b.unit = '00'
    LEFT JOIN products_stock c ON a.code = c.product_code
    LEFT JOIN coin f ON a.coin = f.code
    WHERE a.code IS NOT NULL AND a.code != ''
      AND a.code = '01'
    LIMIT 1
""")

result = cursor.fetchone()
if result:
    print(f"\n✅ Producto encontrado en consulta de sincronización:\n")
    print(f"Índice 0 (code): {result[0]}")
    print(f"Índice 1 (description): {result[1]}")
    print(f"Índice 2 (short_name): {result[2]}")
    print(f"Índice 3 (department): {result[3]}")
    print(f"Índice 4 (stock): {result[4]}")
    print(f"Índice 5 (product_type): {result[5]}")
    print(f"Índice 6 (coin): '{result[6]}' ← ESTE ES EL CAMPO QUE SE VERIFICA")
    print(f"Índice 7 (description_coin): {result[7]}")
    print(f"Índice 8 (higher_price): {result[8]}")
    print(f"Índice 9 (offer_price): {result[9]}")
    print(f"Índice 10 (minimum_price): {result[10]}")
    print(f"Índice 11 (unitary_cost): {result[11]}")
    print(f"\n¿coin == '01'? {result[6] == '01'}")
else:
    print("❌ Producto NO encontrado en consulta de sincronización")
    print("\n💡 Puede que el producto no tenga:")
    print("   - Un registro en products_units con unit='00'")
    print("   - Un registro en la tabla coin con code='01'")

cursor.close()
conn.close()
