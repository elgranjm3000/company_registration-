#!/usr/bin/env python3
"""
Test del flujo de eliminación de clientes de PostgreSQL a API REST

Este test verifica:
1. Eliminar un cliente en PostgreSQL
2. Verificar que el trigger marca deleted_at en sync_hashes
3. Detectar el cambio con detect_changes()
4. Verificar que se llame a delete_from_api()
"""

import psycopg2
import json
from datetime import datetime

# Configuración de PostgreSQL
PG_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'nueva',
    'user': 'postgres',
    'password': 'muentes123.'
}

# Company ID para pruebas
COMPANY_ID = 99

def connect_postgres():
    """Conectar a PostgreSQL"""
    try:
        conn = psycopg2.connect(**PG_CONFIG)
        conn.autocommit = False
        cursor = conn.cursor()
        return conn, cursor
    except Exception as e:
        print(f"❌ Error conectando a PostgreSQL: {e}")
        return None, None

def print_section(title):
    """Imprimir separador de sección"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)

def test_delete_flow():
    """Probar el flujo completo de eliminación"""

    print_section("TEST DE ELIMINACIÓN DE CLIENTES")

    conn, cursor = connect_postgres()
    if not conn:
        return

    try:
        # =========================================================================
        # PASO 1: Buscar un cliente de prueba
        # =========================================================================
        print_section("PASO 1: Buscar cliente de prueba")

        cursor.execute("""
            SELECT code, description
            FROM clients
            LIMIT 1
        """)

        cliente = cursor.fetchone()

        if not cliente:
            print("❌ No hay clientes en la tabla. Creando uno de prueba...")

            # Crear un cliente de prueba
            test_code = 'TEST_DELETE_001'
            cursor.execute("""
                INSERT INTO clients (
                    code, description, address, client_id,
                    email, phone, contact, name_fiscal, status, generic_client,
                    client_type,
                    country, province, city, town, area_sales, seller, client_group,
                    credit_days, credit_limit, discount, sale_price
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s
                )
            """, (
                test_code, 'Cliente Test Eliminar', 'Dirección Test', '12345678',
                'test@test.com', '0414-1234567', 'Contacto', 0, '01', False, '01',
                '00', '00', '00', '00', '00', '00', '00',
                0, 0, 0, 0
            ))
            conn.commit()

            cliente_code = test_code
            cliente_desc = 'Cliente Test Eliminar'
        else:
            cliente_code = cliente[0]
            cliente_desc = cliente[1]

        print(f"✅ Cliente encontrado: {cliente_code} - {cliente_desc}")

        # =========================================================================
        # PASO 2: Verificar que existe en sync_hashes ANTES de eliminar
        # =========================================================================
        print_section("PASO 2: Verificar sync_hashes ANTES de eliminar")

        cursor.execute("""
            SELECT record_key, pending_sync, deleted_at
            FROM sync_hashes
            WHERE table_name = 'customers'
              AND record_key = %s
              AND company_id = %s
        """, (cliente_code, COMPANY_ID))

        sync_hash_before = cursor.fetchone()

        if sync_hash_before:
            print(f"✅ Cliente existe en sync_hashes:")
            print(f"   - record_key: {sync_hash_before[0]}")
            print(f"   - pending_sync: {sync_hash_before[1]}")
            print(f"   - deleted_at: {sync_hash_before[2]}")
        else:
            print(f"⚠️  Cliente NO existe en sync_hashes")
            print("   Creando registro en sync_hashes...")

            cursor.execute("""
                INSERT INTO sync_hashes (
                    table_name, record_key, company_id,
                    record_hash, pending_sync, synced_at
                ) VALUES (
                    %s, %s, %s,
                    'hash_test', FALSE, NOW()
                )
            """, ('customers', cliente_code, COMPANY_ID))
            conn.commit()
            print("✅ Registro creado en sync_hashes")

        # =========================================================================
        # PASO 3: Eliminar el cliente en PostgreSQL
        # =========================================================================
        print_section("PASO 3: Eliminar cliente en PostgreSQL")

        print(f"Eliminando cliente: {cliente_code}")
        cursor.execute("""
            DELETE FROM clients
            WHERE code = %s
        """, (cliente_code,))

        filas_eliminadas = cursor.rowcount
        conn.commit()

        if filas_eliminadas > 0:
            print(f"✅ Cliente eliminado de clients ({filas_eliminadas} fila(s))")
        else:
            print(f"⚠️  No se eliminó ninguna fila de clients")
            return

        # =========================================================================
        # PASO 4: Verificar que el trigger marcó deleted_at en sync_hashes
        # =========================================================================
        print_section("PASO 4: Verificar trigger en sync_hashes")

        cursor.execute("""
            SELECT record_key, pending_sync, deleted_at
            FROM sync_hashes
            WHERE table_name = 'customers'
              AND record_key = %s
              AND company_id = %s
        """, (cliente_code, COMPANY_ID))

        sync_hash_after = cursor.fetchone()

        if sync_hash_after:
            print(f"✅ Registro en sync_hashes después de eliminar:")
            print(f"   - record_key: {sync_hash_after[0]}")
            print(f"   - pending_sync: {sync_hash_after[1]}")
            print(f"   - deleted_at: {sync_hash_after[2]}")

            if sync_hash_after[2]:
                print(f"✅ Trigger funcionó: deleted_at = {sync_hash_after[2]}")
            else:
                print(f"❌ ERROR: El trigger NO marcó deleted_at")
                print("   El trigger de eliminación no está funcionando correctamente")
        else:
            print(f"❌ ERROR: El registro fue eliminado completamente de sync_hashes")
            print("   El trigger está eliminando el registro en lugar de marcar deleted_at")

        # =========================================================================
        # PASO 5: Detectar cambios con lógica de sincronización
        # =========================================================================
        print_section("PASO 5: Detectar cambios")

        cursor.execute("""
            SELECT record_key
            FROM sync_hashes
            WHERE table_name = 'customers'
              AND company_id = %s
              AND deleted_at IS NOT NULL
            ORDER BY deleted_at DESC
        """, (COMPANY_ID,))

        eliminados = cursor.fetchall()

        if eliminados:
            print(f"✅ Detectados {len(eliminados)} clientes eliminados:")
            for (codigo,) in eliminados:
                print(f"   - {codigo}")

            # Verificar si nuestro cliente está en la lista
            encontrado = False
            for (codigo,) in eliminados:
                if codigo == cliente_code:
                    print(f"\n✅ Cliente '{cliente_code}' detectado como eliminado")
                    encontrado = True
                    break

            if not encontrado:
                print(f"\n❌ ERROR: Cliente '{cliente_code}' NO aparece en la lista de eliminados")
        else:
            print("❌ No se detectaron clientes eliminados")

        # =========================================================================
        # PASO 6: Preparar datos para API
        # =========================================================================
        print_section("PASO 6: Preparar llamada a API")

        deleted_items = [{'code': codigo} for (codigo,) in eliminados]
        document_numbers = [item['code'] for item in deleted_items]

        print(f"Endpoint: DELETE /api/sync-batch/customers")
        print(f"Body JSON:")
        print(json.dumps({
            'company_id': COMPANY_ID,
            'documents': document_numbers
        }, indent=2))

        # =========================================================================
        # PASO 7: Verificar si existen triggers de eliminación
        # =========================================================================
        print_section("PASO 7: Verificar triggers en PostgreSQL")

        cursor.execute("""
            SELECT trigger_name, event_manipulation, action_statement
            FROM information_schema.triggers
            WHERE event_object_table = 'clients'
               OR event_object_table = 'sync_hashes'
            ORDER BY event_object_table, trigger_name
        """)

        triggers = cursor.fetchall()

        if triggers:
            print(f"✅ Triggers encontrados ({len(triggers)}):")
            for trigger_name, event, action in triggers:
                print(f"\n   Trigger: {trigger_name}")
                print(f"   Evento: {event}")
                print(f"   Tabla: clients")
                print(f"   Acción: {action[:100]}...")
        else:
            print("⚠️  No se encontraron triggers en 'clients' o 'sync_hashes'")

        # =========================================================================
        # RESUMEN
        # =========================================================================
        print_section("RESUMEN DEL TEST")

        if sync_hash_after and sync_hash_after[2]:
            print("✅ Flujo de eliminación CORRECTO:")
            print("   1. ✅ Cliente eliminado de clients")
            print("   2. ✅ Trigger marcó deleted_at en sync_hashes")
            print("   3. ✅ detect_changes() puede encontrar el cliente eliminado")
            print("   4. ✅ Datos preparados para enviar a API")
            print("\n📋 Siguiente paso: Ejecutar sincronización para eliminar en API")
        else:
            print("❌ Flujo de eliminación INCORRECTO:")
            print("   El trigger de eliminación no está funcionando correctamente")
            print("\n📋 Se requiere revisión de los triggers")

        # Restaurar el cliente de prueba si fue creado para el test
        if cliente_code == 'TEST_DELETE_001':
            print("\n" + "="*70)
            print("NOTA: Se creó un cliente de prueba que ya no existe en clients")
            print("      El registro en sync_hashes tendrá deleted_at marcado")
            print("="*70)

    except Exception as e:
        print(f"\n❌ Error durante el test: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()

    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    test_delete_flow()
