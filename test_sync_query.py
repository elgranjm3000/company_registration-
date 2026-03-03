#!/usr/bin/env python3
"""
Probar la consulta exacta que usa smart_sync_complete
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
print("🔍 EJECUTANDO CONSULTA DE SMART_SYNC_COMPLETE")
print("="*70)

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
WHERE a.code IN ('01')
  AND a.code IS NOT NULL
  AND a.code != ''
  AND a.product_type <> 'C'
ORDER BY a.code, b.maximum_price DESC;
"""

try:
    cursor.execute(query)
    result = cursor.fetchall()

    if result:
        print(f"\n✅ Consulta exitosa: {len(result)} filas devueltas\n")

        for idx, row in enumerate(result):
            print(f"📦 Fila {idx}:")
            print(f"  [0] code: {row[0]}")
            print(f"  [1] unit: {row[1]}")
            print(f"  [2] description: {row[2]}")
            print(f"  [3] short_name: {row[3]}")
            print(f"  [4] department: {row[4]}")
            print(f"  [5] product_code_pg: {row[5]}")
            print(f"  [6] unidad: {row[6]}")
            print(f"  [7] stock: {row[7]}")
            print(f"  [8] product_type: {row[8]}")
            print(f"  [9] coin: '{row[9]}'  ← ¿ES '01'? {row[9] == '01'}")
            print(f"  [10] description_coin: {row[10]}")
            print(f"  [11] price (maximum_price): {row[11]}")
            print(f"  [12] offer_price: {row[12]}")
            print(f"  [13] minimum_price: {row[13]}")
            print(f"  [14] minimal_stock: {row[14]}")
            print(f"  [15] status: {row[15]}")
            print(f"  [16] image_type: {row[16]}")
            print(f"  [17] product_image: {row[17]}")
            print(f"  [18] sale_tax: {row[18]}")
            print(f"  [19] aliquot: {row[19]}")
            print(f"  [20] buy_tax: {row[20]}")
            print(f"  [21] buy_aliquot: {row[21]}")
            print(f"  [22] unitary_cost: {row[22]}")

            if row[9] == '01':
                print(f"\n  💰 Debería convertirse de VES a USD:")
                print(f"     Precio actual: {row[11]} VES")
                print(f"     Precio convertido (tasa 421.88): {float(row[11])/421.88:.4f} USD")
    else:
        print("❌ NO devolvió resultados")
        print("\n💡 Verificar:")
        print("   - ¿El producto tiene registro en products_units?")
        print("   - ¿El producto tiene product_type <> 'C'?")

except Exception as e:
    print(f"❌ Error en consulta: {e}")
    import traceback
    traceback.print_exc()

cursor.close()
conn.close()
