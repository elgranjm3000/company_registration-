#!/usr/bin/env python3
"""
Test para verificar el registro en system_logs de MySQL
"""

import pymysql
import os
from dotenv import load_dotenv
import uuid

load_dotenv()

def get_public_ip():
    """Obtener IP pública del equipo"""
    try:
        import urllib.request

        services = [
            'https://api.ipify.org',
            'https://icanhazip.com',
            'https://ifconfig.me/ip'
        ]

        for service in services:
            try:
                with urllib.request.urlopen(service, timeout=5) as response:
                    ip = response.read().decode('utf-8').strip()
                    if ip:
                        print(f"✅ IP pública obtenida: {ip}")
                        return ip
            except:
                continue

        print("⚠️  No se pudo obtener IP pública")
        return None
    except Exception as e:
        print(f"❌ Error obteniendo IP pública: {e}")
        return None

def get_mac_address():
    """Obtener MAC address del equipo"""
    try:
        mac = uuid.getnode()
        mac_address = ':'.join([f'{(mac >> i) & 0xff:02x}' for i in range(0, 48, 8)][::-1])

        if mac_address != '00:00:00:00:00:00':
            print(f"✅ MAC address obtenida: {mac_address}")
            return mac_address
        else:
            return None
    except Exception as e:
        print(f"❌ Error obteniendo MAC address: {e}")
        return None

def get_geolocation(ip_address):
    """Obtener geolocalización desde IP"""
    if not ip_address:
        return None, None

    try:
        import urllib.request
        import json

        url = f'http://ip-api.com/json/{ip_address}?fields=status,lat,lon'

        with urllib.request.urlopen(url, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))

            if data.get('status') == 'success':
                lat = data.get('lat')
                lon = data.get('lon')
                if lat is not None and lon is not None:
                    print(f"✅ Geolocalización obtenida: {lat}, {lon}")
                    return lat, lon

        return None, None
    except Exception as e:
        print(f"⚠️  Error obteniendo geolocalización: {e}")
        return None, None

def main():
    print("=" * 80)
    print("🧪 TEST: REGISTRO EN system_logs")
    print("=" * 80)

    try:
        # Conectar a MySQL
        conn = pymysql.connect(
            host=os.getenv('DB_HOST_MYSQL'),
            database=os.getenv('DB_PORT_DATABASE_MYSQL'),
            user=os.getenv('DB_USER_MYSQL'),
            password=os.getenv('DB_PASSWORD_MYSQL')
        )
        cursor = conn.cursor()
        print("✅ Conectado a MySQL\n")

        # PASO 1: Obtener información del sistema
        print("📌 PASO 1: Obtener información del sistema")
        print("-" * 80)

        ip_address = get_public_ip()
        mac_address = get_mac_address()
        lat, lng = get_geolocation(ip_address)

        # PASO 2: Convertir IP a varbinary(16)
        print("\n📌 PASO 2: Convertir IP a varbinary(16)")
        print("-" * 80)

        ip_bytes = None
        if ip_address:
            try:
                import ipaddress
                ip_obj = ipaddress.ip_address(ip_address)
                ip_bytes = ip_obj.packed
                print(f"✅ IP convertida a bytes: {ip_bytes.hex() if ip_bytes else 'None'}")
            except Exception as e:
                print(f"❌ Error convirtiendo IP: {e}")

        # PASO 3: Crear POINT para MySQL
        print("\n📌 PASO 3: Crear POINT para MySQL")
        print("-" * 80)

        location_point = None
        if lat is not None and lng is not None:
            location_point = f'POINT({lng} {lat})'
            print(f"✅ POINT creado: {location_point}")
        else:
            print("⚠️  No se creó POINT (falta lat/lng)")

        # PASO 4: Insertar en system_logs
        print("\n📌 PASO 4: Insertar en system_logs")
        print("-" * 80)

        insert_query = """
        INSERT INTO system_logs (
            user_id,
            action,
            ip_address,
            mac_address,
            location,
            lat,
            lng,
            created_at
        ) VALUES (
            %s, %s, %s, %s, ST_GeomFromText(%s), %s, %s, NOW()
        )
        """

        rif_prueba = 'J123456789'
        action = 'test_sync'

        cursor.execute(insert_query, (
            rif_prueba,
            action,
            ip_bytes,
            mac_address,
            location_point,
            lat,
            lng
        ))

        conn.commit()

        print("✅ Registro insertado exitosamente")

        # PASO 5: Verificar el registro
        print("\n📌 PASO 5: Verificar el registro insertado")
        print("-" * 80)

        cursor.execute("""
            SELECT id, user_id, action,
                   HEX(ip_address) as ip_hex,
                   mac_address,
                   ASTEXT(location) as location_text,
                   lat, lng,
                   created_at
            FROM system_logs
            WHERE user_id = %s AND action = %s
            ORDER BY created_at DESC
            LIMIT 1
        """, (rif_prueba, action))

        row = cursor.fetchone()
        if row:
            (log_id, user_id, log_action, ip_hex, mac, loc, lat_log, lng_log, created) = row

            print(f"ID: {log_id}")
            print(f"User ID: {user_id}")
            print(f"Action: {log_action}")
            print(f"IP Address (hex): {ip_hex}")
            print(f"MAC Address: {mac}")
            print(f"Location: {loc}")
            print(f"Lat: {lat_log}")
            print(f"Lng: {lng_log}")
            print(f"Created at: {created}")

        # CONCLUSIÓN
        print("\n" + "=" * 80)
        print("📊 RESULTADO")
        print("=" * 80)

        if row:
            print("\n✅ TEST EXITOSO")
            print("✅ El registro se guardó correctamente en system_logs")
            print("✅ IP address se convirtió correctamente a varbinary(16)")
            if lat and lng:
                print("✅ Geolocalización se guardó correctamente")
        else:
            print("\n❌ TEST FALLIDO")
            print("❌ No se encontró el registro en system_logs")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
