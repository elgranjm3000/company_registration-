#!/usr/bin/env python3
"""
Script de diagnóstico para verificar por qué los productos NO se insertan en MySQL

Ejecuta este script para diagnosticar el problema:
python3 test_mysql_products.py
"""

import pymysql
import json
import os

def load_config():
    """Carga configuración desde sync_config.json"""
    config_file = None

    # Buscar archivo de configuración
    for fname in ['sync_config.json', '.sync_config.json', '../sync_config.json']:
        if os.path.exists(fname):
            config_file = fname
            break

    if not config_file:
        print("❌ No se encontró sync_config.json")
        return None

    with open(config_file, 'r') as f:
        config = json.load(f)

    # Desencriptar si es necesario
    from config_encryption import decrypt_config
    config = decrypt_config(config)

    return config

def test_mysql_connection():
    """Prueba la conexión a MySQL"""
    print("=" * 60)
    print("🔍 DIAGNÓSTICO: Por qué los productos NO se insertan en MySQL")
    print("=" * 60)
    print()

    config = load_config()
    if not config:
        return

    try:
        print("📊 Conectando a MySQL...")
        conn = pymysql.connect(
            host=config['mysql_host'],
            port=int(config['mysql_port']),
            user=config['mysql_user'],
            password=config['mysql_password'],
            database=config['mysql_database']
        )
        cursor = conn.cursor()
        print("✅ Conexión exitosa")
        print()

        # 1. Verificar si existe la tabla companies
        print("1️⃣  Verificando tabla 'companies'...")
        cursor.execute("SHOW TABLES LIKE 'companies'")
        if cursor.fetchone():
            print("   ✅ Tabla 'companies' existe")

            # Obtener company_id
            cursor.execute("SELECT id, rif FROM companies WHERE rif = %s", (config.get('company_rif', ''),))
            company = cursor.fetchone()
            if company:
                company_id, rif = company
                print(f"   ✅ Empresa encontrada: ID={company_id}, RIF={rif}")
            else:
                print(f"   ❌ NO existe empresa con RIF '{config.get('company_rif', '')}'")
                print("   ⚠️ Los productos necesitan un company_id válido")
                return
        else:
            print("   ❌ Tabla 'companies' NO existe")
            return
        print()

        # 2. Verificar si existe la tabla categories
        print("2️⃣  Verificando tabla 'categories'...")
        cursor.execute("SHOW TABLES LIKE 'categories'")
        if cursor.fetchone():
            print("   ✅ Tabla 'categories' existe")

            # Verificar cuántas categorías hay para esta empresa
            cursor.execute("SELECT COUNT(*) FROM categories WHERE company_id = %s", (company_id,))
            count = cursor.fetchone()[0]
            print(f"   📊 Categorías para esta empresa: {count}")

            if count == 0:
                print("   ❌ PROBLEMA ENCONTRADO: NO hay categorías para esta empresa")
                print("   ⚠️ Los productos NO se pueden insertar sin categorías")
                print()
                print("   SOLUCIONES:")
                print("   1. Sincroniza las categorías desde PostgreSQL primero")
                print("   2. O crea manualmente al menos una categoría en MySQL:")
                print()
                print("      INSERT INTO categories (company_id, name, status) VALUES")
                print(f"      ({company_id}, 'General', 'active');")
                print()
            else:
                # Mostrar las categorías disponibles
                cursor.execute("SELECT name, id FROM categories WHERE company_id = %s LIMIT 10", (company_id,))
                categories = cursor.fetchall()
                print(f"   ✅ Categorías disponibles:")
                for name, cat_id in categories:
                    print(f"      - {name} (ID: {cat_id})")
                if count > 10:
                    print(f"      ... y {count - 10} más")
        else:
            print("   ❌ Tabla 'categories' NO existe")
            print("   ⚠️ Los productos necesitan categorías")
        print()

        # 3. Verificar si existen productos
        print("3️⃣  Verificando tabla 'products'...")
        cursor.execute("SHOW TABLES LIKE 'products'")
        if cursor.fetchone():
            cursor.execute("SELECT COUNT(*) FROM products WHERE company_id = %s", (company_id,))
            count = cursor.fetchone()[0]
            print(f"   📊 Productos para esta empresa: {count}")

            if count == 0:
                print("   ⚠️ NO hay productos en MySQL")
            else:
                print(f"   ✅ Hay {count} productos en MySQL")
        else:
            print("   ❌ Tabla 'products' NO existe")
        print()

        # 4. Verificar permisos de INSERT
        print("4️⃣  Verificando permisos de INSERT...")
        try:
            # Intentar hacer un INSERT de prueba
            test_code = "TEST_DELETE_ME"
            cursor.execute("""
                INSERT INTO products (company_id, code, name, price, cost, stock, category_id, status)
                VALUES (%s, %s, 'Test', 0, 0, 0, %s, 'inactive')
            """, (company_id, test_code, list(cursor.execute("SELECT id FROM categories WHERE company_id = %s LIMIT 1", (company_id,)) or [None])[0] if count else None))
            conn.commit()
            print("   ✅ INSERT exitoso - Tienes permisos para insertar")

            # Limpiar el test
            cursor.execute("DELETE FROM products WHERE code = %s", (test_code,))
            conn.commit()
            print("   ✅ Test limpiado")

        except Exception as e:
            print(f"   ❌ ERROR de INSERT: {e}")
            print("   ⚠️ No tienes permisos para insertar productos")
        print()

        # 5. Diagnóstico final
        print("=" * 60)
        print("📋 DIAGNÓSTICO FINAL:")
        print("=" * 60)

        if count == 0:
            print()
            print("❌ PROBLEMA: NO hay productos en MySQL")
            print()
            print("CAUSAS MÁS PROBABLES:")
            print("   1. NO hay categorías para esta empresa en MySQL")
            print("      → Los productos no pueden insertarse sin categoría")
            print()
            print("   2. La sincronización se está ejecutando pero falla silenciosamente")
            print()
            print("SOLUCIONES:")
            print("   1. Ejecuta el sincronizador nuevamente y revisa los logs")
            print("   2. Busca estos mensajes en los logs:")
            print("      - '❌ ERROR CRÍTICO: NO hay categorías en MySQL'")
            print("      - '❌ ERROR en BATCH INSERT'")
            print("   3. Crea categorías manualmente en MySQL si es necesario")
            print()
        else:
            print()
            print("✅ Los productos SÍ están en MySQL")
            print(f"   Total: {count} productos")
            print()

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_mysql_connection()
