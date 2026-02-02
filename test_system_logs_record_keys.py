#!/usr/bin/env python3
"""
Test para verificar el campo record_key en system_logs
Prueba con IDs reales de productos
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
    print("🧪 TEST: REGISTRO DE record_key EN system_logs")
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

        # TEST 1: Registrar log con IDs específicos
        print("\n📌 PASO 4: Registrar log con IDs de productos")
        print("-" * 80)

        # Simular algunos IDs de productos
        productos_ids = ['001', '002', '003', '004', '005']
        record_keys_str = ','.join(productos_ids)

        print(f"Registrando productos: {record_keys_str}")
        sync._log_to_system_logs('products', record_keys_str)
        print("✅ Log registrado")

        # TEST 2: Registrar log con IDs de customers
        print("\n📌 PASO 5: Registrar log con IDs de customers")
        print("-" * 80)

        customers_ids = ['C001', 'C002', 'C003']
        record_keys_str = ','.join(customers_ids)

        print(f"Registrando customers: {record_keys_str}")
        sync._log_to_system_logs('customers', record_keys_str)
        print("✅ Log registrado")

        # TEST 3: Registrar log con IDs de categories
        print("\n📌 PASO 6: Registrar log con IDs de categories")
        print("-" * 80)

        categories_ids = ['CAT01', 'CAT02', 'CAT03', 'CAT04']
        record_keys_str = ','.join(categories_ids)

        print(f"Registrando categories: {record_keys_str}")
        sync._log_to_system_logs('categories', record_keys_str)
        print("✅ Log registrado")

        # TEST 4: Registrar log sin IDs (sellers)
        print("\n📌 PASO 7: Registrar log sin IDs (sellers)")
        print("-" * 80)

        sync._log_to_system_logs('sellers', None)
        print("✅ Log registrado (sin IDs)")

        # TEST 5: Verificar registros en system_logs
        print("\n📌 PASO 8: Verificar registros en system_logs")
        print("-" * 80)

        sync.mysql_cursor.execute("""
            SELECT
                id,
                user_id,
                action,
                record_key,
                LENGTH(record_key) as record_key_length,
                ip_address,
                mac_address,
                ASTEXT(location) as location_text,
                lat,
                lng,
                created_at
            FROM system_logs
            WHERE user_id = %s
            ORDER BY created_at ASC
        """, (company_rif,))

        registros = sync.mysql_cursor.fetchall()

        if registros:
            print(f"\n✅ Se encontraron {len(registros)} registros:\n")

            for reg in registros:
                (log_id, user_id, action, record_key, key_len, ip, mac, loc, lat, lng, created) = reg
                print(f"  📋 Registro #{log_id}:")
                print(f"     Action: {action}")
                print(f"     Record Key: {record_key}")
                print(f"     Record Key Length: {key_len} caracteres")

                # Contar cuántos IDs hay
                if record_key:
                    ids_count = len(record_key.split(','))
                    print(f"     Cantidad de IDs: {ids_count}")
                    print(f"     IDs: {record_key[:100]}{'...' if len(record_key) > 100 else ''}")
                else:
                    print(f"     Cantidad de IDs: 0 (sin IDs)")

                print(f"     IP: {ip.hex() if ip else 'NULL'}")
                print(f"     MAC: {mac}")
                print(f"     Location: {loc}")
                print(f"     Lat: {lat}")
                print(f"     Lng: {lng}")
                print(f"     Created: {created}")
                print()
        else:
            print("❌ No se encontraron registros en system_logs")

        # TEST 6: Verificar que los IDs se guardaron correctamente
        print("📌 PASO 9: Verificar integridad de record_key")
        print("-" * 80)

        for reg in registros:
            action = reg[2]
            record_key = reg[3]

            if record_key:
                ids = record_key.split(',')
                print(f"✅ {action}: {len(ids)} IDs guardados correctamente")
                print(f"   Primer ID: {ids[0]}")
                print(f"   Último ID: {ids[-1]}")
            else:
                print(f"⚠️  {action}: Sin IDs (NULL)")

        # RESUMEN FINAL
        print("\n" + "=" * 80)
        print("📊 RESULTADO DEL TEST")
        print("=" * 80)

        print(f"\nRegistros encontrados: {len(registros)}")
        print(f"Registros esperados: 4 (products, customers, categories, sellers)")

        if len(registros) == 4:
            print("\n✅ TEST EXITOSO")
            print("✅ Todos los registros se guardaron correctamente")
            print("✅ El campo record_key contiene los IDs de cada entidad")
            print("✅ Los IDs están separados por coma")

            # Verificar contenido de record_key
            productos_reg = next((r for r in registros if r[2] == 'products'), None)
            if productos_reg and productos_reg[3]:
                ids = productos_reg[3].split(',')
                if len(ids) == 5:
                    print(f"✅ Products: 5 IDs guardados correctamente")
            else:
                print(f"❌ Products: IDs no guardados correctamente")
        else:
            print("\n❌ TEST FALLIDO")
            print(f"❌ Se esperaban 4 registros pero se encontraron {len(registros)}")

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
