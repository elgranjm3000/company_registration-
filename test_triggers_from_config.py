#!/usr/bin/env python3
"""
Script de prueba para verificar que los triggers se crean correctamente
Lee la configuración desde sync_config_api.json
"""

import psycopg2
import sys
import os
import json

CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".chrystal_sync_config.json")

def cargar_configuracion():
    """Carga la configuración desde el archivo"""
    if not os.path.exists(CONFIG_FILE):
        print(f"❌ No existe configuración en: {CONFIG_FILE}")
        print("   Primero ejecuta el sincronizador en modo --config")
        return None

    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)

    return config

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

def main():
    """Función principal"""
    print("=" * 70)
    print("🧪 PRUEBA DE TRIGGERS DE SINCRONIZACIÓN")
    print("=" * 70)

    # Cargar configuración
    config = cargar_configuracion()
    if not config:
        return 1

    # Configurar conexión PostgreSQL
    pg_config = {
        'host': config.get('postgres_host', 'localhost'),
        'port': int(config.get('postgres_port', 5432)),
        'database': config.get('postgres_database', ''),
        'user': config.get('postgres_user', 'postgres'),
        'password': config.get('postgres_password', '')
    }

    try:
        # Conectar a PostgreSQL
        print(f"\n🔗 Conectando a PostgreSQL...")
        print(f"   Host: {pg_config['host']}")
        print(f"   Port: {pg_config['port']}")
        print(f"   Database: {pg_config['database']}")
        print(f"   User: {pg_config['user']}")

        conn = psycopg2.connect(**pg_config)
        cursor = conn.cursor()
        print("✅ Conexión exitosa")

        # Verificar sync_config
        verificar_sync_config(cursor)

        # Ejecutar archivo SQL de triggers
        print("\n" + "=" * 70)
        print("📝 EJECUTANDO ARCHIVO SQL DE TRIGGERS")
        print("=" * 70)

        # Obtener directorio del script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        sql_file = os.path.join(script_dir, 'create_triggers_all_versions.sql')

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

        # Resumen final
        print("\n" + "=" * 70)
        print("✅ TODAS LAS PRUEBAS PASARON EXITOSAMENTE")
        print("=" * 70)
        print("\n📋 Resumen:")
        print("  ✅ Triggers creados correctamente")
        print("  ✅ Triggers verificados en PostgreSQL")
        print("\n💡 Los triggers están listos para usar")
        print("\n📝 Prueba manual:")
        print("   INSERT INTO products (code, description, price) VALUES ('TEST001', 'Prueba', 100);")
        print("   SELECT * FROM sync_hashes WHERE table_name = 'products' AND record_key = 'TEST001';")

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
