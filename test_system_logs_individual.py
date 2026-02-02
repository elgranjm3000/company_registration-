#!/usr/bin/env python3
"""
Test para verificar que se crea UN REGISTRO POR CADA ID en system_logs
"""

import sys
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Importar el módulo de sincronización
from smart_sync_complete import SmartSyncComplete

def main():
    print("=" * 80)
    print("🧪 TEST: UN REGISTRO POR CADA ID EN system_logs")
    print("=" * 80)

    # Configuración PostgreSQL
    postgresql_config = {
        'host': os.getenv('DB_HOST'),
        'port': 5432,
        'database': os.getenv('DB_DATABASE'),
        'user': os.getenv('DB_USER'),
        'password': os.getenv('DB_PASSWORD')
    }

    # Configuración MySQL
    mysql_config = {
        'host': os.getenv('DB_HOST_MYSQL'),
        'port': 3306,
        'database': os.getenv('DB_PORT_DATABASE_MYSQL'),
        'user': os.getenv('DB_USER_MYSQL'),
        'password': os.getenv('DB_PASSWORD_MYSQL')
    }

    # Datos de empresa real existente
    company_rif = 'J316277860'
    company_email = '@'
    company_name = 'Empresa Test'

    try:
        # Crear instancia de SmartSyncComplete
        print("\n📌 PASO 1: Crear instancia de SmartSyncComplete")
        print("-" * 80)

        sync = SmartSyncComplete(
            app=None,
            postgresql_config=postgresql_config,
            mysql_config=mysql_config,
            company_rif=company_rif,
            company_email=company_email,
            company_name=company_name
        )

        print("✅ Instancia creada")

        # Conectar a las bases de datos
        print("\n📌 PASO 2: Conectar a bases de datos")
        print("-" * 80)

        if not sync._conectar_bases_datos():
            print("❌ Error conectando a bases de datos")
            return

        if not sync._obtener_company_id():
            print("❌ No se pudo obtener company_id")
            return

        print(f"✅ Company ID: {sync.company_id}")

        # Limpiar logs anteriores de prueba
        print("\n📌 PASO 3: Limpiar logs anteriores de prueba")
        print("-" * 80)

        sync.mysql_cursor.execute(
            "DELETE FROM system_logs WHERE user_id = %s",
            (company_rif,)
        )
        sync.mysql_conn.commit()
        print("✅ Logs anteriores eliminados")

        # TEST: Registrar 5 productos individualmente
        print("\n📌 PASO 4: Registrar 5 productos (5 registros individuales)")
        print("-" * 80)

        productos_ids = ['001', '002', '003', '004', '005']
        print(f"Productos a registrar: {', '.join(productos_ids)}")

        sync._log_to_system_logs_batch('products', productos_ids)
        print("✅ Productos registrados")

        # TEST: Registrar 3 customers individualmente
        print("\n📌 PASO 5: Registrar 3 customers (3 registros individuales)")
        print("-" * 80)

        customers_ids = ['C001', 'C002', 'C003']
        print(f"Customers a registrar: {', '.join(customers_ids)}")

        sync._log_to_system_logs_batch('customers', customers_ids)
        print("✅ Customers registrados")

        # TEST: Registrar sellers (1 registro vacío)
        print("\n📌 PASO 6: Registrar sellers (1 registro sin ID)")
        print("-" * 80)

        sync._log_to_system_logs_batch('sellers', [])
        print("✅ Sellers registrado")

        # Verificar registros
        print("\n📌 PASO 7: Verificar registros en system_logs")
        print("-" * 80)

        sync.mysql_cursor.execute("""
            SELECT
                id,
                user_id,
                action,
                record_key,
                ip_address,
                mac_address,
                ASTEXT(location) as location_text,
                created_at
            FROM system_logs
            WHERE user_id = %s
            ORDER BY created_at ASC
        """, (company_rif,))

        registros = sync.mysql_cursor.fetchall()

        if registros:
            print(f"\n✅ Se encontraron {len(registros)} registros:\n")

            # Agrupar por acción
            por_accion = {}
            for reg in registros:
                action = reg[2]
                if action not in por_accion:
                    por_accion[action] = []
                por_accion[action].append(reg)

            for action, regs in por_accion.items():
                print(f"  📦 {action.upper()}: {len(regs)} registro(s)")
                for reg in regs:
                    (log_id, user_id, accion, record_key, ip, mac, loc, created) = reg
                    print(f"     - ID #{log_id}: record_key='{record_key}'")
                print()
        else:
            print("❌ No se encontraron registros en system_logs")

        # Verificar conteo
        print("📌 PASO 8: Verificar conteo de registros")
        print("-" * 80)

        sync.mysql_cursor.execute("""
            SELECT action, COUNT(*) as total
            FROM system_logs
            WHERE user_id = %s
            GROUP BY action
            ORDER BY action
        """, (company_rif,))

        conteos = sync.mysql_cursor.fetchall()

        print("\nRegistros por acción:")
        total_registros = 0
        for accion, cantidad in conteos:
            print(f"  {accion}: {cantidad} registro(s)")
            total_registros += cantidad

        print(f"\n  TOTAL: {total_registros} registro(s)")

        # Verificar que cada producto tenga su propio registro
        print("\n📌 PASO 9: Verificar productos individuales")
        print("-" * 80)

        for prod_id in productos_ids:
            sync.mysql_cursor.execute("""
                SELECT id, record_key, created_at
                FROM system_logs
                WHERE user_id = %s AND action = 'products' AND record_key = %s
            """, (company_rif, prod_id))

            reg = sync.mysql_cursor.fetchone()
            if reg:
                print(f"  ✅ Producto {prod_id}: Registro #{reg[0]} encontrado")
            else:
                print(f"  ❌ Producto {prod_id}: NO encontrado")

        # RESUMEN FINAL
        print("\n" + "=" * 80)
        print("📊 RESULTADO DEL TEST")
        print("=" * 80)

        esperado = len(productos_ids) + len(customers_ids) + 1  # +1 por sellers
        print(f"\nRegistros esperados: {esperado}")
        print(f"  - Products: {len(productos_ids)}")
        print(f"  - Customers: {len(customers_ids)}")
        print(f"  - Sellers: 1 (vacío)")
        print(f"\nRegistros encontrados: {total_registros}")

        if total_registros == esperado:
            print("\n✅ TEST EXITOSO")
            print("✅ Se creó UN REGISTRO POR CADA ID")
            print("✅ Cada producto tiene su propio registro")
            print("✅ Cada customer tiene su propio registro")
            print("✅ Sellers tiene un registro vacío")
        else:
            print("\n❌ TEST FALLIDO")
            print(f"❌ Se esperaban {esperado} registros pero se encontraron {total_registros}")

        # Cerrar conexiones
        sync.pg_cursor.close()
        sync.pg_conn.close()
        sync.mysql_cursor.close()
        sync.mysql_conn.close()

        print("\n✅ Conexiones cerradas")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
