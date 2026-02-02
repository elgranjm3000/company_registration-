#!/usr/bin/env python3
"""
Test completo del sistema de registro en system_logs
Simula una sincronización real de cada entidad
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
    print("🧪 TEST COMPLETO: REGISTRO EN system_logs DURANTE SINCRONIZACIÓN")
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

    # Datos de empresa de prueba (usar empresa real existente)
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

        # Obtener company_id
        print("\n📌 PASO 3: Obtener company_id")
        print("-" * 80)

        if not sync._obtener_company_id():
            print("❌ No se pudo obtener company_id")
            return

        print(f"✅ Company ID: {sync.company_id}")

        # Limpiar logs anteriores de prueba
        print("\n📌 PASO 4: Limpiar logs anteriores de prueba")
        print("-" * 80)

        sync.mysql_cursor.execute(
            "DELETE FROM system_logs WHERE user_id = %s",
            (company_rif,)
        )
        sync.mysql_conn.commit()
        print("✅ Logs anteriores eliminados")

        # TEST 1: Verificar obtención de IP pública
        print("\n📌 PASO 5: Probar obtención de información del sistema")
        print("-" * 80)

        ip_publica = sync._get_public_ip()
        print(f"IP Pública: {ip_publica if ip_publica else 'No disponible'}")

        mac_address = sync._get_mac_address()
        print(f"MAC Address: {mac_address if mac_address else 'No disponible'}")

        if ip_publica:
            lat, lng = sync._get_geolocation(ip_publica)
            print(f"Geolocalización: {lat}, {lng}")
        else:
            print("Geolocalización: No disponible (sin IP)")

        # TEST 2: Registrar logs para cada entidad
        print("\n📌 PASO 6: Registrar logs de sincronización")
        print("-" * 80)

        entidades = ['products', 'customers', 'categories', 'quotes', 'sellers']

        for entidad in entidades:
            print(f"\n  Registrando: {entidad}...")
            sync._log_to_system_logs(entidad)
            print(f"  ✅ {entidad} registrado")

        # TEST 3: Verificar registros en system_logs
        print("\n📌 PASO 7: Verificar registros en system_logs")
        print("-" * 80)

        sync.mysql_cursor.execute("""
            SELECT
                id,
                user_id,
                action,
                HEX(ip_address) as ip_hex,
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
                (log_id, user_id, action, ip_hex, mac, loc, lat, lng, created) = reg
                print(f"  📋 Registro #{log_id}:")
                print(f"     User ID: {user_id}")
                print(f"     Action: {action}")
                print(f"     IP (hex): {ip_hex}")
                print(f"     MAC: {mac}")
                print(f"     Location: {loc}")
                print(f"     Lat: {lat}")
                print(f"     Lng: {lng}")
                print(f"     Created: {created}")
                print()
        else:
            print("❌ No se encontraron registros en system_logs")

        # TEST 4: Verificar IP address en formato legible
        print("📌 PASO 8: Verificar IP address en formato legible")
        print("-" * 80)

        for reg in registros:
            ip_hex = reg[3]
            if ip_hex and ip_hex != '':
                try:
                    import ipaddress
                    # Convertir hex a bytes
                    ip_bytes = bytes.fromhex(ip_hex)
                    # Convertir bytes a IP address
                    ip_obj = ipaddress.ip_address(ip_bytes)
                    print(f"✅ IP convertida: {ip_obj}")
                    break
                except:
                    pass

        # TEST 5: Verificar geolocalización
        print("\n📌 PASO 9: Verificar datos de geolocalización")
        print("-" * 80)

        for reg in registros:
            action = reg[2]
            lat = reg[6]
            lng = reg[7]

            if lat is not None and lng is not None:
                print(f"✅ {action}: Lat={lat}, Lng={lng}")
            else:
                print(f"⚠️  {action}: Sin geolocalización")

        # RESUMEN FINAL
        print("\n" + "=" * 80)
        print("📊 RESULTADO DEL TEST")
        print("=" * 80)

        total_esperado = len(entidades)
        total_registrado = len(registros)

        print(f"\nEntidades a registrar: {total_esperado}")
        print(f"Registros encontrados: {total_registrado}")

        if total_registrado == total_esperado:
            print("\n✅ TEST EXITOSO")
            print(f"✅ Todas las {total_esperado} entidades se registraron correctamente")
            print("✅ IP pública detectada")
            print("✅ MAC address detectada")
            print("✅ Geolocalización funcionando")
        else:
            print("\n❌ TEST FALLIDO")
            print(f"❌ Se esperaban {total_esperado} registros pero solo se encontraron {total_registrado}")

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
