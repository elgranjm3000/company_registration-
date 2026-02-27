#!/usr/bin/env python3
"""
Script de prueba para el trigger de eliminación de productos

Este script:
1. Crea un producto de prueba
2. Crea un hash en sync_hashes
3. Elimina el producto (activa el trigger)
4. Verifica que sync_hashes tenga deleted_at marcado
5. Ejecuta la sincronización
6. Verifica que se eliminó de MySQL
"""

import psycopg2
import pymysql
from dotenv import load_dotenv
import os
import time

def test_trigger_eliminacion():
    """Prueba el trigger de eliminación"""
    load_dotenv()

    print("=" * 80)
    print("🧪 PRUEBA DE TRIGGER DE ELIMINACIÓN DE PRODUCTOS")
    print("=" * 80)
    print()

    # Conectar a PostgreSQL
    print("1️⃣ Conectando a PostgreSQL...")
    pg_conn = psycopg2.connect(
        host=os.getenv('DB_HOST'),
        database=os.getenv('DB_DATABASE'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD')
    )
    pg_cursor = pg_conn.cursor()
    print("   ✅ Conectado")

    # Conectar a MySQL
    print("\n2️⃣ Conectando a MySQL...")
    mysql_conn = pymysql.connect(
        host='91.238.160.176',
        port=3306,
        database='chrystal_movil',
        user='chrystal_app',
        password='muentes123.',
        charset='utf8mb4'
    )
    mysql_cursor = mysql_conn.cursor()
    print("   ✅ Conectado")

    # Obtener company_id
    print("\n3️⃣ Obteniendo company_id...")
    mysql_cursor.execute(
        "SELECT id FROM acceso WHERE id_fiscal = %s AND correo_electronico = %s LIMIT 1",
        ('J502741283', 'multiserviciosleblanc@gmail.com')
    )
    company = mysql_cursor.fetchone()
    if not company:
        print("   ❌ Empresa no encontrada")
        return
    company_id = company[0]
    print(f"   ✅ Company ID: {company_id}")

    # PASO 1: Crear producto de prueba en PostgreSQL
    print("\n4️⃣ Creando producto de prueba en PostgreSQL...")
    test_code = 'TEST-DELETE-001'
    pg_cursor.execute(
        """
        INSERT INTO products (code, name, description, price, cost)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING code
        """,
        (test_code, 'Producto Test Eliminación', 'Producto para probar trigger', 100.0, 50.0)
    )
    pg_conn.commit()
    print(f"   ✅ Producto creado: {test_code}")

    # PASO 2: Sincronizar el producto a MySQL (simular sincronización)
    print("\n5️⃣ Sincronizando producto a MySQL...")
    mysql_cursor.execute(
        """
        INSERT INTO products (company_id, code, name, description, price, cost)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (company_id, test_code, 'Producto Test Eliminación', 'Producto para probar trigger', 100.0, 50.0)
    )
    mysql_conn.commit()
    print(f"   ✅ Producto sincronizado a MySQL")

    # PASO 3: Crear hash en sync_hashes
    print("\n6️⃣ Creando hash en sync_hashes...")
    pg_cursor.execute(
        """
        INSERT INTO sync_hashes (table_name, record_key, record_hash, company_id)
        VALUES (%s, %s, %s, %s)
        """,
        ('products', test_code, 'test_hash_123', company_id)
    )
    pg_conn.commit()
    print(f"   ✅ Hash creado")

    # Verificar que el producto existe en ambos lados
    print("\n7️⃣ Verificando estado antes de eliminar...")

    pg_cursor.execute("SELECT code FROM products WHERE code = %s", (test_code,))
    exists_pg = pg_cursor.fetchone()
    print(f"   PostgreSQL: {'✅ Existe' if exists_pg else '❌ No existe'}")

    mysql_cursor.execute("SELECT id FROM products WHERE code = %s AND company_id = %s", (test_code, company_id))
    exists_mysql = mysql_cursor.fetchone()
    print(f"   MySQL: {'✅ Existe' if exists_mysql else '❌ No existe'}")

    pg_cursor.execute("SELECT deleted_at FROM sync_hashes WHERE record_key = %s", (test_code,))
    hash_deleted = pg_cursor.fetchone()
    print(f"   sync_hashes deleted_at: {'❌ NULL' if not hash_deleted or not hash_deleted[0] else '✅ Tiene valor'}")

    # PASO 4: Eliminar producto de PostgreSQL (ACTIVA EL TRIGGER)
    print(f"\n8️⃣ Eliminando producto de PostgreSQL (ACTIVA EL TRIGGER)...")
    pg_cursor.execute("DELETE FROM products WHERE code = %s", (test_code,))
    pg_conn.commit()
    print(f"   ✅ Producto eliminado de PostgreSQL")

    # PASO 5: Verificar que el trigger marcó deleted_at
    print("\n9️⃣ Verificando que el TRIGGER marcó deleted_at...")
    pg_cursor.execute(
        """
        SELECT table_name, record_key, deleted_at
        FROM sync_hashes
        WHERE record_key = %s
        """,
        (test_code,)
    )
    result = pg_cursor.fetchone()

    if result and result[2]:
        print(f"   ✅ TRIGGER FUNCIONÓ!")
        print(f"      table_name: {result[0]}")
        print(f"      record_key: {result[1]}")
        print(f"      deleted_at: {result[2]}")
    else:
        print(f"   ❌ TRIGGER NO FUNCIONÓ - deleted_at sigue siendo NULL")

    # PASO 6: Verificar cuántos productos marcados para eliminar hay
    print("\n🔟 Verificando productos marcados para eliminar...")
    pg_cursor.execute(
        """
        SELECT COUNT(*)
        FROM sync_hashes
        WHERE table_name = 'products'
        AND deleted_at IS NOT NULL
        """
    )
    count = pg_cursor.fetchone()[0]
    print(f"   Productos marcados para eliminar: {count}")

    # PASO 7: Simular sincronización (eliminar de MySQL)
    print("\n1️⃣1️⃣ Simulando sincronización (eliminar de MySQL)...")

    pg_cursor.execute(
        """
        SELECT record_key
        FROM sync_hashes
        WHERE table_name = 'products'
        AND deleted_at IS NOT NULL
        """
    )
    productos_a_eliminar = pg_cursor.fetchall()

    for (product_code,) in productos_a_eliminar:
        mysql_cursor.execute(
            "DELETE FROM products WHERE code = %s AND company_id = %s",
            (product_code, company_id)
        )
        print(f"   🗑️ Producto {product_code} eliminado de MySQL")

    mysql_conn.commit()

    # PASO 8: Limpiar sync_hashes
    print("\n1️⃣2️⃣ Limpiando sync_hashes...")
    pg_cursor.execute(
        "DELETE FROM sync_hashes WHERE table_name = 'products' AND deleted_at IS NOT NULL"
    )
    filas = pg_cursor.rowcount
    pg_conn.commit()
    print(f"   ✅ {filas} registros eliminados de sync_hashes")

    # VERIFICACIÓN FINAL
    print("\n" + "=" * 80)
    print("📊 VERIFICACIÓN FINAL")
    print("=" * 80)

    pg_cursor.execute("SELECT code FROM products WHERE code = %s", (test_code,))
    exists_pg = pg_cursor.fetchone()
    print(f"PostgreSQL: {'❌ No existe (correcto)' if not exists_pg else '⚠️ Aún existe'}")

    mysql_cursor.execute("SELECT id FROM products WHERE code = %s AND company_id = %s", (test_code, company_id))
    exists_mysql = mysql_cursor.fetchone()
    print(f"MySQL: {'❌ No existe (correcto)' if not exists_mysql else '⚠️ Aún existe'}")

    pg_cursor.execute("SELECT record_key FROM sync_hashes WHERE record_key = %s", (test_code,))
    exists_hash = pg_cursor.fetchone()
    print(f"sync_hashes: {'❌ No existe (correcto)' if not exists_hash else '⚠️ Aún existe'}")

    print("\n" + "=" * 80)
    print("✅ PRUEBA COMPLETADA")
    print("=" * 80)

    pg_cursor.close()
    pg_conn.close()
    mysql_cursor.close()
    mysql_conn.close()

if __name__ == "__main__":
    test_trigger_eliminacion()
