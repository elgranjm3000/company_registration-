#!/usr/bin/env python3
"""
Verificar qué datos devuelve la consulta de sincronización para TESTVES
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

print("="*70)
print("🔍 VERIFICANDO DATOS DE TESTVES EN CONSULTA DE SINCRONIZACIÓN")
print("="*70)

# La misma consulta que usa smart_sync_complete
query = """
SELECT DISTINCT ON (a.code)
    a.code,
    b.unit,
    a.description,
    a.short_name,
    a.department,
    b.product_code,
    h.description as unidad,
    COALESCE(c.total_stock, 0) AS stock,
    a.product_type,
    a.coin,
    f.description AS description_coin,
    CASE
        WHEN b.maximum_price IS NULL
        THEN 0
        ELSE b.maximum_price
    END AS price,
    b.offer_price,
    b.minimum_price,
    a.minimal_stock,
    a.status,
    d.image_type,
    d.product_image,
    a.sale_tax,
    e.aliquot,
    a.buy_tax,
    g.aliquot AS buy_aliquot,
    b.unitary_cost
FROM products a
LEFT JOIN products_units b ON a.code = b.product_code
LEFT JOIN products_image d ON d.main_code = a.code
LEFT JOIN taxes e ON e.code = a.sale_tax
LEFT JOIN taxes g ON g.code = a.buy_tax
LEFT JOIN coin f ON f.code = a.coin
LEFT JOIN units h ON h.code = b.unit
LEFT JOIN (
    SELECT product_code, SUM(stock) as total_stock
    FROM products_stock
    GROUP BY product_code
) c ON a.code = c.product_code
WHERE a.code IN ('TESTVES')
  AND a.code IS NOT NULL
  AND a.code != ''
  AND a.product_type <> 'C'
ORDER BY a.code, b.maximum_price DESC;
"""

cursor.execute(query)
result = cursor.fetchall()

if result:
    row = result[0]
    print(f"\n✅ Producto TESTVES encontrado en consulta:\n")
    print(f"Índice 0 (code): {row[0]}")
    print(f"Índice 1 (unit): {row[1]}")
    print(f"Índice 2 (description): {row[2]}")
    print(f"Índice 3 (short_name): {row[3]}")
    print(f"Índice 4 (department): {row[4]}")
    print(f"Índice 5 (product_code): {row[5]}")
    print(f"Índice 6 (unidad): {row[6]}")
    print(f"Índice 7 (stock): {row[7]}")
    print(f"Índice 8 (product_type): {row[8]}")
    print(f"Índice 9 (coin): '{row[9]}'  ← ¿ES '01'? {row[9] == '01'}")
    print(f"Índice 10 (description_coin): {row[10]}")
    print(f"Índice 11 (price/maximum_price): {row[11]}")
    print(f"Índice 12 (offer_price): {row[12]}")
    print(f"Índice 13 (minimum_price): {row[13]}")
    print(f"Índice 14 (minimal_stock): {row[14]}")
    print(f"Índice 15 (status): {row[15]}")
    print(f"Índice 16 (image_type): {row[16]}")
    print(f"Índice 17 (product_image): {row[17]}")
    print(f"Índice 18 (sale_tax): {row[18]}")
    print(f"Índice 19 (aliquot): {row[19]}")
    print(f"Índice 20 (buy_tax): {row[20]}")
    print(f"Índice 21 (buy_aliquot): {row[21]}")
    print(f"Índice 22 (unitary_cost): {row[22]}")

    # Verificar si debería convertirse
    print(f"\n{'='*70}")
    print("💰 VERIFICACIÓN DE CONVERSIÓN:")
    print(f"{'='*70}")

    if row[9] == '01':
        print(f"✅ coin = '01' (BOLÍVARES)")
        print(f"   Debería convertirse a USD")

        # Calcular precios convertidos
        tasa = 421.88
        price = float(row[11]) if row[11] else 0
        cost = float(row[22]) if row[22] else 0

        print(f"\n   Precios en PostgreSQL (VES):")
        print(f"   - price (maximum_price): {price} VES")
        print(f"   - cost (unitary_cost): {cost} VES")

        print(f"\n   Precios esperados en MySQL (USD con tasa {tasa}):")
        print(f"   - price: {price/tasa:.4f} USD")
        print(f"   - cost: {cost/tasa:.4f} USD")
    else:
        print(f"❌ coin = '{row[9]}' (NO es '01')")
        print(f"   NO se convertirá")
else:
    print("❌ TESTVES NO encontrado en consulta")

cursor.close()
conn.close()
