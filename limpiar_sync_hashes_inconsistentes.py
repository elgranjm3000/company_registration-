#!/usr/bin/env python3
"""
Limpiar registros inconsistentes en sync_hashes

Este script:
1. Busca clientes marcados como eliminados (deleted_at IS NOT NULL)
2. Verifica si aún existen en la tabla clients
3. Si existen, elimina el registro de sync_hashes (para que se sincronicen de nuevo)
"""

import psycopg2

# Configuración de PostgreSQL
PG_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'nueva',
    'user': 'postgres',
    'password': 'muentes123.'
}

def limpiar_inconsistentes():
    """Limpiar registros inconsistentes en sync_hashes"""

    try:
        conn = psycopg2.connect(**PG_CONFIG)
        cursor = conn.cursor()

        print("="*70)
        print("LIMPIANDO REGISTROS INCONSISTENTES EN sync_hashes")
        print("="*70)

        # Buscar clientes marcados como eliminados
        cursor.execute("""
            SELECT sh.record_key, c.code
            FROM sync_hashes sh
            LEFT JOIN clients c ON sh.record_key = c.code
            WHERE sh.table_name = 'customers'
              AND sh.deleted_at IS NOT NULL
              AND sh.company_id = 99
        """)

        eliminados_marcados = cursor.fetchall()

        if not eliminados_marcados:
            print("✅ No hay clientes marcados como eliminados")
            return

        print(f"\n📋 Encontrados {len(eliminados_marcados)} clientes marcados como eliminados")
        print("\nVerificando cuáles aún existen en clients...")

        clientes_existentes = []
        clientes_no_existentes = []

        for record_key, cliente_code in eliminados_marcados:
            if cliente_code:
                clientes_existentes.append((record_key, cliente_code))
                print(f"   ✅ {record_key} - AÚN EXISTE en clients")
            else:
                clientes_no_existentes.append((record_key, cliente_code))
                print(f"   ❌ {record_key} - NO existe en clients (correcto)")

        print(f"\n📊 Resumen:")
        print(f"   - Existen en clients: {len(clientes_existentes)}")
        print(f"   - No existen en clients: {len(clientes_no_existentes)}")

        if clientes_existentes:
            print(f"\n🧹 Limpiando {len(clientes_existentes)} registros inconsistentes...")

            for record_key, cliente_code in clientes_existentes:
                # Eliminar el registro de sync_hashes
                # Esto permitirá que el cliente se sincronice de nuevo como "nuevo"
                cursor.execute("""
                    DELETE FROM sync_hashes
                    WHERE table_name = 'customers'
                      AND record_key = %s
                      AND company_id = 99
                """, (record_key,))

                print(f"   ✅ Eliminado registro de sync_hashes: {record_key}")

            conn.commit()
            print(f"\n✅ Limpieza completada: {len(clientes_existentes)} registros")
        else:
            print("\n✅ No hay registros inconsistentes para limpiar")

        # Verificar resultado final
        cursor.execute("""
            SELECT COUNT(*)
            FROM sync_hashes
            WHERE table_name = 'customers'
              AND company_id = 99
              AND deleted_at IS NOT NULL
        """)

        count_deleted = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*)
            FROM sync_hashes
            WHERE table_name = 'customers'
              AND company_id = 99
              AND deleted_at IS NULL
        """)

        count_active = cursor.fetchone()[0]

        print(f"\n📊 Estado final de sync_hashes (customers):")
        print(f"   - Activos (deleted_at IS NULL): {count_active}")
        print(f"   - Eliminados (deleted_at IS NOT NULL): {count_deleted}")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        try:
            conn.rollback()
        except:
            pass

if __name__ == '__main__':
    limpiar_inconsistentes()
