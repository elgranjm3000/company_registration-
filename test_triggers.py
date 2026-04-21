#!/usr/bin/env python3
"""
Script de prueba para verificar que los triggers se crean correctamente
"""

import psycopg2
import sys
import os

# Configuración de PostgreSQL (modificar según necesidad)
PG_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'chrystal',  # Cambiar por tu base de datos
    'user': 'postgres',      # Cambiar por tu usuario
    'password': 'root'       # Cambiar por tu password
}

def ejecutar_sql_archivo(cursor, sql_file):
    """Ejecuta un archivo SQL dividiéndolo en statements individuales"""
    if not os.path.exists(sql_file):
        print(f"❌ Archivo no encontrado: {sql_file}")
        return False

    print(f"📄 Leyendo archivo: {sql_file}")
    with open(sql_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()

    # Dividir en statements
    statements = []
    for statement in sql_content.split(';'):
        statement = statement.strip()
        if statement and not statement.startswith('--'):
            statements.append(statement)

    print(f"📊 Total de statements a ejecutar: {len(statements)}")

    # Ejecutar cada statement
    exitosos = 0
    fallidos = 0
    for i, statement in enumerate(statements, 1):
        try:
            cursor.execute(statement)
            exitosos += 1
            if i % 10 == 0:
                print(f"  Progreso: {i}/{len(statements)} statements...")
        except Exception as e:
            fallidos += 1
            print(f"  ⚠️ Error en statement {i}: {str(e)[:100]}")

    print(f"✅ Statements ejecutados: {exitosos} exitosos, {fallidos} fallidos")
    return exitosos > 0

def verificar_triggers_creados(cursor):
    """Verifica qué triggers fueron creados"""
    print("\n🔍 Verificando triggers creados...")

    cursor.execute("""
        SELECT tgname
        FROM pg_trigger
        WHERE tgname LIKE '%sync_hashes%'
        ORDER BY tgname
    """)

    triggers = [row[0] for row in cursor.fetchall()]

    if not triggers:
        print("❌ No se encontraron triggers creados")
        return False

    print(f"✅ Triggers encontrados ({len(triggers)}):")
    for trigger in triggers:
        print(f"  - {trigger}")

    return True

def verificar_sync_config(cursor):
    """Verifica que sync_config tenga el company_id"""
    print("\n🔍 Verificando sync_config...")

    cursor.execute("""
        SELECT key, value
        FROM sync_config
        WHERE key = 'company_id'
    """)

    result = cursor.fetchone()

    if result:
        print(f"✅ company_id encontrado: {result[1]}")
        return True
    else:
        print("⚠️ company_id no encontrado en sync_config")
        print("   Insertando company_id = 1...")
        cursor.execute("""
            INSERT INTO sync_config (key, value, updated_at)
            VALUES ('company_id', '1', NOW())
            ON CONFLICT (key) DO UPDATE SET value = '1', updated_at = NOW()
        """)
        print("✅ company_id insertado")
        return True

def prueba_trigger_insert(cursor, conn):
    """Prueba que el trigger de INSERT funcione"""
    print("\n🧪 Probando trigger INSERT en products...")

    try:
        # Insertar un producto de prueba
        cursor.execute("""
            INSERT INTO products (code, description, price, cost)
            VALUES ('TEST_TRIGGER_001', 'Producto de prueba triggers', 100.00, 50.00)
            RETURNING code
        """)
        product_code = cursor.fetchone()[0]
        conn.commit()

        print(f"  ✅ Producto insertado: {product_code}")

        # Verificar que se creó en sync_hashes
        cursor.execute("""
            SELECT table_name, record_key, pending_sync, company_id
            FROM sync_hashes
            WHERE table_name = 'products'
            AND record_key = %s
        """, (product_code,))

        result = cursor.fetchone()

        if result:
            print(f"  ✅ Trigger funcionó:")
            print(f"     - table_name: {result[0]}")
            print(f"     - record_key: {result[1]}")
            print(f"     - pending_sync: {result[2]}")
            print(f"     - company_id: {result[3]}")

            # Limpiar producto de prueba
            cursor.execute("DELETE FROM products WHERE code = %s", (product_code,))
            cursor.execute("DELETE FROM sync_hashes WHERE record_key = %s", (product_code,))
            conn.commit()
            return True
        else:
            print("  ❌ Trigger NO funcionó: no se encontró registro en sync_hashes")
            return False

    except Exception as e:
        print(f"  ❌ Error en prueba: {e}")
        conn.rollback()
        return False

def main():
    """Función principal"""
    print("=" * 70)
    print("🧪 PRUEBA DE TRIGGERS DE SINCRONIZACIÓN")
    print("=" * 70)

    try:
        # Conectar a PostgreSQL
        print(f"\n🔗 Conectando a PostgreSQL...")
        print(f"   Host: {PG_CONFIG['host']}")
        print(f"   Port: {PG_CONFIG['port']}")
        print(f"   Database: {PG_CONFIG['database']}")
        print(f"   User: {PG_CONFIG['user']}")

        conn = psycopg2.connect(**PG_CONFIG)
        cursor = conn.cursor()
        print("✅ Conexión exitosa")

        # Verificar sync_config
        verificar_sync_config(cursor)

        # Ejecutar archivo SQL de triggers
        print("\n" + "=" * 70)
        print("📝 EJECUTANDO ARCHIVO SQL DE TRIGGERS")
        print("=" * 70)

        sql_file = 'create_triggers_all_versions.sql'
        if not ejecutar_sql_archivo(cursor, sql_file):
            print("❌ Error ejecutando archivo SQL")
            return 1

        conn.commit()

        # Verificar triggers creados
        print("\n" + "=" * 70)
        print("VERIFICACIÓN DE TRIGGERS")
        print("=" * 70)

        if not verificar_triggers_creados(cursor):
            print("❌ No se crearon los triggers correctamente")
            return 1

        # Prueba de funcionamiento
        print("\n" + "=" * 70)
        print("PRUEBA DE FUNCIONAMIENTO")
        print("=" * 70)

        if not prueba_trigger_insert(cursor, conn):
            print("❌ La prueba de funcionamiento falló")
            return 1

        # Resumen final
        print("\n" + "=" * 70)
        print("✅ TODAS LAS PRUEBAS PASARON EXITOSAMENTE")
        print("=" * 70)
        print("\n📋 Resumen:")
        print("  ✅ Triggers creados correctamente")
        print("  ✅ Triggers verificados en PostgreSQL")
        print("  ✅ Prueba de funcionamiento exitosa")
        print("\n💡 Los triggers están listos para usar")

        cursor.close()
        conn.close()
        return 0

    except psycopg2.Error as e:
        print(f"\n❌ Error de PostgreSQL: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
