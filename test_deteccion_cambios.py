#!/usr/bin/env python3
"""
Script de diagnóstico para verificar la detección de cambios en productos
"""

import hashlib
import psycopg2
from decimal import Decimal
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

def generar_hash_product(product):
    """Generar hash MD5 para un producto (misma lógica que smart_sync_complete.py)"""
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
        print(f"Error generando hash: {e}")
        return hashlib.md5(str(product[0]).encode()).hexdigest()

def main():
    print("=" * 80)
    print("🔍 DIAGNÓSTICO: DETECCIÓN DE CAMBIOS EN PRODUCTOS")
    print("=" * 80)

    try:
        # Conectar a PostgreSQL
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST'),
            database=os.getenv('DB_DATABASE'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD')
        )
        cursor = conn.cursor()

        print("\n📌 Paso 1: Obtener productos de PostgreSQL")
        print("-" * 80)

        query = """
        SELECT DISTINCT ON (a.code)
            a.code,
            a.description,
            a.short_name,
            a.department,
            COALESCE(c.total_stock, 0) AS stock,
            a.product_type,
            a.coin,
            f.description AS description_coin,
            CASE
                WHEN b.maximum_price IS NULL OR b.maximum_price < 0 OR b.maximum_price > 99999999
                THEN 0
                ELSE b.maximum_price
            END AS price,
            CASE
                WHEN b.offer_price IS NULL OR b.offer_price < 0 OR b.offer_price > 99999999
                THEN 0
                ELSE b.offer_price
            END AS cost,
            CASE
                WHEN b.higher_price IS NULL OR b.higher_price < 0 OR b.higher_price > 99999999
                THEN 0
                ELSE b.higher_price
            END AS higher_price,
            CASE
                WHEN a.minimal_stock IS NULL OR a.minimal_stock < 0 OR a.minimal_stock > 2147483647
                THEN 0
                ELSE a.minimal_stock
            END AS min_stock,
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
        WHERE a.code IS NOT NULL
          AND a.code != ''
          AND a.status = '01'
        ORDER BY a.code, b.maximum_price DESC
        LIMIT 5
        """

        cursor.execute(query)
        productos = cursor.fetchall()

        print(f"✅ Se obtuvieron {len(productos)} productos de muestra\n")

        # Obtener hashes guardados
        print("📌 Paso 2: Obtener hashes guardados en sync_hashes")
        print("-" * 80)

        cursor.execute("""
            SELECT record_key, record_hash, last_sync_data
            FROM sync_hashes
            WHERE table_name = 'products'
            LIMIT 5
        """)
        hashes_guardados = cursor.fetchall()
        print(f"✅ Se obtuvieron {len(hashes_guardados)} hashes guardados\n")

        # Crear diccionario de hashes
        hashes_dict = {row[0]: row[1] for row in hashes_guardados}

        # Analizar productos
        print("📌 Paso 3: Comparar hashes y detectar cambios")
        print("-" * 80)
        print("\n{:<15} | {:<10} | {:<10} | {:<10} | {:<10}".format(
            "Código", "Hash Nuevo", "Hash Guardado", "¿Cambio?", "Precio"
        ))
        print("-" * 80)

        cambios_detectados = 0
        sin_cambios = 0

        for producto in productos:
            code = producto[0]
            hash_nuevo = generar_hash_product(producto)
            hash_guardado = hashes_dict.get(code)
            precio = float(producto[8]) if producto[8] else 0

            if hash_guardado:
                if hash_nuevo != hash_guardado:
                    estado = "¡CAMBIÓ!"
                    cambios_detectados += 1
                else:
                    estado = "Igual"
                    sin_cambios += 1
            else:
                estado = "Nuevo"

            # Mostrar solo primeros 8 caracteres del hash para legibilidad
            hash_nuevo_short = hash_nuevo[:8] + "..."
            hash_guardado_short = hash_guardado[:8] + "..." if hash_guardado else "N/A"

            print("{:<15} | {:<10} | {:<10} | {:<10} | ${:.2f}".format(
                code, hash_nuevo_short, hash_guardado_short, estado, precio
            ))

        print("\n" + "=" * 80)
        print(f"📊 RESUMEN:")
        print(f"   - Productos analizados: {len(productos)}")
        print(f"   - Cambios detectados: {cambios_detectados}")
        print(f"   - Sin cambios: {sin_cambios}")
        print("=" * 80)

        # Mostrar un producto completo con todos sus valores
        if productos:
            print("\n📌 Paso 4: Ejemplo completo de un producto")
            print("-" * 80)
            p = productos[0]
            print(f"""
Código:           {p[0]}
Descripción:       {p[1]}
Nombre corto:      {p[2]}
Departamento:      {p[3]}
Stock:            {p[4]} (tipo: {type(p[4]).__name__})
Tipo producto:     {p[5]}
Moneda:           {p[6]}
Desc. moneda:      {p[7]}
Precio:           {p[8]} (tipo: {type(p[8]).__name__})
Costo:            {p[9]} (tipo: {type(p[9]).__name__})
Precio alto:       {p[10]} (tipo: {type(p[10]).__name__})
Stock mínimo:      {p[11]} (tipo: {type(p[11]).__name__})
Status:           {p[12]}
Tipo imagen:       {p[13]}
Sale tax:         {p[15]}
Aliquot:         {p[16]}

Hash generado:    {generar_hash_product(p)}
""")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
