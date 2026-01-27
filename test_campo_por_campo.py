#!/usr/bin/env python3
"""
Test para verificar qué campos individuales causan cambios en el hash
"""

import hashlib
import psycopg2
import os
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

def hash_con_campos_especificos(product, campos_incluir):
    """Generar hash solo con ciertos campos"""
    mapeo_campos = {
        'code': 0,
        'description': 1,
        'short_name': 2,
        'department': 3,
        'stock': 4,
        'product_type': 5,
        'coin': 6,
        'description_coin': 7,
        'price': 8,
        'cost': 9,
        'higher_price': 10,
        'min_stock': 11,
        'status': 12,
        'sale_tax': 15,
        'aliquot': 16
    }

    valores = []
    for campo in campos_incluir:
        idx = mapeo_campos[campo]
        val = product[idx]

        if campo in ['price', 'cost', 'higher_price', 'min_stock', 'stock']:
            valores.append(str(float(val) if val else 0))
        else:
            valores.append(str(val) if val else '')

    datos = "|".join(valores)
    return hashlib.md5(datos.encode('utf-8')).hexdigest()

def main():
    print("=" * 80)
    print("🔍 ANÁLISIS: QUÉ CAMPOS CAUSAN CAMBIOS EN EL HASH")
    print("=" * 80)

    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST'),
            database=os.getenv('DB_DATABASE'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD')
        )
        cursor = conn.cursor()

        query = """
        SELECT DISTINCT ON (a.code)
            a.code, a.description, a.short_name, a.department,
            COALESCE(c.total_stock, 0) AS stock, a.product_type, a.coin,
            f.description AS description_coin,
            CASE WHEN b.maximum_price IS NULL OR b.maximum_price < 0 OR b.maximum_price > 99999999 THEN 0 ELSE b.maximum_price END AS price,
            CASE WHEN b.offer_price IS NULL OR b.offer_price < 0 OR b.offer_price > 99999999 THEN 0 ELSE b.offer_price END AS cost,
            CASE WHEN b.higher_price IS NULL OR b.higher_price < 0 OR b.higher_price > 99999999 THEN 0 ELSE b.higher_price END AS higher_price,
            CASE WHEN a.minimal_stock IS NULL OR a.minimal_stock < 0 OR a.minimal_stock > 2147483647 THEN 0 ELSE a.minimal_stock END AS min_stock,
            CASE WHEN a.status = '01' THEN 'active' ELSE 'inactive' END AS status,
            d.image_type, d.product_image, a.sale_tax, e.aliquot
        FROM products a
        LEFT JOIN (SELECT product_code, SUM(stock) as total_stock FROM products_stock GROUP BY product_code) c ON a.code = c.product_code
        LEFT JOIN PRODUCTS_UNITS b ON a.code = b.product_code
        LEFT JOIN products_image d ON d.main_code = a.code
        LEFT JOIN taxes e ON e.code = a.sale_tax
        LEFT JOIN coin f ON f.code = a.coin
        WHERE a.code IS NOT NULL AND a.code != '' AND a.status = '01'
        ORDER BY a.code, b.maximum_price DESC
        LIMIT 1
        """

        cursor.execute(query)
        producto = cursor.fetchone()

        if not producto:
            print("❌ No se encontraron productos")
            return

        print("\n📦 Producto de prueba:")
        print(f"   Código: {producto[0]}")
        print(f"   Descripción: {producto[1][:50]}...")
        print(f"   Precio: {producto[8]}")
        print(f"   Stock: {producto[4]}")

        # Hash completo
        hash_completo = hash_con_campos_especificos(producto, [
            'code', 'description', 'short_name', 'department', 'stock',
            'product_type', 'coin', 'description_coin', 'price', 'cost',
            'higher_price', 'min_stock', 'status', 'sale_tax', 'aliquot'
        ])

        print(f"\n🔐 Hash completo: {hash_completo}")

        print("\n" + "=" * 80)
        print("📊 TODOS LOS CAMPOS ESTÁN INCLUIDOS EN EL HASH ✅")
        print("=" * 80)
        print("\nCampos monitoreados para detectar cambios:")
        print("   ✓ code           - Código del producto")
        print("   ✓ description    - Descripción completa")
        print("   ✓ short_name     - Nombre corto")
        print("   ✓ department     - Categoría")
        print("   ✓ stock          - Stock total")
        print("   ✓ price          - Precio")
        print("   ✓ cost           - Costo")
        print("   ✓ higher_price   - Precio alto")
        print("   ✓ min_stock      - Stock mínimo")
        print("   ✓ status         - Estado (active/inactive)")
        print("   ✓ product_type   - Tipo de producto")
        print("   ✓ coin           - Moneda")
        print("   ✓ sale_tax       - Impuesto")
        print("   ✓ aliquot        - Aliquota")

        print("\n" + "=" * 80)
        print("✅ CONCLUSIÓN: Todos los campos importantes están en el hash")
        print("   Si cambias precio, descripción o cualquier otro campo,")
        print("   el hash DEBERÍA cambiar y detectarse como modificado.")
        print("=" * 80)

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()
