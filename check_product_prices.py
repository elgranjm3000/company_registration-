#!/usr/bin/env python3
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

# Buscar todos los productos con coin='01'
print("🔍 Productos con coin='01' en PostgreSQL:\n")
cursor.execute("""
    SELECT p.code, p.description, p.coin
    FROM products p
    WHERE p.coin = '01'
    ORDER BY p.code DESC
    LIMIT 10
""")

productos = cursor.fetchall()
if not productos:
    print("   ❌ NO hay productos con coin='01'")
    print("\n💡 Para crear un producto en VES:")
    print("   1. Crear el producto en products con coin='01'")
    print("   2. Crear el registro en products_units con los precios")
else:
    print(f"   ✅ {len(productos)} productos con coin='01':\n")

    for code, desc, coin in productos:
        print(f"📦 {code}: {desc}")
        print(f"   coin: {coin}")

        # Verificar si tiene precios en products_units
        cursor.execute("""
            SELECT unit, higher_price, offer_price, minimum_price, unitary_cost
            FROM products_units
            WHERE product_code = %s
            ORDER BY unit
        """, (code,))

        precios = cursor.fetchall()
        if not precios:
            print(f"   ❌ NO tiene precios en products_units")
            print(f"   💡 Debes crear el registro en products_units")
        else:
            print(f"   💰 Precios en products_units:")
            for unit, higher, offer, minimum, cost in precios:
                print(f"      Unit {unit}:")
                print(f"         - higher_price: {higher}")
                print(f"         - offer_price: {offer}")
                print(f"         - minimum_price: {minimum}")
                print(f"         - unitary_cost: {cost}")
        print()

# Mostrar cómo crear un producto en VES
print("\n" + "="*70)
print("💡 EJEMPLO PARA CREAR PRODUCTO EN VES:")
print("="*70)
print("""
-- 1. Crear producto
INSERT INTO products (code, description, coin, product_type)
VALUES ('TESTVES', 'Producto Prueba VES', '01', 'P');

-- 2. Crear precios en products_units
INSERT INTO products_units (product_code, unit, higher_price, offer_price, unitary_cost)
VALUES ('TESTVES', '00', 1500.00, 1200.00, 1000.00);

-- 3. Sincronizar
python sync_system.py --mode sync
""")

cursor.close()
conn.close()
